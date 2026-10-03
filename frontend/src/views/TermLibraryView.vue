<template>
  <div class="term-library-view">
    <div class="page-header">
      <el-button class="back-btn" @click="emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <div class="header-text">
        <h1 class="title">{{ systemOnly ? '大词典' : '词库' }}</h1>
        <span class="subtitle">{{ headerSubtitle }}</span>
      </div>
      <el-radio-group v-if="!systemOnly" v-model="libraryScope" size="small" class="scope-switch">
        <el-radio-button label="document" :disabled="!translationId">小词库</el-radio-button>
        <el-radio-button label="global">大词库</el-radio-button>
      </el-radio-group>
      <el-button
        v-if="systemOnly || libraryScope === 'global'"
        size="small"
        class="sync-btn"
        :loading="syncing"
        @click="syncFromProjects"
      >归并小词典</el-button>
    </div>

    <div class="page-body">
      <div class="term-shell">
        <div class="scope-banner" :class="isGlobal ? 'is-global' : 'is-document'">
          <div class="banner-mark" aria-hidden="true">{{ isGlobal ? '大' : '小' }}</div>
          <div class="banner-copy">
            <strong>{{ isGlobal ? '系统大词典' : '当前文档小词库' }}</strong>
            <p>
              {{ isGlobal
                ? '各项目小词典按文学/专业类型归类后保存在这里，全系统共用。'
                : '仅当前文档的词汇，翻译时优先使用；可入库到大词典。' }}
            </p>
          </div>
        </div>

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

const isGlobal = computed(() => props.systemOnly || libraryScope.value === 'global')
const headerSubtitle = computed(() =>
  isGlobal.value ? '系统级术语与译法统一管理' : '当前文档专用术语，翻译时优先命中'
)

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
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;

  .header-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .subtitle {
    font-size: 12px;
    color: var(--ins-muted);
    font-weight: 500;
  }

  .scope-switch,
  .sync-btn {
    margin-left: auto;
  }

  .scope-switch + .sync-btn {
    margin-left: 8px;
  }
}

.page-body {
  flex: 1;
  min-height: 0;
  padding: 8px 24px 24px;
  display: flex;
}

.term-shell {
  width: 100%;
  max-width: 1080px;
  margin: 0 auto;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  background: var(--ins-surface);
  border: 1px solid var(--ins-line);
  border-radius: 14px;
  box-shadow: var(--ins-shadow-sm);
  padding: 16px 18px 14px;
}

.scope-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid transparent;
  flex-shrink: 0;

  &.is-global {
    background: rgba(var(--ins-primary-rgb), 0.08);
    border-color: rgba(var(--ins-primary-rgb), 0.16);
  }

  &.is-document {
    background: rgba(16, 185, 129, 0.08);
    border-color: rgba(16, 185, 129, 0.16);
  }

  .banner-mark {
    width: 36px;
    height: 36px;
    border-radius: 10px;
    display: grid;
    place-items: center;
    font-size: 14px;
    font-weight: 700;
    color: #fff;
    flex-shrink: 0;
  }

  &.is-global .banner-mark {
    background: var(--ins-grad, var(--el-color-primary));
  }

  &.is-document .banner-mark {
    background: linear-gradient(135deg, #10b981, #059669);
  }

  .banner-copy {
    min-width: 0;

    strong {
      display: block;
      font-size: 14px;
      color: var(--ins-ink);
      margin-bottom: 2px;
    }

    p {
      margin: 0;
      font-size: 12px;
      line-height: 1.5;
      color: var(--ins-muted);
    }
  }
}

.term-shell :deep(.term-panel) {
  flex: 1;
  min-height: 0;
}

@media (max-width: 768px) {
  .page-body {
    padding: 8px 12px 16px;
  }

  .page-header {
    .scope-switch,
    .sync-btn {
      margin-left: 0;
      width: 100%;
    }
  }
}
</style>
