<template>
  <div class="login-callback">
    <div class="cb-card">
      <template v-if="state === 'loading'">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <p>正在完成登录…</p>
      </template>
      <template v-else-if="state === 'error'">
        <el-icon :size="32" color="#f56c6c"><CircleCloseFilled /></el-icon>
        <p>{{ error }}</p>
        <el-button type="primary" @click="$router.push('/admin/login')">重新登录</el-button>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { exchangeFeishuCode } from '@/api/admin'
import { setLogin } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const state = ref('loading')
const error = ref('')

onMounted(async () => {
  const code = route.query.code
  if (!code) {
    state.value = 'error'
    error.value = '缺少授权码'
    return
  }
  try {
    const { data } = await exchangeFeishuCode(code)
    setLogin({ access: data.access, user: data.user })
    router.replace('/admin/articles')
  } catch (e) {
    state.value = 'error'
    error.value = e.response?.data?.detail || '登录交换失败，请重试'
  }
})
</script>

<style scoped>
.login-callback {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7f5;
}

.cb-card {
  text-align: center;
  color: #6b7f6c;
}

.cb-card p {
  margin: 16px 0;
}
</style>
