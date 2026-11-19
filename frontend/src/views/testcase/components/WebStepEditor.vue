<template>
  <div class="web-step-editor">
    <el-table :data="model" border size="small" empty-text="暂无步骤, 请添加">
      <el-table-column label="#" type="index" width="50" align="center" />
      <el-table-column label="动作" width="150">
        <template #default="{ row }">
          <el-select v-model="row.action" style="width: 100%">
            <el-option v-for="a in ACTIONS" :key="a.value" :label="a.label" :value="a.value" />
          </el-select>
        </template>
      </el-table-column>
      <el-table-column label="定位器 Selector" min-width="180">
        <template #default="{ row }">
          <el-input v-model="row.selector" placeholder="#id / .class / text=登录" />
        </template>
      </el-table-column>
      <el-table-column label="输入值 / 断言值" min-width="160">
        <template #default="{ row }">
          <el-input v-model="row.value" placeholder="填写内容或期望值" />
        </template>
      </el-table-column>
      <el-table-column label="元素语义描述" min-width="160">
        <template #default="{ row }">
          <el-input v-model="row.element_desc" placeholder="如 用户名输入框" />
        </template>
      </el-table-column>
      <el-table-column label="自愈选择器" width="120">
        <template #default="{ row }">
          <el-input v-model="row.ai_healed_selector" placeholder="AI 自愈预留" />
        </template>
      </el-table-column>
      <el-table-column label="排序" width="150" align="center">
        <template #default="{ $index }">
          <el-button v-permission="'testcase:edit'" link :disabled="$index === 0" @click="moveUp($index)">上移</el-button>
          <el-button v-permission="'testcase:edit'" link :disabled="$index === model.length - 1" @click="moveDown($index)">下移</el-button>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="70" align="center">
        <template #default="{ $index }">
          <el-button v-permission="'testcase:edit'" link type="danger" @click="model.splice($index, 1)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-button v-permission="'testcase:edit'" class="add-row" size="small" @click="addStep">+ 添加步骤</el-button>
    <div class="hint">
      提示: 步骤按顺序执行; <b>element_desc</b> 用于 AI 语义定位, <b>ai_healed_selector</b> 由自愈引擎回填。
    </div>
  </div>
</template>

<script setup lang="ts">
const ACTIONS = [
  { label: 'goto 打开页面', value: 'goto' },
  { label: 'click 点击', value: 'click' },
  { label: 'fill 输入', value: 'fill' },
  { label: 'select 选择', value: 'select' },
  { label: 'wait 等待', value: 'wait' },
  { label: 'assert_text 文本断言', value: 'assert_text' },
  { label: 'assert_url URL 断言', value: 'assert_url' },
]

const model = defineModel<any[]>({ required: true })

function addStep() {
  model.value.push({
    action: 'click',
    selector: '',
    value: '',
    element_desc: '',
    ai_healed_selector: '',
  })
}

function moveUp(index: number) {
  if (index <= 0) return
  const arr = model.value
  const [item] = arr.splice(index, 1)
  arr.splice(index - 1, 0, item)
}

function moveDown(index: number) {
  const arr = model.value
  if (index >= arr.length - 1) return
  const [item] = arr.splice(index, 1)
  arr.splice(index + 1, 0, item)
}
</script>

<style scoped>
.add-row {
  margin-top: 8px;
}
.hint {
  margin-top: 10px;
  font-size: 12px;
  color: #909399;
}
</style>
