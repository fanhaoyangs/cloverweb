<template>
  <div class="cms-login">
    <div class="cms-login-card">
      <div class="cms-login-logo">
        <span class="logo-mark">CW</span>
        <h1>CloverWeb 内容管理</h1>
        <p class="sub">内部系统，仅限授权成员</p>
      </div>

      <el-tabs v-model="mode" class="login-tabs">
        <el-tab-pane label="飞书登录" name="feishu" />
        <el-tab-pane label="账号密码" name="password" />
      </el-tabs>

      <!-- 飞书登录 -->
      <div v-if="mode === 'feishu'" class="login-body">
        <el-button
          type="primary"
          size="large"
          class="feishu-btn"
          :loading="feishuLoading"
          @click="goFeishu"
        >使用飞书扫码登录</el-button>
        <p class="hint">将跳转到飞书授权页，授权后自动返回</p>
      </div>

      <!-- 账号密码（superuser / 内部账号） -->
      <div v-else class="login-body">
        <el-form @submit.prevent="login">
          <el-form-item>
            <el-input v-model="username" placeholder="用户名" size="large" />
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="password"
              type="password"
              placeholder="密码"
              size="large"
              show-password
              @keyup.enter="login"
            />
          </el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="login"
          >登 录</el-button>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { loginByPassword, getFeishuLoginUrl } from '@/api/admin'
import { setLogin } from '@/utils/auth'

const router = useRouter()
const mode = ref('feishu')
const username = ref('')
const password = ref('')
const loading = ref(false)
const feishuLoading = ref(false)

async function goFeishu() {
  feishuLoading.value = true
  try {
    const { data } = await getFeishuLoginUrl()
    window.location.href = data.authorize_url
  } catch (e) {
    const detail = e.response?.data?.detail
    ElMessage.error(detail || '飞书登录暂不可用（未配置 FEISHU_APP_ID），可先用账号密码登录')
    feishuLoading.value = false
  }
}

async function login() {
  if (!username.value || !password.value) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const { data } = await loginByPassword(username.value, password.value)
    setLogin({ access: data.access })
    router.push('/admin/articles')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '登录失败，请检查用户名密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.cms-login {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1d2b1f 0%, #2f4a33 100%);
}

.cms-login-card {
  width: 380px;
  padding: 40px 36px 32px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.25);
}

.cms-login-logo {
  text-align: center;
  margin-bottom: 24px;
}

.logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #7bc47f;
  color: #1d2b1f;
  font-weight: 700;
  font-size: 18px;
  margin-bottom: 12px;
}

.cms-login-logo h1 {
  font-size: 19px;
  color: #2c3e2d;
  margin: 0 0 6px;
}

.sub {
  font-size: 13px;
  color: #8a9a8a;
  margin: 0;
}

.login-tabs {
  margin-bottom: 24px;
}

.login-body {
  min-height: 160px;
}

.feishu-btn,
.login-btn {
  width: 100%;
}

.hint {
  text-align: center;
  font-size: 12px;
  color: #a0aea0;
  margin-top: 14px;
}
</style>
