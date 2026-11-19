<template>
  <div class="bug-wrap">
    <div class="page-head">
      <div>
        <h2>缺陷管理</h2>
        <div class="sub">缺陷跟踪与处理闭环，共 {{ pagination.total }} 条</div>
      </div>
      <div class="actions">
        <el-button v-permission="'bug:create'" type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon> 新建 Bug
        </el-button>
      </div>
    </div>

    <!-- 快捷视角 -->
    <div class="page-card tabs-bar">
        <el-tabs v-model="activeTab" @tab-change="handleTabChange">
          <el-tab-pane label="全部 Bug" name="all" />
          <el-tab-pane label="指派给我的" name="assigned" />
          <el-tab-pane label="我创建的" name="created" />
          <el-tab-pane label="待我验证的" name="verify" />
        </el-tabs>
      </div>

      <!-- 筛选 -->
      <div class="page-card filter-bar">
        <el-form :inline="true" size="default" @submit.prevent>
          <el-form-item>
            <el-select v-model="projectFilter" style="width: 150px">
              <el-option label="全部项目" value="all" />
              <el-option label="未关联项目" value="unassigned" />
              <el-option v-for="p in projectOptions" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="filters.keyword"
              placeholder="标题 / 编号"
              clearable
              style="width: 170px"
              @keyup.enter="handleSearch"
            />
          </el-form-item>
          <el-form-item>
            <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
              <el-option v-for="s in STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-select v-model="filters.severity" placeholder="严重程度" clearable style="width: 116px">
              <el-option v-for="s in SEVERITIES" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-select v-model="filters.priority" placeholder="优先级" clearable style="width: 100px">
              <el-option v-for="p in ['P0', 'P1', 'P2', 'P3']" :key="p" :label="p" :value="p" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-select v-model="filters.environment_id" placeholder="环境" clearable style="width: 120px">
              <el-option v-for="e in environmentOptions" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-cascader
              v-model="filters.module_id"
              :options="moduleOptions"
              :props="cascaderProps"
              clearable
              placeholder="所属模块"
              style="width: 160px"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSearch">搜索</el-button>
            <el-button @click="resetFilters">重置</el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 用例联动提示 -->
      <div v-if="caseFilterId" class="case-tip">
        <span>仅看用例 <b>{{ caseFilterNo || '#' + caseFilterId }}</b> 关联的未关闭 Bug</span>
        <el-button link type="primary" @click="clearCaseFilter">清除筛选</el-button>
      </div>

      <!-- 表格 -->
      <div class="page-card table-wrap">
        <el-table :data="tableData" v-loading="loading" row-key="id">
          <el-table-column prop="bug_no" label="编号" width="96">
            <template #default="{ row }">
              <span class="bug-no">{{ row.bug_no }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="title" label="缺陷标题" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <el-link type="primary" :underline="false" @click="openDetail(row.id)">{{ row.title }}</el-link>
            </template>
          </el-table-column>
          <el-table-column label="所属项目" width="136" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.project_name" class="project-name">{{ row.project_name }}</span>
              <el-tag v-else size="small" type="info" effect="plain" class="unlinked-tag">未关联项目</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="环境" width="104" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.environment_name" size="small" effect="plain" type="info">
                {{ row.environment_name }}
              </el-tag>
              <span v-else class="muted">-</span>
            </template>
          </el-table-column>
          <el-table-column label="严重程度" width="96" align="center">
            <template #default="{ row }">
              <span class="severity-pill" :class="row.severity.toLowerCase()">
                {{ row.severity_display }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="priority" label="优先级" width="74" align="center">
            <template #default="{ row }">
              <span class="tech-pill" :class="row.priority.toLowerCase()">{{ row.priority }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="reproducibility_display" label="复现概率" width="88" align="center" />
          <el-table-column label="状态" width="126">
            <template #default="{ row }">
              <div class="status-cell">
                <span class="status-text" :class="statusClass(row.status)">
                  <i />{{ row.status_display }}
                </span>
                <span v-if="row.status === 'CLOSED' && row.resolution" class="resolution">
                  {{ row.resolution_display }}
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="处理人" min-width="150">
            <template #default="{ row }">
              <template v-if="row.assignees?.length">
                <el-tag
                  v-for="a in row.assignees"
                  :key="a.id"
                  size="small"
                  class="assignee-tag"
                >{{ a.real_name || a.username }}</el-tag>
              </template>
              <span v-else class="muted">未指派</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="118">
            <template #default="{ row }">
              <span class="time">{{ formatTime(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="openDetail(row.id)">详情</el-button>
              <el-button v-permission="'bug:edit'" size="small" link type="primary" @click="openEdit(row.id)">编辑</el-button>
              <el-button v-permission="'bug:delete'" size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-wrap">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.page_size"
            :total="pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="loadList"
            @current-change="loadList"
          />
        </div>
      </div>

    <BugFormDrawer
      v-model="formVisible"
      :project-id="projectId"
      :bug-id="editingId"
      @saved="handleSaved"
    />
    <BugDetailDrawer v-model="detailVisible" :bug-id="detailId" @updated="loadList" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { bugApi, environmentApi, moduleApi, projectApi } from '@/api'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import BugFormDrawer from '../components/BugFormDrawer.vue'
import BugDetailDrawer from '../components/BugDetailDrawer.vue'

const STATUS_OPTIONS = [
  { value: 'NEW', label: '新建' },
  { value: 'ASSIGNED', label: '已指派' },
  { value: 'IN_PROGRESS', label: '处理中' },
  { value: 'RESOLVED', label: '已解决/待验证' },
  { value: 'CLOSED', label: '已关闭' },
  { value: 'REOPENED', label: '重新打开' },
]
const SEVERITIES = [
  { value: 'BLOCKER', label: '阻塞' },
  { value: 'ERROR', label: '严重' },
  { value: 'NORMAL', label: '一般' },
  { value: 'OTHER', label: '其他' },
]
const cascaderProps = {
  value: 'id',
  label: 'name',
  children: 'children',
  checkStrictly: true,
  emitPath: false,
}

const appStore = useAppStore()
const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const projectId = computed(() => appStore.currentProjectId)
const currentUserId = computed(() => authStore.userInfo?.id)

const activeTab = ref('all')
const loading = ref(false)
const tableData = ref<any[]>([])
const projectOptions = ref<any[]>([])
const projectFilter = ref<'all' | 'unassigned' | number>('all')
const environmentOptions = ref<any[]>([])
const moduleOptions = ref<any[]>([])
const caseFilterId = ref<number | null>(null)
const caseFilterNo = ref('')
const caseFilterUnclosed = ref(false)

const filters = reactive({
  keyword: '',
  status: '',
  severity: '',
  priority: '',
  environment_id: null as number | null,
  module_id: null as number | null,
})
const pagination = reactive({ page: 1, page_size: 20, total: 0 })

const formVisible = ref(false)
const editingId = ref<number | null>(null)
const detailVisible = ref(false)
const detailId = ref<number | null>(null)

// ---------- 数据加载 ----------
async function loadList() {
  loading.value = true
  try {
    const projectParam = typeof projectFilter.value === 'number'
      ? projectFilter.value
      : (projectFilter.value === 'unassigned' ? 'unassigned' : undefined)
    const params: any = {
      project_id: projectParam,
      keyword: filters.keyword || undefined,
      status: filters.status || undefined,
      severity: filters.severity || undefined,
      priority: filters.priority || undefined,
      environment_id: filters.environment_id || undefined,
      module_id: filters.module_id || undefined,
      testcase_id: caseFilterId.value || undefined,
      unclosed: caseFilterUnclosed.value ? '1' : undefined,
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (activeTab.value === 'assigned' && currentUserId.value) {
      params.assignee_id = currentUserId.value
    } else if (activeTab.value === 'created' && currentUserId.value) {
      params.creator_id = currentUserId.value
    } else if (activeTab.value === 'verify' && currentUserId.value) {
      params.assignee_id = currentUserId.value
      params.status = 'RESOLVED'
    }
    const res = await bugApi.list(params)
    tableData.value = res.results || []
    pagination.total = res.count || 0
  } catch {
    tableData.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  environmentOptions.value = []
  moduleOptions.value = []
  const pid = typeof projectFilter.value === 'number' ? projectFilter.value : null
  if (!pid) return
  try {
    const [envs, treeRes] = await Promise.all([
      environmentApi.list(pid),
      moduleApi.tree(pid),
    ])
    environmentOptions.value = envs || []
    moduleOptions.value = (treeRes?.tree || []).map(toCascaderNode)
  } catch {
    environmentOptions.value = []
    moduleOptions.value = []
  }
}

async function loadProjects() {
  try {
    projectOptions.value = await projectApi.myProjects()
  } catch {
    projectOptions.value = []
  }
}

function toCascaderNode(node: any): any {
  return {
    id: node.id,
    name: node.name,
    children: (node.children || []).map(toCascaderNode),
  }
}

// ---------- 交互 ----------
function handleTabChange() {
  pagination.page = 1
  loadList()
}
function handleSearch() {
  pagination.page = 1
  loadList()
}
function resetFilters() {
  const wasAll = projectFilter.value === 'all'
  filters.keyword = ''
  filters.status = ''
  filters.severity = ''
  filters.priority = ''
  filters.environment_id = null
  filters.module_id = null
  pagination.page = 1
  projectFilter.value = 'all'
  if (wasAll) loadList()
}

function openCreate() {
  editingId.value = null
  formVisible.value = true
}
function openEdit(id: number) {
  editingId.value = id
  formVisible.value = true
}
function openDetail(id: number) {
  detailId.value = id
  detailVisible.value = true
}
function handleSaved() {
  loadList()
}
function clearCaseFilter() {
  caseFilterId.value = null
  caseFilterNo.value = ''
  caseFilterUnclosed.value = false
  router.replace({ path: '/bug/list' })
  loadList()
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除缺陷「${row.bug_no} ${row.title}」?`, '删除缺陷', {
    type: 'warning',
  })
  await bugApi.delete(row.id)
  ElMessage.success('删除成功')
  loadList()
}

// ---------- 展示辅助 ----------
function statusClass(s: string) {
  return ({
    NEW: 'new', ASSIGNED: 'assigned', IN_PROGRESS: 'in_progress',
    RESOLVED: 'resolved', CLOSED: 'closed', REOPENED: 'reopened',
  } as Record<string, string>)[s] || 'new'
}
function formatTime(t: string) {
  return t ? t.replace('T', ' ').slice(5, 16) : '-'
}

// ---------- 生命周期 ----------
onMounted(async () => {
  const tid = Number(route.query.testcase_id)
  if (tid) {
    caseFilterId.value = tid
    caseFilterNo.value = String(route.query.case_no || '')
    caseFilterUnclosed.value = String(route.query.unclosed || '') === '1'
  }
  await loadProjects()
  await loadMeta()
  loadList()
})

watch(projectFilter, async () => {
  filters.module_id = null
  filters.environment_id = null
  pagination.page = 1
  await loadMeta()
  loadList()
})
</script>

<style scoped lang="scss">
.bug-wrap {
  min-height: calc(100vh - 110px);
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  h2 {
    margin: 0;
    font-size: 20px;
    color: #0f172a;
  }
  .sub {
    margin-top: 4px;
    font-size: 12.5px;
    color: #94a3b8;
  }
}
.tabs-bar {
  padding: 4px 14px 0;
  :deep(.el-tabs__header) {
    margin-bottom: 0;
  }
  :deep(.el-tabs__nav-wrap::after) {
    display: none;
  }
}
.filter-bar {
  padding: 12px 14px 0;
  :deep(.el-form-item) {
    margin-bottom: 12px;
    margin-right: 10px;
  }
}
.case-tip {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12.5px;
  color: #4f46e5;
  background: rgba(79, 70, 229, 0.06);
  border: 1px solid rgba(79, 70, 229, 0.16);
  border-radius: 10px;
  padding: 8px 14px;
}
.table-wrap {
  padding: 4px 6px 8px;
}
.bug-no {
  font-family: Consolas, monospace;
  font-size: 12.5px;
  color: #4f46e5;
}
.project-name {
  font-size: 12.5px;
  color: #475569;
}
.unlinked-tag {
  color: #94a3b8;
}
.severity-pill {
  display: inline-block;
  padding: 1px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid transparent;
  &.blocker { color: #b91c1c; background: #fee2e2; border-color: #fecaca; }
  &.error { color: #b45309; background: #fef3c7; border-color: #fde68a; }
  &.normal { color: #1d4ed8; background: #dbeafe; border-color: #bfdbfe; }
  &.other { color: #475569; background: #f1f5f9; border-color: #e2e8f0; }
}
.status-cell {
  display: flex;
  flex-direction: column;
  line-height: 1.35;
  .resolution {
    font-size: 11px;
    color: #94a3b8;
  }
  .status-text {
    &.new { color: #64748b; }
    &.new i { background: #94a3b8; }
    &.assigned { color: #1d4ed8; }
    &.assigned i { background: #3b82f6; }
    &.in_progress { color: #b45309; }
    &.in_progress i { background: #f59e0b; }
    &.resolved { color: #6d28d9; }
    &.resolved i { background: #8b5cf6; }
    &.closed { color: #15803d; }
    &.closed i { background: #22c55e; }
    &.reopened { color: #b91c1c; }
    &.reopened i { background: #ef4444; }
  }
}
.assignee-tag {
  margin: 1px 4px 1px 0;
}
.time {
  font-family: Consolas, monospace;
  font-size: 12px;
  color: #94a3b8;
}
.muted {
  color: #cbd5e1;
}
.pagination-wrap {
  margin-top: 8px;
  padding: 8px 8px 4px;
  display: flex;
  justify-content: flex-end;
}
</style>
