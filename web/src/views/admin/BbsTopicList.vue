<template>
  <div class="bbs-topic-admin">
    <!-- 筛选栏 -->
    <div class="toolbar">
      <el-select v-model="filters.node" placeholder="全部板块" clearable style="width: 150px" @change="load(1)">
        <el-option v-for="n in nodes" :key="n.slug" :label="`${n.icon} ${n.name}`" :value="n.slug" />
      </el-select>
      <el-input
        v-model="filters.q"
        placeholder="搜索标题/正文"
        clearable
        style="width: 220px"
        @keyup.enter="load(1)"
        @clear="load(1)"
      />
      <el-button type="primary" @click="load(1)">查询</el-button>
    </div>

    <!-- 列表 -->
    <el-table :data="list" v-loading="loading" stripe>
      <el-table-column label="话题" min-width="280" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="topic-cell">
            <el-tag v-if="row.isPinned" size="small" type="warning" class="badge">置顶</el-tag>
            <el-tag v-if="row.isClosed" size="small" type="info" class="badge">锁定</el-tag>
            <span class="topic-title" @click="openFront(row)">{{ row.title }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="板块" width="110">
        <template #default="{ row }">{{ row.node?.name || '—' }}</template>
      </el-table-column>
      <el-table-column label="作者" width="110">
        <template #default="{ row }">{{ row.author?.name || '—' }}</template>
      </el-table-column>
      <el-table-column prop="replyCount" label="回复" width="70" align="center" />
      <el-table-column prop="likeCount" label="点赞" width="70" align="center" />
      <el-table-column prop="viewCount" label="浏览" width="70" align="center" />
      <el-table-column label="发布时间" width="160">
        <template #default="{ row }">{{ fmtTime(row.createdAt) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="210" fixed="right">
        <template #default="{ row }">
          <el-switch
            :model-value="row.isPinned"
            inline-prompt
            active-text="顶"
            inactive-text="顶"
            @change="toggle(row, 'isPinned')"
          />
          <el-switch
            :model-value="row.isClosed"
            inline-prompt
            active-text="锁"
            inactive-text="锁"
            class="ml8"
            @change="toggle(row, 'isClosed')"
          />
          <el-button link type="danger" size="small" class="ml8" @click="remove(row)">删除</el-button>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { listNodes, listTopics, adminUpdateTopic, adminDeleteTopic } from '@/api/bbs'

const loading = ref(false)
const list = ref([])
const nodes = ref([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const filters = reactive({ node: '', q: '' })

onMounted(async () => {
  try {
    nodes.value = await listNodes()
  } catch { /* 板块加载失败不阻塞列表 */ }
  load()
})

async function load(p = page.value) {
  page.value = p
  loading.value = true
  try {
    const { list: items, total: t } = await listTopics({
      node: filters.node || undefined,
      q: filters.q || undefined,
      page: p,
      pageSize
    })
    list.value = items
    total.value = t
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function toggle(row, field) {
  try {
    const updated = await adminUpdateTopic(row.id, { [field]: !row[field] })
    Object.assign(row, updated)
    ElMessage.success(field === 'isPinned' ? (updated.isPinned ? '已置顶' : '已取消置顶') : updated.isClosed ? '已锁定' : '已解锁')
  } catch {
    ElMessage.error('操作失败')
  }
}

function openFront(row) {
  window.open(`/bbs/t/${row.id}`, '_blank')
}

function remove(row) {
  ElMessageBox.confirm(
    `确定删除话题「${row.title}」？其下 ${row.replyCount} 条回复将一并删除，不可恢复。`,
    '删除确认',
    { type: 'warning' }
  )
    .then(async () => {
      await adminDeleteTopic(row.id)
      ElMessage.success('已删除')
      load()
    })
    .catch(() => {})
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

.topic-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.badge {
  flex-shrink: 0;
}

.topic-title {
  color: #3a7d44;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.topic-title:hover {
  text-decoration: underline;
}

.ml8 {
  margin-left: 8px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
