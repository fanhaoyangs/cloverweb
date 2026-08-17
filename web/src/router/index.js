import { createRouter, createWebHistory } from 'vue-router'
import SitePageView from '@/views/SitePageView.vue'

const publicRoutes = [
  {
    path: '/',
    name: 'Home',
    component: SitePageView,
    props: { slug: 'home' }
  },
  {
    path: '/about',
    name: 'About',
    component: SitePageView,
    props: { slug: 'about' }
  },
  {
    path: '/philosophy',
    name: 'Philosophy',
    component: SitePageView,
    props: { slug: 'philosophy' }
  },
  {
    path: '/news',
    name: 'NewsList',
    component: () => import('@/views/NewsList.vue')
  },
  {
    path: '/news/:slug',
    name: 'ArticleDetail',
    component: () => import('@/views/ArticleDetail.vue')
  }
]

const router = createRouter({
  // history 模式（SEO 友好），Nginx 需配 try_files 回退 index.html
  history: createWebHistory(),
  routes: publicRoutes,
  scrollBehavior() {
    return { top: 0 }
  }
})

export default router
