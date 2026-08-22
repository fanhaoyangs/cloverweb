<template>
  <div class="bbs-wrap new-page">
    <div class="bbs-toolbar">
      <h1 class="bbs-title">发起话题</h1>
      <button class="bbs-btn bbs-btn-ghost" @click="$router.back()">返回</button>
    </div>

    <div class="new-form">
      <div class="form-row">
        <input
          v-model="title"
          class="new-input"
          placeholder="标题（至少 6 个字）"
          maxlength="200"
        />
        <select v-model="nodeSlug" class="new-select">
          <option value="" disabled>选择板块</option>
          <option v-for="n in nodes" :key="n.slug" :value="n.slug">
            {{ n.icon }} {{ n.name }}<template v-if="n.staffOnly">（仅管理员）</template>
          </option>
        </select>
      </div>

      <MdEditor
        v-model="contentMd"
        :rows="14"
        placeholder="分享花园营造经验、竞赛组队信息……（支持 Markdown 与图片上传）"
        @submit="submit"
      />

      <div class="form-actions">
        <button class="bbs-btn bbs-btn-primary" :disabled="submitting" @click="submit">
          {{ submitting ? '发布中…' : '发布话题' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import MdEditor from '@/components/bbs/MdEditor.vue'
import { listNodes, createTopic, requireLogin } from '@/api/bbs'

const router = useRouter()

const nodes = ref([])
const title = ref('')
const nodeSlug = ref('')
const contentMd = ref('')
const submitting = ref(false)

onMounted(() => {
  if (!requireLogin('/bbs/new')) return
  listNodes()
    .then((list) => {
      nodes.value = list
    })
    .catch(() => {
      nodes.value = []
    })
})

async function submit() {
  if (submitting.value) return
  if (title.value.trim().length < 6) {
    ElMessage.warning('标题至少 6 个字')
    return
  }
  if (!nodeSlug.value) {
    ElMessage.warning('请选择板块')
    return
  }
  if (contentMd.value.trim().length < 3) {
    ElMessage.warning('正文太短了')
    return
  }
  submitting.value = true
  try {
    const t = await createTopic({
      title: title.value.trim(),
      node: nodeSlug.value,
      contentMd: contentMd.value.trim()
    })
    ElMessage.success('发布成功')
    router.replace(`/bbs/t/${t.id}`)
  } catch (e) {
    const detail = e?.response?.data
    const msg =
      detail?.title?.[0] ||
      detail?.content_md?.[0] ||
      detail?.detail ||
      '发布失败，请重试'
    ElMessage.error(msg)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.new-page {
  max-width: 820px;
}
.new-form {
  background: #fff;
  border: 1px solid #e9ede9;
  border-radius: 8px;
  padding: 20px;
}
.form-row {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.new-input {
  flex: 1;
  min-width: 240px;
  padding: 9px 12px;
  border: 1px solid #dce4dc;
  border-radius: 6px;
  font-size: 15px;
  outline: none;
  font-family: inherit;
}
.new-input:focus,
.new-select:focus {
  border-color: var(--primary-green);
}
.new-select {
  padding: 9px 12px;
  border: 1px solid #dce4dc;
  border-radius: 6px;
  font-size: 14px;
  outline: none;
  background: #fff;
  color: var(--text-dark);
  min-width: 150px;
}
.form-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>
