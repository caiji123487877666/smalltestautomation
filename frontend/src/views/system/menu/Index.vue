<template>
  <div class="menu-page page-container">
    <div class="page-card search-bar flex-between">
      <span style="color: #606266">菜单/按钮权限树 (开发中)</span>
      <el-button type="success" disabled @click="openDialog()">
        <el-icon><Plus /></el-icon> 新增节点
      </el-button>
    </div>
    <div class="page-card flex-center" style="height: 300px; color: #909399">
      菜单管理模块, 后续迭代完善
    </div>
  </div>
</template>

<script setup lang="ts">
function openDialog() {}
</script>
