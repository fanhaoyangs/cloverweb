<template>
  <div class="article-admin">
    <!-- 筛选栏 -->
    <div class="toolbar">
      <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 130px" @change="load(1)">
        <el-option label="草稿" value="draft" />
        <el-option label="已发布" value="published" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-select v-model="filters.category" placeholder="全部分类" clearable style="width: 150px" @change="load(1)">
        <el-option v-for="c in categories" :key="c.slug" :label="c.name" :value="c.slug" />
      </el-select>
      <el-input
        v-model="filters.search"
        placeholder="搜索标题/摘要"
        clearable
        style="width: 220px"
        @keyup.enter="load(1)"
        @clear="load(1)"
      />
      <el-button type="primary" @click="load(1)">查询</el-button>
      <div class="spacer"></div>
      <el-button type="primary" @click="$router.push('/admin/articles/edit')">
        <el-icon><Plus /></el-icon>&nbsp;新建文章
      </el-button>
    </div>

    <!-- 列表 -->
    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column prop="title" label="标题" min-width="240" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="art-title" @click="goEdit(row)">{{ row.title }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="category_name" label="分类" width="110">
        <template #default="{ row }">{{ row.category_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="首页精选" width="90" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.is_featured" @change="toggleFeatured(row)" />
        </template>
      </el-table-column>
      <el-table-column label="发布时间" width="170">
        <template #default="{ row }">{{ fmtTime(row.published_at) || '—' }}</template>
      </el-table-column>
      <el-table-column prop="view_count" label="浏览" width="80" align="center" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="goEdit(row)">编辑</el-button>
          <el-button
            v-if="row.status !== 'published'"
            link type="success" size="small"
            @click="setStatus(row, 'published')"
          >发布</el-button>
          <el-button
            v-else
            link type="warning" size="small"
            @click="setStatus(row, 'draft')"
          >撤回</el-button>
          <el-button link type="danger" size="small" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listAdminArticles,
  listCategories,
  updateAdminArticle,
  deleteAdminArticle
} from '@/api/admin'

const router = useRouter()
const loading = ref(false)
const list = ref([])
const categories = ref([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const filters = reactive({ status: '', category: '', search: '' })

onMounted(async () => {
  load()
  try {
    const { data } = await listCategories()
    categories.value = data.results || data
  } catch { /* 分类加载失败不阻塞 */ }
})

async function load(p = page.value) {
  page.value = p
  loading.value = true
  try {
    const { data } = await listAdminArticles({ ...filters, page: p, pageSize })
    list.value = data.results
    total.value = data.count
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

function goEdit(row) {
  router.push(`/admin/articles/edit/${row.id}`)
}

async function toggleFeatured(row) {
  try {
    await updateAdminArticle(row.id, { is_featured: !row.is_featured })
    row.is_featured = !row.is_featured
  } catch {
    ElMessage.error('操作失败')
  }
}

async function setStatus(row, status) {
  try {
    const { data } = await updateAdminArticle(row.id, { status })
    Object.assign(row, data)
    ElMessage.success(status === 'published' ? '已发布' : '已撤回为草稿')
  } catch {
    ElMessage.error('操作失败')
  }
}

function remove(row) {
  ElMessageBox.confirm(`确定删除「${row.title}」？该操作不可恢复。`, '删除确认', { type: 'warning' })
    .then(async () => {
      await deleteAdminArticle(row.id)
      ElMessage.success('已删除')
      load()
    })
    .catch(() => {})
}

function statusType(s) {
  return { draft: 'info', published: 'success', archived: 'warning' }[s] || 'info'
}

function statusLabel(s) {
  return { draft: '草稿', published: '已发布', archived: '已归档' }[s] || s
}

function fmtTime(t) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  align-items: center;
}

.spacer {
  flex: 1;
}

.art-title {
  color: #3a7d44;
  cursor: pointer;
}

.art-title:hover {
  text-decoration: underline;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
