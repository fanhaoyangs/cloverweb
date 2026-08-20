<template>
  <div ref="editorContainer" class="ueditor-wrapper"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  config: { type: Object, default: () => ({}) },
  height: { type: Number, default: 500 }
})

const emit = defineEmits(['update:modelValue', 'feishu-import'])

const editorContainer = ref(null)
const editorId = `ueditor-${Date.now()}`
let editor = null

const defaultConfig = {
  UEDITOR_HOME_URL: '/UEditorPlus/',
  UEDITOR_CORS_URL: '/UEditorPlus/',
  serverUrl: '/api/ueditor/',
  autoHeightEnabled: false,
  initialFrameHeight: props.height,
  initialFrameWidth: '100%',
  enableAutoSave: false,
  saveInterval: 5000,
  catchRemoteImageEnable: true,
  catchRemoteImageFormat: ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
  catchRemoteImageTimeout: 30000,
  toolbars: [[
    'fullscreen', 'source', '|', 'undo', 'redo', '|', 'bold', 'italic', 'underline', 'fontborder',
    'strikethrough', '|', 'forecolor', 'backcolor', '|', 'insertorderedlist', 'insertunorderedlist',
    '|', 'justifyleft', 'justifycenter', 'justifyright', 'justifyjustify', '|', 'link', 'unlink', '|',
    'insertimage', 'emotion', 'scrawl', '|', 'insertvideo', 'insertaudio', 'attachment', '|',
    'horizontal', 'date', 'time', 'spechars', '|', 'inserttable', 'deletetable', '|',
    'xiumi', 'feishuimport', '|', 'template', 'background', 'formula', '|', 'print', 'preview'
  ]]
}

window.UEDITOR_CONFIG_IMAGE = {
  imageActionName: 'uploadimage',
  imageFieldName: 'upfile',
  imageMaxSize: 20 * 1024 * 1024,
  imageAllowFiles: ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
  imageCompressEnable: true,
  imageCompressBorder: 1600,
  imageInsertAlign: 'none',
  imageUrlPrefix: '',
  imagePathFormat: 'ueditor/images/{yyyy}{mm}{dd}/{time}{rand:6}',
  imageManagerActionName: 'listimage',
  imageManagerListSize: 20,
  imageManagerInsertAlign: 'none',
  imageManagerUrlPrefix: '',
  catchRemoteImageEnable: true,
  catchRemoteImageFormat: ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
  catchRemoteImageTimeout: 30000
}

let catchImageTimer = null
let isReplacingImages = false
const uploadedImageCache = {}

// 批量转存远程图片（秀米等）到 COS：走 Django /api/ueditor/?action=catchimage
async function transferRemoteImages(urls) {
  const pending = [...urls].filter(u => !uploadedImageCache[u.split('?')[0]])
  if (pending.length === 0) return {}

  const params = new URLSearchParams()
  pending.forEach(u => params.append('source[]', u))

  const res = await fetch('/api/ueditor/?action=catchimage', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
    body: params.toString()
  })
  const data = await res.json()
  if (data.state !== 'SUCCESS') {
    throw new Error(data.message || '远程图片转存失败')
  }

  const urlMap = {}
  data.list.forEach(item => {
    urlMap[item.source] = item.url
    uploadedImageCache[item.source.split('?')[0]] = item.url
  })
  console.log(`[UEditor] 转存成功 ${data.list.length}/${pending.length} 张`)
  return urlMap
}

