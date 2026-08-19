<template>
  <div class="sitepage-edit">
    <!-- 左侧页列表 -->
    <div class="page-list">
      <div class="page-list-title">页面</div>
      <div
        v-for="p in pages"
        :key="p.slug"
        class="page-item"
        :class="{ active: current === p.slug }"
        @click="select(p.slug)"
      >
        <span class="page-name">{{ pageName(p.slug) }}</span>
        <span class="page-slug">/{{ p.slug === 'home' ? '' : p.slug }}</span>
      </div>
    </div>

    <!-- 编辑区 -->
    <div class="page-editor" v-loading="loading">
      <template v-if="form">
        <el-form label-width="70px">
          <el-form-item label="标题">
            <el-input v-model="form.title" style="width: 400px" />
          </el-form-item>
          <el-form-item label="内容">
            <div class="editor-box">
              <ContentEditor ref="editorRef" v-model="form.content_html" :height="520" @feishu-import="feishuDialogVisible = true" />
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="save">保存</el-button>
            <el-button @click="preview">预览页面</el-button>
          </el-form-item>
        </el-form>
      </template>
      <div v-else class="empty">请选择左侧页面</div>
    </div>

    <FeishuImportDialog v-model="feishuDialogVisible" @insert="handleFeishuInsert" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ContentEditor from '@/components/content-editor/ContentEditor.vue'
import FeishuImportDialog from '@/components/FeishuImportDialog.vue'
import { listSitePages, getSitePageAdmin, updateSitePage } from '@/api/admin'

const PAGE_NAMES = { home: '首页', about: '关于我们', philosophy: '理念路径' }

const pages = ref([])
const current = ref('')
const form = ref(null)
const loading = ref(false)
const saving = ref(false)
const editorRef = ref(null)
const feishuDialogVisible = ref(false)

function handleFeishuInsert({ html, title, mode, fillTitle }) {
  if (fillTitle && form.value && !form.value.title.trim() && title) {
    form.value.title = title
  }
  if (mode === 'replace') {
    editorRef.value?.setContent(html)
    form.value.content_html = html
  } else {
    editorRef.value?.insertHtml(html)
  }
  ElMessage.success('飞书文档已插入编辑器')
}

onMounted(async () => {
  const { data } = await listSitePages()
  pages.value = data.results || data
  if (pages.value.length) select(pages.value[0].slug)
})

function pageName(slug) {
  return PAGE_NAMES[slug] || slug
}

async function select(slug) {
  current.value = slug
  loading.value = true
  form.value = null
  try {
    const { data } = await getSitePageAdmin(slug)
    form.value = { title: data.title, content_html: data.content_html }
  } catch {
    ElMessage.error('页面加载失败')
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const { data } = await updateSitePage(current.value, form.value)
    ElMessage.success(`「${pageName(current.value)}」已保存`)
    // 同步左侧列表标题
    const p = pages.value.find(x => x.slug === current.value)
    if (p) p.title = data.title
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

function preview() {
  const path = current.value === 'home' ? '/' : `/${current.value}`
  window.open(path, '_blank')
}
</script>

<style scoped>
.sitepage-edit {
  display: flex;
  gap: 16px;
  height: calc(100vh - 56px - 48px);
}

.page-list {
  width: 200px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 8px;
  padding: 12px;
}

.page-list-title {
  font-size: 13px;
  color: #8a9a8a;
  padding: 4px 8px 10px;
}

.page-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.page-item:hover {
  background: #f0f5f0;
}

.page-item.active {
  background: #e8f4e9;
}

.page-name {
  font-size: 14px;
  font-weight: 500;
  color: #2c3e2d;
}

.page-slug {
  font-size: 12px;
  color: #a0aea0;
}

.page-editor {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  overflow: auto;
}

.editor-box {
  width: calc(100% - 4px);
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 4px;
}

.empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #a0aea0;
}
</style>
