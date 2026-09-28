<template>
  <div class="term-library-view">
    <div class="page-header">
      <el-button class="back-btn" @click="emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h1 class="title">{{ systemOnly ? '大词典' : '词库' }}</h1>
      <el-radio-group v-if="!systemOnly" v-model="libraryScope" size="small" class="scope-switch">
        <el-radio-button label="document" :disabled="!translationId">小词库</el-radio-button>
        <el-radio-button label="global">大词库</el-radio-button>
      </el-radio-group>
      <el-button
        v-if="systemOnly || libraryScope === 'global'"
        size="small"
        :loading="syncing"
        @click="syncFromProjects"
      >归并小词典</el-button>
    </div>
    <div class="page-body">
      <div class="term-card">
        <p class="scope-hint">
          {{ (systemOnly || libraryScope === 'global')
            ? '系统大词典：各项目小词典按文学/专业类型归类后保存在这里，全系统共用。'
            : '小词库：仅当前文档的词汇，翻译时优先使用。' }}
        </p>
        <TermLibraryPanel
          :key="panelKey"
          :scope="systemOnly ? 'global' : libraryScope"
          :translation-id="systemOnly ? undefined : translationId"
          :literary-type="systemOnly ? undefined : literaryType"
          :source-lang="systemOnly ? undefined : sourceLang"
          :target-lang="systemOnly ? undefined : targetLang"
          :reload-token="reloadToken"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import TermLibraryPanel from '@/components/TermLibraryPanel.vue'
import { literaryApi } from '@/api'

const props = defineProps<{
  translationId?: number
  literaryType?: string
  sourceLang?: string
  targetLang?: string
  systemOnly?: boolean
}>()

const emit = defineEmits<{ back: [] }>()
const libraryScope = ref<'document' | 'global'>(
  props.systemOnly || !props.translationId ? 'global' : 'document'
)
const syncing = ref(false)
const reloadToken = ref(0)

const panelKey = computed(() =>
  `${props.systemOnly ? 'system' : libraryScope.value}-${reloadToken.value}`
)

watch(
  () => props.translationId,
  (id) => {
    if (!id && libraryScope.value === 'document') libraryScope.value = 'global'
  }
)

const syncFromProjects = async () => {
  syncing.value = true
  try {
    const res = await literaryApi.syncGlobalTerms()
    const data = res.data || {}
    ElMessage.success(`已归并：新增 ${data.created || 0}，更新 ${data.updated || 0}`)
    reloadToken.value += 1
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '归并失败')
  } finally {
    syncing.value = false
  }
}
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
  .scope-switch,
  .el-button:last-child {
    margin-left: auto;
  }
  .scope-switch + .el-button {
    margin-left: 8px;
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
