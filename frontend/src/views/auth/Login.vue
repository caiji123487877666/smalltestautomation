<template>
  <div class="auth-page">
    <!-- 左侧品牌区 -->
    <section class="auth-brand">
      <div class="auth-logo"><div class="brand-mark">灵</div>灵测 AI</div>

      <div>
        <h1 class="brand-title">
          AI 驱动的<br /><span class="gradient-text">自动化测试平台</span>
        </h1>
        <p class="brand-desc">
          用例设计、接口与页面自动化、AI 自愈定位，一站式完成从编写到回归的全流程。
        </p>
        <div class="brand-points">
          <div class="brand-point"><i>01</i>可视化用例编排，API / WEB 双模式</div>
          <div class="brand-point"><i>02</i>项目级数据隔离与 RBAC 权限体系</div>
          <div class="brand-point"><i>03</i>Excel / Swagger 一键导入导出</div>
        </div>
      </div>

      <div class="brand-foot">© 2026 灵测 AI · TEST PLATFORM</div>
    </section>

    <!-- 右侧表单 -->
    <section class="auth-panel">
      <div class="auth-card">
        <h2 class="auth-title">欢迎回来</h2>
        <p class="auth-sub">登录以继续使用平台</p>

        <el-form ref="formRef" :model="form" :rules="rules" label-width="0" size="large">
          <el-form-item prop="username">
            <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码"
              prefix-icon="Lock"
              show-password
              @keyup.enter="handleLogin"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" size="large" style="width: 100%" @click="handleLogin">
              登 录
            </el-button>
          </el-form-item>
          <div class="auth-footer">
            <router-link to="/register">没有账号? 立即注册</router-link>
            <span class="tip">admin / admin123456</span>
          </div>
        </el-form>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({
  username: 'admin',
  password: 'admin123456',
})
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function handleLogin() {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    await authStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || '/'
    router.push(redirect)
  } catch {
    // 错误已由 axios 拦截器处理
  } finally {
    loading.value = false
  }
}
</script>
