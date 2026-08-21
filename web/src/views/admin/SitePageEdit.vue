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
            <el-button size="small" @click="editorRef?.openSearch()">搜索</el-button>
            <el-button size="small" @click="editorRef?.openReplace()">替换</el-button>
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
          <div class="page-meta">
            <el-tag size="small" :type="statusTagType">{{ statusLabel }}</el-tag>
            <el-input
              v-model="form.slug"
              size="small"
              class="meta-slug"
              title="访问地址标识（可修改，英文/数字/连字符）"
            >
              <template #prepend>/</template>
            </el-input>
            <el-input v-model="form.menu_label" placeholder="导航菜单名称" size="small" class="meta-input" clearable />
            <el-switch v-model="form.in_menu" size="small" active-text="入导航" />
            <el-input-number v-model="form.menu_order" :min="0" :max="999" size="small" class="meta-order" />
          </div>
          <div class="action-btns">
            <el-button :loading="saving" @click="save()">保存</el-button>
            <el-button :loading="saving" @click="save('draft')">存草稿</el-button>
            <el-button type="success" :loading="saving" @click="save('published')">发布</el-button>
            <el-button type="danger" plain :loading="saving" @click="removePage">删除</el-button>
            <el-button @click="openFront">打开前台新页</el-button>
            <span class="dirty-tip" v-if="dirty">● 有未保存修改</span>
          </div>
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
            ref="previewIframe"
            class="preview-iframe"
            :srcdoc="previewDoc"
            sandbox="allow-scripts allow-popups allow-forms"
          ></iframe>
        </div>
      </div>
    </div>
    <div v-else class="preview-empty">选择页面后此处预览</div>
  </div>
</template>

