/**
 * Auth Store - 登录态 & 用户信息
 */
import { defineStore } from 'pinia'
import { http } from '@/utils/request'
import router from '@/router'

export interface RoleInfo {
  code: string
  name: string
}

export interface MenuNode {
  id: number
  name: string
  type: string
  path: string
  component: string
  icon: string
  permission_code: string
  sort_order: number
  is_visible: boolean
  children: MenuNode[]
}

export interface UserInfo {
  id: number
  username: string
  real_name?: string
  email?: string
  phone?: string
  department?: string
  gender: string
  avatar?: string
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  roles: RoleInfo[]
  permissions: string[] | 'all'
  menus: MenuNode[]
  date_joined: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    userInfo: null as UserInfo | null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    username: (state) => state.userInfo?.username || '',
    displayName: (state) => state.userInfo?.real_name || state.userInfo?.username || '',
    roles: (state) => state.userInfo?.roles || [],
    menus: (state) => state.userInfo?.menus || [],
    permissions: (state) => {
      const p = state.userInfo?.permissions
      if (p === 'all') return 'all'
      return p || []
    },
  },
  actions: {
    async login(username: string, password: string) {
      const res = await http.post<any>('/api/users/login/', { username, password })
      this.token = res.access
      this.refreshToken = res.refresh
      localStorage.setItem('access_token', res.access)
      localStorage.setItem('refresh_token', res.refresh)
      this.userInfo = res.user
      return res.user
    },

    async register(data: { username: string; password: string; email?: string }) {
      return http.post('/api/users/register/', data)
    },

    async fetchUserInfo() {
      const data = await http.get<UserInfo>('/api/users/me/')
      this.userInfo = data
      return data
    },

    hasPermission(code: string): boolean {
      if (this.permissions === 'all') return true
      if (Array.isArray(this.permissions) && this.permissions.length === 0) return true
      return Array.isArray(this.permissions) && this.permissions.includes(code)
    },

    logout() {
      this.token = ''
      this.refreshToken = ''
      this.userInfo = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      router.push('/login')
    },
  },
  persist: {
    paths: ['token', 'refreshToken'],
  },
})
