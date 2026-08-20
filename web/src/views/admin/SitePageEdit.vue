<template>
  <div class="sitepage-edit" ref="workspaceRef">
    <!-- 中间：代码编辑区 -->
    <div class="page-editor" v-loading="loading" :style="editorStyle">
      <template v-if="form">
        <div class="editor-head">
          <el-input v-model="form.title" placeholder="页面标题" class="title-input" />
          <div class="toolbar">
            <el-button size="small" @click="editorRef?.undo()">撤销</el-button>
            <el-button size="small" @click="editorRef?.redo()">重做</el-button>
            <el-divider direction="vertical" />
            <template v-for="snip in SNIPPETS" :key="snip.label">
              <el-button size="small" @click="insertSnippet(snip.html)">{{ snip.label }}</el-button>
            </template>
          </div>
        </div>

        <div class="editor-body">
          <HtmlCodeEditor
            ref="editorRef"
            v-model="form.content_html"
            :height="editorHeight"
          />
        </div>

        <div class="editor-actions">
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button @click="openFront">打开前台新页</el-button>
          <span class="dirty-tip" v-if="dirty">● 有未保存修改</span>
        </div>
      </template>
      <div v-else class="empty">请从左侧「静态页管理」下方选择页面</div>
    </div>

    <!-- 拖动分隔条 -->
    <div class="splitter" title="拖动调整宽度" @mousedown="onSplitterDown"></div>

    <!-- 右侧：实时预览区 -->
    <div class="page-preview" v-if="form">
      <div class="preview-toolbar">
        <span class="preview-title">实时预览</span>
        <el-radio-group v-model="device" size="small">
          <el-radio-button value="desktop">桌面</el-radio-button>
          <el-radio-button value="tablet">平板</el-radio-button>
          <el-radio-button value="mobile">手机</el-radio-button>
        </el-radio-group>
      </div>
      <div class="preview-stage">
        <div class="device-frame" :style="frameStyle">
          <iframe
            class="preview-iframe"
            :srcdoc="previewDoc"
            sandbox="allow-same-origin allow-popups allow-forms"
          ></iframe>
        </div>
      </div>
    </div>
    <div v-else class="preview-empty">选择页面后此处预览</div>
  </div>
</template>

