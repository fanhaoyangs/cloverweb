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
        <template v-if="onSitepages">
          <div class="sitepage-select">
            <el-select
              :model-value="currentPage"
              placeholder="选择页面"
              size="small"
              @change="selectPage"
            >
              <el-option
                v-for="p in sitepages"
                :key="p.slug"
                :label="pageLabel(p.slug)"
                :value="p.slug"
              />
            </el-select>
          </div>
        </template>
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
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { getUser, clearLogin } from '@/utils/auth'
import { listSitePages } from '@/api/admin'
import { sitepageStore } from '@/utils/sitepageStore'

const route = useRoute()
const router = useRouter()
const user = getUser()

const PAGE_NAMES = { home: '首页', about: '关于我们', philosophy: '理念路径', clover: '四叶草堂' }

const sitepages = ref([])
const onSitepages = computed(() => route.path.startsWith('/admin/sitepages'))
const currentPage = computed(() => route.query.page || '')

const activeMenu = computed(() => {
  if (route.path.startsWith('/admin/sitepages')) return '/admin/sitepages'
  return '/admin/articles'
})

const pageTitle = computed(() => {
  if (route.name === 'AdminArticleEdit') return route.params.id ? '编辑文章' : '新建文章'
  if (route.path.startsWith('/admin/sitepages')) return '静态页管理'
  return '文章管理'
})

function pageLabel(slug) {
  return PAGE_NAMES[slug] || slug
}

// 拉取一次页面列表并缓存；无 page 参数时默认选中 home
async function loadPages() {
  if (sitepageStore.pages.length) {
    sitepages.value = sitepageStore.pages
  } else {
    const { data } = await listSitePages()
    const arr = data.results || data
    sitepageStore.pages = arr
    sitepages.value = arr
  }
  if (!route.query.page && sitepages.value.length && route.path === '/admin/sitepages') {
    const def = sitepages.value.find(p => p.slug === 'home') || sitepages.value[0]
    router.replace({ path: '/admin/sitepages', query: { page: def.slug } })
  }
}

watch(onSitepages, (v) => { if (v) loadPages() }, { immediate: true })

// 切换页面：未保存时先确认
async function selectPage(slug) {
  if (slug === currentPage.value) return
  if (sitepageStore.dirty) {
    try {
      await ElMessageBox.confirm('当前页面有未保存的修改，确定切换吗？', '提示', {
        type: 'warning', confirmButtonText: '切换', cancelButtonText: '取消'
      })
    } catch {
      return
    }
  }
  router.push({ path: '/admin/sitepages', query: { page: slug } })
}

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

.sitepage-select {
  padding: 8px 16px 16px;
}
.sitepage-select :deep(.el-select__wrapper) {
  background: rgba(255, 255, 255, 0.06);
  box-shadow: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
  min-height: 28px;
}
.sitepage-select :deep(.el-select__placeholder) {
  color: #8fa08f;
}
.sitepage-select :deep(.el-select__selected-item) {
  color: #7bc47f;
}
.sitepage-select :deep(.el-select__caret) {
  color: #c8d6c9;
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
