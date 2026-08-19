<template>
  <div class="cms-layout">
    <aside class="cms-aside">
      <div class="cms-logo">
        <span class="cms-logo-mark">CW</span>
        <span class="cms-logo-text">CloverWeb CMS</span>
      </div>
      <el-menu
        class="cms-menu"
        :default-active="activeMenu"
        router
        background-color="#1d2b1f"
        text-color="#c8d6c9"
        active-text-color="#7bc47f"
      >
        <el-menu-item index="/admin/articles">
          <el-icon><Document /></el-icon>
          <span>文章管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/sitepages">
          <el-icon><Files /></el-icon>
          <span>静态页管理</span>
        </el-menu-item>
        <!-- 不用 el-menu-item：其 click 事件无原生事件对象，.prevent 会崩；且 router 模式会把 SPA 路由推到空白页 -->
        <li class="el-menu-item django-admin-item" role="menuitem" @click="openDjangoAdmin">
          <el-icon><Setting /></el-icon>
          <span>Django 后台</span>
        </li>
      </el-menu>
      <div class="cms-aside-footer">
        <el-button text size="small" @click="$router.push('/')">
          <el-icon><HomeFilled /></el-icon>&nbsp;返回官网
        </el-button>
      </div>
    </aside>

    <div class="cms-main">
      <header class="cms-header">
        <div class="cms-header-title">{{ pageTitle }}</div>
        <div class="cms-header-user">
          <span class="cms-username">{{ user?.display_name || user?.username || '已登录' }}</span>
          <el-button text type="danger" size="small" @click="logout">退出</el-button>
        </div>
      </header>
      <main class="cms-content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { getUser, clearLogin } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const user = getUser()

const activeMenu = computed(() => {
  if (route.path.startsWith('/admin/sitepages')) return '/admin/sitepages'
  return '/admin/articles'
})

const pageTitle = computed(() => {
  if (route.name === 'AdminArticleEdit') return route.params.id ? '编辑文章' : '新建文章'
  if (route.path.startsWith('/admin/sitepages')) return '静态页管理'
  return '文章管理'
})

function openDjangoAdmin() {
  window.open('/django-admin/', '_blank')
}

function logout() {
  ElMessageBox.confirm('确定退出登录？', '提示', { type: 'warning' })
    .then(() => {
      clearLogin()
      router.push('/admin/login')
    })
    .catch(() => {})
}
</script>

<style scoped>
.cms-layout {
  display: flex;
  min-height: 100vh;
  background: #f5f7f5;
}

.cms-aside {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: #1d2b1f;
}

.cms-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px;
  color: #fff;
}

.cms-logo-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #7bc47f;
  color: #1d2b1f;
  font-weight: 700;
  font-size: 13px;
}

.cms-logo-text {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.cms-menu {
  border-right: none;
  flex: 1;
}

.cms-aside-footer {
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.cms-aside-footer :deep(.el-button) {
  color: #c8d6c9;
}

.cms-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.cms-header {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #e4e9e4;
}

.cms-header-title {
  font-size: 16px;
  font-weight: 600;
  color: #2c3e2d;
}

.cms-header-user {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cms-username {
  font-size: 13px;
  color: #6b7f6c;
}

.cms-content {
  flex: 1;
  padding: 24px;
  overflow: auto;
}
</style>
