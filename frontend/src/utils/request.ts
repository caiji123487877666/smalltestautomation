/**
 * Axios 封装 - 自动携带 Token, 统一错误处理
 */
import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import router from '@/router'

// 后端统一响应格式
export interface ApiResponse<T = any> {
  code: number
  msg: string
  data: T
}

const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/',
  timeout: 15000,
})

// --- 请求拦截器 ---
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// --- 响应拦截器 ---
let isRefreshing = false
let pendingRequests: Array<(token: string) => void> = []

request.interceptors.response.use(
  (response) => {
    // 文件下载 (blob) 直接返回原始数据
    if (response.config.responseType === 'blob') {
      return response.data
    }
    // 204 No Content 等空响应 (如删除成功)
    if (response.status === 204 || response.data === '' || response.data === null || response.data === undefined) {
      return null
    }
    const res = response.data as ApiResponse
    // 后端走标准格式 {code, msg, data}
    if (res.code === 200) {
      return res.data  // 直接返回 data
    }
    // 业务错误
    ElMessage.error(res.msg || '请求失败')
    return Promise.reject(new Error(res.msg || '请求失败'))
  },
  async (error) => {
    const status = error.response?.status
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    // 401 未授权 -> 尝试刷新 token 或跳转登录
    if (status === 401) {
      if (originalRequest._retry) {
        // 刷新也失败了, 强制登出
        handleLogout()
        return Promise.reject(error)
      }

      const refreshToken = localStorage.getItem('refresh_token')
      if (!refreshToken) {
        handleLogout()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // 正在刷新, 把请求加入队列
        return new Promise((resolve) => {
          pendingRequests.push((token: string) => {
            originalRequest.headers = originalRequest.headers || {}
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(request(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const res = await axios.post(
          `${import.meta.env.VITE_API_BASE || ''}/api/users/token/refresh/`,
          { refresh: refreshToken }
        )
        const newAccessToken = res.data?.access
        const newRefreshToken = res.data?.refresh
        if (newAccessToken) {
          localStorage.setItem('access_token', newAccessToken)
          // 开启 refresh 轮换后, 新 refresh token 必须覆盖旧的, 否则下次刷新会失败
          if (newRefreshToken) {
            localStorage.setItem('refresh_token', newRefreshToken)
          }
          // 队列中的请求用新 token 重放
          pendingRequests.forEach((cb) => cb(newAccessToken))
          pendingRequests = []
          originalRequest.headers = originalRequest.headers || {}
          originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
          return request(originalRequest)
        } else {
          handleLogout()
        }
      } catch {
        handleLogout()
      } finally {
        isRefreshing = false
      }
      return Promise.reject(error)
    }

    // 403 权限不足
    if (status === 403) {
      ElMessage.error('没有权限执行此操作')
      return Promise.reject(error)
    }

    // 其他错误
    const msg = error.response?.data?.msg || error.message || '网络错误'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

function handleLogout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  ElMessageBox.confirm('登录已过期, 请重新登录', '提示', {
    confirmButtonText: '重新登录',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      router.push('/login')
    })
    .catch(() => {
      // ignore
    })
}

// 便捷方法
export const http = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return request.get(url, config) as unknown as Promise<T>
  },
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return request.post(url, data, config) as unknown as Promise<T>
  },
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return request.put(url, data, config) as unknown as Promise<T>
  },
  patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return request.patch(url, data, config) as unknown as Promise<T>
  },
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return request.delete(url, config) as unknown as Promise<T>
  },
}

export default request
