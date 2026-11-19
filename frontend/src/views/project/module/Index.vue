<template>
  <div class="module-page page-container">
    <el-empty description="请先选择项目 (顶部下拉), 测试模块开发中">
      <el-button type="primary" @click="$router.push('/project/list')">去项目列表</el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
</script>
