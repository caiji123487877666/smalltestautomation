<template>
  <el-drawer
    v-model="visible"
    size="720px"
    direction="rtl"
    destroy-on-close
    append-to-body
  >
    <template #header>
      <div class="drawer-head">
        <div class="drawer-title">
          <h2>{{ isEdit ? '编辑缺陷' : '新建缺陷' }}</h2>
          <span v-if="form.bug_no" class="bug-no-chip">{{ form.bug_no }}</span>
        </div>
      </div>
    </template>

    <el-form ref="formRef" :model="form" :rules="rules" label-width="92px" v-loading="loading">
      <el-form-item label="所属项目">
        <el-select
          v-model="form.project"
          clearable
          placeholder="未关联项目 (全局 Bug)"
          style="width: 100%"
          @change="handleProjectChange"
        >
          <el-option v-for="p in projectOptions" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <div v-if="!form.project" class="form-tip">
          未选择项目时, 处理人可选系统内全部激活用户; 模块/环境/关联用例不可用
        </div>
      </el-form-item>

      <el-form-item label="缺陷标题" prop="title">
        <el-input v-model="form.title" maxlength="255" show-word-limit placeholder="简明描述问题现象" />
      </el-form-item>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="所属模块">
            <el-cascader
              v-model="form.module"
              :options="moduleOptions"
              :props="cascaderProps"
              :disabled="!form.project"
              clearable
              :placeholder="form.project ? '未规划模块' : '请先选择项目'"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="关联用例">
            <el-select
              v-model="form.testcase"
              filterable
              remote
              clearable
              :disabled="!form.project"
              :remote-method="searchCases"
              :loading="caseLoading"
              :placeholder="form.project ? '搜索用例编号 / 标题' : '请先选择项目'"
              style="width: 100%"
            >
              <el-option
                v-for="c in caseOptions"
                :key="c.id"
                :label="`${c.case_no} ${c.title}`"
                :value="c.id"
              />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="发现环境">
            <el-select
              v-model="form.environment"
              :disabled="!form.project"
              clearable
              :placeholder="form.project ? '选择环境' : '请先选择项目'"
              style="width: 100%"
            >
              <el-option v-for="e in environmentOptions" :key="e.id" :label="e.name" :value="e.id" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="严重程度">
            <el-select v-model="form.severity" style="width: 100%">
              <el-option v-for="s in SEVERITIES" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="优先级">
            <el-select v-model="form.priority" style="width: 100%">
              <el-option v-for="p in ['P0', 'P1', 'P2', 'P3']" :key="p" :label="p" :value="p" />
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="8">
          <el-form-item label="复现概率">
            <el-select v-model="form.reproducibility" style="width: 100%">
              <el-option v-for="r in REPRODUCIBILITIES" :key="r.value" :label="r.label" :value="r.value" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="16">
          <el-form-item label="处理人">
            <el-select
              v-model="form.assignee_ids"
              multiple
              filterable
              clearable
              :placeholder="form.project ? '选择项目成员 (可多选, 不限角色)' : '选择系统激活用户 (可多选)'"
              style="width: 100%"
            >
              <el-option
                v-for="m in memberOptions"
                :key="m.id"
                :label="m.real_name || m.username"
                :value="m.id"
              >
                <span>{{ m.real_name || m.username }}</span>
                <span class="member-role">{{ (m.roles || []).map((r: any) => r.name).join(' / ') }}</span>
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
      </el-row>

      <el-divider content-position="left">详细描述 (支持粘贴截图)</el-divider>

      <el-form-item label-width="0">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="10"
          placeholder="复现步骤 / 期望结果 / 实际结果, 支持 Markdown; 可直接粘贴截图"
          @paste="handlePaste"
        />
      </el-form-item>

      <el-form-item label="截图附件" label-width="92px">
        <div class="upload-area">
          <div class="shot-list">
            <div v-for="(url, idx) in form.attachments" :key="url" class="shot-item">
              <el-image :src="url" :preview-src-list="form.attachments" :initial-index="idx" fit="cover" />
              <span class="shot-del" @click="form.attachments.splice(idx, 1)">×</span>
            </div>
          </div>
          <el-upload
            :show-file-list="false"
            accept="image/*"
            :http-request="handleUpload"
            :disabled="uploading"
          >
            <el-button size="small" :loading="uploading">+ 上传截图</el-button>
          </el-upload>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSubmit">
        {{ isEdit ? '保存修改' : '创建缺陷' }}
      </el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { bugApi, moduleApi, projectApi, environmentApi, testcaseApi } from '@/api'
