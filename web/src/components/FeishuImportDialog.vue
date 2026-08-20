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
      <!-- 状态未加载完成前不渲染告警/列表，避免首次打开的闪烁 -->
      <template v-if="statusLoaded">
        <el-alert
          v-if="!status.configured"
          type="warning"
          :closable="false"
          title="飞书应用未配置"
          description="请联系管理员在 backend/.env 配置 FEISHU_APP_ID / FEISHU_APP_SECRET，并在飞书开放平台开通 docx / drive 读取权限。"
          show-icon
          class="mb16"
        />

        <template v-else>
          <!-- 未授权：直接引导授权 -->
          <div v-if="!status.authorized">
            <el-alert type="info" :closable="false" class="mb16" title="需要授权飞书以读取你的文档">
              <template #default>
                <div>点击「前往授权」在新窗口完成飞书授权，返回后自动加载你本人云空间的文档。</div>
                <div style="margin-top: 10px; display: flex; gap: 8px; align-items: center;">
                  <el-button type="primary" size="small" @click="openAuth">前往授权</el-button>
                  <el-button size="small" @click="loadStatus">刷新状态</el-button>
                  <span v-if="waitingAuth" class="waiting">正在等待授权完成…</span>
                </div>
                <div v-if="authError" class="auth-error">{{ authError }}</div>
              </template>
            </el-alert>
          </div>

          <!-- 已授权：本人云空间文档列表 -->
          <template v-else>
            <div class="doc-section-title">我的飞书文档（点击右侧「导入」）</div>
            <div v-if="docs.length" class="doc-list">
              <div v-for="f in docs" :key="f.token" class="doc-item">
                <span class="doc-name" :title="f.name">{{ f.name }}</span>
                <span class="doc-time">{{ formatTime(f.modified_time) }}</span>
                <el-button size="small" type="primary" link :disabled="importing" @click="importFromList(f)">
                  {{ importingToken === f.token ? '导入中…' : '导入' }}
                </el-button>
              </div>
            </div>
            <div v-else-if="!loadingDocs" class="empty-tip">
              云空间暂无可导入的 docx 文档，请到飞书「我的空间」上传后再刷新
            </div>
            <div class="doc-refresh">
              <el-button size="small" :loading="loadingDocs" @click="loadDocs">刷新文档列表</el-button>
            </div>
          </template>
        </template>
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
import { ref, computed, watch, onBeforeUnmount } from 'vue'
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
const statusLoaded = ref(false)
const docs = ref([])
const loadingDocs = ref(false)
const importing = ref(false)
const importingToken = ref('')
const result = ref(null)
const insertMode = ref('append')
const fillTitle = ref(true)
const waitingAuth = ref(false)
const authError = ref('')

let pollTimer = null
let pollTicks = 0

function clearPoll() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
  pollTicks = 0
  waitingAuth.value = false
}

watch(visible, (val) => {
  if (val) {
    result.value = null
    statusLoaded.value = false
    clearPoll()
    loadStatus(true)
  }
})

onBeforeUnmount(clearPoll)

// 打开后：未授权 → 自动弹授权窗口并轮询等待；已授权 → 直接加载文档
async function loadStatus(autoAuth = false) {
  try {
    const { data } = await getFeishuStatus()
    status.value = data
    statusLoaded.value = true
    if (data.authorized) {
      clearPoll()
      loadDocs()
    } else if (autoAuth) {
      openAuth()   // 直接跳出授权（命名弹窗，不顶掉当前页）
    }
  } catch {
    statusLoaded.value = true
  }
}

async function openAuth() {
  authError.value = ''
  try {
    const { data } = await getFeishuAuthorizeUrl()
    if (data.authorize_url) {
      window.open(data.authorize_url, 'clover_feishu_auth', 'noopener')
      startPolling()
    } else {
      authError.value = '未能获取授权链接，请稍后重试'
    }
  } catch (e) {
    authError.value = e.response?.data?.detail || '获取授权链接失败'
  }
}

function startPolling() {
  waitingAuth.value = true
  clearPoll()
  pollTicks = 0
  pollTimer = setInterval(async () => {
    pollTicks += 1
    if (pollTicks > 45) { // 最多等 90 秒
      clearPoll()
      authError.value = '授权等待超时，请再次点击「前往授权」'
      return
    }
    try {
      const { data } = await getFeishuStatus()
      status.value = data
      if (data.authorized) {
        clearPoll()
        ElMessage.success('飞书授权成功，已加载你的文档')
        loadDocs()
      }
    } catch { /* 静默，继续轮询 */ }
  }, 2000)
}

async function loadDocs() {
  loadingDocs.value = true
  try {
    const { data } = await listFeishuDocuments()
    docs.value = data.files || []
  } catch (e) {
    if (e.response?.data?.need_auth) {
      status.value.authorized = false
      ElMessage.warning('飞书授权已过期，请重新授权')
    } else {
      docs.value = []
    }
  } finally {
    loadingDocs.value = false
  }
}

async function doImport(url) {
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
      const msg = errorData?.detail || '导入失败，请重试'
      ElMessage.error(msg)
    }
  } finally {
    importing.value = false
    importingToken.value = ''
  }
}

async function importFromList(file) {
  if (importing.value) return
  importingToken.value = file.token
  const url = file.url || `https://feishu.cn/docx/${file.token}`
  await doImport(url)
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

.doc-section-title {
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 500;
}

.doc-list {
  max-height: 280px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}

.doc-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
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
  cursor: pointer;
}

.doc-time {
  color: #909399;
  font-size: 12px;
  flex-shrink: 0;
}

.doc-refresh {
  margin-top: 10px;
  text-align: right;
}

.waiting {
  color: #e6a23c;
  font-size: 13px;
}

.auth-error {
  margin-top: 8px;
  color: #f56c6c;
  font-size: 13px;
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
