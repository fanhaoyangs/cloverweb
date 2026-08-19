<template>
  <div class="article-edit" v-loading="loading && isEdit">
    <el-form label-width="90px" class="edit-form">
      <div class="form-row">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" placeholder="文章标题" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="URL 标识">
          <el-input v-model="form.slug" placeholder="英文/数字/连字符，留空自动生成" />
        </el-form-item>
      </div>

      <div class="form-row">
        <el-form-item label="分类">
          <el-select v-model="form.category" placeholder="选择分类" clearable style="width: 100%">
            <el-option v-for="c in categories" :key="c.slug" :label="c.name" :value="c.slug" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="draft">草稿</el-radio>
            <el-radio value="published">发布</el-radio>
            <el-radio value="archived">归档</el-radio>
          </el-radio-group>
        </el-form-item>
      </div>

      <el-form-item label="标签">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入后回车添加，最多 10 个"
          style="width: 50%"
        >
          <el-option v-for="t in tagOptions" :key="t" :label="t" :value="t" />
        </el-select>
      </el-form-item>

      <div class="form-row">
        <el-form-item label="首页精选">
          <el-switch v-model="form.is_featured" />
        </el-form-item>
        <el-form-item label="首页板块">
          <el-select
            v-model="form.website_sections"
            multiple
            placeholder="挂载到首页哪些板块（如 home_news）"
            style="width: 100%"
          >
            <el-option label="首页·新闻回顾" value="home_news" />
          </el-select>
        </el-form-item>
      </div>

      <el-form-item label="封面图">
        <el-input v-model="form.cover_image" placeholder="封面图 URL（可从正文编辑器上传后复制）" />
      </el-form-item>

      <el-form-item label="摘要">
        <el-input
          v-model="form.excerpt"
          type="textarea"
          :rows="2"
          maxlength="500"
          show-word-limit
          placeholder="列表页摘要，留空时前端显示标题"
        />
      </el-form-item>

      <el-form-item label="正文">
        <div class="editor-box">
          <ContentEditor ref="editorRef" v-model="form.content_html" :height="480" @feishu-import="feishuDialogVisible = true" />
        </div>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="saving" @click="save">{{ isEdit ? '保存修改' : '创建' }}</el-button>
        <el-button @click="$router.back()">返回</el-button>
        <el-button v-if="isEdit" @click="preview">预览</el-button>
      </el-form-item>
    </el-form>

    <FeishuImportDialog v-model="feishuDialogVisible" @insert="handleFeishuInsert" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import ContentEditor from '@/components/content-editor/ContentEditor.vue'
import FeishuImportDialog from '@/components/FeishuImportDialog.vue'
import {
  getAdminArticle,
  createAdminArticle,
  updateAdminArticle,
  listCategories
} from '@/api/admin'

const route = useRoute()
const router = useRouter()

const isEdit = computed(() => !!route.params.id)
const loading = ref(false)
const saving = ref(false)
const categories = ref([])
const tagOptions = ['社区花园', '竞赛', '活动', '媒体报道']
const editorRef = ref(null)
const feishuDialogVisible = ref(false)

function handleFeishuInsert({ html, title, mode, fillTitle }) {
  if (fillTitle && !form.title.trim() && title) {
    form.title = title
  }
  if (mode === 'replace') {
    editorRef.value?.setContent(html)
    form.content_html = html
  } else {
    editorRef.value?.insertHtml(html)
  }
  ElMessage.success('飞书文档已插入编辑器')
}

const form = reactive({
  title: '',
  slug: '',
  category: '',
  tags: [],
  status: 'draft',
  is_featured: false,
  website_sections: [],
  cover_image: '',
  excerpt: '',
  content_html: ''
})

onMounted(async () => {
  try {
    const { data } = await listCategories()
    categories.value = data.results || data
  } catch { /* 不阻塞 */ }

  if (isEdit.value) {
    loading.value = true
    try {
      const { data } = await getAdminArticle(route.params.id)
      Object.assign(form, {
        title: data.title,
        slug: data.slug,
        category: data.category || '',
        tags: data.tags || [],
        status: data.status,
        is_featured: data.is_featured,
        website_sections: data.website_sections || [],
        cover_image: data.cover_image || '',
        excerpt: data.excerpt || '',
        content_html: data.content_html || ''
      })
    } catch {
      ElMessage.error('文章加载失败')
    } finally {
      loading.value = false
    }
  }
})

async function save() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  const payload = { ...form }
  if (!payload.slug) {
    payload.slug = `article-${Date.now().toString(36)}`
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await updateAdminArticle(route.params.id, payload)
      ElMessage.success('已保存')
    } else {
      const { data } = await createAdminArticle(payload)
      ElMessage.success('已创建')
      router.replace(`/admin/articles/edit/${data.id}`)
    }
  } catch (e) {
    const detail = e.response?.data
    const msg = detail && typeof detail === 'object'
      ? Object.entries(detail).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(';') : v}`).join(' | ')
      : '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

function preview() {
  window.open(`/news/${form.slug}`, '_blank')
}
</script>

<style scoped>
.article-edit {
  background: #fff;
  border-radius: 8px;
  padding: 24px;
}

.edit-form {
  max-width: 1100px;
}

.form-row {
  display: flex;
  gap: 16px;
}

.form-row .el-form-item {
  flex: 1;
}

.editor-box {
  width: calc(100% - 4px);
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 4px;
}
</style>
