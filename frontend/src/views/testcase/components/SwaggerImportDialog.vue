<template>
  <el-dialog v-model="visible" title="导入 Swagger / OpenAPI" width="620px" destroy-on-close append-to-body>
    <el-alert
      type="info"
      :closable="false"
      title="上传 Swagger 2.0 或 OpenAPI 3.x 的 JSON 文件, 系统会自动将每个接口转换为 API 类型用例"
      style="margin-bottom: 14px"
    />

    <el-upload
      drag
      :auto-upload="false"
      :limit="1"
      accept=".json"
      :on-change="handleFileChange"
      :on-remove="handleRemove"
      :file-list="fileList"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">将 JSON 文件拖到此处, 或 <em>点击选择文件</em></div>
      <template #tip>
        <div class="el-upload__tip">支持 .json 格式的 Swagger/OpenAPI 文档</div>
      </template>
    </el-upload>

    <div v-if="result" class="result">
      <el-alert
        :type="result.failed ? 'warning' : 'success'"
        :closable="false"
        :title="`成功生成 ${result.success} 条用例, 失败 ${result.failed} 条`"
      />
      <el-table v-if="result.errors && result.errors.length" :data="result.errors" size="small" border style="margin-top: 10px" max-height="180">
        <el-table-column prop="row" label="序号" width="70" />
        <el-table-column prop="msg" label="错误原因" />
      </el-table>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
      <el-button type="primary" :loading="importing" :disabled="!file" @click="handleImport">
        开始导入
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { testcaseApi } from '@/api'

const props = defineProps<{ projectId: number | null }>()
const emit = defineEmits<{ (e: 'imported'): void }>()

const visible = defineModel<boolean>({ required: true })
const file = ref<File | null>(null)
const fileList = ref<any[]>([])
const importing = ref(false)
const result = ref<{ success: number; failed: number; errors: any[] } | null>(null)

function handleFileChange(uploadFile: any) {
  file.value = uploadFile.raw
  fileList.value = [uploadFile]
  result.value = null
}
function handleRemove() {
  file.value = null
  fileList.value = []
}

async function handleImport() {
  if (!file.value || !props.projectId) return
  importing.value = true
  try {
    const res = await testcaseApi.importSwagger(props.projectId, file.value)
    result.value = res
    if (res.success > 0) {
      ElMessage.success(`成功生成 ${res.success} 条 API 用例`)
      emit('imported')
    }
    if (res.failed > 0) ElMessage.warning(`有 ${res.failed} 个接口处理失败`)
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.result {
  margin-top: 14px;
}
</style>
