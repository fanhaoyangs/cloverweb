import { createRouter, createWebHashHistory } from 'vue-router'

const publicRoutes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('@/views/HomePage.vue')
  },
  {
    path: '/about',
    name: 'About',
    component: () => import('@/views/AboutPage.vue')
  },
  {
    path: '/philosophy',
    name: 'Philosophy',
    component: () => import('@/views/PhilosophyPage.vue')
  },
  {
    path: '/news',
    name: 'NewsList',
    component: () => import('@/views/NewsList.vue')
  },
  {
    path: '/news/:id',
    name: 'ArticleDetail',
    component: () => import('@/views/ArticleDetail.vue')
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes: publicRoutes
})

export default router
