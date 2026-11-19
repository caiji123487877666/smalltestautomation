<template>
  <el-drawer
    v-model="visible"
    size="960px"
    direction="rtl"
    destroy-on-close
    append-to-body
  >
    <template #header="{ close }">
      <div class="drawer-head">
        <div class="drawer-title">
          <h2>{{ isEdit ? '编辑测试用例' : '新建测试用例' }}</h2>
          <span v-if="form.case_no" class="case-no-chip">{{ form.case_no }}</span>
        </div>
        <el-button link class="close-btn" @click="close">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </template>

    <el-form ref="formRef" :model="form" :rules="rules" label-width="90px" v-loading="loading">
      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="用例标题" prop="title">
            <el-input v-model="form.title" maxlength="255" show-word-limit />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="用例编号">
            <el-input :model-value="isEdit ? form.case_no : '保存后自动生成'" disabled />
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="所属模块">
            <el-cascader
              v-model="form.module"
              :options="moduleOptions"
              :props="cascaderProps"
              clearable
              placeholder="未规划模块"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-row :gutter="12">
        <el-col :span="6">
          <el-form-item label="用例类型" prop="case_type">
            <el-radio-group v-model="form.case_type">
              <el-radio-button value="API">API</el-radio-button>
              <el-radio-button value="WEB">WEB</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="优先级">
            <el-select v-model="form.priority" style="width: 100%">
              <el-option v-for="p in ['P0', 'P1', 'P2', 'P3']" :key="p" :label="p" :value="p" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option label="草稿" value="DRAFT" />
              <el-option label="可用" value="ACTIVE" />
              <el-option label="已废弃" value="DEPRECATED" />
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="6">
          <el-form-item label="标签">
            <el-select
              v-model="form.tags"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="输入后回车创建"
              style="width: 100%"
            />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="前置条件">
        <el-input v-model="form.precondition" type="textarea" :rows="2" placeholder="可选" />
      </el-form-item>

      <el-divider content-position="left">
        {{ form.case_type === 'API' ? '接口请求配置' : '页面操作步骤' }}
      </el-divider>

      <ApiStepEditor v-if="form.case_type === 'API'" v-model="apiSteps" :project-id="projectId" />
      <WebStepEditor v-else v-model="webSteps" />
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSubmit">保存用例</el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { testcaseApi } from '@/api'
import ApiStepEditor from './ApiStepEditor.vue'
import WebStepEditor from './WebStepEditor.vue'

const props = defineProps<{
  projectId: number | null
  moduleOptions: any[]
  defaultModuleId?: number | null
  caseId: number | null
}>()
const emit = defineEmits<{ (e: 'saved'): void }>()

// 级联选择器: 任意层级可选, 返回单值 id
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
const formRef = ref<FormInstance>()

const isEdit = computed(() => !!props.caseId)

function defaultApiSteps() {
  return {
    method: 'GET',
    url: '',
    headers: [],
    params: [],
    body_type: 'none',
    body: '',
    body_items: [],
    assertions: [{ type: 'status_code', operator: 'eq', expression: '', expected: '200' }],
    extract_rules: [],
    sync_variables: false,
  }
}
function defaultWebSteps() {
  return [{ action: 'goto', selector: '', value: '', element_desc: '打开页面', ai_healed_selector: '' }]
}

const form = reactive<any>({
  id: null,
  case_no: '',
  title: '',
  module: null,
  case_type: 'API',
  priority: 'P1',
  status: 'DRAFT',
  precondition: '',
  tags: [],
  steps: defaultApiSteps(),
})

const apiSteps = computed({
  get: () => (Array.isArray(form.steps) ? defaultApiSteps() : form.steps || defaultApiSteps()),
  set: (v) => { form.steps = v },
})
const webSteps = computed({
  get: () => (Array.isArray(form.steps) ? form.steps : []),
  set: (v) => { form.steps = v },
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入用例标题', trigger: 'blur' }],
  case_type: [{ required: true, message: '请选择用例类型', trigger: 'change' }],
}

watch(visible, async (val) => {
  if (!val) return
  resetForm()
  if (props.caseId) {
    loading.value = true
    try {
      const detail = await testcaseApi.detail(props.caseId)
      Object.assign(form, {
        id: detail.id,
        case_no: detail.case_no,
        title: detail.title,
        module: detail.module,
        case_type: detail.case_type,
        priority: detail.priority,
        status: detail.status,
        precondition: detail.precondition || '',
        tags: detail.tags || [],
        steps: detail.steps,
      })
      if (normalizeType(form.case_type) === 'API' && Array.isArray(form.steps)) {
        form.steps = defaultApiSteps()
      }
      if (normalizeType(form.case_type) === 'WEB' && !Array.isArray(form.steps)) {
        form.steps = defaultWebSteps()
      }
    } finally {
      loading.value = false
    }
  }
})

// 切换类型时重置步骤结构
watch(() => form.case_type, (val, old) => {
  if (!old || val === old) return
  if (val === 'API' && Array.isArray(form.steps)) form.steps = defaultApiSteps()
  if (val === 'WEB' && !Array.isArray(form.steps)) form.steps = defaultWebSteps()
})

function normalizeType(t: string) {
  return t === 'WEB' ? 'WEB' : 'API'
}

function resetForm() {
  Object.assign(form, {
    id: null,
    case_no: '',
    title: '',
    module: props.defaultModuleId ?? null,
    case_type: 'API',
    priority: 'P1',
    status: 'DRAFT',
    precondition: '',
    tags: [],
    steps: defaultApiSteps(),
  })
  formRef.value?.clearValidate()
}

async function handleSubmit() {
  if (!formRef.value || !props.projectId) return
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      project: props.projectId,
      module: form.module || null,
      title: form.title,
      case_type: form.case_type,
      priority: form.priority,
      status: form.status,
      precondition: form.precondition,
      tags: form.tags,
      steps: form.steps,
    }
    if (isEdit.value) {
      await testcaseApi.update(props.caseId!, payload)
      ElMessage.success('更新成功')
    } else {
      await testcaseApi.create(payload)
      ElMessage.success('创建成功')
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
  width: 100%;
}
.drawer-title {
  display: flex;
  align-items: center;
  gap: 10px;
  h2 {
    margin: 0;
    font-size: 16px;
    font-weight: 650;
    color: #0f172a;
  }
}
.case-no-chip {
  font-family: Consolas, monospace;
  font-size: 11.5px;
  color: #4f46e5;
  background: #eef2ff;
  border: 1px solid #dfe3fd;
  padding: 2px 8px;
  border-radius: 6px;
}
.close-btn {
  font-size: 16px;
  color: #94a3b8;
}
:deep(.el-drawer__footer) {
  border-top: 1px solid var(--app-border);
  padding: 14px 24px;
  background: #fff;
}
</style>
