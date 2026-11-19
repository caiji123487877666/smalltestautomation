<template>
  <div class="testcase-wrap">
    <!-- 页面标题 -->
    <div class="page-head">
      <div>
        <h2>测试用例</h2>
        <div class="sub">管理项目下的接口与页面自动化用例，共 {{ pagination.total }} 条</div>
      </div>
      <div class="actions">
        <el-button v-permission="'testcase:import_export'" @click="excelImportVisible = true">
          <el-icon><Upload /></el-icon> Excel 导入
        </el-button>
        <el-button v-permission="'testcase:import_export'" @click="swaggerImportVisible = true">
          <el-icon><Connection /></el-icon> 导入 Swagger
        </el-button>
        <el-button v-permission="'testcase:import_export'" @click="handleExport">
          <el-icon><Download /></el-icon> 导出 Excel
        </el-button>
      </div>
    </div>

    <div class="testcase-page">
    <!-- 左: 模块树 -->
    <ModuleTreePanel
      ref="modulePanelRef"
      :project-id="projectId"
      :selected="selectedModule"
      @update:selected="selectModule"
      @loaded="handleModulesLoaded"
      @changed="handleModuleChanged"
    />

    <!-- 右: 用例工作区 -->
    <section class="main-panel">
      <el-empty v-if="!projectId" description="请先在顶部选择项目；若还没有项目，请前往「项目管理」新建" />

      <template v-else>
        <!-- 筛选栏 -->
        <div class="page-card filter-bar">
          <el-form :inline="true" size="default" @submit.prevent>
            <el-form-item>
              <el-input
                v-model="filters.keyword"
                placeholder="标题 / 编号"
                clearable
                style="width: 180px"
                @keyup.enter="handleSearch"
              />
            </el-form-item>
            <el-form-item>
              <el-select v-model="filters.case_type" placeholder="类型" clearable style="width: 100px">
                <el-option label="API" value="API" />
                <el-option label="WEB" value="WEB" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-select v-model="filters.priority" placeholder="优先级" clearable style="width: 105px">
                <el-option v-for="p in ['P0', 'P1', 'P2', 'P3']" :key="p" :label="p" :value="p" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-select v-model="filters.status" placeholder="状态" clearable style="width: 110px">
                <el-option label="草稿" value="DRAFT" />
                <el-option label="可用" value="ACTIVE" />
                <el-option label="已废弃" value="DEPRECATED" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-input v-model="filters.tag" placeholder="标签" clearable style="width: 110px" @keyup.enter="handleSearch" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSearch">搜索</el-button>
              <el-button @click="resetFilters">重置</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 工具条 -->
        <div class="page-card toolbar">
          <div class="toolbar-left">
            <el-button
              v-permission="'testcase:create'"
              type="primary"
              @click="openCreate"
            >
              <el-icon><Plus /></el-icon> 新建用例
            </el-button>
          </div>
          <div class="toolbar-right">
            <span class="selected-tip">已选 {{ selectedIds.length }} 条</span>
            <el-button v-permission="'testcase:delete'" size="small" type="danger" plain :disabled="!selectedIds.length" @click="batchDelete">
              批量删除
            </el-button>
            <el-dropdown :disabled="!selectedIds.length" @command="(cmd: string) => batchUpdate('priority', cmd)">
              <el-button size="small" :disabled="!selectedIds.length">批量优先级<el-icon><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-for="p in ['P0', 'P1', 'P2', 'P3']" :key="p" :command="p">{{ p }}</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-dropdown :disabled="!selectedIds.length" @command="(cmd: string) => batchUpdate('status', cmd)">
              <el-button size="small" :disabled="!selectedIds.length">批量状态<el-icon><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="DRAFT">草稿</el-dropdown-item>
                  <el-dropdown-item command="ACTIVE">可用</el-dropdown-item>
                  <el-dropdown-item command="DEPRECATED">已废弃</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button size="small" :disabled="!selectedIds.length" @click="batchMoveVisible = true">批量移动</el-button>
          </div>
        </div>

        <!-- 表格 -->
        <div class="page-card table-wrap">
          <el-table
            :data="tableData"
            v-loading="loading"
            row-key="id"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="40" reserve-selection />
            <el-table-column prop="case_no" label="编号" width="94">
              <template #default="{ row }">
                <span class="case-no">{{ row.case_no }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="用例标题" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">
                <div class="title-cell">
                  <el-link type="primary" :underline="false" @click="openEdit(row.id)">{{ row.title }}</el-link>
                  <span
                    v-if="row.open_bug_count > 0"
                    class="bug-badge"
                    title="查看该用例未关闭的 Bug"
                    @click.stop="goCaseBugs(row)"
                  >🐞 {{ row.open_bug_count }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="case_type" label="类型" width="74" align="center">
              <template #default="{ row }">
                <span class="tech-pill" :class="row.case_type === 'API' ? 'api' : 'web'">
                  {{ row.case_type }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="priority" label="优先级" width="76" align="center">
              <template #default="{ row }">
                <span class="tech-pill" :class="row.priority.toLowerCase()">{{ row.priority }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="84" align="center">
              <template #default="{ row }">
                <span class="status-text" :class="statusClass(row.status)">
                  <i />{{ statusLabel(row.status) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="module_path" label="所属模块" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <span class="module-path" :class="{ unplanned: !row.module }">{{ row.module_path }}</span>
              </template>
            </el-table-column>
            <el-table-column label="最近更新" width="124">
              <template #default="{ row }">
                <div class="upd">
                  <b>{{ row.updater_name || '-' }}</b>
                  <span>{{ formatTime(row.updated_at) }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="188" fixed="right">
              <template #default="{ row }">
                <el-button v-permission="'testcase:edit'" size="small" link type="primary" @click="openEdit(row.id)">编辑</el-button>
                <el-button v-permission="'bug:create'" size="small" link type="warning" @click="openBugForm(row)">提 Bug</el-button>
                <el-button v-permission="'testcase:create'" size="small" link type="success" @click="handleDuplicate(row)">复制</el-button>
                <el-button v-permission="'testcase:delete'" size="small" link type="danger" @click="handleDelete(row)">删除</el-button>
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
      </template>
    </section>

    <!-- 用例编辑弹窗 -->
    <TestCaseForm
      v-model="formVisible"
      :project-id="projectId"
      :module-options="moduleTree"
      :default-module-id="createModuleId"
      :case-id="editingId"
      @saved="reloadAll"
    />

    <!-- 提 Bug (自动预填模块/用例/环境/描述模板) -->
    <BugFormDrawer
      v-model="bugFormVisible"
      :project-id="bugFormCase?.project ?? projectId"
      :default-module-id="bugFormCase?.module ?? null"
      :default-testcase-id="bugFormCase?.id ?? null"
      :default-environment-id="appStore.currentEnvironmentId"
      :default-description="bugFormDescription"
      @saved="loadList"
    />

    <!-- Excel 导入 -->
    <ExcelImportDialog
      v-model="excelImportVisible"
      :project-id="projectId"
      @imported="reloadAll"
    />
    <!-- Swagger 导入 -->
    <SwaggerImportDialog
      v-model="swaggerImportVisible"
      :project-id="projectId"
      @imported="reloadAll"
    />

    <!-- 批量移动弹窗 -->
    <el-dialog v-model="batchMoveVisible" title="批量移动到模块" width="420px">
      <el-select v-model="batchMoveModule" clearable placeholder="未规划模块" style="width: 100%">
        <el-option
          v-for="opt in moduleOptions"
          :key="opt.id"
          :label="opt.label"
          :value="opt.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="batchMoveVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchMove">确定移动</el-button>
      </template>
    </el-dialog>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { testcaseApi } from '@/api'
import TestCaseForm from '../components/TestCaseForm.vue'
import ModuleTreePanel from '../components/ModuleTreePanel.vue'
import ExcelImportDialog from '../components/ExcelImportDialog.vue'
import SwaggerImportDialog from '../components/SwaggerImportDialog.vue'
import BugFormDrawer from '@/views/bug/components/BugFormDrawer.vue'

const appStore = useAppStore()
const projectId = computed(() => appStore.currentProjectId)

// ---------- 模块树 ----------
const modulePanelRef = ref()
const moduleTree = ref<any[]>([])
const selectedModule = ref<number | 'all' | 'unassigned'>('all')

function handleModulesLoaded(payload: { tree: any[] }) {
  moduleTree.value = payload.tree || []
}

function selectModule(key: number | 'all' | 'unassigned') {
  selectedModule.value = key
  pagination.page = 1
  loadList()
}

function handleModuleChanged() {
  loadList()
}

// 扁平模块选项 (用于批量移动下拉)
const moduleOptions = computed(() => {
  const result: Array<{ id: number; label: string }> = []
  const walk = (nodes: any[], prefix = '') => {
    for (const n of nodes) {
      result.push({ id: n.id, label: `${prefix}${n.name}` })
      if (n.children?.length) walk(n.children, `${prefix}${n.name} / `)
    }
  }
  walk(moduleTree.value)
  return result
})

// ---------- 列表 ----------
const loading = ref(false)
const tableData = ref<any[]>([])
const selectedIds = ref<number[]>([])
const filters = reactive({
  keyword: '',
  case_type: '',
  priority: '',
  status: '',
  tag: '',
})
const pagination = reactive({ page: 1, page_size: 20, total: 0 })

async function loadList() {
  if (!projectId.value) return
  loading.value = true
  try {
    const res = await testcaseApi.list({
      project_id: projectId.value,
      module_id: selectedModule.value === 'all' ? undefined : selectedModule.value,
      keyword: filters.keyword || undefined,
      case_type: filters.case_type || undefined,
      priority: filters.priority || undefined,
      status: filters.status || undefined,
      tag: filters.tag || undefined,
      page: pagination.page,
      page_size: pagination.page_size,
    })
    tableData.value = res.results || []
    pagination.total = res.count || 0
  } catch {
    tableData.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  pagination.page = 1
  loadList()
}
function resetFilters() {
  filters.keyword = ''
  filters.case_type = ''
  filters.priority = ''
  filters.status = ''
  filters.tag = ''
  pagination.page = 1
  loadList()
}

function handleSelectionChange(rows: any[]) {
  selectedIds.value = rows.map((r) => r.id)
}

async function reloadAll() {
  await modulePanelRef.value?.reload()
  await loadList()
}

// ---------- 编辑/复制/删除 ----------
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const createModuleId = ref<number | null>(null)

function openCreate() {
  if (!projectId.value) {
    ElMessage.warning('还没有可用项目，请先在「项目管理」中创建或选择项目')
    return
  }
  editingId.value = null
  createModuleId.value = typeof selectedModule.value === 'number' ? selectedModule.value : null
  formVisible.value = true
}
function openEdit(id: number) {
  editingId.value = id
  createModuleId.value = null
  formVisible.value = true
}

// ---------- 提 Bug 联动 ----------
const router = useRouter()
const bugFormVisible = ref(false)
const bugFormCase = ref<any>(null)
const bugFormDescription = ref('')

async function openBugForm(row: any) {
  let detail = row
  try {
    detail = await testcaseApi.detail(row.id)
  } catch {
    // 请求失败时使用列表数据
  }
  bugFormCase.value = detail
  bugFormDescription.value = buildBugDescription(detail)
  bugFormVisible.value = true
}

function buildBugDescription(c: any) {
  const lines: string[] = [`**关联用例**: ${c.case_no || ''} ${c.title || ''}`]
  if (c.precondition) {
    lines.push('', '**前置条件**', c.precondition)
  }
  const steps = c.steps
  if (c.case_type === 'API' && steps && !Array.isArray(steps)) {
    lines.push('', '**接口信息**', `${steps.method || 'GET'} ${steps.url || ''}`)
    if (steps.body_type && steps.body_type !== 'none' && steps.body) {
      lines.push('', '```', steps.body, '```')
    }
  } else if (Array.isArray(steps) && steps.length) {
    lines.push('', '**测试步骤**')
    steps.forEach((s: any, i: number) => {
      const value = s.value ? ` → ${s.value}` : ''
      const desc = s.element_desc ? ` (${s.element_desc})` : ''
      lines.push(`${i + 1}. ${s.action || ''} ${s.selector || ''}${value}${desc}`)
    })
  }
  lines.push('', '**预期结果**', '', '**实际结果**', '')
  return lines.join('\n')
}

function goCaseBugs(row: any) {
  router.push({
    path: '/bug/list',
    query: { testcase_id: row.id, case_no: row.case_no, unclosed: '1' },
  })
}

async function handleDuplicate(row: any) {
  await testcaseApi.duplicate(row.id)
  ElMessage.success('已复制用例')
  loadList()
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除用例「${row.title}」?`, '删除用例', { type: 'warning' })
  await testcaseApi.delete(row.id)
  ElMessage.success('删除成功')
  loadList()
}

// ---------- 批量操作 ----------
const excelImportVisible = ref(false)
const swaggerImportVisible = ref(false)
const batchMoveVisible = ref(false)
const batchMoveModule = ref<number | null>(null)

async function batchDelete() {
  if (!selectedIds.value.length) return
  await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 条用例?`, '批量删除', { type: 'warning' })
  const res = await testcaseApi.batchAction({ ids: selectedIds.value, action: 'delete' })
  ElMessage.success(`已删除 ${res.affected} 条`)
  selectedIds.value = []
  loadList()
}

async function batchUpdate(field: 'priority' | 'status', value: string) {
  if (!selectedIds.value.length) return
  const res = await testcaseApi.batchAction({
    ids: selectedIds.value,
    action: field === 'priority' ? 'update_priority' : 'update_status',
    ...(field === 'priority' ? { priority: value } : { status: value }),
  })
  ElMessage.success(`已更新 ${res.affected} 条`)
  loadList()
}

async function handleBatchMove() {
  if (!selectedIds.value.length) return
  const res = await testcaseApi.batchAction({
    ids: selectedIds.value,
    action: 'move_module',
    module_id: batchMoveModule.value,
  })
  ElMessage.success(`已移动 ${res.affected} 条`)
  batchMoveVisible.value = false
  batchMoveModule.value = null
  loadList()
}

// ---------- 导出 ----------
async function handleExport() {
  if (!projectId.value) return
  const params: any = {
    project_id: projectId.value,
    module_id: selectedModule.value === 'all' ? undefined : selectedModule.value,
    keyword: filters.keyword || undefined,
    case_type: filters.case_type || undefined,
    priority: filters.priority || undefined,
    status: filters.status || undefined,
    tag: filters.tag || undefined,
  }
  if (selectedIds.value.length) params.ids = selectedIds.value.join(',')
  const blob = await testcaseApi.exportExcel(params)
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `测试用例_${new Date().getTime()}.xlsx`
  a.click()
  window.URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

// ---------- 展示辅助 ----------
function statusClass(s: string) {
  return ({ DRAFT: 'draft', ACTIVE: 'act', DEPRECATED: 'dep' } as Record<string, string>)[s] || 'draft'
}
function statusLabel(s: string) {
  return ({ DRAFT: '草稿', ACTIVE: '可用', DEPRECATED: '已废弃' } as Record<string, string>)[s] || s
}
function formatTime(t: string) {
  return t ? t.replace('T', ' ').slice(5, 16) : '-'
}

// ---------- 生命周期 ----------
onMounted(() => {
  if (projectId.value) loadList()
})

watch(projectId, (val) => {
  selectedModule.value = 'all'
  pagination.page = 1
  if (val) {
    loadList()
  } else {
    moduleTree.value = []
    tableData.value = []
    pagination.total = 0
  }
})
</script>

<style scoped lang="scss">
.testcase-wrap {
  min-height: calc(100vh - 110px);
}
.testcase-page {
  display: flex;
  gap: 14px;
  align-items: stretch;
}
.module-panel {
  width: 232px;
  flex-shrink: 0;
}
.main-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.filter-bar {
  padding: 12px 14px 0;
  :deep(.el-form-item) {
    margin-bottom: 12px;
    margin-right: 10px;
  }
}
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 14px;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.selected-tip {
  font-size: 12.5px;
  color: #4f46e5;
  margin-right: 2px;
}
.table-wrap {
  padding: 4px 6px 8px;
}
.upd {
  line-height: 1.3;
  b {
    display: block;
    font-size: 12.5px;
    font-weight: 500;
    color: #334155;
  }
  span {
    font-size: 11.5px;
    color: #94a3b8;
    font-family: Consolas, monospace;
  }
}
.muted {
  color: #cbd5e1;
}
.module-path {
  font-size: 12.5px;
  color: #475569;
  &.unplanned {
    color: #94a3b8;
  }
}
.title-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}
.bug-badge {
  flex: 0 0 auto;
  font-size: 11.5px;
  line-height: 1;
  padding: 3px 7px;
  border-radius: 999px;
  color: #dc2626;
  background: #fee2e2;
  border: 1px solid #fecaca;
  cursor: pointer;
  transition: all 0.15s;
  &:hover {
    background: #fecaca;
  }
}
.pagination-wrap {
  margin-top: 8px;
  padding: 8px 8px 4px;
  display: flex;
  justify-content: flex-end;
}
</style>
