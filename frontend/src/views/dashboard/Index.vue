<template>
  <div class="dashboard">
    <div class="page-head">
      <div>
        <h2>工作台</h2>
        <div class="sub">欢迎回来，{{ authStore.displayName }}，这里是你的测试工作概览</div>
      </div>
      <div class="live"><i />SYSTEM ONLINE</div>
    </div>

    <el-row :gutter="14">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon indigo"><el-icon :size="20"><User /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ authStore.userInfo?.username || '-' }}</div>
            <div class="stat-label">当前用户</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon cyan"><el-icon :size="20"><Folder /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ appStore.currentProjectName || '未选择' }}</div>
            <div class="stat-label">当前项目</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon violet"><el-icon :size="20"><Lock /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ rolesText }}</div>
            <div class="stat-label">角色</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon emerald"><el-icon :size="20"><Key /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ permCount }}</div>
            <div class="stat-label">权限码</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <div class="page-card welcome">
      <div class="welcome-main">
        <h3>欢迎使用 AI 自动化测试平台</h3>
        <p>
          左侧菜单根据你的角色权限动态展示，顶部可切换当前项目。用例支持 API / WEB 双模式可视化编排，
          并可批量导入导出。
        </p>
      </div>
      <div class="welcome-actions">
        <el-button type="primary" @click="go('/testcase/list')"><el-icon><Plus /></el-icon> 新建用例</el-button>
        <el-button @click="go('/testcase/list')">进入用例列表</el-button>
      </div>
    </div>

    <div class="page-card quick-panel">
      <div class="panel-title">快捷入口</div>
      <div class="quick-nav">
        <div class="quick-item" @click="go('/testcase/list')">
          <span class="qi-icon indigo"><el-icon><Document /></el-icon></span>
          <div><b>测试用例</b><small>设计与管理用例</small></div>
        </div>
        <div class="quick-item" @click="go('/project/list')">
          <span class="qi-icon cyan"><el-icon><Connection /></el-icon></span>
          <div><b>项目空间</b><small>查看所属项目</small></div>
        </div>
        <div class="quick-item" @click="go('/system/user')">
          <span class="qi-icon violet"><el-icon><UserFilled /></el-icon></span>
          <div><b>用户管理</b><small>成员与角色</small></div>
        </div>
        <div class="quick-item" @click="ElMessage.info('执行记录模块将在下一阶段上线')">
          <span class="qi-icon emerald"><el-icon><DataAnalysis /></el-icon></span>
          <div><b>执行记录</b><small>即将上线</small></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useAppStore } from '@/stores/app'

const router = useRouter()
const authStore = useAuthStore()
const appStore = useAppStore()

const rolesText = computed(() => authStore.roles.map((r) => r.name).join(', ') || '-')
const permCount = computed(() => {
  const p = authStore.permissions
  if (p === 'all') return '全部'
  return Array.isArray(p) ? p.length : 0
})

function go(path: string) {
  router.push(path)
}
</script>

<style scoped lang="scss">
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.live {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 10px;
  border-radius: 6px;
  font-family: Consolas, monospace;
  font-size: 10.5px;
  letter-spacing: 1px;
  color: #0891b2;
  background: #ecfeff;
  border: 1px solid #cffafe;
  i {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: #06b6d4;
    box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.15);
  }
}
.stat-card {
  background: #fff;
  border: 1px solid rgba(231, 236, 244, 0.9);
  border-radius: 14px;
  box-shadow: var(--app-shadow);
  padding: 18px;
  display: flex;
  align-items: center;
  gap: 14px;
  height: 96px;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 26px rgba(16, 24, 40, 0.08);
  }
}
.stat-icon {
  width: 44px;
  height: 44px;
  flex: 0 0 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  &.indigo {
    color: #4f46e5;
    background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  }
  &.cyan {
    color: #0891b2;
    background: linear-gradient(135deg, #ecfeff, #cffafe);
  }
  &.violet {
    color: #7c3aed;
    background: linear-gradient(135deg, #f5f3ff, #ede9fe);
  }
  &.emerald {
    color: #059669;
    background: linear-gradient(135deg, #ecfdf5, #d1fae5);
  }
}
.stat-info {
  min-width: 0;
}
.stat-value {
  font-size: 19px;
  font-weight: 650;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.stat-label {
  font-size: 12.5px;
  color: #8b9ab1;
  margin-top: 4px;
}
.welcome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 20px 22px;
  h3 {
    margin: 0 0 8px;
    font-size: 16px;
    font-weight: 650;
    color: #0f172a;
  }
  p {
    margin: 0;
    font-size: 13px;
    line-height: 1.8;
    color: #64748b;
    max-width: 720px;
  }
}
.welcome-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}
.quick-panel {
  padding: 18px 20px 20px;
}
.panel-title {
  font-size: 14px;
  font-weight: 650;
  color: #1e293b;
  margin-bottom: 14px;
}
.quick-nav {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.quick-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid #eef2f8;
  background: #fbfcff;
  transition: all 0.18s;
  cursor: pointer;
  &:hover {
    border-color: #dfe3fd;
    background: #f7f8ff;
  }
  b {
    display: block;
    font-size: 13.5px;
    font-weight: 600;
    color: #1e293b;
  }
  small {
    display: block;
    margin-top: 3px;
    font-size: 11.5px;
    color: #94a3b8;
  }
}
.qi-icon {
  width: 38px;
  height: 38px;
  flex: 0 0 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 17px;
  &.indigo {
    color: #4f46e5;
    background: #eef2ff;
  }
  &.cyan {
    color: #0891b2;
    background: #ecfeff;
  }
  &.violet {
    color: #7c3aed;
    background: #f5f3ff;
  }
  &.emerald {
    color: #059669;
    background: #ecfdf5;
  }
}
</style>
