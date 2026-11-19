<template>
  <div class="user-page page-container">
    <!-- 搜索栏 -->
    <div class="page-card search-bar">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="关键字">
          <el-input v-model="searchForm.keyword" placeholder="用户名/姓名/邮箱" clearable />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="searchForm.role_id" placeholder="全部" clearable style="width: 160px">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
          <el-button
            v-permission="'system:user:create'"
            type="success"
            style="margin-left: auto"
            @click="openDialog()"
          >
            <el-icon><Plus /></el-icon> 新增用户
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 表格 -->
    <div class="page-card">
      <el-table :data="tableData" v-loading="loading" stripe border>
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="real_name" label="姓名" width="120">
          <template #default="{ row }">{{ row.real_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="email" label="邮箱" min-width="180">
          <template #default="{ row }">{{ row.email || '-' }}</template>
        </el-table-column>
        <el-table-column prop="department" label="部门" width="120">
          <template #default="{ row }">{{ row.department || '-' }}</template>
        </el-table-column>
        <el-table-column label="角色" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="r in row.roles" :key="r.code" size="small" style="margin-right: 4px">
              {{ r.name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button v-permission="'system:user:update'" size="small" type="primary" link
              @click="openDialog(row)">编辑</el-button>
            <el-button v-permission="'system:user:reset_password'" size="small" type="warning" link
              @click="handleResetPwd(row)">重置密码</el-button>
            <el-button v-permission="'system:user:update'" size="small" type="info" link
              @click="handleToggleActive(row)">{{ row.is_active ? '禁用' : '启用' }}</el-button>
            <el-button v-permission="'system:user:delete'" size="small" type="danger" link
              @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </div>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用户' : '新增用户'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" :disabled="isEdit" />
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="form.password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item v-else label="重置密码">
          <el-input v-model="form.password" type="password" show-password placeholder="留空则不修改" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.real_name" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" />
        </el-form-item>
        <el-form-item label="部门">
          <el-input v-model="form.department" />
        </el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.gender">
            <el-radio value="male">男</el-radio>
            <el-radio value="female">女</el-radio>
            <el-radio value="unknown">未知</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role_ids" multiple placeholder="选择角色" style="width: 100%">
            <el-option v-for="r in roles" :key="r.id" :label="r.name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.is_active" />
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { userApi, roleApi } from '@/api'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const isEdit = computed(() => !!form.id)

const searchForm = reactive({ keyword: '', role_id: undefined as number | undefined })
const pagination = reactive({ page: 1, page_size: 20, total: 0 })
const tableData = ref<any[]>([])
const roles = ref<any[]>([])

const formRef = ref<FormInstance>()
const form = reactive({
  id: undefined as number | undefined,
  username: '',
  password: '',
  real_name: '',
  email: '',
  phone: '',
  department: '',
  gender: 'unknown',
  is_active: true,
  role_ids: [] as number[],
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur', min: 6 }],
}

onMounted(() => {
  loadRoles()
  loadData()
})

async function loadRoles() {
  try {
    roles.value = await roleApi.list()
  } catch {
    roles.value = []
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await userApi.list({
      keyword: searchForm.keyword || undefined,
      role_id: searchForm.role_id,
      page: pagination.page,
      page_size: pagination.page_size,
    })
    tableData.value = res.results || res
    pagination.total = res.count || res.length || 0
  } catch {
    tableData.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  searchForm.keyword = ''
  searchForm.role_id = undefined
  pagination.page = 1
  loadData()
}

function openDialog(row?: any) {
  if (row) {
    // 编辑: 填充
    Object.assign(form, {
      id: row.id,
      username: row.username,
      password: '',
      real_name: row.real_name || '',
      email: row.email || '',
      phone: row.phone || '',
      department: row.department || '',
      gender: row.gender || 'unknown',
      is_active: row.is_active,
      role_ids: row.roles?.map((r: any) => r.id) || [],
    })
  } else {
    // 新增
    Object.assign(form, {
      id: undefined,
      username: '',
      password: '',
      real_name: '',
      email: '',
      phone: '',
      department: '',
      gender: 'unknown',
      is_active: true,
      role_ids: [],
    })
  }
  dialogVisible.value = true
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()
  submitLoading.value = true
  try {
    const payload: any = { ...form }
    if (!form.password) delete payload.password
    if (isEdit.value) {
      await userApi.update(form.id!, payload)
      ElMessage.success('更新成功')
    } else {
      await userApi.create(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除用户 "${row.username}" ?`, '提示', { type: 'warning' })
  await userApi.delete(row.id)
  ElMessage.success('删除成功')
  loadData()
}

async function handleResetPwd(row: any) {
  const { value } = await ElMessageBox.prompt(
    `为用户 "${row.username}" 设置新密码 (至少 8 位, 不能为纯数字)`,
    '重置密码',
    {
      inputPattern: /^(?=.*[A-Za-z])(?=.*\d).{8,32}$/,
      inputErrorMessage: '密码需 8-32 位, 且同时包含字母和数字',
    }
  )
  await userApi.resetPassword(row.id, value)
  ElMessage.success('密码已重置')
}

async function handleToggleActive(row: any) {
  await userApi.toggleActive(row.id)
  ElMessage.success('操作成功')
  loadData()
}
</script>

<style scoped>
.user-page {
  min-height: calc(100vh - 92px);
}
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