import { useAppStore } from '@/stores/app'

const props = defineProps<{
  projectId: number | null
  bugId?: number | null
  defaultModuleId?: number | null
  defaultTestcaseId?: number | null
  defaultEnvironmentId?: number | null
  defaultDescription?: string
}>()
const emit = defineEmits<{ (e: 'saved'): void }>()

const appStore = useAppStore()

const SEVERITIES = [
  { value: 'BLOCKER', label: '阻塞 Blocker' },
  { value: 'ERROR', label: '严重 Error' },
  { value: 'NORMAL', label: '一般 Normal' },
  { value: 'OTHER', label: '其他 Other' },
]
const REPRODUCIBILITIES = [
  { value: 'ALWAYS', label: '必现' },
  { value: 'OFTEN', label: '大概率' },
  { value: 'SOMETIMES', label: '偶现' },
]

const cascaderProps = {
  value: 'id',
  label: 'name',
  children: 'children',
  checkStrictly: true,
  emitPath: false,
}

const visible = defineModel<boolean>({ required: true })
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const caseLoading = ref(false)
const formRef = ref<FormInstance>()

const moduleOptions = ref<any[]>([])
const memberOptions = ref<any[]>([])
const environmentOptions = ref<any[]>([])
const caseOptions = ref<any[]>([])
const projectOptions = ref<any[]>([])

const isEdit = computed(() => !!props.bugId)

