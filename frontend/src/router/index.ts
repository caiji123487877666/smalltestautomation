/**
 * Router 配置 - 含登录守卫 & 动态菜单
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 静态路由 (无需权限)
const staticRoutes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: '登录', public: true },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/Register.vue'),
    meta: { title: '注册', public: true },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Index.vue'),
        meta: { title: '工作台', icon: 'DataBoard' },
      },
      // 系统管理
      {
        path: 'system/user',
        name: 'SystemUser',
        component: () => import('@/views/system/user/Index.vue'),
        meta: { title: '用户管理' },
      },
      {
        path: 'system/role',
        name: 'SystemRole',
        component: () => import('@/views/system/role/Index.vue'),
        meta: { title: '角色权限' },
      },
      {
        path: 'system/menu',
        name: 'SystemMenu',
        component: () => import('@/views/system/menu/Index.vue'),
        meta: { title: '菜单管理' },
      },
      // 项目管理
      {
        path: 'project/list',
        name: 'ProjectList',
        component: () => import('@/views/project/list/Index.vue'),
        meta: { title: '项目列表' },
      },
      {
        path: 'project/module',
        name: 'ProjectModule',
        component: () => import('@/views/project/module/Index.vue'),
        meta: { title: '测试模块' },
      },
      // 占位 (后续实现)
      {
        path: 'testcase/list',
        name: 'TestCaseList',
        component: () => import('@/views/testcase/list/Index.vue'),
        meta: { title: '用例列表' },
      },
      {
        path: 'testcase/ai-generate',
        name: 'AIGenerate',
        component: () => import('@/views/_placeholder.vue'),
        meta: { title: 'AI 生成用例' },
      },
      // 缺陷管理
      {
        path: 'bug/list',
        name: 'BugList',
        component: () => import('@/views/bug/list/Index.vue'),
        meta: { title: 'Bug 列表' },
      },
      {
        path: 'execution/plan',
        name: 'ExecutionPlan',
        component: () => import('@/views/_placeholder.vue'),
        meta: { title: '执行计划' },
      },
      {
        path: 'execution/record',
        name: 'ExecutionRecord',
        component: () => import('@/views/_placeholder.vue'),
        meta: { title: '执行记录' },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { public: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: staticRoutes,
})

// 白名单
const WHITE_LIST = ['/login', '/register']

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 已登录
  if (authStore.isLoggedIn) {
    if (to.path === '/login' || to.path === '/register') {
      next('/')
      return
    }
    // 没有用户信息则拉取
    if (!authStore.userInfo) {
      try {
        await authStore.fetchUserInfo()
      } catch {
        authStore.logout()
        next(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
        return
      }
    }
    next()
    return
  }

  // 未登录
  if (WHITE_LIST.includes(to.path)) {
    next()
    return
  }
  next(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
})

export default router
