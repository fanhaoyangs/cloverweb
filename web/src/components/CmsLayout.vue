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
        <el-menu-item index="/admin/bbs/topics">
          <el-icon><ChatDotRound /></el-icon>
          <span>论坛话题</span>
        </el-menu-item>
        <el-menu-item index="/admin/bbs/nodes">
          <el-icon><Grid /></el-icon>
          <span>论坛板块</span>
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
                :label="pageLabel(p)"
                :value="p.slug"
              />
            </el-select>
            <el-button size="small" type="primary" class="new-page-btn" @click="createPage">＋ 新建页面</el-button>
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
import { ref, computed, watch, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox, ElMessage, ElInput } from 'element-plus'
import { getUser, clearLogin } from '@/utils/auth'
import { listSitePages, createSitePage } from '@/api/admin'
import { sitepageStore } from '@/utils/sitepageStore'

const route = useRoute()
const router = useRouter()
const user = getUser()

const sitepages = ref([])
const onSitepages = computed(() => route.path.startsWith('/admin/sitepages'))
const currentPage = computed(() => route.query.page || '')

const activeMenu = computed(() => {
  if (route.path.startsWith('/admin/sitepages')) return '/admin/sitepages'
  if (route.path.startsWith('/admin/bbs/topics')) return '/admin/bbs/topics'
  if (route.path.startsWith('/admin/bbs/nodes')) return '/admin/bbs/nodes'
  return '/admin/articles'
})

const pageTitle = computed(() => {
  if (route.name === 'AdminArticleEdit') return route.params.id ? '编辑文章' : '新建文章'
  if (route.path.startsWith('/admin/sitepages')) return '静态页管理'
  if (route.path.startsWith('/admin/bbs/topics')) return '论坛话题管理'
  if (route.path.startsWith('/admin/bbs/nodes')) return '论坛板块管理'
  return '文章管理'
})

function pageLabel(p) {
  return p.menu_label || p.title || p.slug
}

// 新建静态页（草稿），随后跳转编辑；标题必填，地址选填（留空按标题自动生成）
async function createPage() {
  const title = ref('')
  const slug = ref('')
  const labelStyle = 'font-size:12px;color:#6b7f6c;margin:0 0 4px;'
  try {
    await ElMessageBox({
      title: '新建静态页',
      message: h('div', null, [
        h('div', { style: 'margin-bottom:14px;' }, [
          h('p', { style: labelStyle }, '页面标题（必填）'),
          h(ElInput, {
            modelValue: title.value,
            'onUpdate:modelValue': (v) => (title.value = v),
            placeholder: '如：社区花园',
            maxlength: 200
          })
        ]),
        h('div', null, [
          h('p', { style: labelStyle }, '访问地址（选填）'),
          h(ElInput, {
            modelValue: slug.value,
            'onUpdate:modelValue': (v) => (slug.value = v),
            placeholder: '英文/数字/连字符，如 community-garden；留空自动生成'
          })
        ])
      ]),
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      showCancelButton: true,
      closeOnClickModal: false
    })
  } catch {
    return /* 用户取消 */
  }
  const t = title.value.trim()
  const s = slug.value.trim()
  if (!t) {
    ElMessage.warning('标题不能为空')
    return
  }
  if (s && !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/i.test(s)) {
    ElMessage.warning('地址只能用英文、数字和连字符，且不能以连字符开头/结尾')
    return
  }
  try {
    const { data } = await createSitePage({ title: t, slug: s || undefined, status: 'draft', in_menu: false })
    const list = await listSitePages()
    const arr = list.data.results || list.data
    sitepageStore.pages = arr
    sitepages.value = arr
    router.push({ path: '/admin/sitepages', query: { page: data.slug } })
  } catch (e) {
    const detail = e?.response?.data?.slug?.[0]
    ElMessage.error(detail ? `地址无效：${detail}` : '页面创建失败，请重试')
  }
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