<script setup>
import { ref, computed, watch, watchEffect, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import HtmlCodeEditor from '@/components/code-editor/HtmlCodeEditor.vue'
import { getSitePageAdmin, updateSitePage, deleteSitePage, listSitePages } from '@/api/admin'
import { sitepageStore } from '@/utils/sitepageStore'

const route = useRoute()
const router = useRouter()

const STATUS_META = {
  draft: { label: '草稿', tag: 'warning' },
  published: { label: '已发布', tag: 'success' }
}

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
    html: `\n<div data-article-block="板块名" data-card="review" data-limit="8">\n  <!-- 文章卡片由前台注入：data-article-block=板块名，data-card=review/media/publication/case/salon -->\n</div>\n`
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

const statusLabel = computed(() => (form.value ? (STATUS_META[form.value.status]?.label || form.value.status) : ''))
const statusTagType = computed(() => (form.value ? (STATUS_META[form.value.status]?.tag || 'info') : 'info'))
const displayName = computed(() => form.value?.title || form.value?.slug || '')

// 当前页面 slug 来自路由 query（CmsLayout 侧边栏驱动）
const current = computed(() => route.query.page || '')

// 与保存快照比对，判断是否有未保存修改（覆盖全部可编辑字段）
const DIRTY_KEYS = ['slug', 'title', 'content_html', 'status', 'in_menu', 'menu_label', 'menu_order']
const dirty = computed(() =>
  !!form.value && DIRTY_KEYS.some((k) => form.value[k] !== saved.value[k])
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
// 同时注入 data-hx-offset，实现"编辑区↔预览"双向光标联动
// 打字时每键都重算索引+DOMParser+重载 iframe 太重，300ms 防抖后再刷新预览
const previewIframe = ref(null)
const debouncedHtml = ref('')
let previewTimer = 0
watch(
  () => form.value?.content_html,
  (v) => {
    clearTimeout(previewTimer)
    previewTimer = setTimeout(() => { debouncedHtml.value = v || '' }, 300)
  },
  { immediate: true }
)
const htmlIndex = computed(() => buildHtmlIndex(debouncedHtml.value))
const previewDoc = computed(() => buildPreviewDoc(debouncedHtml.value, htmlIndex.value))

// 扫描 HTML：按文档序记录每个开标签在源码中的起始 offset（跳过 void/自闭合标签）
// 注意：style/script 等会被 DOMParser 移到 <head>，为对齐 body 元素计数需一并跳过
function buildHtmlIndex(html) {
  const index = []
  const stack = []
  const VOID_RE = /^(area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)$/i
  const HEAD_RE = /^(style|script|title|base|link|meta)$/i
  const re = /<\s*(\/?)\s*([a-zA-Z][\w-]*)((?:"[^"]*"|'[^']*'|[^"'>])*)\s*\/?\s*>/g
  let m
  while ((m = re.exec(html))) {
    const tag = m[2]
    if (HEAD_RE.test(tag)) continue
    if (m[1]) {
      while (stack.length) {
        const open = stack.pop()
        if (open.tag.toLowerCase() === tag.toLowerCase()) {
          open.end = m.index
          break
        }
      }
    } else if (!VOID_RE.test(tag)) {
      const node = { tag: tag.toLowerCase(), start: m.index, end: -1 }
      stack.push(node)
      index.push(node)
    }
  }
  return index
}

// 由源码 offset 找其所在的最内层元素起始 offset
function findElementByOffset(index, offset) {
  let best = null
  for (const node of index) {
    if (node.start > offset) break
    if (node.end === -1 || offset <= node.end) best = node
  }
  return best ? best.start : null
}

function buildPreviewDoc(htmlContent, index) {
  let bodyHtml = htmlContent
  if (index.length) {
    try {
      const doc = new DOMParser().parseFromString(htmlContent, 'text/html')
      const els = doc.body.querySelectorAll('*')
      if (els.length === index.length) {
        els.forEach((el, i) => el.setAttribute('data-hx-offset', String(index[i].start)))
        bodyHtml = doc.body.innerHTML
      }
    } catch {
      /* 保持原样 */
    }
  }
  return `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>预览</title>
</head>
<body style="margin:0;background:#fff;color:#2c3e2c;font-family:-apple-system,BlinkMacSystemFont,'Noto Sans SC',sans-serif;line-height:1.9;">
${bodyHtml}
<script>
document.addEventListener('click', (e) => {
  let t = e.target
  while (t && t !== document.body) {
    const o = t.getAttribute && t.getAttribute('data-hx-offset')
    if (o !== null && o !== undefined && o !== '') {
      parent.postMessage({ type: 'hx-pick', offset: Number(o) }, '*')
      return
    }
    t = t.parentNode
  }
})
window.addEventListener('message', (e) => {
  if (!e.data || e.data.type !== 'hx-hover') return
  document.querySelectorAll('[data-hx-offset]').forEach((el) => { el.style.outline = '' })
  const el = document.querySelector('[data-hx-offset="' + e.data.offset + '"]')
  if (el) {
    el.style.outline = '2px solid #409eff'
    el.style.outlineOffset = '1px'
    el.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
  }
})
<\/script>
</body>
</html>`
}

// 编辑区光标变化 → 预览中高亮对应元素（rAF 节流，避免高频触发）
let unregisterCursor = null
let hoverRaf = 0

function onEditorCursor(pos) {
  const frame = previewIframe.value
  if (!frame || !htmlIndex.value.length) return
  const start = findElementByOffset(htmlIndex.value, pos)
  if (start === null) return
  frame.contentWindow?.postMessage({ type: 'hx-hover', offset: start }, '*')
}

function onEditorCursorThrottled(pos) {
  if (hoverRaf) return
  hoverRaf = requestAnimationFrame(() => {
    hoverRaf = 0
    onEditorCursor(pos)
  })
}

// 预览点击元素 → 编辑区光标定位到对应代码
function onPreviewMessage(e) {
  const data = e.data
  if (!data || data.type !== 'hx-pick') return
  if (e.source !== previewIframe.value?.contentWindow) return
  editorRef.value?.setCursorOffset(data.offset)
}

onMounted(() => {
  window.addEventListener('message', onPreviewMessage)
})
onBeforeUnmount(() => {
  clearTimeout(previewTimer)
  unregisterCursor && unregisterCursor()
  window.removeEventListener('message', onPreviewMessage)
})

// 编辑器在 v-if="form" 内，挂载晚于本组件且切换页面会重建：
// 不能在 onMounted 注册，需 watch 组件实例就绪后再挂光标监听
watch(editorRef, (inst) => {
  if (unregisterCursor) {
    unregisterCursor()
    unregisterCursor = null
  }
  if (inst) {
    unregisterCursor = inst.onCursorChange(onEditorCursorThrottled)
  }
})

function insertSnippet(html) {
  editorRef.value?.insertSnippet(html)
}

async function load(slug) {
  if (!slug) { form.value = null; return }
  loading.value = true
  form.value = null
  try {
    const { data } = await getSitePageAdmin(slug)
    form.value = {
      slug: data.slug,
      title: data.title,
      content_html: data.content_html,
      status: data.status || 'draft',
      in_menu: !!data.in_menu,
      menu_label: data.menu_label || '',
      menu_order: data.menu_order ?? 0
    }
    saved.value = { ...form.value }
  } catch {
    ElMessage.error('页面加载失败')
  } finally {
    loading.value = false
  }
}

// 页面由路由 query 驱动，切换即重新加载
watch(() => current.value, (slug) => load(slug), { immediate: true })

// 保存：targetStatus 传值则同时切换状态（存草稿/发布）；slug 可改名，保存后同步路由
async function save(targetStatus) {
  if (!form.value) return
  const slug = (form.value.slug || '').trim()
  if (!slug) {
    ElMessage.warning('访问地址不能为空')
    return
  }
  if (!/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i.test(slug)) {
    ElMessage.warning('地址只能用英文、数字和连字符，且不能以连字符开头/结尾')
    return
  }
  form.value.slug = slug
  if (targetStatus) form.value.status = targetStatus
  saving.value = true
  try {
    const { title, content_html, status, in_menu, menu_label, menu_order } = form.value
    await updateSitePage(current.value, { slug, title, content_html, status, in_menu, menu_label, menu_order })
    ElMessage.success(`「${displayName.value}」已保存（${statusLabel.value}）`)
    saved.value = { ...form.value }
    await refreshPages()
    // slug 改名后同步路由与侧边栏选中项
    if (slug !== current.value) {
      router.replace({ path: '/admin/sitepages', query: { page: slug } })
    }
  } catch (e) {
    const detail = e?.response?.data?.slug?.[0]
    ElMessage.error(detail ? `地址无效：${detail}` : '保存失败')
  } finally {
    saving.value = false
  }
}

async function refreshPages() {
  try {
    const { data } = await listSitePages()
    const arr = data.results || data
    sitepageStore.pages = arr
  } catch {
    /* 忽略，仅刷新缓存 */
  }
}

async function removePage() {
  try {
    await ElMessageBox.confirm('确定删除该页面？此操作不可恢复。', '删除静态页', { type: 'warning' })
  } catch {
    return
  }
  saving.value = true
  try {
    await deleteSitePage(current.value)
    ElMessage.success('页面已删除')
    await refreshPages()
    const arr = sitepageStore.pages
    const def = arr.find(p => p.slug === 'home') || arr[0]
    if (def) router.push({ path: '/admin/sitepages', query: { page: def.slug } })
    else router.push('/admin/articles')
  } catch {
    ElMessage.error('删除失败')
  } finally {
    saving.value = false
  }
}

function openFront() {
  const slug = (form.value?.slug || current.value || '').trim()
  const path = slug === 'home' ? '/' : `/${slug}`
  window.open(path, '_blank')
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
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.page-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-slug {
  width: 200px;
}

.meta-slug :deep(.el-input-group__prepend) {
  padding: 0 8px;
  color: #6b7f6c;
}

.meta-input {
  width: 160px;
}

.meta-order {
  width: 120px;
}

.action-btns {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
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
