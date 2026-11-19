/**
 * API 接口定义
 */
import { http } from '@/utils/request'
import type { UserInfo } from '@/stores/auth'

// ========= Auth =========
export const authApi = {
  login: (username: string, password: string) =>
    http.post<any>('/api/users/login/', { username, password }),
  register: (data: { username: string; password: string; email?: string }) =>
    http.post('/api/users/register/', data),
  refreshToken: (refresh: string) =>
    http.post<{ access: string }>('/api/users/token/refresh/', { refresh }),
  getMe: () => http.get<UserInfo>('/api/users/me/'),
}

// ========= Users (Admin) =========
export interface UserAdmin {
  id?: number
  username: string
  password?: string
  real_name?: string
  email?: string
  phone?: string
  gender?: string
  department?: string
  is_active?: boolean
  role_ids?: number[]
}
export const userApi = {
  list: (params?: { keyword?: string; role_id?: number; page?: number; page_size?: number }) =>
    http.get<any>('/api/users/admin/users/', { params }),
  create: (data: UserAdmin) => http.post('/api/users/admin/users/', data),
  update: (id: number, data: UserAdmin) => http.put(`/api/users/admin/users/${id}/`, data),
  delete: (id: number) => http.delete(`/api/users/admin/users/${id}/`),
  resetPassword: (id: number, password: string) =>
    http.post(`/api/users/admin/users/${id}/reset-password/`, { password }),
  toggleActive: (id: number) => http.post(`/api/users/admin/users/${id}/toggle-active/`),
}

// ========= Roles =========
export interface Role {
  id?: number
  code: string
  name: string
  description?: string
  is_builtin?: boolean
  sort_order?: number
  permission_ids?: number[]
}
export const roleApi = {
  list: (params?: { keyword?: string }) => http.get<any>('/api/users/roles/', { params }),
  create: (data: Partial<Role>) => http.post('/api/users/roles/', data),
  update: (id: number, data: Partial<Role>) => http.put(`/api/users/roles/${id}/`, data),
  delete: (id: number) => http.delete(`/api/users/roles/${id}/`),
  getPermissions: (id: number) => http.get<number[]>(`/api/users/roles/${id}/permissions/`),
}

// ========= Menu Permissions =========
export const menuApi = {
  tree: () => http.get<any[]>('/api/users/menu-permissions/'),
  create: (data: any) => http.post('/api/users/menu-permissions/', data),
  update: (id: number, data: any) => http.put(`/api/users/menu-permissions/${id}/`, data),
  delete: (id: number) => http.delete(`/api/users/menu-permissions/${id}/`),
}

// ========= Projects =========
export const projectApi = {
  list: (params?: { keyword?: string; status?: string }) =>
    http.get<any[]>('/api/projects/projects/', { params }),
  myProjects: () => http.get<any[]>('/api/projects/projects/my-projects/'),
  detail: (id: number) => http.get<any>(`/api/projects/projects/${id}/`),
  create: (data: any) => http.post('/api/projects/projects/', data),
  update: (id: number, data: any) => http.put(`/api/projects/projects/${id}/`, data),
  delete: (id: number) => http.delete(`/api/projects/projects/${id}/`),
  modules: (id: number) => http.get<any[]>(`/api/projects/projects/${id}/modules/`),
}

// ========= Modules =========
export const moduleApi = {
  tree: (projectId: number) =>
    http.get<{ tree: any[]; total_count: number; unassigned_count: number }>(
      `/api/projects/${projectId}/modules/tree/`,
    ),
  create: (data: any) => http.post('/api/projects/modules/', data),
  update: (id: number, data: any) => http.put(`/api/projects/modules/${id}/`, data),
  delete: (id: number) => http.delete(`/api/projects/modules/${id}/`),
}

// ========= TestCases =========
export interface TestCaseQuery {
  project_id: number
  module_id?: number | string
  keyword?: string
  case_type?: string
  priority?: string
  status?: string
  tag?: string
  page?: number
  page_size?: number
}

