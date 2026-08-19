/**
 * 飞书文档导入按钮（UEditorPlus 工具栏，位于秀米按钮旁）
 *
 * 按钮仅作触发器：点击后调用 window.__UE_FEISHU_IMPORT__(editor)，
 * 由 Vue 层（UEditor.vue 注入）打开 Element Plus 导入对话框，
 * 导入完成后通过 editor.execCommand('insertHtml', html) 注入内容。
 */
(function () {
  // 注入按钮图标（20x20，飞书蓝文档样式）
  if (!document.getElementById('feishu-import-btn-style')) {
    var style = document.createElement('style')
    style.id = 'feishu-import-btn-style'
    style.textContent = [
      '.edui-for-feishuimport .edui-icon {',
      '  background-image: url("data:image/svg+xml;charset=utf-8,' +
        encodeURIComponent(
          '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">' +
          '<path fill="#3370ff" d="M11.6 2H5.5A1.5 1.5 0 0 0 4 3.5v13A1.5 1.5 0 0 0 5.5 18h9a1.5 1.5 0 0 0 1.5-1.5V6.4L11.6 2z"/>' +
          '<path fill="#c9d8ff" d="M11.2 3.4l3.4 3.4h-3.4V3.4z"/>' +
          '<path fill="#fff" d="M9.4 15.3l-3.2-2.6 1-1 1.6 1.4V8.8h1.3v4.3l1.6-1.4 1 1z"/>' +
          '</svg>'
        ) + '");',
      '  background-repeat: no-repeat;',
      '  background-position: center;',
      '  background-size: 16px 16px;',
      '}'
    ].join('\n')
    document.head.appendChild(style)
  }

  UE.registerUI('feishuimport', function (editor) {
    var btn = new UE.ui.Button({
      name: 'feishu-import',
      title: '飞书文档导入',
      onclick: function () {
        if (typeof window.__UE_FEISHU_IMPORT__ === 'function') {
          window.__UE_FEISHU_IMPORT__(editor)
        } else {
          console.warn('[UEditor] 飞书导入回调未注册（window.__UE_FEISHU_IMPORT__）')
        }
      }
    })
    return btn
  })
})()
