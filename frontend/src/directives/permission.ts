/**
 * v-permission 按钮权限指令
 * 用法: <el-button v-permission="'system:user:create'">新增</el-button>
 *      <el-button v-permission="['system:user:update', 'system:user:delete']">操作</el-button>
 */
import { useAuthStore } from '@/stores/auth'

type PermissionValue = string | string[]

function mounted(el: HTMLElement, binding: { value: PermissionValue }) {
  const authStore = useAuthStore()
  const value = binding.value
  if (!value) return

  let hasPerm = false
  if (typeof value === 'string') {
    hasPerm = authStore.hasPermission(value)
  } else if (Array.isArray(value)) {
    hasPerm = value.some((code) => authStore.hasPermission(code))
  }

  if (!hasPerm) {
    el.parentNode?.removeChild(el)
  }
}

export function setupPermissionDirective(app: any) {
  app.directive('permission', { mounted })
}

export default { mounted }
