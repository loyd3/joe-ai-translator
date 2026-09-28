<template>
  <div class="term-library-view">
    <div class="page-header">
      <el-button class="back-btn" @click="emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h1 class="title">词库</h1>
      <el-radio-group v-model="libraryScope" size="small" class="scope-switch">
        <el-radio-button label="document" :disabled="!translationId">小词库</el-radio-button>
        <el-radio-button label="global">大词库</el-radio-button>
      </el-radio-group>
    </div>
    <div class="page-body">
      <div class="term-card">
        <p class="scope-hint">
          {{ libraryScope === 'document'
            ? '小词库：仅当前文档的词汇，翻译时优先使用。'
            : '大词库：整个系统的词汇，按项目分类（小说、科技等）管理。' }}
        </p>
        <TermLibraryPanel
          :key="libraryScope"
          :scope="libraryScope"
          :translation-id="translationId"
          :literary-type="literaryType"
          :source-lang="sourceLang"
          :target-lang="targetLang"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import TermLibraryPanel from '@/components/TermLibraryPanel.vue'

const props = defineProps<{
  translationId?: number
  literaryType?: string
  sourceLang?: string
  targetLang?: string
}>()

const emit = defineEmits<{ back: [] }>()
const libraryScope = ref<'document' | 'global'>(props.translationId ? 'document' : 'global')

watch(
  () => props.translationId,
  (id) => {
    if (!id && libraryScope.value === 'document') libraryScope.value = 'global'
  }
)
</script>

<style scoped lang="scss">
.term-library-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
  min-height: 0;
}

.page-header {
  .scope-switch {
    margin-left: auto;
  }
}

.page-body {
  flex: 1;
  min-height: 0;
  padding: 20px 24px 24px;
  display: flex;
  justify-content: center;
}

.term-card {
  width: 100%;
  max-width: 960px;
  height: 100%;
  min-height: 0;
  background: var(--ins-surface);
  border: 1px solid var(--ins-line);
  border-radius: 10px;
  box-shadow: var(--ins-shadow-sm);
  padding: 20px 24px;
  display: flex;
  flex-direction: column;

  .scope-hint {
    margin: 0 0 14px;
    font-size: 13px;
    color: var(--ins-muted);
  }

  :deep(.term-panel) {
    flex: 1;
    min-height: 0;
  }
}
</style>
