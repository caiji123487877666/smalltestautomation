<template>
  <el-dialog
    v-model="visible"
    :title="action?.label || '状态流转'"
    width="470px"
    append-to-body
    @closed="handleClosed"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="104px">
      <el-form-item v-if="action?.target" label="状态变更">
        <div class="status-flow">
          <span class="flow-tag" :class="(fromStatus || '').toLowerCase()">{{ fromStatusLabel }}</span>
          <span class="flow-arrow">→</span>
          <span class="flow-tag" :class="(action?.target || '').toLowerCase()">{{ targetLabel }}</span>
        </div>
      </el-form-item>

      <el-form-item
        v-if="action?.requiresAssignee"
        label="处理人"
        prop="assignee_ids"
        required
      >
        <el-select
          v-model="form.assignee_ids"
          multiple
          filterable
          clearable
          placeholder="请选择至少一名处理人 (不限角色)"
          style="width: 100%"
        >
          <el-option
            v-for="m in memberOptions"
            :key="m.id"
            :label="m.real_name || m.username"
            :value="m.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item
        v-if="action?.requiresResolution"
        label="解决结果"
        prop="resolution"
        required
      >
        <el-select v-model="form.resolution" placeholder="请选择解决结果" style="width: 100%">
          <el-option v-for="r in RESOLUTIONS" :key="r.value" :label="r.label" :value="r.value" />
        </el-select>
      </el-form-item>

      <el-form-item
        :label="action?.requiresComment ? '打回/重开原因' : '处理备注'"
        prop="comment"
        :required="!!action?.requiresComment"
      >
        <el-input
          v-model="form.comment"
          type="textarea"
          :rows="3"
          :placeholder="action?.requiresComment ? '请填写打回/重开原因 (必填)' : '可选, 填写本次处理说明'"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleConfirm">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { bugApi } from '@/api'

const RESOLUTIONS = [
  { value: 'FIXED', label: '已修复' },
  { value: 'BY_DESIGN', label: '设计如此' },
  { value: 'CANNOT_REPRODUCE', label: '无法复现' },
  { value: 'DUPLICATE', label: '重复缺陷' },
  { value: 'WONT_FIX', label: '暂不修复' },
]
const STATUS_LABELS: Record<string, string> = {
  NEW: '新建', ASSIGNED: '已指派', IN_PROGRESS: '处理中',
  RESOLVED: '已解决/待验证', CLOSED: '已关闭', REOPENED: '重新打开',
}

interface TransitionAction {
  label: string
  target: string
  requiresAssignee?: boolean
  requiresResolution?: boolean
  requiresComment?: boolean
}

const props = defineProps<{
  action: TransitionAction | null
  projectId?: number | null
  currentAssigneeIds?: number[]
  fromStatus?: string
  loading?: boolean
}>()
const emit = defineEmits<{ (e: 'confirm', payload: Record<string, any>): void }>()

const visible = defineModel<boolean>({ required: true })
const formRef = ref<FormInstance>()
const memberOptions = ref<any[]>([])
const form = reactive({
  assignee_ids: [] as number[],
  resolution: '',
  comment: '',
})

const fromStatusLabel = computed(() => STATUS_LABELS[props.fromStatus || ''] || '-')
const targetLabel = computed(() => STATUS_LABELS[props.action?.target || ''] || '-')

const rules = computed<FormRules>(() => ({
  assignee_ids: props.action?.requiresAssignee
    ? [{ type: 'array', required: true, min: 1, message: '请至少选择一名处理人', trigger: 'change' }]
    : [],
  resolution: props.action?.requiresResolution
    ? [{ required: true, message: '请选择解决结果', trigger: 'change' }]
    : [],
  comment: props.action?.requiresComment
    ? [{ required: true, whitespace: true, message: '请填写打回/重开原因', trigger: 'blur' }]
    : [],
}))

watch(visible, async (val) => {
  if (!val) return
  form.assignee_ids = [...(props.currentAssigneeIds || [])]
  form.resolution = ''
  form.comment = ''
  formRef.value?.clearValidate()
  if (props.action?.requiresAssignee) {
    try {
      memberOptions.value = await bugApi.availableAssignees(props.projectId)
    } catch {
      memberOptions.value = []
    }
  }
}, { immediate: true })

function handleClosed() {
  formRef.value?.resetFields()
}

async function handleConfirm() {
  if (!formRef.value || !props.action) return
  await formRef.value.validate()
  emit('confirm', {
    target_status: props.action.target,
    assignee_ids: props.action.requiresAssignee ? form.assignee_ids : undefined,
    resolution: props.action.requiresResolution ? form.resolution : undefined,
    comment: form.comment,
  })
  visible.value = false
}
</script>

<style scoped lang="scss">
.status-flow {
  display: flex;
  align-items: center;
  gap: 8px;
}
.flow-arrow {
  color: #94a3b8;
}
.flow-tag {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  &.new { background: #f1f5f9; color: #64748b; }
  &.assigned { background: #dbeafe; color: #1d4ed8; }
  &.in_progress { background: #fef3c7; color: #b45309; }
  &.resolved { background: #ede9fe; color: #6d28d9; }
  &.closed { background: #dcfce7; color: #15803d; }
  &.reopened { background: #fee2e2; color: #b91c1c; }
}
</style>