export const testcaseApi = {
  list: (params: TestCaseQuery) =>
    http.get<{ count: number; results: any[] }>('/api/testcases/cases/', { params }),
  detail: (id: number) => http.get<any>(`/api/testcases/cases/${id}/`),
  create: (data: any) => http.post<any>('/api/testcases/cases/', data),
  update: (id: number, data: any) => http.put<any>(`/api/testcases/cases/${id}/`, data),
  delete: (id: number) => http.delete(`/api/testcases/cases/${id}/`),
  duplicate: (id: number) => http.post<any>(`/api/testcases/cases/${id}/duplicate/`),
  batchAction: (data: {
    ids: number[]
    action: 'delete' | 'update_priority' | 'update_status' | 'move_module'
    priority?: string
    status?: string
    module_id?: number | null
  }) => http.post<{ affected: number }>('/api/testcases/cases/batch-action/', data),
  downloadTemplate: () =>
    http.get<Blob>('/api/testcases/cases/import-template/', { responseType: 'blob' }),
  exportExcel: (params: Partial<TestCaseQuery> & { ids?: string }) =>
    http.get<Blob>('/api/testcases/cases/export-excel/', { params, responseType: 'blob' }),
  importExcel: (projectId: number, file: File) => {
    const form = new FormData()
    form.append('project_id', String(projectId))
    form.append('file', file)
    return http.post<any>('/api/testcases/cases/import-excel/', form)
  },
  importSwagger: (projectId: number, file: File) => {
    const form = new FormData()
    form.append('project_id', String(projectId))
    form.append('file', file)
    return http.post<any>('/api/testcases/cases/import-swagger/', form)
  },
}

// ========= Single API Debug =========
export interface DebugApiPayload {
  project_id?: number | null
  environment_id?: number | null
  method: string
  url: string
  headers: any[]
  params: any[]
  body_type: 'none' | 'json' | 'form-data' | 'urlencoded'
  body?: any
  assertions: any[]
  extract_rules: any[]
  sync_variables?: boolean
}

export const debugApi = {
  send: (data: DebugApiPayload) =>
    http.post<any>('/api/testcases/debug-api/', data),
  parseCurl: (curl: string) =>
    http.post<any>('/api/testcases/parse-curl/', { curl }),
}

// ========= Project Members / Environments =========
export const projectMemberApi = {
  list: (projectId: number) =>
    http.get<any[]>(`/api/projects/${projectId}/members/`),
}

export const environmentApi = {
  list: (projectId: number) =>
    http.get<any[]>('/api/projects/environments/', { params: { project_id: projectId } }),
  create: (data: any) => http.post<any>('/api/projects/environments/', data),
  update: (id: number, data: any) => http.put<any>(`/api/projects/environments/${id}/`, data),
  delete: (id: number) => http.delete(`/api/projects/environments/${id}/`),
}

// ========= Bugs =========
export interface BugQuery {
  project_id?: number | string
  status?: string
  severity?: string
  priority?: string
  reproducibility?: string
  assignee_id?: number
  creator_id?: number
  environment_id?: number
  module_id?: number | string
  testcase_id?: number
  keyword?: string
  unclosed?: string
  page?: number
  page_size?: number
}

export const bugApi = {
  list: (params: BugQuery) =>
    http.get<{ count: number; results: any[] }>('/api/bugs/', { params }),
  availableAssignees: (projectId?: number | null) =>
    http.get<any[]>('/api/bugs/available-assignees/',
      { params: projectId ? { project_id: projectId } : {} }),
  detail: (id: number) => http.get<any>(`/api/bugs/${id}/`),
  create: (data: any) => http.post<any>('/api/bugs/', data),
  update: (id: number, data: any) => http.put<any>(`/api/bugs/${id}/`, data),
  delete: (id: number) => http.delete(`/api/bugs/${id}/`),
  transition: (id: number, data: {
    target_status: string
    resolution?: string
    comment?: string
    assignee_ids?: number[]
  }) => http.post<any>(`/api/bugs/${id}/transition/`, data),
  histories: (id: number) => http.get<any[]>(`/api/bugs/${id}/histories/`),
  comment: (id: number, comment: string) =>
    http.post<any>(`/api/bugs/${id}/comment/`, { comment }),
  uploadImage: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return http.post<{ url: string; name: string }>('/api/bugs/upload-image/', form)
  },
}
