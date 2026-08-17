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
      <li><router-link to="/" :class="{ active: $route.path === '/' }">花开中国</router-link></li>
      <li><router-link to="/philosophy" :class="{ active: $route.path === '/philosophy' }">理念路径</router-link></li>
      <li><router-link to="/news" :class="{ active: $route.path === '/news' }">资讯分享</router-link></li>
      <li><router-link to="/about" :class="{ active: $route.path === '/about' }">关于我们</router-link></li>
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

const route = useRoute()
const router = useRouter()

const navbarRef = ref(null)
const navLinksRef = ref(null)
const mobileMenuBtnRef = ref(null)
const mobileMenuOpen = ref(false)

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
