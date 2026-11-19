<template>
  <aside class="module-panel">
    <div class="panel-header">
      <span>测试模块</span>
      <el-button
        v-permission="'testcase:create'"
        link
        type="primary"
        size="small"
        @click="createModule(null)"
      >
        <el-icon><Plus /></el-icon> 新建
      </el-button>
    </div>

    <el-input
      v-model="keyword"
      size="small"
      placeholder="搜索模块"
      clearable
      prefix-icon="Search"
      class="search-input"
    />

    <!-- 虚拟节点 -->
    <div class="special-nodes">
      <div
        class="special-node"
        :class="{ active: selected === 'all' }"
        @click="select('all')"
      >
        <el-icon><Files /></el-icon>
        <span class="label">全部用例</span>
        <span class="count">{{ totalCount }}</span>
      </div>
      <div
        class="special-node"
        :class="{ active: selected === 'unassigned' }"
        @click="select('unassigned')"
      >
        <el-icon><FolderRemove /></el-icon>
        <span class="label">未规划模块</span>
        <span class="count">{{ unassignedCount }}</span>
      </div>
    </div>

    <!-- 模块树 -->
    <el-scrollbar class="tree-scroll">
      <el-tree
        ref="treeRef"
        :data="tree"
        node-key="id"
        :props="{ label: 'name', children: 'children' }"
        :filter-node-method="filterNode"
        :expand-on-click-node="false"
        highlight-current
        default-expand-all
        @node-click="(data: any) => select(data.id)"
      >
        <template #default="{ data }">
          <span class="tree-node">
            <span class="tree-label" :title="data.name">{{ data.name }}</span>
            <span class="node-count" :class="{ zero: !data.case_count }">{{ data.case_count }}</span>
            <span class="node-actions" @click.stop>
              <el-tooltip v-if="data.level < 3" content="新建子模块" placement="top">
                <el-icon v-permission="'testcase:create'" class="act" @click.stop="createModule(data.id)">
                  <Plus />
                </el-icon>
              </el-tooltip>
              <el-tooltip content="重命名" placement="top">
                <el-icon v-permission="'testcase:edit'" class="act" @click.stop="renameModule(data)">
                  <EditPen />
                </el-icon>
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-icon v-permission="'testcase:delete'" class="act danger" @click.stop="deleteModule(data)">
                  <Delete />
                </el-icon>
              </el-tooltip>
            </span>
          </span>
        </template>
      </el-tree>
      <el-empty v-if="!tree.length" description="暂无模块" :image-size="56" />
    </el-scrollbar>
  </aside>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { moduleApi } from '@/api'

const props = defineProps<{
  projectId: number | null
  selected: number | 'all' | 'unassigned'
}>()

const emit = defineEmits<{
  (e: 'update:selected', value: number | 'all' | 'unassigned'): void
  (e: 'loaded', payload: { tree: any[]; total_count: number; unassigned_count: number }): void
  (e: 'changed'): void
}>()

const treeRef = ref()
const tree = ref<any[]>([])
const keyword = ref('')
const totalCount = ref(0)
const unassignedCount = ref(0)

watch(keyword, (val) => treeRef.value?.filter(val))

// 同步选中态: 虚拟节点时清除树高亮
watch(
  () => props.selected,
  (val) => {
    if (typeof val === 'number') {
      treeRef.value?.setCurrentKey(val)
    } else {
      treeRef.value?.setCurrentKey(null)
    }
  },
)

function filterNode(value: string, data: any) {
  if (!value) return true
  return (data.name || '').includes(value)
}

async function reload() {
  if (!props.projectId) {
    tree.value = []
    totalCount.value = 0
    unassignedCount.value = 0
    return
  }
  try {
    const res = await moduleApi.tree(props.projectId)
    tree.value = res.tree || []
    totalCount.value = res.total_count || 0
    unassignedCount.value = res.unassigned_count || 0
    if (typeof props.selected === 'number') {
      treeRef.value?.setCurrentKey(props.selected)
    }
    emit('loaded', { tree: tree.value, total_count: totalCount.value, unassigned_count: unassignedCount.value })
  } catch {
    tree.value = []
  }
}

