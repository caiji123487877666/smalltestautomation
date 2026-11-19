<template>
  <div class="placeholder page-container">
    <el-empty :description="`「${title}」模块开发中...`">
      <el-button type="primary" @click="$router.back()">返回</el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
const route = useRoute()
const title = (route.meta?.title as string) || '该模块'
</script>
