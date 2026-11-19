<template>
  <div class="role-page page-container">
    <div class="page-card search-bar flex-between">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键字">
          <el-input v-model="searchForm.keyword" placeholder="角色编码/名称" clearable @keyup.enter="loadData" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
      <el-button v-permission="'system:role:create'" type="success" @click="openDialog()">
        <el-icon><Plus /></el-icon> 新增角色
      </el-button>
    </div>

    <div class="page-card">
      <el-table :data="tableData" v-loading="loading" stripe border>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="code" label="角色编码" width="150" />
        <el-table-column prop="name" label="角色名称" width="150" />
        <el-table-column prop="description" label="描述" min-width="200">
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column prop="is_builtin" label="内置" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_builtin" type="warning" size="small">内置</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button v-permission="'system:role:view'" size="small" type="primary" link
              @click="openPermDialog(row)">分配权限</el-button>
            <el-button v-permission="'system:role:update'" size="small" type="success" link
              @click="openDialog(row)">编辑</el-button>
            <el-button
              v-permission="'system:role:delete'"
              size="small" type="danger" link
              :disabled="row.is_builtin"
              @click="handleDelete(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新增/编辑角色 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑角色' : '新增角色'" width="480px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="角色编码" prop="code">
          <el-input v-model="form.code" :disabled="isEdit" placeholder="如: qa_lead" />
        </el-form-item>
        <el-form-item label="角色名称" prop="name">
          <el-input v-model="form.name" placeholder="如: 测试组长" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 权限分配 -->
    <el-dialog v-model="permDialogVisible" :title="`为角色「${currentRole?.name}」分配权限`" width="640px">
      <div v-if="permTreeLoading" class="flex-center" style="height: 200px">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      </div>
      <el-tree
        v-else
        ref="treeRef"
        :data="menuTree"
        show-checkbox
        node-key="id"
        :default-checked-keys="checkedKeys"
        :props="{ label: 'name', children: 'children' }"
      />
      <template #footer>
        <el-button @click="permDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="permSaving" @click="savePermissions">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { roleApi, menuApi } from '@/api'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const permDialogVisible = ref(false)
const permTreeLoading = ref(false)
const permSaving = ref(false)

const searchForm = reactive({ keyword: '' })
const tableData = ref<any[]>([])
const menuTree = ref<any[]>([])
const checkedKeys = ref<number[]>([])
const currentRole = ref<any>(null)
const treeRef = ref()

const isEdit = computed(() => !!form.id)
const formRef = ref<FormInstance>()
const form = reactive({
  id: undefined as number | undefined,
  code: '',
  name: '',
  description: '',
  sort_order: 0,
})
const rules: FormRules = {
  code: [{ required: true, message: '请输入角色编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
}

onMounted(loadData)

async function loadData() {
  loading.value = true
  try {
    tableData.value = await roleApi.list({ keyword: searchForm.keyword || undefined })
  } catch {
    tableData.value = []
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  searchForm.keyword = ''
  loadData()
}

function openDialog(row?: any) {
  if (row) {
    Object.assign(form, {
      id: row.id, code: row.code, name: row.name,
      description: row.description || '', sort_order: row.sort_order || 0,
    })
  } else {
    Object.assign(form, { id: undefined, code: '', name: '', description: '', sort_order: 0 })
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()
  submitLoading.value = true
  try {
    if (isEdit.value) {
      await roleApi.update(form.id!, form)
      ElMessage.success('更新成功')
    } else {
      await roleApi.create(form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除角色 "${row.name}" ?`, '提示', { type: 'warning' })
  await roleApi.delete(row.id)
  ElMessage.success('删除成功')
  loadData()
}

// ---- 权限分配 ----
async function openPermDialog(row: any) {
  currentRole.value = row
  permTreeLoading.value = true
  permDialogVisible.value = true
  try {
    const [tree, ids] = await Promise.all([menuApi.tree(), roleApi.getPermissions(row.id)])
    menuTree.value = tree
    checkedKeys.value = ids
    await nextTick()
    treeRef.value?.setCheckedKeys(ids, false)
  } finally {
    permTreeLoading.value = false
  }
}

async function savePermissions() {
  if (!treeRef.value) return
  const keys = treeRef.value.getCheckedKeys() as number[]
  permSaving.value = true
  try {
    await roleApi.update(currentRole.value.id, { permission_ids: keys })
    ElMessage.success('权限已保存')
    permDialogVisible.value = false
  } finally {
    permSaving.value = false
  }
}
</script>

<style scoped>
.role-page {
  min-height: calc(100vh - 92px);
}
</style>
