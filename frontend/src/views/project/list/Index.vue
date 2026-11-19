<template>
  <div class="project-page page-container">
    <div class="page-card search-bar flex-between">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键字">
          <el-input v-model="searchForm.keyword" placeholder="项目名称/编码" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable style="width: 140px">
            <el-option label="进行中" value="active" />
            <el-option label="暂停" value="paused" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
      <el-button type="success" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新建项目
      </el-button>
    </div>

    <div class="page-card">
      <el-table :data="tableData" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="项目名称" min-width="160" />
        <el-table-column prop="code" label="项目编码" width="150" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="member_count" label="成员" width="80" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openDialog(row)">编辑</el-button>
            <el-button size="small" type="warning" link @click="handleSelect(row)">设为当前</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建/编辑 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑项目' : '新建项目'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="项目编码" prop="code">
          <el-input v-model="form.code" :disabled="isEdit" placeholder="英文编码, 如 qa_web" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="进行中" value="active" />
            <el-option label="暂停" value="paused" />
            <el-option label="已归档" value="archived" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useAppStore } from '@/stores/app'
import { projectApi } from '@/api'

const appStore = useAppStore()
const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)

const searchForm = reactive({ keyword: '', status: '' })
const tableData = ref<any[]>([])

const formRef = ref<FormInstance>()
const form = reactive({
  id: undefined as number | undefined,
  name: '',
  code: '',
  description: '',
  status: 'active',
})
const isEdit = computed(() => !!form.id)
const rules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入项目编码', trigger: 'blur' }],
}

onMounted(loadData)

async function loadData() {
  loading.value = true
  try {
    tableData.value = await projectApi.list({
      keyword: searchForm.keyword || undefined,
      status: searchForm.status || undefined,
    })
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}
function resetSearch() { searchForm.keyword = ''; searchForm.status = ''; loadData() }

function openDialog(row?: any) {
  if (row) {
    Object.assign(form, { id: row.id, name: row.name, code: row.code, description: row.description || '', status: row.status })
  } else {
    Object.assign(form, { id: undefined, name: '', code: '', description: '', status: 'active' })
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()
  submitLoading.value = true
  try {
    if (isEdit.value) {
      await projectApi.update(form.id!, form)
      ElMessage.success('更新成功')
    } else {
      await projectApi.create(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除项目 "${row.name}" ?`, '提示', { type: 'warning' })
  await projectApi.delete(row.id)
  ElMessage.success('删除成功')
  loadData()
}

function handleSelect(row: any) {
  appStore.setCurrentProject(row.id, row.name)
  ElMessage.success(`已切换到项目: ${row.name}`)
}

function statusTag(s: string): any {
  return { active: 'success', paused: 'warning', archived: 'info' }[s] || 'info'
}
function statusLabel(s: string) {
  return { active: '进行中', paused: '暂停', archived: '已归档' }[s] || s
}
</script>

<style scoped>
.project-page { min-height: calc(100vh - 92px); }
</style>