<script setup>
import { ref, computed, watch, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import HtmlCodeEditor from '@/components/code-editor/HtmlCodeEditor.vue'
import { getSitePageAdmin, updateSitePage } from '@/api/admin'
import { sitepageStore } from '@/utils/sitepageStore'

const route = useRoute()

const PAGE_NAMES = { home: '首页', about: '关于我们', philosophy: '理念路径', clover: '四叶草堂' }

// 常用 HTML 代码片段
const SNIPPETS = [
  {
    label: '标题区',
    html: `\n<section class="home-banner">\n  <h1>标题</h1>\n  <p>副标题</p>\n</section>\n`
  },
  {
    label: '段落',
    html: `\n<p>这里是段落文本。</p>\n`
  },
  {
    label: '文章列表容器',
    html: `\n<div class="review-grid">\n  <!-- 文章卡片由前台按 section 注入 -->\n</div>\n`
  }
]

const DEVICE_WIDTHS = { desktop: '100%', tablet: '768px', mobile: '390px' }
const RATIO_KEY = 'sitepage_editor_ratio'

const form = ref(null)
const saved = ref({ title: '', content_html: '' })
const loading = ref(false)
const saving = ref(false)
const editorRef = ref(null)
const device = ref('desktop')

// 当前页面 slug 来自路由 query（CmsLayout 侧边栏驱动）
const current = computed(() => route.query.page || '')

// 与保存快照比对，判断是否有未保存修改（覆盖 title 与内容）
const dirty = computed(() =>
  !!form.value && (form.value.title !== saved.value.title || form.value.content_html !== saved.value.content_html)
)
// 回写共享 store，供 CmsLayout 切换前确认
watchEffect(() => { sitepageStore.dirty = dirty.value })

// 编辑器 / 预览 拖动分隔条
const workspaceRef = ref(null)
const editorRatio = ref(parseFloat(localStorage.getItem(RATIO_KEY)) || 0.5)

function onSplitterDown(e) {
  const workspace = workspaceRef.value
  if (!workspace) return
  const rect = workspace.getBoundingClientRect()
  document.body.style.userSelect = 'none'
  const move = (ev) => {
    const ratio = (ev.clientX - rect.left) / rect.width
    editorRatio.value = Math.min(0.8, Math.max(0.25, ratio))
  }
  const up = () => {
    document.body.style.userSelect = ''
    localStorage.setItem(RATIO_KEY, String(editorRatio.value))
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', up)
  }
  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
  e.preventDefault()
}

const editorStyle = computed(() => ({
  flex: '0 0 auto',
  width: (editorRatio.value * 100) + '%'
}))

const editorHeight = computed(() =>
  Math.max(360, Math.floor((window.innerHeight - 220) * 0.7))
)

const frameStyle = computed(() => ({
  width: DEVICE_WIDTHS[device.value] || '100%',
  maxWidth: '100%'
}))

// 预览文档：content_html 自带 <style>，用薄 HTML 壳包裹即可贴近前台渲染
const previewDoc = computed(() => buildPreviewDoc(form.value?.content_html || ''))

function buildPreviewDoc(htmlContent) {
  return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>预览</title>
</head>
<body style="margin:0;background:#fff;color:#2c3e2c;font-family:-apple-system,BlinkMacSystemFont,'Noto Sans SC',sans-serif;line-height:1.9;">
${htmlContent}
</body>
</html>`
}

function insertSnippet(html) {
  editorRef.value?.insertSnippet(html)
}

async function load(slug) {
  if (!slug) { form.value = null; return }
  loading.value = true
  form.value = null
  try {
    const { data } = await getSitePageAdmin(slug)
    form.value = { title: data.title, content_html: data.content_html }
    saved.value = { title: data.title, content_html: data.content_html }
  } catch {
    ElMessage.error('页面加载失败')
  } finally {
    loading.value = false
  }
}

// 页面由路由 query 驱动，切换即重新加载
watch(() => current.value, (slug) => load(slug), { immediate: true })

async function save() {
  saving.value = true
  try {
    const { data } = await updateSitePage(current.value, form.value)
    ElMessage.success(`「${pageName(current.value)}」已保存`)
    saved.value = { ...form.value }
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function openFront() {
  const path = current.value === 'home' ? '/' : `/${current.value}`
  window.open(path, '_blank')
}

function pageName(slug) {
  return PAGE_NAMES[slug] || slug
}
</script>

<style scoped>
.sitepage-edit {
  display: flex;
  gap: 12px;
  height: calc(100vh - 56px - 48px);
  min-height: 0;
}

/* 中间编辑区 */
.page-editor {
  min-width: 0;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.editor-head {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.title-input {
  max-width: 420px;
}

.toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.editor-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.editor-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.dirty-tip {
  font-size: 12px;
  color: #e6a23c;
}

.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #a0aea0;
}

/* 拖动分隔条 */
.splitter {
  flex: 0 0 6px;
  cursor: col-resize;
  border-radius: 3px;
  background: transparent;
  transition: background 0.2s;
  align-self: stretch;
}
.splitter:hover,
.splitter:active {
  background: #cfe3d0;
}

/* 右侧预览区 */
.page-preview {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid #eef2ee;
}

.preview-title {
  font-size: 13px;
  font-weight: 500;
  color: #2c3e2d;
}

.preview-stage {
  flex: 1;
  overflow: auto;
  background: #eef1ee;
  padding: 16px;
  display: flex;
  justify-content: center;
}

.device-frame {
  transition: width 0.25s ease;
  background: #fff;
  border-radius: 6px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  height: 100%;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
  background: #fff;
}

.preview-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a0aea0;
}
</style>