const form = reactive<any>({
  id: null,
  bug_no: '',
  project: null,
  title: '',
  module: null,
  testcase: null,
  environment: null,
  severity: 'NORMAL',
  priority: 'P1',
  reproducibility: 'ALWAYS',
  description: '',
  attachments: [],
  assignee_ids: [],
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入缺陷标题', trigger: 'blur' }],
}

watch(visible, async (val) => {
  if (!val) return
  resetForm()
  await loadProjects()
  // 缓存的项目可能已被删除, 回退为"未关联项目", 避免依赖接口报"项目不存在"
  if (
    form.project &&
    projectOptions.value.length &&
    !projectOptions.value.some((p: any) => p.id === form.project)
  ) {
    form.project = null
    form.environment = null
  }
  if (props.bugId) {
    await loadDetail(props.bugId)
  } else {
    await refreshDependencies(true)
  }
})

function resetForm() {
  Object.assign(form, {
    id: null,
    bug_no: '',
    project: props.projectId ?? appStore.currentProjectId ?? null,
    title: '',
    module: props.defaultModuleId ?? null,
    testcase: props.defaultTestcaseId ?? null,
    environment: props.defaultEnvironmentId ?? appStore.currentEnvironmentId ?? null,
    severity: 'NORMAL',
    priority: 'P1',
    reproducibility: 'ALWAYS',
    description: props.defaultDescription || '',
    attachments: [],
    assignee_ids: [],
  })
  formRef.value?.clearValidate()
}

async function loadProjects() {
  try {
    projectOptions.value = await projectApi.myProjects()
  } catch {
    projectOptions.value = []
  }
}

async function handleProjectChange() {
  await refreshDependencies(true)
}

async function refreshDependencies(clearRelations = true) {
  if (clearRelations) {
    form.module = null
    form.testcase = null
    form.environment = null
  }
  moduleOptions.value = []
  environmentOptions.value = []
  caseOptions.value = []

  const pid = form.project
  loading.value = true
  try {
    // 处理人: 有项目取项目成员, 无项目取系统全部激活用户
    memberOptions.value = await bugApi.availableAssignees(pid)
    if (!pid) return

    const [treeRes, envs] = await Promise.all([
      moduleApi.tree(pid),
      environmentApi.list(pid),
    ])
    moduleOptions.value = (treeRes?.tree || []).map(toCascaderNode)
    environmentOptions.value = envs || []
    if (!form.environment) {
      const def = environmentOptions.value.find((e) => e.is_default) || environmentOptions.value[0]
      form.environment = def?.id ?? null
    }
    await searchCases('')
    if (props.defaultTestcaseId && !caseOptions.value.some((c) => c.id === props.defaultTestcaseId)) {
      try {
        const detail = await testcaseApi.detail(props.defaultTestcaseId)
        caseOptions.value.unshift(detail)
      } catch {
        // ignore
      }
    }
  } finally {
    loading.value = false
  }
}

function toCascaderNode(node: any): any {
  return {
    id: node.id,
    name: node.name,
    children: (node.children || []).map(toCascaderNode),
  }
}

async function loadDetail(id: number) {
  loading.value = true
  try {
    const detail = await bugApi.detail(id)
    form.project = detail.project ?? null
    // 先加载该项目下的模块/环境/用例, 再回填详情
    await refreshDependencies(false)
    Object.assign(form, {
      id: detail.id,
      bug_no: detail.bug_no,
      project: detail.project ?? null,
      title: detail.title,
      module: detail.module ?? null,
      testcase: detail.testcase ?? null,
      environment: detail.environment ?? null,
      severity: detail.severity,
      priority: detail.priority,
      reproducibility: detail.reproducibility,
      description: detail.description || '',
      attachments: detail.attachments || [],
      assignee_ids: (detail.assignees || []).map((a: any) => a.id),
    })
    if (detail.testcase && !caseOptions.value.some((c) => c.id === detail.testcase)) {
      caseOptions.value.unshift({
        id: detail.testcase,
        case_no: detail.testcase_no,
        title: detail.testcase_title,
      })
    }
  } finally {
    loading.value = false
  }
}

async function searchCases(keyword: string) {
  if (!form.project) return
  caseLoading.value = true
  try {
    const res = await testcaseApi.list({
      project_id: form.project,
      keyword: keyword || undefined,
      page: 1,
    })
    caseOptions.value = res.results || []
  } catch {
    caseOptions.value = []
  } finally {
    caseLoading.value = false
  }
}

async function uploadFile(file: File) {
  uploading.value = true
  try {
    const res = await bugApi.uploadImage(file)
    form.attachments.push(res.url)
    ElMessage.success('截图已上传')
  } finally {
    uploading.value = false
  }
}

function handleUpload(options: any) {
  return uploadFile(options.file)
}

async function handlePaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of Array.from(items)) {
    if (item.type.startsWith('image/')) {
      const file = item.getAsFile()
      if (file) {
        e.preventDefault()
        await uploadFile(file)
      }
    }
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      project: form.project ?? null,
      title: form.title,
      module: form.module,
      testcase: form.testcase,
      environment: form.environment,
      severity: form.severity,
      priority: form.priority,
      reproducibility: form.reproducibility,
      description: form.description,
      attachments: form.attachments,
      assignee_ids: form.assignee_ids,
    }
    if (isEdit.value && props.bugId) {
      await bugApi.update(props.bugId, payload)
      ElMessage.success('缺陷已更新')
    } else {
      await bugApi.create(payload)
      ElMessage.success('缺陷已创建')
    }
    visible.value = false
    emit('saved')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped lang="scss">
.drawer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.drawer-title {
  display: flex;
  align-items: center;
  gap: 10px;
  h2 {
    margin: 0;
    font-size: 17px;
    color: #0f172a;
  }
}
.bug-no-chip {
  font-family: Consolas, monospace;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  color: #4f46e5;
  background: rgba(79, 70, 229, 0.08);
  border: 1px solid rgba(79, 70, 229, 0.18);
}
.member-role {
  float: right;
  margin-left: 10px;
  font-size: 11.5px;
  color: #94a3b8;
}
.form-tip {
  flex: 0 0 100%;
  width: 100%;
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.4;
  color: #94a3b8;
}
:deep(.el-form-item__content) {
  flex-wrap: wrap;
}
.upload-area {
  width: 100%;
}
.shot-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 8px;
}
.shot-item {
  position: relative;
  width: 78px;
  height: 58px;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  :deep(.el-image) {
    width: 100%;
    height: 100%;
  }
}
.shot-del {
  position: absolute;
  top: 0;
  right: 0;
  width: 16px;
  height: 16px;
  line-height: 14px;
  text-align: center;
  font-size: 13px;
  color: #fff;
  background: rgba(15, 23, 42, 0.66);
  cursor: pointer;
  border-bottom-left-radius: 6px;
}
</style>
