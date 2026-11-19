<template>
  <div class="api-debug-editor">
    <!-- ===== 顶部请求栏 ===== -->
    <div class="request-bar">
      <el-select
        v-model="model.method"
        class="method-select"
        :class="'m-' + String(model.method || 'get').toLowerCase()"
      >
        <el-option v-for="m in METHODS" :key="m" :label="m" :value="m" />
      </el-select>
      <el-input
        v-model="model.url"
        class="url-input"
        placeholder="/api/users 或 https://example.com/api/users, 支持 {{变量}}"
        clearable
        @blur="handleUrlBlur"
        @keyup.enter="handleSend"
      />
      <el-button type="primary" class="send-btn" :loading="sending" @click="handleSend">
        {{ sending ? '发送中' : '发送测试' }}
      </el-button>
      <el-button plain class="curl-btn" @click="curlVisible = true">导入 cURL</el-button>
    </div>

    <div class="env-line">
      <el-tag v-if="activeEnv" size="small" effect="plain" class="env-tag">
        {{ activeEnv.name }}
        <span class="env-url">{{ activeEnv.base_url || '未配置域名' }}</span>
      </el-tag>
      <el-tag v-else size="small" effect="plain" type="info" class="env-tag">
        未选择环境 · 需填写完整 URL
      </el-tag>
      <div class="var-hint">
        <span class="var-label">变量</span>
        <el-tag
          v-for="name in availableVariables.slice(0, 8)"
          :key="name"
          size="small"
          class="var-chip"
          @click="insertVariable(name)"
        >{{ varToken(name) }}</el-tag>
        <el-dropdown v-if="availableVariables.length > 8" trigger="click" @command="insertVariable">
          <span class="var-more">更多</span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="name in availableVariables.slice(8)" :key="name" :command="name">
                {{ name }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
    <div v-if="detectedVariables.length" class="detected-line">
      已使用：
      <el-tag
        v-for="name in detectedVariables"
        :key="name"
        size="small"
        :type="isKnownVariable(name) ? 'success' : 'warning'"
        effect="light"
        class="detected-chip"
      >{{ varToken(name) }}</el-tag>
    </div>

    <!-- ===== 请求配置 ===== -->
    <el-tabs v-model="activeTab" class="editor-tabs">
      <!-- Params -->
      <el-tab-pane name="params">
        <template #label>
          Params
          <span class="tab-count" v-if="enabledParams.length">{{ enabledParams.length }}</span>
        </template>
        <el-table :data="model.params" size="small" border class="kv-table" empty-text="暂无查询参数">
          <el-table-column width="52" align="center">
            <template #default="{ row }">
              <el-checkbox v-model="row.enabled" />
            </template>
          </el-table-column>
          <el-table-column label="Key" min-width="170">
            <template #default="{ row }">
              <el-input v-model="row.key" placeholder="如 page" @change="syncUrlFromParams" />
            </template>
          </el-table-column>
          <el-table-column label="Value" min-width="220">
            <template #default="{ row }">
              <el-input v-model="row.value" placeholder="如 1 或 {{token}}" @change="syncUrlFromParams" />
            </template>
          </el-table-column>
          <el-table-column width="64" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" @click="removeParam($index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button class="add-row" size="small" @click="addParam">+ 添加参数</el-button>
      </el-tab-pane>

      <!-- Headers -->
      <el-tab-pane name="headers">
        <template #label>
          Headers
          <span class="tab-count" v-if="enabledHeaders.length">{{ enabledHeaders.length }}</span>
        </template>
        <div class="preset-line">
          <span class="preset-label">快捷添加</span>
          <el-tag
            v-for="preset in HEADER_PRESETS"
            :key="preset.key"
            size="small"
            class="preset-chip"
            @click="addHeaderPreset(preset)"
          >{{ preset.key }}</el-tag>
        </div>
        <el-table :data="model.headers" size="small" border class="kv-table" empty-text="暂无请求头">
          <el-table-column width="52" align="center">
            <template #default="{ row }">
              <el-checkbox v-model="row.enabled" />
            </template>
          </el-table-column>
          <el-table-column label="Key" min-width="170">
            <template #default="{ row }">
              <el-input v-model="row.key" placeholder="如 Authorization" />
            </template>
          </el-table-column>
          <el-table-column label="Value" min-width="220">
            <template #default="{ row }">
              <el-input v-model="row.value" placeholder="如 Bearer {{token}}" />
            </template>
          </el-table-column>
          <el-table-column width="64" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" @click="model.headers.splice($index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button class="add-row" size="small" @click="model.headers.push({ key: '', value: '', enabled: true })">
          + 添加请求头
        </el-button>
      </el-tab-pane>

      <!-- Body -->
      <el-tab-pane name="body">
        <template #label>
          Body
          <span class="tab-count" v-if="model.body_type !== 'none'">1</span>
        </template>
        <div class="body-head">
          <el-radio-group v-model="model.body_type" size="small">
            <el-radio-button value="none">none</el-radio-button>
            <el-radio-button value="json">JSON</el-radio-button>
            <el-radio-button value="urlencoded">x-www-form-urlencoded</el-radio-button>
            <el-radio-button value="form-data">form-data</el-radio-button>
          </el-radio-group>
          <div v-if="model.body_type === 'json'" class="body-tools">
            <span v-if="jsonError" class="json-error">{{ jsonError }}</span>
            <el-button size="small" @click="formatJsonBody">格式化</el-button>
          </div>
        </div>

        <el-input
          v-if="model.body_type === 'json'"
          v-model="model.body"
          type="textarea"
          :rows="9"
          class="json-area"
          placeholder='{ "name": "{{username}}" }'
        />

        <template v-else-if="model.body_type !== 'none'">
          <el-table :data="model.body_items" size="small" border class="kv-table" empty-text="暂无表单字段">
            <el-table-column width="52" align="center">
              <template #default="{ row }">
                <el-checkbox v-model="row.enabled" />
              </template>
            </el-table-column>
            <el-table-column label="Key" min-width="170">
              <template #default="{ row }">
                <el-input v-model="row.key" placeholder="字段名" />
              </template>
            </el-table-column>
            <el-table-column label="Value" min-width="220">
              <template #default="{ row }">
                <el-input v-model="row.value" placeholder="字段值, 支持 {{变量}}" />
              </template>
            </el-table-column>
            <el-table-column width="64" align="center">
              <template #default="{ $index }">
                <el-button link type="danger" @click="model.body_items.splice($index, 1)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <el-button
            class="add-row"
            size="small"
            @click="model.body_items.push({ key: '', value: '', enabled: true })"
          >+ 添加字段</el-button>
        </template>

        <div v-else class="empty-body">该请求不携带 Body</div>
      </el-tab-pane>

      <!-- Assertions -->
      <el-tab-pane name="assertions">
        <template #label>
          断言
          <span class="tab-count" v-if="model.assertions.length">{{ model.assertions.length }}</span>
        </template>
        <el-table :data="model.assertions" size="small" border class="kv-table" empty-text="暂无断言规则">
          <el-table-column label="校验对象" width="150">
            <template #default="{ row }">
              <el-select v-model="row.type" style="width: 100%" @change="onAssertTypeChange(row)">
                <el-option label="状态码" value="status_code" />
                <el-option label="JSON 字段" value="jsonpath" />
                <el-option label="响应文本" value="response_text" />
                <el-option label="响应耗时" value="response_time" />
                <el-option label="响应头" value="header" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="比较符" width="126">
            <template #default="{ row }">
              <el-select v-model="row.operator" style="width: 100%">
                <el-option v-for="op in OPERATORS" :key="op.value" :label="op.label" :value="op.value" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="表达式 / JSONPath" min-width="190">
            <template #default="{ row }">
              <el-input
                v-model="row.expression"
                :disabled="row.type === 'status_code' || row.type === 'response_time'"
                :placeholder="expressionPlaceholder(row.type)"
              />
            </template>
          </el-table-column>
          <el-table-column label="期望值" width="150">
            <template #default="{ row }">
              <el-input
                v-model="row.expected"
                :disabled="row.operator === 'exists' || row.operator === 'not_exists'"
                placeholder="期望值"
              />
            </template>
          </el-table-column>
          <el-table-column width="64" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" @click="model.assertions.splice($index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-button class="add-row" size="small" @click="addAssertion">+ 添加断言</el-button>
      </el-tab-pane>

      <!-- Extract -->
      <el-tab-pane name="extract">
        <template #label>
          变量提取
          <span class="tab-count" v-if="model.extract_rules.length">{{ model.extract_rules.length }}</span>
        </template>
        <el-table :data="model.extract_rules" size="small" border class="kv-table" empty-text="暂无提取规则">
          <el-table-column label="来源" width="126">
            <template #default="{ row }">
              <el-select v-model="row.source" style="width: 100%">
                <el-option label="JSONPath" value="jsonpath" />
                <el-option label="响应头" value="header" />
                <el-option label="状态码" value="status_code" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="表达式" min-width="200">
            <template #default="{ row }">
              <el-input
                v-model="row.expression"
                :disabled="row.source === 'status_code'"
                placeholder="如 $.data.token"
              />
            </template>
          </el-table-column>
          <el-table-column label="写入变量名" min-width="160">
            <template #default="{ row }">
              <el-input v-model="row.variable" placeholder="如 auth_token" />
            </template>
          </el-table-column>
          <el-table-column width="64" align="center">
            <template #default="{ $index }">
              <el-button link type="danger" @click="model.extract_rules.splice($index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="extract-foot">
          <el-button class="add-row" size="small" @click="addExtract">+ 添加提取规则</el-button>
          <el-switch
            v-model="model.sync_variables"
            active-text="调试后自动写入当前环境变量"
            :disabled="!activeEnv"
          />
        </div>
        <div v-if="!activeEnv" class="muted-tip">未选择环境, 提取结果只展示不写入</div>
      </el-tab-pane>
    </el-tabs>

    <!-- ===== 响应面板 ===== -->
    <div v-if="!response" class="response-empty">
      <el-empty description="发送请求后在此查看响应结果" :image-size="56" />
    </div>

    <div v-else class="response-panel">
      <div class="resp-head">
        <span v-if="response.success" class="status-badge" :class="statusClass">
          {{ response.response.status_code }} {{ response.response.reason || '' }}
        </span>
        <span v-else class="status-badge err">请求失败</span>
        <span v-if="response.response" class="meta">{{ response.response.elapsed_ms }} ms</span>
        <span v-if="response.response" class="meta">{{ response.response.size_text }}</span>
        <span v-if="response.response?.content_type" class="meta">{{ response.response.content_type }}</span>
        <span v-if="response.assertions_total" class="assert-summary" :class="{ fail: response.assertions_failed }">
          断言 {{ response.assertions_total - response.assertions_failed }}/{{ response.assertions_total }} 通过
        </span>
      </div>

      <el-alert
        v-if="!response.success"
        :title="response.error || '请求失败'"
        type="error"
        :closable="false"
        show-icon
        class="resp-alert"
      />

      <el-tabs v-model="respTab" class="resp-tabs">
        <el-tab-pane label="响应体" name="body">
          <div v-if="response.success" class="resp-body">
            <div class="resp-tools">
              <el-button size="small" link @click="copyText(prettyBody)">复制</el-button>
              <el-button size="small" link @click="bodyCollapsed = !bodyCollapsed">
                {{ bodyCollapsed ? '展开' : '折叠' }}
              </el-button>
            </div>
            <pre class="code-block" :class="{ collapsed: bodyCollapsed }" v-html="highlightedBody || '&nbsp;'"></pre>
          </div>
          <div v-else class="muted-tip">请求未能完成，请查看上方错误信息与“实际请求”快照</div>
        </el-tab-pane>

        <el-tab-pane label="响应头" name="headers">
          <el-table
            v-if="response.response"
            :data="responseHeaders"
            size="small"
            border
            max-height="260"
            empty-text="无响应头"
          >
            <el-table-column prop="key" label="Header" width="220" />
            <el-table-column prop="value" label="Value" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane :label="`断言结果${response.assertions_total ? ' (' + response.assertions_total + ')' : ''}`" name="assertions">
          <div v-if="response.assertions?.length" class="assert-list">
            <div
              v-for="item in response.assertions"
              :key="item.index"
              class="assert-item"
              :class="{ failed: !item.passed }"
            >
              <span class="assert-mark">{{ item.passed ? '✓' : '✕' }}</span>
              <div class="assert-main">
                <div class="assert-title">
                  {{ item.type_label }}
                  <span v-if="item.expression" class="assert-expr">{{ item.expression }}</span>
                  <span class="assert-op">{{ operatorLabel(item.operator) }}</span>
                  <span class="assert-expected">{{ item.expected }}</span>
                </div>
                <div class="assert-detail">
                  实际值：<b>{{ item.actual }}</b>
                  <span v-if="!item.passed" class="assert-msg">{{ item.message }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="muted-tip">未配置断言</div>

          <template v-if="response.extracts?.length">
            <div class="sub-title">变量提取结果</div>
            <el-table :data="response.extracts" size="small" border>
              <el-table-column prop="variable" label="变量" width="160" />
              <el-table-column prop="value" label="提取值" show-overflow-tooltip />
              <el-table-column label="结果" width="90" align="center">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.success ? 'success' : 'danger'" effect="light">
                    {{ row.success ? '成功' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="message" label="说明" width="180" />
            </el-table>
            <div v-if="response.updated_variables && Object.keys(response.updated_variables).length" class="muted-tip ok">
              已写入环境变量：{{ Object.keys(response.updated_variables).join(', ') }}
            </div>
          </template>
        </el-tab-pane>

        <el-tab-pane label="实际请求" name="request">
          <div class="snapshot">
            <div class="snap-row">
              <span class="snap-key">请求</span>
              <span class="snap-method" :class="'m-' + String(response.request.method).toLowerCase()">
                {{ response.request.method }}
              </span>
              <span class="snap-url">{{ response.request.url }}</span>
            </div>
            <div v-if="response.request.unresolved_variables?.length" class="snap-warn">
              未解析变量：{{ response.request.unresolved_variables.join(', ') }}
            </div>
            <div class="snap-block">
              <div class="sub-title">Headers</div>
              <el-table :data="response.request.headers" size="small" border empty-text="无">
                <el-table-column prop="key" label="Key" width="190" />
                <el-table-column prop="value" label="Value" />
              </el-table>
            </div>
            <div v-if="response.request.params?.length" class="snap-block">
              <div class="sub-title">Query Params</div>
              <el-table :data="response.request.params" size="small" border>
                <el-table-column prop="key" label="Key" width="190" />
                <el-table-column prop="value" label="Value" />
              </el-table>
            </div>
            <div v-if="response.request.body" class="snap-block">
              <div class="sub-title">Body ({{ response.request.body_type }})</div>
              <pre class="code-block small">{{ response.request.body }}</pre>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- ===== cURL 导入 ===== -->
    <el-dialog v-model="curlVisible" title="导入 cURL" width="680px" append-to-body>
      <div class="curl-tip">从浏览器开发者工具 Network 面板右键复制为 cURL (bash)，粘贴到下方即可自动填充。</div>
      <el-input
        v-model="curlText"
        type="textarea"
        :rows="9"
        placeholder="curl 'https://api.example.com/users' -H 'Authorization: Bearer xxx'"
      />
      <div v-if="curlWarnings.length" class="curl-warn">
        <div v-for="(w, i) in curlWarnings" :key="i">· {{ w }}</div>
      </div>
      <template #footer>
        <el-button @click="curlVisible = false">取消</el-button>
        <el-button type="primary" :loading="curlLoading" @click="handleParseCurl">解析并填充</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { debugApi, environmentApi } from '@/api'
import { useAppStore } from '@/stores/app'

const METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
const OPERATORS = [
  { value: 'eq', label: '等于' },
  { value: 'ne', label: '不等于' },
  { value: 'contains', label: '包含' },
  { value: 'not_contains', label: '不包含' },
  { value: 'gt', label: '大于' },
  { value: 'gte', label: '大于等于' },
  { value: 'lt', label: '小于' },
  { value: 'lte', label: '小于等于' },
  { value: 'exists', label: '存在' },
  { value: 'not_exists', label: '不存在' },
]
const HEADER_PRESETS = [
  { key: 'Content-Type', value: 'application/json' },
  { key: 'Authorization', value: 'Bearer {{token}}' },
  { key: 'Accept', value: 'application/json' },
]
const DYNAMIC_FUNCTIONS = ['$timestamp', '$timestamp_ms', '$uuid', '$random_int']
const VAR_PATTERN = /\{\{\s*([^{}]+?)\s*\}\}/g

const props = defineProps<{ projectId: number | null }>()
const model = defineModel<Record<string, any>>({ required: true })
const appStore = useAppStore()

const activeTab = ref('params')
const respTab = ref('body')
const sending = ref(false)
const response = ref<any>(null)
const bodyCollapsed = ref(false)

const curlVisible = ref(false)
const curlText = ref('')
const curlLoading = ref(false)
const curlWarnings = ref<string[]>([])

const environments = ref<any[]>([])

const activeEnv = computed(() => {
  if (!environments.value.length) return null
  return (
    environments.value.find((e) => e.id === appStore.currentEnvironmentId) ||
    environments.value.find((e) => e.is_default) ||
    environments.value[0]
  )
})

const availableVariables = computed(() => [
  ...Object.keys(activeEnv.value?.variables || {}),
  ...DYNAMIC_FUNCTIONS,
])

const detectedVariables = computed(() => {
  const source = [
    model.value.url || '',
    JSON.stringify(model.value.headers || []),
    typeof model.value.body === 'string' ? model.value.body : '',
    JSON.stringify(model.value.body_items || []),
  ].join(' ')
  const found: string[] = []
  VAR_PATTERN.lastIndex = 0
  let match: RegExpExecArray | null
  while ((match = VAR_PATTERN.exec(source)) !== null) {
    const name = match[1].trim()
    if (name && !found.includes(name)) found.push(name)
  }
  return found
})

const enabledParams = computed(() =>
  (model.value.params || []).filter((p: any) => p.key && p.enabled !== false))
const enabledHeaders = computed(() =>
  (model.value.headers || []).filter((h: any) => h.key && h.enabled !== false))

const jsonError = computed(() => {
  if (model.value.body_type !== 'json') return ''
  const text = (typeof model.value.body === 'string' ? model.value.body : '').trim()
  if (!text) return ''
  try {
    JSON.parse(text)
    return ''
  } catch (err: any) {
    return `JSON 语法错误：${err.message}`
  }
})

const statusClass = computed(() => {
  const code = response.value?.response?.status_code ?? 0
  if (!code) return 'err'
  if (code < 300) return 'ok'
  if (code < 400) return 'warn'
  return 'err'
})

const responseHeaders = computed(() => {
  const headers = response.value?.response?.headers || {}
  return Object.keys(headers).map((key) => ({ key, value: headers[key] }))
})

const prettyBody = computed(() => {
  const res = response.value
  if (!res?.response) return ''
  if (res.response.is_json) {
    try {
      return JSON.stringify(res.response.json, null, 2)
    } catch {
      return res.response.body || ''
    }
  }
  return res.response.body || ''
})

// 先转义 HTML 再做 JSON 语法着色, 避免响应内容注入
const highlightedBody = computed(() => {
  const text = prettyBody.value
  if (!text) return ''
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  if (!response.value?.response?.is_json) return escaped
  return escaped.replace(
    /("(?:\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"\s*:?|\b(?:true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
    (token: string) => {
      let cls = 'num'
      if (token.startsWith('"')) {
        cls = token.trimEnd().endsWith(':') ? 'key' : 'str'
      } else if (/^(true|false|null)$/.test(token)) {
        cls = 'lit'
      }
      return `<span class="tok-${cls}">${token}</span>`
    },
  )
})

// ---------- 数据规范化 ----------
function ensureShape() {
  const steps = model.value
  if (!steps || typeof steps !== 'object') return
  if (!steps.method) steps.method = 'GET'
  if (!steps.body_type) steps.body_type = 'none'
  if (typeof steps.body !== 'string') steps.body = steps.body ? String(steps.body) : ''
  for (const key of ['headers', 'params', 'assertions', 'extract_rules', 'body_items']) {
    if (!Array.isArray(steps[key])) steps[key] = []
  }
  if (typeof steps.sync_variables !== 'boolean') steps.sync_variables = false
  for (const row of [...steps.headers, ...steps.params, ...steps.body_items]) {
    if (row.enabled === undefined) row.enabled = true
  }
  for (const row of steps.assertions) {
    if (!row.operator) row.operator = defaultOperator(row.type)
  }
  for (const row of steps.extract_rules) {
    if (!row.source) row.source = 'jsonpath'
  }
}
ensureShape()
watch(model, ensureShape)

// ---------- 环境 ----------
async function loadEnvironments() {
  if (!props.projectId) {
    environments.value = []
    return
  }
  try {
    environments.value = await environmentApi.list(props.projectId)
  } catch {
    environments.value = []
  }
}
watch(() => props.projectId, loadEnvironments, { immediate: true })

// ---------- URL / Params 双向同步 ----------
let syncing = false

function buildQuery(params: any[]) {
  return params
    .filter((p) => p.key && p.enabled !== false)
    .map((p) => `${encodeURIComponent(p.key)}=${encodeURIComponent(p.value ?? '')}`)
    .join('&')
}

function syncUrlFromParams() {
  if (syncing) return
  syncing = true
  const current = String(model.value.url || '')
  const base = current.split('?')[0]
  const query = buildQuery(model.value.params || [])
  model.value.url = query ? `${base}?${query}` : base
  nextTick(() => { syncing = false })
}

function handleUrlBlur() {
  if (syncing) return
  const raw = String(model.value.url || '')
  const index = raw.indexOf('?')
  if (index === -1) return
  const base = raw.slice(0, index)
  const query = raw.slice(index + 1)
  const parsed = query
    .split('&')
    .filter(Boolean)
    .map((pair) => {
      const pos = pair.indexOf('=')
      const key = pos === -1 ? pair : pair.slice(0, pos)
      const value = pos === -1 ? '' : pair.slice(pos + 1)
      return {
        key: decodeURIComponent(key),
        value: decodeURIComponent(value),
        enabled: true,
      }
    })
  syncing = true
  model.value.url = base
  model.value.params = parsed
  nextTick(() => { syncing = false })
}

function addParam() {
  model.value.params.push({ key: '', value: '', enabled: true })
}
function removeParam(index: number) {
  model.value.params.splice(index, 1)
  syncUrlFromParams()
}

// ---------- Headers ----------
function addHeaderPreset(preset: { key: string; value: string }) {
  const exists = model.value.headers.some(
    (h: any) => String(h.key || '').toLowerCase() === preset.key.toLowerCase())
  if (exists) {
    ElMessage.info(`${preset.key} 已存在`)
    return
  }
  model.value.headers.push({ ...preset, enabled: true })
}

// ---------- Body / Assertions / Extract ----------
function formatJsonBody() {
  const text = (typeof model.value.body === 'string' ? model.value.body : '').trim()
  if (!text) return
  try {
    model.value.body = JSON.stringify(JSON.parse(text), null, 2)
    ElMessage.success('JSON 已格式化')
  } catch (err: any) {
    ElMessage.error(`JSON 格式错误：${err.message}`)
  }
}

function defaultOperator(type: string) {
  if (type === 'response_text') return 'contains'
  if (type === 'response_time') return 'lte'
  return 'eq'
}

function onAssertTypeChange(row: any) {
  row.operator = defaultOperator(row.type)
  row.expression = ''
  if (row.type === 'status_code') row.expected = '200'
  else if (row.type === 'response_time') row.expected = '1000'
  else row.expected = ''
}

function addAssertion() {
  model.value.assertions.push({
    type: 'status_code', operator: 'eq', expression: '', expected: '200',
  })
}

function addExtract() {
  model.value.extract_rules.push({ source: 'jsonpath', expression: '$.data.token', variable: '' })
}

function expressionPlaceholder(type: string) {
  if (type === 'status_code') return '状态码无需表达式'
  if (type === 'response_time') return '耗时无需表达式'
  if (type === 'header') return '响应头名称, 如 content-type'
  return '如 $.data.id'
}

function operatorLabel(value: string) {
  return OPERATORS.find((op) => op.value === value)?.label || value
}

// ---------- 变量 ----------
function isKnownVariable(name: string) {
  return availableVariables.value.includes(name)
}

function varToken(name: string) {
  return `{{${name}}}`
}

function insertVariable(name: string) {
  model.value.url = `${model.value.url || ''}{{${name}}}`
}

function copyText(text: string) {
  if (!text) return
  navigator.clipboard?.writeText(text)
    .then(() => ElMessage.success('已复制'))
    .catch(() => ElMessage.warning('复制失败, 请手动选择'))
}

// ---------- 发送 ----------
async function handleSend() {
  const url = String(model.value.url || '').trim()
  if (!url) {
    ElMessage.warning('请先填写请求 URL')
    return
  }
  if (!/^https?:\/\//i.test(url) && !activeEnv.value?.base_url) {
    ElMessage.warning('未选择环境且 URL 不是完整地址, 请先在顶部选择环境或填写完整 URL')
    return
  }

  const bodyType = model.value.body_type || 'none'
  const payload = {
    project_id: props.projectId,
    environment_id: activeEnv.value?.id ?? null,
    method: model.value.method || 'GET',
    url,
    headers: enabledHeaders.value,
    params: enabledParams.value,
    body_type: bodyType,
    body:
      bodyType === 'none'
        ? null
        : bodyType === 'json'
          ? model.value.body || ''
          : model.value.body_items || [],
    assertions: model.value.assertions || [],
    extract_rules: model.value.extract_rules || [],
    sync_variables: !!model.value.sync_variables,
  }

  sending.value = true
  try {
    const res = await debugApi.send(payload as any)
    response.value = res
    respTab.value = 'body'
    bodyCollapsed.value = false
    if (res.success) {
      if (res.updated_variables && Object.keys(res.updated_variables).length) {
        // 环境变量已更新, 重新加载以刷新变量 chips
        await loadEnvironments()
      }
      if (res.assertions_total && res.assertions_failed) {
        ElMessage.warning(`请求完成，${res.assertions_failed} 条断言未通过`)
      } else {
        ElMessage.success(`请求完成 ${res.response?.status_code}`)
      }
    } else {
      ElMessage.error(res.error || '请求失败')
    }
  } catch {
    response.value = null
  } finally {
    sending.value = false
  }
}

// ---------- cURL 导入 ----------
async function handleParseCurl() {
  if (!curlText.value.trim()) {
    ElMessage.warning('请粘贴 cURL 内容')
    return
  }
  curlLoading.value = true
  try {
    const res = await debugApi.parseCurl(curlText.value)
    model.value.method = res.method || 'GET'
    model.value.url = res.url || ''
    model.value.params = (res.params || []).map((p: any) => ({
      key: p.key, value: p.value, enabled: p.enabled !== false,
    }))
    model.value.headers = (res.headers || []).map((h: any) => ({
      key: h.key, value: h.value, enabled: h.enabled !== false,
    }))
    model.value.body_type = res.body_type || 'none'
    if (res.body_type === 'json') {
      model.value.body = typeof res.body === 'string'
        ? res.body
        : JSON.stringify(res.body ?? '', null, 2)
      model.value.body_items = []
    } else if (res.body_type === 'none') {
      model.value.body = ''
      model.value.body_items = []
    } else {
      model.value.body_items = (res.form_body || []).map((f: any) => ({
        key: f.key, value: f.value, enabled: f.enabled !== false,
      }))
      model.value.body = ''
    }
    curlWarnings.value = res.warnings || []
    curlVisible.value = false
    ElMessage.success('cURL 已解析并填充')
  } finally {
    curlLoading.value = false
  }
}
</script>

<style scoped lang="scss">
.api-debug-editor {
  border: 1px solid var(--app-border, #e7ecf4);
  border-radius: 12px;
  background: #fff;
  padding: 14px;
}

/* 顶部请求栏 */
.request-bar {
  display: flex;
  gap: 8px;
  align-items: center;
}

.method-select {
  width: 112px;
  flex: 0 0 112px;
  :deep(.el-select__wrapper) {
    font-weight: 700;
    letter-spacing: 0.4px;
  }
  &.m-get :deep(.el-select__wrapper) { color: #059669; }
  &.m-post :deep(.el-select__wrapper) { color: #4f46e5; }
  &.m-put :deep(.el-select__wrapper) { color: #d97706; }
  &.m-patch :deep(.el-select__wrapper) { color: #7c3aed; }
  &.m-delete :deep(.el-select__wrapper) { color: #dc2626; }
}

.url-input {
  flex: 1;
  :deep(.el-input__inner) {
    font-family: Consolas, 'SFMono-Regular', monospace;
    font-size: 13px;
  }
}

.send-btn {
  flex: 0 0 auto;
  min-width: 96px;
}

.curl-btn {
  flex: 0 0 auto;
}

/* 环境与变量 */
.env-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.env-tag {
  :deep(.el-tag__content) {
    display: inline-flex;
    gap: 6px;
    align-items: center;
  }
}

.env-url {
  font-family: Consolas, monospace;
  font-size: 11.5px;
  color: #64748b;
}

.var-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.var-label {
  font-size: 12px;
  color: #94a3b8;
}

.var-chip,
.preset-chip,
.detected-chip {
  cursor: pointer;
  font-family: Consolas, monospace;
}

.var-more {
  font-size: 12px;
  color: #4f46e5;
  cursor: pointer;
}

.detected-line {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

/* Tabs */
.editor-tabs {
  margin-top: 10px;
  :deep(.el-tabs__header) {
    margin-bottom: 10px;
  }
}

.tab-count {
  display: inline-block;
  min-width: 17px;
  height: 17px;
  line-height: 17px;
  padding: 0 5px;
  margin-left: 4px;
  border-radius: 9px;
  background: #eef2ff;
  color: #4f46e5;
  font-size: 11px;
  text-align: center;
}

.kv-table {
  :deep(.el-input__wrapper) {
    box-shadow: none;
    background: transparent;
  }
}

.add-row {
  margin-top: 8px;
}

.preset-line {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}

.preset-label {
  font-size: 12px;
  color: #94a3b8;
}

.body-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  gap: 12px;
}

.body-tools {
  display: flex;
  align-items: center;
  gap: 10px;
}

.json-error {
  font-size: 12px;
  color: #dc2626;
  max-width: 320px;
}

.json-area :deep(textarea) {
  font-family: Consolas, 'SFMono-Regular', monospace;
  font-size: 12.5px;
}

.empty-body {
  padding: 26px 0;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  background: #f8fafc;
  border-radius: 8px;
}

.extract-foot {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  gap: 12px;
}

.muted-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #94a3b8;
  &.ok { color: #059669; }
}

/* 响应面板 */
.response-empty {
  margin-top: 14px;
  border: 1px dashed var(--app-border, #e2e8f0);
  border-radius: 10px;
  background: #fbfcfe;
}

.response-panel {
  margin-top: 14px;
  border: 1px solid var(--app-border, #e7ecf4);
  border-radius: 12px;
  overflow: hidden;
}

.resp-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid var(--app-border, #eef2f8);
}

.status-badge {
  font-family: Consolas, monospace;
  font-size: 12.5px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 6px;
  &.ok { color: #047857; background: #ecfdf5; border: 1px solid #a7f3d0; }
  &.warn { color: #b45309; background: #fffbeb; border: 1px solid #fde68a; }
  &.err { color: #b91c1c; background: #fef2f2; border: 1px solid #fecaca; }
}

.meta {
  font-size: 12px;
  color: #64748b;
  font-family: Consolas, monospace;
}

.assert-summary {
  margin-left: auto;
  font-size: 12px;
  font-weight: 600;
  color: #047857;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  padding: 2px 9px;
  border-radius: 999px;
  &.fail {
    color: #b91c1c;
    background: #fef2f2;
    border-color: #fecaca;
  }
}

.resp-alert {
  margin: 12px 14px 0;
}

.resp-tabs {
  padding: 0 14px 12px;
  :deep(.el-tabs__header) {
    margin-bottom: 10px;
  }
}

.resp-body {
  position: relative;
}

.resp-tools {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  margin-bottom: 4px;
}

.code-block {
  margin: 0;
  padding: 12px 14px;
  background: #0f172a;
  color: #d6e2f5;
  border-radius: 8px;
  font-family: Consolas, 'SFMono-Regular', monospace;
  font-size: 12.5px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 420px;
  overflow: auto;
  &.collapsed {
    max-height: 150px;
    overflow: hidden;
  }
  &.small {
    max-height: 220px;
    font-size: 12px;
  }
  :deep(.tok-key) { color: #93c5fd; }
  :deep(.tok-str) { color: #86efac; }
  :deep(.tok-num) { color: #fbbf24; }
  :deep(.tok-lit) { color: #f0abfc; }
}

.assert-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assert-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f0fdf9;
  border: 1px solid #d1fae5;
  &.failed {
    background: #fff7f7;
    border-color: #fecaca;
  }
}

.assert-mark {
  font-weight: 700;
  color: #059669;
  .failed & { color: #dc2626; }
}

.assert-main {
  flex: 1;
  min-width: 0;
}

.assert-title {
  font-size: 13px;
  color: #0f172a;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.assert-expr {
  font-family: Consolas, monospace;
  font-size: 12px;
  color: #4f46e5;
  background: #eef2ff;
  padding: 0 6px;
  border-radius: 4px;
}

.assert-op {
  font-size: 12px;
  color: #64748b;
}

.assert-expected {
  font-family: Consolas, monospace;
  font-size: 12px;
  color: #0f172a;
}

.assert-detail {
  margin-top: 3px;
  font-size: 12px;
  color: #64748b;
  word-break: break-all;
  b { color: #334155; font-weight: 600; }
}

.assert-msg {
  margin-left: 8px;
  color: #dc2626;
}

.sub-title {
  margin: 12px 0 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: #475569;
}

.snapshot {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.snap-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  word-break: break-all;
}

.snap-key {
  color: #94a3b8;
}

.snap-method {
  font-weight: 700;
  font-family: Consolas, monospace;
  &.m-get { color: #059669; }
  &.m-post { color: #4f46e5; }
  &.m-put { color: #d97706; }
  &.m-patch { color: #7c3aed; }
  &.m-delete { color: #dc2626; }
}

.snap-url {
  font-family: Consolas, monospace;
  color: #0f172a;
}

.snap-warn {
  font-size: 12px;
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 6px 10px;
}

.snap-block {
  margin-top: 6px;
}

.curl-tip {
  font-size: 12.5px;
  color: #64748b;
  margin-bottom: 8px;
}

.curl-warn {
  margin-top: 8px;
  font-size: 12px;
  color: #b45309;
}
</style>
