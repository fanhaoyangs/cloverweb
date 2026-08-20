/**
 * 图片增强：裁剪（UEditorPlus 增强，独立插件，不侵入核心缩放逻辑）
 *
 * 说明：
 * - 4 个角手柄：等比缩放（核心逻辑已在 ueditor.all.js 的 updateContainerStyle 中改为按原图宽高比缩放）
 * - 4 条边中点手柄 / 工具栏「裁剪」按钮：打开裁剪对话框
 *   在裁剪框内拖动移动选区、拖 4 角调整大小；确认后用 canvas 裁切，
 *   上传 COS 后替换原图 src（持久化，前台渲染与编辑器内一致）。
 *
 * 由 UEditor.vue 在编辑器 ready 后调用 window.__CLOVER_IMG_CROP__(editor) 挂载。
 */
(function () {
  var currentEditor = null
  var currentImg = null
  var overlay = null
  var viewport = null
  var imgEl = null
  var selEl = null
  var handles = []
  var S = 1            // 显示缩放比 = 显示宽 / 原图宽
  var natural = { w: 0, h: 0 }
  var sel = { x: 0, y: 0, w: 0, h: 0 }
  var mode = null      // 'move' | 'resize' | 'new'
  var resizeDir = ''
  var dragStart = { x: 0, y: 0, selX: 0, selY: 0, selW: 0, selH: 0 }

  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)) }

  function injectStyle() {
    if (document.getElementById('clover-crop-style')) return
    var s = document.createElement('style')
    s.id = 'clover-crop-style'
    s.textContent = [
      '.clover-crop-overlay{position:fixed;inset:0;z-index:100000;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center}',
      '.clover-crop-box{background:#fff;border-radius:8px;box-shadow:0 8px 30px rgba(0,0,0,.3);width:auto;max-width:90vw;display:flex;flex-direction:column;overflow:hidden}',
      '.clover-crop-head{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #ebeef5;font-size:15px;font-weight:600;color:#333}',
      '.clover-crop-close{cursor:pointer;color:#909399;font-size:20px;line-height:1}',
      '.clover-crop-close:hover{color:#333}',
      '.clover-crop-body{padding:16px}',
      '.clover-crop-viewport{position:relative;background:#f5f7fa;overflow:hidden;user-select:none;cursor:crosshair;max-width:100%}',
      '.clover-crop-img{display:block;max-width:100%;max-height:70vh;pointer-events:none}',
      '.clover-crop-sel{position:absolute;border:1px solid #3370ff;box-shadow:0 0 0 9999px rgba(0,0,0,.45);cursor:move;box-sizing:border-box}',
      '.clover-crop-hand{position:absolute;width:10px;height:10px;background:#3370ff;border:1px solid #fff;box-sizing:border-box}',
      '.clover-crop-h-nw{left:-5px;top:-5px;cursor:nw-resize}',
      '.clover-crop-h-ne{right:-5px;top:-5px;cursor:ne-resize}',
      '.clover-crop-h-sw{left:-5px;bottom:-5px;cursor:sw-resize}',
      '.clover-crop-h-se{right:-5px;bottom:-5px;cursor:se-resize}',
      '.clover-crop-tip{color:#909399;font-size:12px;margin-top:10px}',
      '.clover-crop-foot{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-top:1px solid #ebeef5}',
      '.clover-crop-info{font-size:12px;color:#606266}',
      '.clover-crop-btn{border:1px solid #dcdfe6;border-radius:4px;padding:6px 16px;cursor:pointer;font-size:13px;background:#fff;color:#333;margin-left:8px}',
      '.clover-crop-btn:hover{background:#f5f7fa}',
      '.clover-crop-btn.clover-crop-ok{background:#3370ff;border-color:#3370ff;color:#fff}',
      '.clover-crop-btn.clover-crop-ok:hover{background:#2a5fd6}',
      // 「裁剪」按钮（注入到 imagescale resizer）
      '.clover-crop-btn-img{position:absolute;right:4px;bottom:4px;z-index:10;background:#3370ff;color:#fff;border:none;border-radius:3px;font-size:12px;padding:2px 8px;cursor:pointer}',
      '.clover-crop-btn-img:hover{background:#2a5fd6}'
    ].join('\n')
    document.head.appendChild(s)
  }

  // ---------- 裁剪对话框 ----------
  function buildDialog() {
    overlay = document.createElement('div')
    overlay.className = 'clover-crop-overlay'
    overlay.innerHTML =
      '<div class="clover-crop-box">' +
        '<div class="clover-crop-head"><span>图片裁剪</span><span class="clover-crop-close">×</span></div>' +
        '<div class="clover-crop-body">' +
          '<div class="clover-crop-viewport">' +
            '<img class="clover-crop-img" crossorigin="anonymous" alt="" />' +
            '<div class="clover-crop-sel"><span class="clover-crop-hand clover-crop-h-nw"></span>' +
              '<span class="clover-crop-hand clover-crop-h-ne"></span>' +
              '<span class="clover-crop-hand clover-crop-h-sw"></span>' +
              '<span class="clover-crop-hand clover-crop-h-se"></span></div>' +
          '</div>' +
          '<div class="clover-crop-tip">拖动选区移动，拖四角调整大小；裁剪后替换原图</div>' +
        '</div>' +
        '<div class="clover-crop-foot">' +
          '<span class="clover-crop-info"></span>' +
          '<div><button class="clover-crop-btn clover-crop-cancel">取消</button>' +
          '<button class="clover-crop-btn clover-crop-ok">确认裁剪</button></div>' +
        '</div>' +
      '</div>'
    document.body.appendChild(overlay)

    viewport = overlay.querySelector('.clover-crop-viewport')
    imgEl = overlay.querySelector('.clover-crop-img')
    selEl = overlay.querySelector('.clover-crop-sel')
    handles = overlay.querySelectorAll('.clover-crop-hand')

    overlay.querySelector('.clover-crop-close').addEventListener('click', closeDialog)
    overlay.querySelector('.clover-crop-cancel').addEventListener('click', closeDialog)
    overlay.querySelector('.clover-crop-ok').addEventListener('click', doCrop)

    bindSelectionEvents()
  }

  function bindSelectionEvents() {
    // 在空白处新建选区
    viewport.addEventListener('mousedown', function (e) {
      if (e.target === imgEl || e.target === viewport) {
        startNewSel(e)
      }
    })
    // 拖选区移动
    selEl.addEventListener('mousedown', function (e) {
      if (e.target === selEl) startMove(e)
    })
    // 拖四角调整
    handles.forEach(function (h) {
      h.addEventListener('mousedown', function (e) {
        e.stopPropagation()
        startResize(e, h.className.slice(-2))
      })
    })
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  function startNewSel(e) {
    mode = 'new'
    var r = viewport.getBoundingClientRect()
    dragStart.x = e.clientX - r.left
    dragStart.y = e.clientY - r.top
    sel.x = dragStart.x; sel.y = dragStart.y; sel.w = 0; sel.h = 0
    renderSel()
  }

  function startMove(e) {
    e.preventDefault()
    mode = 'move'
    dragStart.x = e.clientX; dragStart.y = e.clientY
    dragStart.selX = sel.x; dragStart.selY = sel.y
  }

  function startResize(e, dir) {
    e.preventDefault()
    mode = 'resize'
    resizeDir = dir
    dragStart.x = e.clientX; dragStart.y = e.clientY
    dragStart.selX = sel.x; dragStart.selY = sel.y
    dragStart.selW = sel.w; dragStart.selH = sel.h
  }

  function onMove(e) {
    if (!mode) return
    var vw = viewport.clientWidth, vh = viewport.clientHeight
    var dx = e.clientX - dragStart.x
    var dy = e.clientY - dragStart.y
    if (mode === 'move') {
      sel.x = clamp(dragStart.selX + dx, 0, vw - sel.w)
      sel.y = clamp(dragStart.selY + dy, 0, vh - sel.h)
    } else if (mode === 'resize') {
      var nx = dragStart.selX, ny = dragStart.selY, nw = dragStart.selW, nh = dragStart.selH
      if (resizeDir.indexOf('w') !== -1) { nw = dragStart.selW - dx; nx = dragStart.selX + dx }
      if (resizeDir.indexOf('e') !== -1) { nw = dragStart.selW + dx }
      if (resizeDir.indexOf('n') !== -1) { nh = dragStart.selH - dy; ny = dragStart.selY + dy }
      if (resizeDir.indexOf('s') !== -1) { nh = dragStart.selH + dy }
      if (nw < 10) { if (resizeDir.indexOf('w') !== -1) { nw = 10; nx = dragStart.selX + dragStart.selW - 10 } else nw = 10 }
      if (nh < 10) { if (resizeDir.indexOf('n') !== -1) { nh = 10; ny = dragStart.selY + dragStart.selH - 10 } else nh = 10 }
      sel.x = clamp(nx, 0, vw); sel.y = clamp(ny, 0, vh)
      sel.w = clamp(nw, 10, vw - sel.x); sel.h = clamp(nh, 10, vh - sel.y)
    } else if (mode === 'new') {
      sel.x = clamp(Math.min(dragStart.x, dragStart.x + dx), 0, vw)
      sel.y = clamp(Math.min(dragStart.y, dragStart.y + dy), 0, vh)
      sel.w = clamp(Math.abs(dx), 10, vw - sel.x)
      sel.h = clamp(Math.abs(dy), 10, vh - sel.y)
    }
    renderSel()
  }

  function onUp() {
    if (mode === 'new' && sel.w < 10) { sel.w = 10; sel.h = 10; renderSel() }
    mode = null
  }

  function renderSel() {
    selEl.style.left = sel.x + 'px'
    selEl.style.top = sel.y + 'px'
    selEl.style.width = sel.w + 'px'
    selEl.style.height = sel.h + 'px'
    var info = overlay.querySelector('.clover-crop-info')
    var cw = Math.round(sel.w / S), ch = Math.round(sel.h / S)
    info.textContent = '裁切尺寸：' + cw + ' × ' + ch + ' px'
  }

  // ---------- 打开 / 关闭 ----------
  function openDialog(editor, img) {
    currentEditor = editor
    currentImg = img
    natural.w = img.naturalWidth || img.width
    natural.h = img.naturalHeight || img.height
    if (!natural.w || !natural.h) { alert('无法获取图片原始尺寸'); return }
    injectStyle()

    buildDialog()
    // 显示等比缩放后的图片（限宽 680、限高 460）
    var availW = Math.min(680, window.innerWidth - 120)
    var availH = 460
    var dispW = natural.w, dispH = natural.h
    if (dispW > availW) { dispH = dispH * availW / dispW; dispW = availW }
    if (dispH > availH) { dispW = dispW * availH / dispH; dispH = availH }
    S = dispW / natural.w
    imgEl.style.width = dispW + 'px'
    imgEl.style.height = dispH + 'px'
    viewport.style.width = dispW + 'px'
    viewport.style.height = dispH + 'px'
    imgEl.src = img.getAttribute('src') || img.src

    // 初始选区 = 整图
    sel = { x: 0, y: 0, w: dispW, h: dispH }
    renderSel()
  }

  function closeDialog() {
    if (overlay) { overlay.remove(); overlay = null }
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    currentEditor = null; currentImg = null
  }

  function doCrop() {
    var sx = sel.x / S, sy = sel.y / S, sw = sel.w / S, sh = sel.h / S
    var cw = Math.round(sw), ch = Math.round(sh)
    var canvas = document.createElement('canvas')
    canvas.width = cw; canvas.height = ch
    var ctx = canvas.getContext('2d')
    var im = new Image()
    im.crossOrigin = 'anonymous'
    im.onload = function () {
      ctx.drawImage(im, sx, sy, sw, sh, 0, 0, cw, ch)
      try {
        canvas.toBlob(function (blob) {
          if (!blob) { alert('图片导出失败'); return }
          uploadCrop(blob, function (url) {
            currentImg.setAttribute('src', url)
            currentImg.setAttribute('data-crop', '1')
            currentEditor.fireEvent('contentchange')
            closeDialog()
          })
        }, 'image/png')
      } catch (err) {
        alert('裁剪失败（浏览器安全限制，可能是图片跨域导致）：' + err.message)
      }
    }
    im.onerror = function () { alert('图片加载失败') }
    im.src = currentImg.getAttribute('src') || currentImg.src
  }

  function uploadCrop(blob, ok) {
    var fd = new FormData()
    fd.append('upfile', blob, 'crop.png')
    fetch('/api/ueditor/?action=uploadimage', { method: 'POST', body: fd })
      .then(function (r) { return r.json() })
      .then(function (d) {
        if (d.state === 'SUCCESS') ok(d.url)
        else alert('上传失败：' + (d.message || '未知错误'))
      })
      .catch(function (e) { alert('上传失败：' + e.message) })
  }

  // ---------- 编辑器挂载 ----------
  function resizerEl(editor) {
    return document.getElementById(editor.ui.id + '_imagescale')
  }

  function injectCropButton(editor) {
    var resizer = resizerEl(editor)
    if (!resizer || resizer.querySelector('.clover-crop-btn-img')) return
    var btn = document.createElement('button')
    btn.type = 'button'
    btn.className = 'clover-crop-btn-img'
    btn.textContent = '裁剪'
    btn.title = '裁剪图片'
    resizer.appendChild(btn)
    btn.addEventListener('mousedown', function (e) { e.preventDefault(); e.stopPropagation() })
    btn.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation()
      var img = getCurrentImg(editor)
      if (img) openDialog(editor, img)
    })
  }

  function getCurrentImg(editor) {
    try {
      var node = editor.selection.getRange().getClosedNode()
      if (node && node.tagName === 'IMG') return node
    } catch (e) {}
    // 兜底：从 imagescale 位置反查图片
    var resizer = resizerEl(editor)
    if (resizer) {
      var r = resizer.getBoundingClientRect()
      var imgs = editor.body ? editor.body.getElementsByTagName('img') : []
      for (var i = 0; i < imgs.length; i++) {
        var b = imgs[i].getBoundingClientRect()
        if (Math.abs(b.left - r.left) < 2 && Math.abs(b.top - r.top) < 2) return imgs[i]
      }
    }
    return null
  }

  window.__CLOVER_IMG_CROP__ = function (editor) {
    if (!editor || editor._cloverCropWired) return
    editor._cloverCropWired = true

    // 图片被选中（imagescale 显示）→ 注入「裁剪」按钮 + 边中点手柄打开裁剪
    editor.addListener('afterscaleshow', function () {
      injectCropButton(editor)
      var resizer = resizerEl(editor)
      if (!resizer) return
      // 四边中点（hand1/3/4/6）：拖拽 → 打开裁剪对话框（替代原缩放）
      ;[1, 3, 4, 6].forEach(function (idx) {
        var h = resizer.querySelector('.edui-editor-imagescale-hand' + idx)
        if (h && !h.getAttribute('data-clover-crop')) {
          h.setAttribute('data-clover-crop', '1')
          h.addEventListener('mousedown', function (e) {
            e.preventDefault(); e.stopPropagation()
            var img = getCurrentImg(editor)
            if (img) openDialog(editor, img)
          })
        }
      })
    })
  }
})()
