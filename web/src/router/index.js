import { createRouter, createWebHistory } from 'vue-router'
import SitePageView from '@/views/SitePageView.vue'
import { isLoggedIn } from '@/utils/auth'

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
    path: '/clover',
    name: 'Clover',
    component: SitePageView,
    props: { slug: 'clover' }
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

const cmsRoutes = [
  {
    path: '/admin/login',
    name: 'CmsLogin',
    component: () => import('@/views/admin/Login.vue')
  },
  {
    path: '/login-callback',
    name: 'LoginCallback',
    component: () => import('@/views/admin/LoginCallback.vue')
  },
  {
    path: '/admin',
    component: () => import('@/components/CmsLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/admin/articles' },
      {
        path: 'articles',
        name: 'AdminArticleList',
        component: () => import('@/views/admin/ArticleList.vue')
      },
      {
        path: 'articles/edit/:id?',
        name: 'AdminArticleEdit',
        component: () => import('@/views/admin/ArticleEdit.vue')
      },
      {
        path: 'sitepages',
        name: 'AdminSitePageEdit',
        component: () => import('@/views/admin/SitePageEdit.vue')
      }
    ]
  }
]

const router = createRouter({
  // history 模式（SEO 友好），Nginx 需配 try_files 回退 index.html
  history: createWebHistory(),
  routes: [...publicRoutes, ...cmsRoutes],
  scrollBehavior() {
    return { top: 0 }
  }
})

// CMS 登录守卫
router.beforeEach((to) => {
  if (to.meta.requiresAuth && !isLoggedIn()) {
    return { path: '/admin/login', query: { redirect: to.fullPath } }
  }
  // 已登录访问登录页 → 直达后台
  if (to.path === '/admin/login' && isLoggedIn()) {
    return '/admin/articles'
  }
})

export default router