function select(value: number | 'all' | 'unassigned') {
  emit('update:selected', value)
}

async function promptName(title: string, initial = '') {
  try {
    const { value } = await ElMessageBox.prompt('请输入模块名称', title, {
      inputValue: initial,
      inputValidator: (v: string) => (!!v && v.trim().length > 0) || '模块名称不能为空',
    })
    return value.trim()
  } catch {
    return null
  }
}

async function createModule(parentId: number | null) {
  if (!props.projectId) {
    ElMessage.warning('请先在顶部选择项目')
    return
  }
  const name = await promptName(parentId ? '新建子模块' : '新建模块')
  if (!name) return
  await moduleApi.create({ project: props.projectId, name, parent: parentId })
  ElMessage.success('创建成功')
  await reload()
  emit('changed')
}

async function renameModule(data: any) {
  const name = await promptName('重命名模块', data.name)
  if (!name || name === data.name) return
  await moduleApi.update(data.id, {
    project: props.projectId,
    name,
    parent: data.parent,
  })
  ElMessage.success('重命名成功')
  await reload()
  emit('changed')
}

async function deleteModule(data: any) {
  try {
    await ElMessageBox.confirm(
      '删除模块后，其下属子模块将被删除，关联的测试用例将自动移入【未规划模块】，是否确认？',
      `删除模块「${data.name}」`,
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await moduleApi.delete(data.id)
  ElMessage.success('删除成功')
  await reload()
  if (props.selected === data.id) emit('update:selected', 'all')
  emit('changed')
}

onMounted(reload)
watch(() => props.projectId, reload)

defineExpose({ reload })
</script>

<style scoped lang="scss">
.module-panel {
  width: 232px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid rgba(231, 236, 244, 0.9);
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  box-shadow: var(--app-shadow);
  min-height: 520px;
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #1e293b;
  font-size: 13.5px;
}
.search-input {
  margin: 10px 0;
  :deep(.el-input__wrapper) {
    background: #fbfcfe;
  }
}
.special-nodes {
  margin-bottom: 8px;
}
.special-node {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  padding: 0 10px;
  border-radius: 8px;
  font-size: 13px;
  color: #475569;
  cursor: pointer;
  margin-bottom: 2px;
  transition: all 0.16s;
  .label {
    flex: 1;
  }
  .count {
    font-family: Consolas, monospace;
    font-size: 11.5px;
    color: #94a3b8;
  }
  &:hover {
    background: #f8fafc;
  }
  &.active {
    background: #eef2ff;
    color: #4f46e5;
    font-weight: 500;
    box-shadow: inset 0 0 0 1px #e0e4fd;
    .count {
      color: #6366f1;
    }
  }
  .el-icon {
    font-size: 15px;
  }
}
.tree-scroll {
  flex: 1;
  overflow: hidden;
  :deep(.el-tree) {
    background: transparent;
    --el-tree-node-hover-bg-color: #f8fafc;
  }
  :deep(.el-tree-node__content) {
    height: 36px;
    border-radius: 8px;
    margin-bottom: 2px;
  }
  :deep(.el-tree-node.is-current > .el-tree-node__content) {
    background: #eef2ff;
    color: #4f46e5;
    font-weight: 500;
    box-shadow: inset 0 0 0 1px #e0e4fd;
  }
}
.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding-right: 4px;
  font-size: 13px;
  .tree-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .node-count {
    font-family: Consolas, monospace;
    font-size: 11px;
    color: #94a3b8;
    &.zero {
      color: #cbd5e1;
    }
  }
  .node-actions {
    display: flex;
    align-items: center;
    gap: 2px;
    opacity: 0;
    transition: opacity 0.16s;
    .act {
      font-size: 13px;
      color: #94a3b8;
      padding: 3px;
      border-radius: 4px;
      &:hover {
        color: #4f46e5;
        background: #eef2ff;
      }
      &.danger:hover {
        color: #ef4444;
        background: #fef2f2;
      }
    }
  }
  &:hover .node-actions {
    opacity: 1;
  }
}
</style>
