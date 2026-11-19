<template>
  <div class="layout">
    <!-- 侧边栏 -->
    <aside class="aside" :class="{ collapsed: appStore.isCollapsed }">
      <div class="logo">
        <div class="logo-mark">灵</div>
        <div v-if="!appStore.isCollapsed" class="logo-text">
          <div class="logo-name">灵测 AI</div>
          <div class="logo-sub">TEST PLATFORM</div>
        </div>
      </div>

      <el-scrollbar class="menu-scroll">
        <div v-if="!appStore.isCollapsed" class="nav-label">NAVIGATION</div>
        <el-menu
          :default-active="activeMenu"
          :collapse="appStore.isCollapsed"
          :collapse-transition="false"
          router
        >
          <template v-for="menu in menus" :key="menu.id">
            <el-sub-menu
              v-if="hasVisibleChildren(menu)"
              :index="menu.path || String(menu.id)"
            >
              <template #title>
                <el-icon v-if="menu.icon"><component :is="menu.icon" /></el-icon>
                <span>{{ menu.name }}</span>
              </template>
              <el-menu-item
                v-for="child in visibleChildren(menu)"
                :key="child.id"
                :index="resolvePath(menu.path, child.path)"
              >
                <el-icon v-if="child.icon"><component :is="child.icon" /></el-icon>
                <span>{{ child.name }}</span>
                <el-sub-menu
                  v-if="hasVisibleChildren(child)"
                  :index="resolvePath(menu.path, child.path) + '-sub'"
                >
                  <template #title><span>{{ child.name }}</span></template>
                  <el-menu-item
                    v-for="sub in visibleChildren(child)"
                    :key="sub.id"
                    :index="resolvePath(menu.path, child.path, sub.path)"
                  >
                    {{ sub.name }}
                  </el-menu-item>
                </el-sub-menu>
              </el-menu-item>
            </el-sub-menu>
            <el-menu-item v-else :index="menu.path || String(menu.id)">
              <el-icon v-if="menu.icon"><component :is="menu.icon" /></el-icon>
              <span>{{ menu.name }}</span>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>

      <div v-if="!appStore.isCollapsed" class="engine-card">
        <div class="engine-row"><span>AI ENGINE</span><i /></div>
        <div class="engine-meta">v1.0.0 · RUNNING</div>
      </div>
    </aside>

    <!-- 主体 -->
    <div class="body">
      <header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="appStore.toggleSidebar()">
            <Fold v-if="!appStore.isCollapsed" />
            <Expand v-else />
          </el-icon>
          <div class="crumb">
            <template v-for="(c, i) in crumbs" :key="i">
              <span v-if="i > 0" class="sep">/</span>
              <span :class="{ current: i === crumbs.length - 1 }">{{ c }}</span>
            </template>
          </div>
        </div>

        <div class="header-right">
          <el-select
            v-model="selectedProjectId"
            placeholder="选择项目"
            class="project-select"
            size="default"
            @change="handleProjectChange"
          >
            <template #prefix><span class="project-dot" /></template>
            <el-option v-for="p in projectOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>

          <el-select
            v-if="selectedProjectId"
            v-model="selectedEnvId"
            placeholder="环境"
            class="env-select"
            size="default"
            @change="handleEnvChange"
          >
            <template #prefix><span class="env-dot" /></template>
            <el-option v-for="e in environmentOptions" :key="e.id" :label="e.name" :value="e.id" />
          </el-select>

          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :src="authStore.userInfo?.avatar" class="avatar">
                {{ authStore.displayName?.charAt(0)?.toUpperCase() || 'U' }}
              </el-avatar>
              <span class="username">{{ authStore.displayName }}</span>
              <el-icon class="caret"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore, type MenuNode } from '@/stores/auth'
import { useAppStore } from '@/stores/app'
import { projectApi, environmentApi } from '@/api'

const authStore = useAuthStore()
const appStore = useAppStore()
const route = useRoute()

const activeMenu = computed(() => route.path)
const menus = computed(() => authStore.menus)

