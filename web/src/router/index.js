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
    path: '/news',
    name: 'NewsList',
    component: () => import('@/views/NewsList.vue')
  },
  {
    path: '/news/:slug',
    name: 'ArticleDetail',
    component: () => import('@/views/ArticleDetail.vue')
  },
  // BBS 论坛（P1：首页/板块/详情/发帖）
  {
    path: '/bbs',
    name: 'BbsHome',
    component: () => import('@/views/bbs/BbsHome.vue')
  },
  {
    path: '/bbs/b/:node',
    name: 'BbsNode',
    component: () => import('@/views/bbs/BbsHome.vue')
  },
  {
    path: '/bbs/t/:id',
    name: 'BbsTopic',
    component: () => import('@/views/bbs/BbsTopic.vue'),
    props: true
  },
  {
    path: '/bbs/new',
    name: 'BbsNew',
    component: () => import('@/views/bbs/BbsNew.vue')
  },
  // 动态静态页（覆盖 /about /philosophy /clover 及后台新建的页面）；
  // 放在具体路由之后，避免吞掉 /news 等保留路径
  {
    path: '/:slug',
    name: 'SitePageDynamic',
    component: SitePageView,
    props: (route) => ({ slug: route.params.slug })
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