async function replaceRemoteImages() {
  if (!editor || isReplacingImages) return
  const content = editor.getContent()
  if (!content || !content.includes('xiumi.us')) return

  isReplacingImages = true

  const xiumiUrlPattern = /https?:\/\/img\.xiumi\.us\/xmi\/[^"')\s?]+/g
  const urls = new Set()
  let match
  while ((match = xiumiUrlPattern.exec(content)) !== null) {
    urls.add(match[0])
  }

  const bgUrlPattern = /background-image\s*:\s*url\(\s*["']?(https?:\/\/img\.xiumi\.us\/xmi\/[^"')\s]+)["']?\s*\)/g
  while ((match = bgUrlPattern.exec(content)) !== null) {
    urls.add(match[1])
  }

  const srcUrlPattern = /src\s*=\s*["'](https?:\/\/img\.xiumi\.us\/xmi\/[^"']+)["']/g
  while ((match = srcUrlPattern.exec(content)) !== null) {
    urls.add(match[1])
  }

  if (urls.size === 0) {
    console.log('[UEditor] 内容包含xiumi.us但无图片URL可替换，跳过')
    isReplacingImages = false
    return
  }

  console.log(`[UEditor] 检测到 ${urls.size} 个秀米图片URL，开始替换...`)

  let urlMap = {}
  try {
    urlMap = await transferRemoteImages(urls)
  } catch (error) {
    console.error('[UEditor] 远程图片转存失败:', error)
    isReplacingImages = false
    return
  }

  const processedCount = Object.keys(urlMap).length

  if (processedCount > 0) {
    let newContent = content
    for (const [oldUrl, newUrl] of Object.entries(urlMap)) {
      const escaped = oldUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      newContent = newContent.replace(new RegExp(escaped, 'g'), newUrl)
    }
    editor.setContent(newContent)
    emit('update:modelValue', newContent)
  }

  console.log('[UEditor] 秀米图片替换完成')
  isReplacingImages = false
}

function triggerCatchRemoteImage() {
  if (!editor) return
  const content = editor.getContent()
  if (content && content.includes('xiumi.us')) {
    if (catchImageTimer) clearTimeout(catchImageTimer)
    catchImageTimer = setTimeout(() => {
      replaceRemoteImages()
    }, 1500)
  }
}

const RESIZE_KEY = 'clover_ueditor_height'

function setEditorHeight(ed, h) {
  if (ed.iframe) {
    ed.iframe.style.height = h + 'px'
    if (ed.iframe.parentNode) ed.iframe.parentNode.style.height = h + 'px'
  }
  localStorage.setItem(RESIZE_KEY, String(h))
}

// 底边拖拽调高编辑器
function attachResizeHandle(ed) {
  const dom = ed.ui && ed.ui.getDom()
  if (!dom || dom.querySelector('.clover-ueditor-resize')) return

  // 恢复上次保存的高度
  const saved = parseInt(localStorage.getItem(RESIZE_KEY) || '0', 10)
  if (saved >= 200) setEditorHeight(ed, saved)

  const bar = document.createElement('div')
  bar.className = 'clover-ueditor-resize'
  bar.title = '拖动调整编辑器高度'
  dom.appendChild(bar)

  bar.addEventListener('mousedown', (e) => {
    e.preventDefault()
    const startY = e.clientY
    const holder = ed.iframe && ed.iframe.parentNode
    const startH = holder ? holder.offsetHeight : (ed.iframe ? ed.iframe.offsetHeight : props.height)
    const move = (ev) => {
      const h = Math.max(200, Math.min(1400, startH + (ev.clientY - startY)))
      setEditorHeight(ed, h)
    }
    const up = () => {
      document.removeEventListener('mousemove', move)
      document.removeEventListener('mouseup', up)
      document.body.style.userSelect = ''
    }
    document.body.style.userSelect = 'none'
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', up)
  })
}

function initEditor() {
  if (typeof window.UE === 'undefined') {
    console.error('UEditor未加载')
    return
  }

  editor = window.UE.getEditor(editorId, {
    ...defaultConfig,
    ...props.config,
    imageConfig: {
      disableUpload: false,
      disableOnline: false,
      selectCallback: null
    },
    imageActionName: 'uploadimage',
    imageFieldName: 'upfile',
    imageMaxSize: 20 * 1024 * 1024,
    imageAllowFiles: ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
    imageCompressEnable: true,
    imageCompressBorder: 1600,
    imageInsertAlign: 'none',
    imageUrlPrefix: '',
    imagePathFormat: 'ueditor/images/{yyyy}{mm}{dd}/{time}{rand:6}',
    imageManagerActionName: 'listimage',
    imageManagerListSize: 20,
    imageManagerInsertAlign: 'none',
    imageManagerUrlPrefix: '',
    catchRemoteImageEnable: true,
    catchRemoteImageFormat: ['.png', '.jpg', '.jpeg', '.gif', '.bmp'],
    catchRemoteImageTimeout: 30000
  })

  // 飞书导入按钮桥接：UEditor 工具栏按钮 → Vue 事件（由父组件打开导入对话框）
  window.__UE_FEISHU_IMPORT__ = () => {
    emit('feishu-import')
  }

  editor.addListener('ready', () => {
    console.log('[UEditor] 编辑器就绪')
    if (props.modelValue) {
      editor.setContent(props.modelValue)
    }
    // 挂载图片裁剪插件（图片等比缩放 + 裁剪）
    if (typeof window.__CLOVER_IMG_CROP__ === 'function') {
      window.__CLOVER_IMG_CROP__(editor)
    }
    // 底边拖拽调整编辑器高度
    attachResizeHandle(editor)
  })

  editor.addListener('contentChange', () => {
    if (isReplacingImages) return
    const content = editor.getContent()
    emit('update:modelValue', content)
    if (content && content.includes('xiumi.us')) {
      triggerCatchRemoteImage()
    }
  })
}

function loadUEditor() {
  const xiumiCss = document.createElement('link')
  xiumiCss.rel = 'stylesheet'
  xiumiCss.href = '/UEditorPlus/dialogs/xiumi-connect/xiumi-ue-v5.css'
  document.head.appendChild(xiumiCss)

  const configScript = document.createElement('script')
  configScript.src = '/UEditorPlus/ueditor.config.js'
  configScript.onload = () => {
    const editorScript = document.createElement('script')
    editorScript.src = '/UEditorPlus/ueditor.all.js'
    editorScript.onload = () => {
      const xiumiScript = document.createElement('script')
      xiumiScript.src = '/UEditorPlus/dialogs/xiumi-connect/xiumi-ue-dialog-v5.js'
      xiumiScript.onerror = () => console.error('秀米脚本加载失败')
      xiumiScript.onload = () => {
        // 飞书导入按钮（registerUI，工具栏秀米旁）
        const feishuScript = document.createElement('script')
        feishuScript.src = '/UEditorPlus/dialogs/feishu-connect/feishu-ue-button.js'
        feishuScript.onerror = () => console.error('飞书导入按钮脚本加载失败')
        feishuScript.onload = () => {
          // 图片裁剪插件
          const cropScript = document.createElement('script')
          cropScript.src = '/UEditorPlus/dialogs/image-crop/image-crop.js'
          cropScript.onerror = () => console.error('图片裁剪脚本加载失败')
          cropScript.onload = () => {
            nextTick(() => {
              const scriptTag = document.createElement('script')
              scriptTag.type = 'text/plain'
              scriptTag.id = editorId
              scriptTag.className = 'ueditor-script'
              editorContainer.value.appendChild(scriptTag)
              initEditor()
            })
          }
          document.head.appendChild(cropScript)
        }
        document.head.appendChild(feishuScript)
      }
      document.head.appendChild(xiumiScript)
    }
    document.head.appendChild(editorScript)
  }
  document.head.appendChild(configScript)
}

onMounted(() => {
  loadUEditor()
})

onBeforeUnmount(() => {
  if (catchImageTimer) clearTimeout(catchImageTimer)
  if (window.__UE_FEISHU_IMPORT__) {
    delete window.__UE_FEISHU_IMPORT__
  }
  if (editor) {
    editor.destroy()
    editor = null
  }
})

watch(() => props.modelValue, (newVal) => {
  if (isReplacingImages) return
  if (editor && newVal !== editor.getContent()) {
    editor.setContent(newVal)
  }
})

defineExpose({
  getContent: () => editor ? editor.getContent() : '',
  setContent: (content) => editor && editor.setContent(content),
  getContentTxt: () => editor ? editor.getContentTxt() : '',
  execCommand: (cmd, args) => editor && editor.execCommand(cmd, args),
  getEditor: () => editor,
  triggerCatchRemoteImage: () => triggerCatchRemoteImage()
})
</script>

<style scoped>
.ueditor-wrapper {
  line-height: normal;
}
</style>

<style>
/* 底边拖拽调高手柄（动态注入 UEditor DOM，须全局） */
.clover-ueditor-resize {
  height: 8px;
  cursor: row-resize;
  background: transparent;
  border-radius: 0 0 4px 4px;
  transition: background 0.2s;
}
.clover-ueditor-resize:hover,
.clover-ueditor-resize:active {
  background: #cfe3d0;
}
</style>
