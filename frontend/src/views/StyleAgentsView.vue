<template>
  <div class="style-agents-view">
    <div class="page-header">
      <el-button class="back-btn" @click="emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h1 class="title">文风设定</h1>
      <span class="subtitle">贴合原文 · 叠加译法</span>
    </div>
    <div class="page-body">
      <StyleAgentsPanel />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import StyleAgentsPanel from '@/components/StyleAgentsPanel.vue'

const emit = defineEmits<{ back: [] }>()
</script>

<style scoped lang="scss">
.style-agents-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
  min-height: 0;
}

.page-header .subtitle {
  font-size: 13px;
  color: var(--ins-muted);
  font-weight: 500;
}

.page-body {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
</style>
