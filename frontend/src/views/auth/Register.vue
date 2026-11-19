<template>
  <div class="auth-page">
    <section class="auth-brand">
      <div class="auth-logo"><div class="brand-mark">灵</div>灵测 AI</div>

      <div>
        <h1 class="brand-title">
          开始你的<br /><span class="gradient-text">自动化测试之旅</span>
        </h1>
        <p class="brand-desc">
          注册后默认分配「测试人员」角色，可直接管理项目用例、执行导入导出。
        </p>
        <div class="brand-points">
          <div class="brand-point"><i>01</i>注册即用，无需额外配置</div>
          <div class="brand-point"><i>02</i>管理员可随时调整角色与菜单权限</div>
          <div class="brand-point"><i>03</i>数据按项目隔离，安全可控</div>
        </div>
      </div>

      <div class="brand-foot">© 2026 灵测 AI · TEST PLATFORM</div>
    </section>

    <section class="auth-panel">
      <div class="auth-card">
        <h2 class="auth-title">创建账号</h2>
        <p class="auth-sub">填写以下信息完成注册</p>

        <el-form ref="formRef" :model="form" :rules="rules" label-width="0" size="large">
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="用户名（3-32 位）" prefix-icon="User" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="form.password" type="password" placeholder="密码（至少 6 位）" prefix-icon="Lock" show-password />
          </el-form-item>
          <el-form-item prop="confirmPassword">
            <el-input v-model="form.confirmPassword" type="password" placeholder="确认密码" prefix-icon="Lock" show-password />
          </el-form-item>
          <el-form-item prop="email">
            <el-input v-model="form.email" placeholder="邮箱（选填）" prefix-icon="Message" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" size="large" style="width: 100%" @click="handleRegister">
              注 册
            </el-button>
          </el-form-item>
          <div class="auth-footer" style="justify-content: center">
            <router-link to="/login">已有账号? 返回登录</router-link>
          </div>
        </el-form>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 32, message: '长度 3-32 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 32, message: '长度 6-32 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator: (_rule, value, cb) => {
        if (value !== form.password) cb(new Error('两次密码不一致'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
  email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
}

async function handleRegister() {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    await authStore.register({
      username: form.username,
      password: form.password,
      email: form.email || undefined,
    })
    ElMessage.success('注册成功, 请登录')
    router.push('/login')
  } catch {
    // handled
  } finally {
    loading.value = false
  }
}
</script>
