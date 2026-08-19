<template>
  <el-dialog
    v-model="visible"
    title="飞书文档导入"
    width="760px"
    :close-on-click-modal="false"
    destroy-on-close
    append-to-body
  >
    <div v-loading="loadingDocs" class="feishu-import">
      <el-alert
        v-if="!status.configured"
        type="warning"
        :closable="false"
        title="飞书应用未配置"
        description="请联系管理员在 backend/.env 配置 FEISHU_APP_ID / FEISHU_APP_SECRET，并在飞书开放平台开通 docx / drive 读取权限。"
        show-icon
        class="mb16"
      />
      <el-alert
        v-else-if="!status.authorized"
        type="warning"
        :closable="false"
        class="mb16"
        title="需要授权飞书"
      >
        <template #default>
          <div>导入飞书文档需要先完成授权。点击下方按钮前往飞书授权页面，授权完成后返回点击「刷新授权状态」。</div>
          <div style="margin-top: 10px; display: flex; gap: 8px;">
            <el-button type="primary" size="small" @click="openAuth">前往授权</el-button>
            <el-button size="small" @click="loadStatus">刷新授权状态</el-button>
          </div>
        </template>
      </el-alert>
      <el-alert
        v-else
        type="info"
        :closable="false"
        class="mb16"
        title="使用说明"
      >
        <template #default>
          直接粘贴你有权限访问的飞书文档链接（docx 或 wiki）到下方即可导入，无需额外共享设置。
        </template>
      </el-alert>

      <!-- 粘贴链接导入 -->
      <div class="import-row">
        <el-input
          v-model="docUrl"
          placeholder="粘贴飞书文档链接（支持 docx 与 wiki 链接）"
          clearable
          :disabled="importing || !status.authorized"
          @keyup.enter="doImport"
        >
          <template #prepend>链接</template>
        </el-input>
        <el-button
          type="primary"
          :loading="importing"
          :disabled="!docUrl.trim() || !status.authorized"
          @click="doImport"
        >
          导入
        </el-button>
      </div>

      <!-- 文件夹列表（可选） -->
      <template v-if="status.folder_enabled && status.authorized">
        <el-divider content-position="left">共享文件夹文档</el-divider>
        <div v-if="docs.length" class="doc-list">
          <div v-for="f in docs" :key="f.token" class="doc-item" @click="importFromList(f)">
            <span class="doc-name">{{ f.name }}</span>
            <span class="doc-time">{{ formatTime(f.modified_time) }}</span>
            <el-button size="small" type="primary" link>导入</el-button>
          </div>
        </div>
        <div v-else-if="!loadingDocs" class="empty-tip">文件夹内暂无可导入的 docx 文档</div>
      </template>

      <!-- 预览 -->
      <template v-if="result">
        <el-divider content-position="left">
          预览（{{ result.title }}，转存图片 {{ result.image_count }} 张<template v-if="result.image_failed">，失败 {{ result.image_failed }} 张</template>）
        </el-divider>
        <div class="preview-box" v-html="result.html"></div>

        <div class="insert-options">
          <el-radio-group v-model="insertMode">
            <el-radio value="append">追加到编辑器末尾</el-radio>
            <el-radio value="replace">替换编辑器现有内容</el-radio>
          </el-radio-group>
          <el-checkbox v-model="fillTitle">将文档标题填入文章标题（仅标题为空时）</el-checkbox>
        </div>
      </template>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :disabled="!result" @click="confirmInsert">
        插入编辑器
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { getFeishuStatus, getFeishuAuthorizeUrl, listFeishuDocuments, importFeishuDocument } from '@/api/admin'

const props = defineProps({
  modelValue: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'insert'])

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const status = ref({ configured: false, folder_enabled: false })
const docUrl = ref('')
const docs = ref([])
const loadingDocs = ref(false)
const importing = ref(false)
const result = ref(null)
const insertMode = ref('append')
const fillTitle = ref(true)

watch(visible, (val) => {
  if (val) {
    result.value = null
    loadStatus()
  }
})

async function loadStatus() {
  try {
    const { data } = await getFeishuStatus()
    status.value = data
    if (data.authorized && data.folder_enabled) loadDocs()
  } catch { /* 静默，导入时会再报错 */ }
}

async function openAuth() {
  try {
    const { data } = await getFeishuAuthorizeUrl()
    if (data.authorize_url) {
      window.open(data.authorize_url, '_blank')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '获取授权链接失败')
  }
}

async function loadDocs() {
  loadingDocs.value = true
  try {
    const { data } = await listFeishuDocuments()
    docs.value = data.files || []
  } catch (e) {
    docs.value = []
  } finally {
    loadingDocs.value = false
  }
}

async function doImport() {
  const url = docUrl.value.trim()
  if (!url) return
  importing.value = true
  result.value = null
  try {
    const { data } = await importFeishuDocument(url)
    result.value = data
    ElMessage.success(`「${data.title}」解析成功，请预览后插入`)
  } catch (e) {
    const errorData = e.response?.data
    if (errorData?.need_auth) {
      ElMessage.warning('飞书授权已过期，请重新授权')
      status.value.authorized = false
    } else {
      const msg = errorData?.detail || '导入失败，请检查链接是否正确'
      ElMessage.error(msg)
    }
  } finally {
    importing.value = false
  }
}

function importFromList(file) {
  docUrl.value = file.url || `https://feishu.cn/docx/${file.token}`
  doImport()
}

function confirmInsert() {
  if (!result.value) return
  emit('insert', {
    html: result.value.html,
    title: result.value.title,
    mode: insertMode.value,
    fillTitle: fillTitle.value
  })
  visible.value = false
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(Number(ts) * 1000).toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
.mb16 {
  margin-bottom: 16px;
}

.import-row {
  display: flex;
  gap: 12px;
}

.import-row .el-input {
  flex: 1;
}

.doc-list {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  cursor: pointer;
}

.doc-item:hover {
  background: #f5f7fa;
}

.doc-item + .doc-item {
  border-top: 1px solid #ebeef5;
}

.doc-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.doc-time {
  color: #909399;
  font-size: 12px;
  flex-shrink: 0;
}

.empty-tip {
  color: #909399;
  font-size: 13px;
  text-align: center;
  padding: 16px 0;
}

.preview-box {
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  padding: 16px;
  line-height: 1.7;
}

.preview-box :deep(img) {
  max-width: 100%;
}

.preview-box :deep(pre) {
  background: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}

.preview-box :deep(blockquote) {
  margin: 10px 0;
  padding: 8px 14px;
  border-left: 4px solid #dcdfe6;
  color: #606266;
  background: #fafafa;
}

.insert-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