// 面包屑
const crumbs = computed(() => {
  const target = route.path
  const walk = (nodes: MenuNode[], trail: string[], prefix: string): string[] | null => {
    for (const n of nodes) {
      if (n.is_visible === false) continue
      const full = n.path?.startsWith('/') ? n.path : resolvePath(prefix, n.path)
      const nextTrail = [...trail, n.name]
      if (full === target) return nextTrail
      if (n.children?.length) {
        const found = walk(n.children, nextTrail, full)
        if (found) return found
      }
    }
    return null
  }
  return walk(menus.value, [], '') || ['工作台']
})

const selectedProjectId = ref<number | null>(appStore.currentProjectId)
const projectOptions = ref<any[]>([])
const selectedEnvId = ref<number | null>(appStore.currentEnvironmentId)
const environmentOptions = ref<any[]>([])

async function refreshProjects() {
  let list: any[]
  try {
    list = await projectApi.myProjects()
  } catch {
    // 接口失败时保留当前选择, 避免误清空
    return
  }
  projectOptions.value = list

  const exists = selectedProjectId.value
    ? list.some((p: any) => p.id === selectedProjectId.value)
    : false
  if (selectedProjectId.value && !exists) {
    // 缓存的项目已被删除, 清空以免保存时提交失效的项目 ID
    selectedProjectId.value = null
    appStore.setCurrentProject(null)
    ElMessage.warning('当前项目已不存在或被删除，请重新选择项目')
  }

  if (!selectedProjectId.value) {
    if (list.length > 0) {
      selectedProjectId.value = list[0].id
      handleProjectChange(selectedProjectId.value)
    }
    return
  }
  if (!environmentOptions.value.length) {
    await loadEnvironments(selectedProjectId.value)
  }
}

onMounted(refreshProjects)
// 路由切换时重新校验, 覆盖"在项目页删除项目后回到列表"的场景
watch(() => route.path, refreshProjects)

function handleProjectChange(id: number | null) {
  const p = projectOptions.value.find((x) => x.id === id)
  appStore.setCurrentProject(id, p?.name || '')
  loadEnvironments(id)
}

async function loadEnvironments(projectId: number | null) {
  environmentOptions.value = []
  if (!projectId) {
    selectedEnvId.value = null
    appStore.setCurrentEnvironment(null)
    return
  }
  try {
    const list = await environmentApi.list(projectId)
    environmentOptions.value = list
    const found =
      list.find((e) => e.id === appStore.currentEnvironmentId) ||
      list.find((e) => e.is_default) ||
      list[0]
    selectedEnvId.value = found?.id ?? null
    appStore.setCurrentEnvironment(selectedEnvId.value, found?.name || '')
  } catch {
    selectedEnvId.value = null
    appStore.setCurrentEnvironment(null)
  }
}

function handleEnvChange(id: number | null) {
  const env = environmentOptions.value.find((e) => e.id === id)
  appStore.setCurrentEnvironment(id, env?.name || '')
}

function hasVisibleChildren(menu: MenuNode): boolean {
  return menu.children?.some((c) => c.is_visible !== false) ?? false
}
function visibleChildren(menu: MenuNode): MenuNode[] {
  return menu.children?.filter((c) => c.is_visible !== false) || []
}
function resolvePath(...parts: (string | undefined)[]): string {
  return parts.filter(Boolean).join('/').replace(/\/+/g, '/') || '/'
}

function handleCommand(cmd: string) {
  if (cmd === 'logout') authStore.logout()
}
</script>

<style scoped lang="scss">
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--app-bg);
}

