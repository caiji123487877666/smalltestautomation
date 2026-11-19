<template>
  <el-dialog v-model="visible" title="Excel 导入测试用例" width="620px" destroy-on-close append-to-body>
    <div class="toolbar">
      <el-button size="small" @click="downloadTemplate">
        <el-icon><Download /></el-icon> 下载导入模板
      </el-button>
      <span class="tip">请先下载模板, 按格式填写后上传</span>
    </div>

    <el-upload
      drag
      :auto-upload="false"
      :limit="1"
      accept=".xlsx,.xls"
      :on-change="handleFileChange"
      :on-remove="handleRemove"
      :file-list="fileList"
    >
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">将 Excel 拖到此处, 或 <em>点击选择文件</em></div>
      <template #tip>
        <div class="el-upload__tip">仅支持 .xlsx / .xls, 单次建议不超过 500 行</div>
      </template>
    </el-upload>

    <div v-if="result" class="result">
      <el-alert
        :type="result.failed ? 'warning' : 'success'"
        :closable="false"
        :title="`成功 ${result.success} 条, 失败 ${result.failed} 条`"
      />
      <el-table v-if="result.errors && result.errors.length" :data="result.errors" size="small" border style="margin-top: 10px" max-height="180">
        <el-table-column prop="row" label="行号" width="70" />
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

async function downloadTemplate() {
  const blob = await testcaseApi.downloadTemplate()
  saveBlob(blob, '测试用例导入模板.xlsx')
}

function saveBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  window.URL.revokeObjectURL(url)
}

async function handleImport() {
  if (!file.value || !props.projectId) return
  importing.value = true
  try {
    const res = await testcaseApi.importExcel(props.projectId, file.value)
    result.value = res
    if (res.success > 0) {
      ElMessage.success(`成功导入 ${res.success} 条用例`)
      emit('imported')
    }
    if (res.failed > 0) ElMessage.warning(`有 ${res.failed} 条导入失败, 请查看明细`)
  } finally {
    importing.value = false
  }
}
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.tip {
  font-size: 12px;
  color: #909399;
}
.result {
  margin-top: 14px;
}
</style>
