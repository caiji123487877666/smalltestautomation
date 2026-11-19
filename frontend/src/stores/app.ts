/**
 * App Store - 全局 UI 状态 (侧边栏折叠, 当前项目等)
 */
import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    sidebarCollapsed: false,
    currentProjectId: null as number | null,
    currentProjectName: '',
    currentEnvironmentId: null as number | null,
    currentEnvironmentName: '',
  }),
  getters: {
    isCollapsed: (state) => state.sidebarCollapsed,
  },
  actions: {
    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
    setCurrentProject(id: number | null, name: string = '') {
      this.currentProjectId = id
      this.currentProjectName = name
      this.currentEnvironmentId = null
      this.currentEnvironmentName = ''
      localStorage.setItem('current_project_id', String(id))
      localStorage.setItem('current_project_name', name)
    },
    setCurrentEnvironment(id: number | null, name: string = '') {
      this.currentEnvironmentId = id
      this.currentEnvironmentName = name
    },
  },
  persist: {
    paths: [
      'sidebarCollapsed', 'currentProjectId', 'currentProjectName',
      'currentEnvironmentId', 'currentEnvironmentName',
    ],
  },
})
