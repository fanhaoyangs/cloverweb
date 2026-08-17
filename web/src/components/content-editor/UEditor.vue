<template>
  <div ref="editorContainer" class="ueditor-wrapper"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import cloudBase from '@/cloud'

const props = defineProps({
  modelValue: { type: String, default: '' },
  config: { type: Object, default: () => ({}) },
  height: { type: Number, default: 500 }
})

const emit = defineEmits(['update:modelValue'])

const editorContainer = ref(null)
const editorId = `ueditor-${Date.now()}`
let editor = null

const defaultConfig = {
  UEDITOR_HOME_URL: '/UEditorPlus/',
  UEDITOR_CORS_URL: '/UEditorPlus/',
  serverUrl: '',
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
    'xiumi', '|', 'template', 'background', 'formula', '|', 'print', 'preview'
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

async function uploadToCos(imageUrl) {
  const cacheKey = imageUrl.split('?')[0]
  if (uploadedImageCache[cacheKey]) {
    console.log('[UEditor] 图片已缓存，跳过上传:', cacheKey)
    return uploadedImageCache[cacheKey]
  }

  try {
    await cloudBase.init()

    const res = await cloudBase.callFunction({
      name: 'getPresignedUrl',
      data: {
        action: 'proxyUploadImage',
        imageUrl: imageUrl
      }
    })

    if (res.result.errCode !== 0) {
      throw new Error(res.result.errMsg || '代理上传失败')
    }

    const fileUrl = res.result.fileUrl
    let processedFileUrl = fileUrl
    if (processedFileUrl && !processedFileUrl.startsWith('http://') && !processedFileUrl.startsWith('https://')) {
      processedFileUrl = `https://${processedFileUrl}`
    }

    uploadedImageCache[cacheKey] = processedFileUrl
    console.log('[UEditor] 代理上传成功:', processedFileUrl)
    return processedFileUrl
  } catch (error) {
    console.error('[UEditor] 代理上传错误:', error)
    return null
  }
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

  const urlMap = {}
  let processedCount = 0
  let i = 0
  for (const url of urls) {
    i++
    console.log(`[UEditor] 正在上传第 ${i} 张图片: ${url}`)
    const newUrl = await uploadToCos(url)
    if (newUrl) {
      urlMap[url] = newUrl
      processedCount++
      console.log(`[UEditor] 第 ${i} 张图片替换成功: ${newUrl}`)
    } else {
      console.error(`[UEditor] 第 ${i} 张图片替换失败`)
    }
  }

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

  editor.addListener('ready', () => {
    console.log('[UEditor] 编辑器就绪')
    if (props.modelValue) {
      editor.setContent(props.modelValue)
    }

    hookEditorActions()
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

function hookEditorActions() {
  if (!editor || !editor.getOpt) return

  editor.getActionUrl = function(actionName) {
    if (actionName === 'uploadimage') {
      return '/api/ueditor/upload'
    }
    if (actionName === 'listimage') {
      return '/api/ueditor/listimage'
    }
    return window.UE.getEditor(editorId).getActionUrl.call(this, actionName)
  }
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
        nextTick(() => {
          const scriptTag = document.createElement('script')
          scriptTag.type = 'text/plain'
          scriptTag.id = editorId
          scriptTag.className = 'ueditor-script'
          editorContainer.value.appendChild(scriptTag)
          initEditor()
        })
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
