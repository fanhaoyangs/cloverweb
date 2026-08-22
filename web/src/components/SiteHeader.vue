<template>
  <nav class="navbar" ref="navbarRef">
    <div class="navbar-logo" @click="goHome">
      <!-- 花开中国页首：只有logo -->
      <template v-if="pageType === 'home'">
        <img src="https://images.communitygarden.org.cn/communitygarden/花开中国logo.png" alt="花开中国">
      </template>
      <!-- 其他页首：logo + 四叶草堂文字 -->
      <template v-else>
        <img src="https://images.communitygarden.org.cn/communitygarden/四叶草堂LOGO.png" alt="四叶草堂">
        <span class="navbar-logo-text">四叶草堂</span>
      </template>
    </div>
    <ul class="nav-links" :class="{ active: mobileMenuOpen }" ref="navLinksRef">
      <li v-for="p in menuPages" :key="p.slug">
        <router-link :to="p.slug === 'home' ? '/' : `/${p.slug}`" :class="{ active: isActive(p.slug) }">
          {{ p.menu_label || p.title || p.slug }}
        </router-link>
      </li>
      <!-- 资讯分享为文章列表页，论坛交流为 BBS，固定展示 -->
      <li><router-link to="/news" :class="{ active: $route.path === '/news' }">资讯分享</router-link></li>
      <li>
        <router-link to="/bbs" :class="{ active: $route.path.startsWith('/bbs') }">论坛交流</router-link>
      </li>
    </ul>
    <div class="mobile-menu-btn" :class="{ active: mobileMenuOpen }" @click="toggleMobileMenu" ref="mobileMenuBtnRef">
      <span></span>
      <span></span>
      <span></span>
    </div>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listSitePagesPublic } from '@/api/sitepage'

const route = useRoute()
const router = useRouter()

const navbarRef = ref(null)
const navLinksRef = ref(null)
const mobileMenuBtnRef = ref(null)
const mobileMenuOpen = ref(false)

// 一级导航：已发布且 in_menu 的静态页（按 menu_order 排序）
const menuPages = ref([])
// 接口异常时的兜底导航（与 0003 迁移的存量菜单一致），避免导航整体消失
const FALLBACK_MENU = [
  { slug: 'home', menu_label: '花开中国', title: '花开中国' },
  { slug: 'philosophy', menu_label: '理念路径', title: '理念路径' },
  { slug: 'clover', menu_label: '关于我们', title: '关于我们' }
]
async function loadMenu() {
  try {
    menuPages.value = await listSitePagesPublic()
  } catch {
    menuPages.value = FALLBACK_MENU
  }
}

function isActive(slug) {
  return slug === 'home' ? route.path === '/' : route.path === `/${slug}`
}

const pageType = computed(() => {
  if (route.path === '/') return 'home'
  return 'other'
})

const goHome = () => {
  router.push('/')
}

const toggleMobileMenu = () => {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

const handleScroll = () => {
  if (navbarRef.value) {
    if (window.scrollY > 50) {
      navbarRef.value.style.background = 'rgba(255, 255, 255, 0.98)'
    } else {
      navbarRef.value.style.background = 'rgba(255, 255, 255, 0.95)'
    }
  }
}

const closeMobileMenu = () => {
  mobileMenuOpen.value = false
}

const handleClickOutside = (e) => {
  if (mobileMenuOpen.value) {
    if (
      navbarRef.value &&
      !navbarRef.value.contains(e.target)
    ) {
      closeMobileMenu()
    }
  }
}

onMounted(() => {
  loadMenu()
  window.addEventListener('scroll', handleScroll)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
  document.removeEventListener('click', handleClickOutside)
})

watch(() => route.path, () => {
  closeMobileMenu()
})
</script>

<style scoped>
/* 样式已在 common.css 中定义 */
</style>