/* ---------- 侧边栏 ---------- */
.aside {
  width: 232px;
  flex: 0 0 232px;
  display: flex;
  flex-direction: column;
  padding: 16px 12px 14px;
  background: linear-gradient(180deg, #0b1220 0%, #0f172a 60%, #0b1220 100%);
  position: relative;
  overflow: hidden;
  transition: width 0.25s ease, flex-basis 0.25s ease;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(320px 180px at 10% -5%, rgba(34, 211, 238, 0.18), transparent 65%),
      radial-gradient(360px 220px at 110% 40%, rgba(99, 102, 241, 0.14), transparent 70%);
  }
  &.collapsed {
    width: 68px;
    flex-basis: 68px;
    padding-left: 8px;
    padding-right: 8px;
  }
  > * {
    position: relative;
    z-index: 1;
  }
}
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 6px 18px;
}
.logo-mark {
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #22d3ee, #6366f1 60%, #a855f7);
  color: #04101d;
  font-weight: 800;
  font-size: 15px;
  box-shadow: 0 0 22px rgba(56, 189, 248, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.4);
}
.logo-name {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 0.4px;
  background: linear-gradient(90deg, #e0f2fe, #a5b4fc);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  white-space: nowrap;
}
.logo-sub {
  font-size: 9.5px;
  color: #4f6482;
  letter-spacing: 2px;
  margin-top: 3px;
  white-space: nowrap;
}
.nav-label {
  font-size: 10px;
  color: #475569;
  letter-spacing: 2px;
  padding: 4px 12px 8px;
}
.menu-scroll {
  flex: 1;
  overflow: hidden;
}
:deep(.el-menu) {
  background: transparent;
  border-right: none;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: #94a3b8;
  --el-menu-active-color: #e0e7ff;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.05);
  --el-menu-item-height: 42px;
  --el-menu-sub-item-height: 38px;
}
:deep(.el-menu-item),
:deep(.el-sub-menu__title) {
  border-radius: 9px;
  margin: 2px 0;
  font-size: 13.5px;
  color: #94a3b8;
}
:deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.26), rgba(34, 211, 238, 0.07));
  color: #e0e7ff;
  font-weight: 500;
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.3);
  position: relative;
  &::before {
    content: '';
    position: absolute;
    left: 0;
    top: 10px;
    bottom: 10px;
    width: 3px;
    border-radius: 0 3px 3px 0;
    background: linear-gradient(180deg, #22d3ee, #6366f1);
    box-shadow: 0 0 10px rgba(34, 211, 238, 0.8);
  }
}
:deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: #c7d2fe;
}
:deep(.el-menu--collapse) {
  width: 100%;
}
:deep(.el-menu-item .el-icon),
:deep(.el-sub-menu__title .el-icon) {
  color: #64748b;
}
:deep(.el-menu-item.is-active .el-icon) {
  color: #a5b4fc;
}
.engine-card {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.1), rgba(99, 102, 241, 0.06));
  border: 1px solid rgba(34, 211, 238, 0.16);
}
.engine-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-family: Consolas, monospace;
  font-size: 10.5px;
  letter-spacing: 1px;
  color: #67e8f9;
  i {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #34d399;
    box-shadow: 0 0 10px #34d399;
  }
}
.engine-meta {
  margin-top: 6px;
  font-family: Consolas, monospace;
  font-size: 10px;
  color: #4f6482;
}

/* ---------- 主体 ---------- */
.body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.header {
  height: 64px;
  flex: 0 0 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  background: rgba(255, 255, 255, 0.86);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--app-border);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}
.collapse-btn {
  font-size: 19px;
  color: #64748b;
  cursor: pointer;
  padding: 6px;
  border-radius: 8px;
  transition: all 0.18s;
  &:hover {
    color: var(--brand-indigo);
    background: #f1f5ff;
  }
}
.crumb {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #94a3b8;
  .sep {
    color: #cbd5e1;
  }
  .current {
    color: #334155;
    font-weight: 500;
  }
}
.header-right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.project-select {
  width: 210px;
  :deep(.el-select__wrapper) {
    border-radius: 999px;
    background: #f8fafc;
    box-shadow: 0 0 0 1px #e7ecf4 inset;
    padding-left: 12px;
  }
}
.project-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.14);
  display: inline-block;
}
.env-select {
  width: 138px;
  :deep(.el-select__wrapper) {
    border-radius: 999px;
    background: #f8fafc;
    box-shadow: 0 0 0 1px #e7ecf4 inset;
    padding-left: 12px;
  }
}
.env-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #6366f1;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.14);
  display: inline-block;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 5px 10px 5px 5px;
  border-radius: 999px;
  transition: background 0.18s;
  &:hover {
    background: #f4f7fc;
  }
}
.avatar {
  background: linear-gradient(135deg, #22d3ee, #6366f1);
  color: #04101d;
  font-weight: 700;
  box-shadow: 0 0 14px rgba(56, 189, 248, 0.35);
}
.username {
  font-size: 13px;
  color: #334155;
}
.caret {
  font-size: 12px;
  color: #94a3b8;
}
.content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 22px 26px;
}
</style>
