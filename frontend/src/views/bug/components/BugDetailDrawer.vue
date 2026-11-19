<template>
  <el-drawer v-model="visible" size="940px" direction="rtl" destroy-on-close append-to-body>
    <template #header>
      <div class="drawer-head">
        <div class="head-left">
          <span class="bug-no">{{ detail.bug_no || '缺陷详情' }}</span>
          <span v-if="detail.status" class="status-tag" :class="detail.status.toLowerCase()">
            {{ detail.status_display }}
          </span>
        </div>
      </div>
    </template>

    <div v-loading="loading" class="detail-body">
      <!-- 左: 详情 -->
      <div class="detail-left">
        <h2 class="bug-title">{{ detail.title }}</h2>

        <div class="action-bar">
          <el-button
            v-for="a in actions"
            :key="a.key"
            v-permission="'bug:transition'"
            size="small"
            :type="a.type || 'primary'"
            :plain="!a.highlight"
            @click="openTransition(a)"
          >{{ a.label }}</el-button>
          <span v-if="!actions.length" class="muted">当前状态无可执行操作</span>
        </div>

        <el-descriptions :column="2" border size="small" class="desc-grid">
          <el-descriptions-item label="所属项目">
            <span v-if="detail.project_name">{{ detail.project_name }}</span>
            <el-tag v-else size="small" type="info" effect="plain">未关联项目</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <span class="severity" :class="(detail.severity || '').toLowerCase()">
              {{ detail.severity_display || '-' }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="优先级">{{ detail.priority || '-' }}</el-descriptions-item>
          <el-descriptions-item label="复现概率">{{ detail.reproducibility_display || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发现环境">
            <el-tag v-if="detail.environment_name" size="small" effect="plain">{{ detail.environment_name }}</el-tag>
            <span v-else class="muted">未指定</span>
          </el-descriptions-item>
          <el-descriptions-item label="所属模块">{{ detail.module_path || '未规划模块' }}</el-descriptions-item>
          <el-descriptions-item label="关联用例">
            <span v-if="detail.testcase_no">{{ detail.testcase_no }} {{ detail.testcase_title }}</span>
            <span v-else class="muted">未关联</span>
          </el-descriptions-item>
          <el-descriptions-item label="处理人">
            <template v-if="detail.assignees?.length">
              <el-tag
                v-for="a in detail.assignees"
                :key="a.id"
                size="small"
                class="assignee-tag"
              >{{ a.real_name || a.username }}</el-tag>
            </template>
            <span v-else class="muted">未指派</span>
          </el-descriptions-item>
          <el-descriptions-item label="创建人">{{ detail.creator_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="解决结果">
            <span v-if="detail.resolution">{{ detail.resolution_display }}</span>
            <span v-else class="muted">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="关闭时间">{{ formatTime(detail.closed_at) }}</el-descriptions-item>
        </el-descriptions>

        <div class="section-title">详细描述</div>
        <div class="description">{{ detail.description || '暂无描述' }}</div>

        <template v-if="detail.attachments?.length">
          <div class="section-title">截图附件 ({{ detail.attachments.length }})</div>
          <div class="shots">
            <el-image
              v-for="(url, idx) in detail.attachments"
              :key="url"
              :src="url"
              :preview-src-list="detail.attachments"
              :initial-index="idx"
              fit="cover"
              class="shot"
            />
          </div>
        </template>
      </div>

      <!-- 右: 流转记录 -->
      <aside class="detail-right">
        <div class="section-title">流转记录</div>
        <el-empty v-if="!histories.length" description="暂无记录" :image-size="60" />
        <el-timeline v-else>
          <el-timeline-item
            v-for="h in histories"
            :key="h.id"
            :timestamp="formatTime(h.created_at)"
            placement="top"
            :type="timelineType(h)"
          >
            <div class="tl-title">
              {{ h.operator_name || '系统' }}
              <span class="tl-action">{{ h.action_label || h.action_display }}</span>
            </div>
            <div v-if="h.from_status || h.to_status" class="tl-status">
              <span class="status-chip" :class="statusClass(h.from_status)">
                {{ h.from_status_display || '-' }}
              </span>
              <span class="arrow">→</span>
              <span class="status-chip" :class="statusClass(h.to_status)">
                {{ h.to_status_display || '-' }}
              </span>
            </div>
            <div v-if="h.resolution" class="tl-badge">
              <el-tag size="small" type="success" effect="light">{{ h.resolution_display }}</el-tag>
            </div>
            <div v-if="h.comment" class="tl-comment">{{ h.comment }}</div>
          </el-timeline-item>
        </el-timeline>

        <!-- 评论 -->
        <div class="comment-box">
          <el-input
            v-model="newComment"
            type="textarea"
            :rows="2"
            placeholder="发送评论..."
          />
          <el-button
            v-permission="'bug:edit'"
            type="primary"
            size="small"
            :loading="commenting"
            style="margin-top: 8px"
            @click="sendComment"
          >发送评论</el-button>
        </div>
      </aside>
    </div>

    <!-- 统一状态流转弹窗 -->
    <TransitionModal
      v-model="transitionVisible"
      :action="currentAction"
      :project-id="detail.project"
      :current-assignee-ids="assigneeIds"
      :from-status="detail.status"
      :loading="submitting"
      @confirm="handleTransition"
    />
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { bugApi } from '@/api'
import TransitionModal from './TransitionModal.vue'

type ButtonType = 'primary' | 'success' | 'warning' | 'danger' | 'info'
interface TransitionAction {
  key: string
  label: string
  target: string
  type?: ButtonType
  requiresAssignee?: boolean
  requiresResolution?: boolean
  requiresComment?: boolean
  highlight?: boolean
}

const ACTIONS_BY_STATUS: Record<string, TransitionAction[]> = {
  NEW: [
    { key: 'assign', label: '指派处理人', target: 'ASSIGNED', type: 'primary', requiresAssignee: true },
    { key: 'start', label: '开始处理', target: 'IN_PROGRESS', type: 'primary' },
    { key: 'close', label: '直接关闭', target: 'CLOSED', type: 'danger', requiresResolution: true },
  ],
  ASSIGNED: [
    { key: 'start', label: '开始处理', target: 'IN_PROGRESS', type: 'primary' },
    { key: 'transfer', label: '转派', target: 'ASSIGNED', type: 'primary', requiresAssignee: true },
    { key: 'resolve', label: '标记已解决', target: 'RESOLVED', type: 'success' },
    { key: 'close', label: '直接关闭', target: 'CLOSED', type: 'danger', requiresResolution: true },
  ],
  IN_PROGRESS: [
    { key: 'resolve', label: '标记已解决', target: 'RESOLVED', type: 'success' },
    { key: 'transfer', label: '转派', target: 'ASSIGNED', type: 'primary', requiresAssignee: true },
    { key: 'close', label: '直接关闭', target: 'CLOSED', type: 'danger', requiresResolution: true },
  ],
  RESOLVED: [
    { key: 'close', label: '✅ 验证通过并关闭', target: 'CLOSED', type: 'success', requiresResolution: true, highlight: true },
    { key: 'reopen', label: '❌ 验证不通过 (打回)', target: 'REOPENED', type: 'danger', requiresComment: true, highlight: true },
  ],
  REOPENED: [
    { key: 'start', label: '开始处理', target: 'IN_PROGRESS', type: 'primary' },
    { key: 'transfer', label: '转派', target: 'ASSIGNED', type: 'primary', requiresAssignee: true },
    { key: 'resolve', label: '标记已解决', target: 'RESOLVED', type: 'success' },
  ],
  CLOSED: [
    { key: 'reopen', label: '🔄 重新打开', target: 'REOPENED', type: 'warning', requiresComment: true },
  ],
}

const props = defineProps<{ bugId: number | null }>()
const emit = defineEmits<{ (e: 'updated'): void }>()

const visible = defineModel<boolean>({ required: true })
const loading = ref(false)
const submitting = ref(false)
const detail = ref<any>({})
const histories = ref<any[]>([])

const transitionVisible = ref(false)
const currentAction = ref<TransitionAction | null>(null)
const newComment = ref('')
const commenting = ref(false)

const actions = computed(() => ACTIONS_BY_STATUS[detail.value.status] || [])
const assigneeIds = computed(() =>
  (detail.value.assignees || []).map((a: any) => a.id))

watch(visible, async (val) => {
  if (val && props.bugId) await loadAll()
})

async function loadAll() {
  if (!props.bugId) return
  loading.value = true
  try {
    const [d, h] = await Promise.all([
      bugApi.detail(props.bugId),
      bugApi.histories(props.bugId),
    ])
    detail.value = d
    histories.value = h || []
  } finally {
    loading.value = false
  }
}

function openTransition(action: TransitionAction) {
  currentAction.value = action
  transitionVisible.value = true
}

async function handleTransition(payload: Record<string, any>) {
  if (!props.bugId) return
  submitting.value = true
  try {
    await bugApi.transition(props.bugId, payload as any)
    ElMessage.success('状态已更新')
    await loadAll()
    emit('updated')
  } finally {
    submitting.value = false
  }
}

async function sendComment() {
  const text = newComment.value.trim()
  if (!text) {
    ElMessage.warning('评论内容不能为空')
    return
  }
  if (!props.bugId) return
  commenting.value = true
  try {
    await bugApi.comment(props.bugId, text)
    newComment.value = ''
    const h = await bugApi.histories(props.bugId)
    histories.value = h || []
    ElMessage.success('评论已发送')
    emit('updated')
  } finally {
    commenting.value = false
  }
}

function timelineType(h: any): 'primary' | 'success' | 'info' | 'warning' | undefined {
  return ({
    CREATE: 'success', TRANSITION: 'primary', COMMENT: 'warning', UPDATE: 'info',
  } as const)[h.action as 'CREATE' | 'TRANSITION' | 'COMMENT' | 'UPDATE']
}

function statusClass(s: string) {
  return ({
    NEW: 'new', ASSIGNED: 'assigned', IN_PROGRESS: 'in_progress',
    RESOLVED: 'resolved', CLOSED: 'closed', REOPENED: 'reopened',
  } as Record<string, string>)[s || ''] || 'new'
}

function formatTime(t: string | null) {
  return t ? t.replace('T', ' ').slice(0, 16) : '-'
}
</script>

<style scoped lang="scss">
.drawer-head {
  display: flex;
  align-items: center;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.bug-no {
  font-family: Consolas, monospace;
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}
.status-tag {
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
.detail-body {
  display: flex;
  gap: 18px;
  align-items: flex-start;
}
.detail-left {
  flex: 1;
  min-width: 0;
}
.detail-right {
  width: 300px;
  flex: 0 0 300px;
  border-left: 1px solid #eef2f7;
  padding-left: 16px;
}
.bug-title {
  margin: 0 0 12px;
  font-size: 19px;
  color: #0f172a;
  line-height: 1.4;
}
.action-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.desc-grid {
  margin-bottom: 16px;
}
.severity {
  font-weight: 600;
  &.blocker { color: #dc2626; }
  &.error { color: #d97706; }
  &.normal { color: #2563eb; }
  &.other { color: #64748b; }
}
.assignee-tag {
  margin-right: 6px;
}
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  margin: 16px 0 8px;
}
.description {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.7;
  color: #475569;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  border-radius: 8px;
  padding: 12px 14px;
}
.shots {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.shot {
  width: 110px;
  height: 80px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  cursor: zoom-in;
}
.tl-title {
  font-size: 12.5px;
  color: #334155;
  font-weight: 500;
}
.tl-action {
  color: #4f46e5;
}
.tl-status {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 4px;
  font-size: 11.5px;
}
.status-chip {
  padding: 1px 7px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #64748b;
  &.new { background: #f1f5f9; color: #64748b; }
  &.assigned { background: #dbeafe; color: #1d4ed8; }
  &.in_progress { background: #fef3c7; color: #b45309; }
  &.resolved { background: #ede9fe; color: #6d28d9; }
  &.closed { background: #dcfce7; color: #15803d; }
  &.reopened { background: #fee2e2; color: #b91c1c; }
}
.arrow {
  color: #94a3b8;
}
.tl-badge {
  margin-top: 4px;
}
.tl-comment {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
  background: #f8fafc;
  border-radius: 6px;
  padding: 5px 8px;
  white-space: pre-wrap;
  word-break: break-word;
}
.comment-box {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #e2e8f0;
}
.muted {
  color: #94a3b8;
}
</style>
