<template>
  <div class="ai-config-view">
    <div class="page-header">
      <el-button class="back-btn" @click="emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h1 class="title">大模型配置</h1>
      <span class="subtitle">多提供商 · 模型与采样参数</span>
    </div>
    <div class="page-body">
      <AIConfigPanel @saved="emit('saved')" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft } from '@element-plus/icons-vue'
import AIConfigPanel from '@/components/AIConfigPanel.vue'

const emit = defineEmits<{ back: []; saved: [] }>()
</script>

<style scoped lang="scss">
.ai-config-view {
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
