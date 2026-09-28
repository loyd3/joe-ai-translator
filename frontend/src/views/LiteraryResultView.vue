<template>
  <div class="literary-result-view">
    <div class="result-header">
      <div class="header-left">
        <el-button class="back-btn" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h1 class="title">{{ task?.title || `定稿 #${task?.id}` }}</h1>
        <el-tag v-if="task?.status" :type="task.status === 'completed' ? 'success' : 'info'">
          {{ task?.status === 'completed' ? '定稿完成' : task?.status }}
        </el-tag>
      </div>
      <div class="header-actions">
        <el-tooltip content="主题设置" placement="bottom">
          <el-button circle class="icon-btn" @click="openThemeSettings">
            <el-icon><Sunny /></el-icon>
          </el-button>
        </el-tooltip>
        <el-button type="primary" :loading="saving" @click="save">
          <el-icon><Select /></el-icon>
          保存修改
        </el-button>
        <el-button :loading="exporting" @click="showExport = true">
          <el-icon><Download /></el-icon>
          导出译文
        </el-button>
      </div>
    </div>

    <div class="result-meta" v-if="task">
      <span>{{ task.source_lang }} → {{ task.target_lang }}</span>
      <span class="meta-divider">|</span>
      <span>类型：{{ getTypeName(task.literary_type) }}</span>
      <div class="icon-switch mode-switch">
        <el-tooltip content="分段对照" placement="bottom">
          <el-button
            circle
            class="icon-btn"
            :type="compareMode === 'segment' ? 'primary' : 'default'"
            @click="setCompareMode('segment')"
          >
            <el-icon><Grid /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip content="全文对照" placement="bottom">
          <el-button
            circle
            class="icon-btn"
            :type="compareMode === 'full' ? 'primary' : 'default'"
            @click="setCompareMode('full')"
          >
            <el-icon><DocumentCopy /></el-icon>
          </el-button>
        </el-tooltip>
      </div>
    </div>

    <div class="segment-tab-bar" v-if="compareMode === 'segment' && pageCount > 0">
      <el-tabs v-model="activePageTab" class="segment-tabs">
        <el-tab-pane
          v-for="page in pageCount"
          :key="page"
          :label="pageTabLabel(page)"
          :name="String(page)"
        />
      </el-tabs>
    </div>

    <div class="result-body" v-loading="loading || loadingFull">
      <div class="compare-wrap" v-if="compareMode === 'segment'">
        <div class="panel source-panel">
          <div class="panel-header">
            <span class="panel-label">原文</span>
            <el-tag size="small" type="info">{{ task?.source_lang || '' }}</el-tag>
          </div>
          <div class="panel-scroll" ref="sourceScrollRef">
            <div
              v-for="para in paragraphs"
              :key="para.id"
              :class="['para-block', { active: para.id === selectedParagraphId }]"
              @click="selectParagraph(para)"
            >
              <div class="para-index">第 {{ para.paragraph_index + 1 }} 段</div>
              <pre>{{ para.source_text }}</pre>
            </div>
            <div v-if="!loading && paragraphs.length === 0" class="no-content">暂无原文</div>
          </div>
        </div>
        <div class="panel-divider" />
        <div class="panel translation-panel">
          <div class="panel-header">
            <span class="panel-label">译文 · {{ pageTabLabel(paragraphPage) }}</span>
            <div class="icon-switch">
              <el-tooltip content="阅读" placement="bottom">
                <el-button
                  circle
                  class="icon-btn"
                  :type="rightMode === 'read' ? 'primary' : 'default'"
                  @click="setRightMode('read')"
                >
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="编辑" placement="bottom">
                <el-button
                  circle
                  class="icon-btn"
                  :type="rightMode === 'bulk' ? 'primary' : 'default'"
                  @click="setRightMode('bulk')"
                >
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </div>
          <div class="panel-scroll" ref="transScrollRef">
            <div
              v-for="para in paragraphs"
              :key="para.id"
              :id="`result-trans-${para.id}`"
              :class="['version-block', { active: para.id === selectedParagraphId }]"
            >
              <div class="version-label">
                <span>第 {{ para.paragraph_index + 1 }} 段</span>
                <div class="version-actions">
                  <el-tooltip content="AI 重译" placement="top">
                    <el-button
                      circle
                      class="icon-btn"
                      :loading="retranslatingId === para.id"
                      :disabled="!!retranslatingId && retranslatingId !== para.id"
                      @click.stop="retranslateParagraph(para)"
                    >
                      <el-icon v-if="retranslatingId !== para.id"><RefreshRight /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip :content="miniEditId === para.id ? '完成' : '编辑'" placement="top">
                    <el-button
                      v-if="rightMode === 'read'"
                      circle
                      class="icon-btn"
                      :type="miniEditId === para.id ? 'primary' : 'default'"
                      :disabled="retranslatingId === para.id"
                      @click.stop="toggleMiniEdit(para)"
                    >
                      <el-icon>
                        <Select v-if="miniEditId === para.id" />
                        <Edit v-else />
                      </el-icon>
                    </el-button>
                  </el-tooltip>
                </div>
              </div>
              <el-input
                v-if="rightMode === 'bulk' || miniEditId === para.id"
                v-model="para.editedText"
                type="textarea"
                :autosize="{ minRows: 3, maxRows: 16 }"
                placeholder="该段译文"
                @input="para.dirty = true"
              />
              <pre v-else-if="para.editedText">{{ para.editedText }}</pre>
              <div v-else class="version-empty">暂无译文</div>
            </div>
            <div v-if="!loading && paragraphs.length === 0" class="no-content">暂无译文</div>
          </div>
        </div>
      </div>
      <div class="compare-wrap" v-else>
        <div class="panel source-panel">
          <div class="panel-header">
            <span class="panel-label">原文</span>
            <el-tag size="small" type="info">{{ task?.source_lang || '' }}</el-tag>
          </div>
          <div class="panel-scroll">
            <pre v-if="fullSource">{{ fullSource }}</pre>
            <div v-else-if="!loadingFull" class="no-content">暂无原文</div>
          </div>
        </div>
        <div class="panel-divider" />
        <div class="panel translation-panel">
          <div class="panel-header">
            <span class="panel-label">译文</span>
            <el-tag size="small" type="success">{{ task?.target_lang || '' }}</el-tag>
          </div>
          <div class="panel-scroll">
            <pre v-if="fullTranslation">{{ fullTranslation }}</pre>
            <div v-else-if="!loadingFull" class="no-content">暂无译文</div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showExport" title="导出译文" width="440px">
      <el-form label-position="top">
        <el-form-item label="格式">
          <el-radio-group v-model="exportFormat">
            <el-radio-button label="txt">TXT</el-radio-button>
            <el-radio-button label="md">Markdown</el-radio-button>
            <el-radio-button label="html">HTML</el-radio-button>
            <el-radio-button label="json">JSON</el-radio-button>
            <el-radio-button label="csv">CSV</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="exportWithSource">同时导出原文对照</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExport = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="doExport">导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Select, Download, Grid, DocumentCopy, View, Edit, Sunny, RefreshRight } from '@element-plus/icons-vue'
import { literaryApi } from '@/api'

const openThemeSettings = inject<() => void>('openThemeSettings', () => {})

const props = defineProps<{
  /** 嵌入主界面全屏时传入；独立路由则走 path 参数 */
  translationId?: number
}>()
const emit = defineEmits<{ back: [] }>()

const route = useRoute()
const router = useRouter()

const task = ref<any>(null)
const paragraphs = ref<any[]>([])
const paragraphPage = ref(1)
const paragraphTotal = ref(0)
const PAGE_SIZE = 20
const compareMode = ref<'segment' | 'full'>('full')
const selectedParagraphId = ref<number | null>(null)
const rightMode = ref<'read' | 'bulk'>('read')
const miniEditId = ref<number | null>(null)
const retranslatingId = ref<number | null>(null)
const fullSource = ref('')
const fullTranslation = ref('')
const loadingFull = ref(false)
const loading = ref(false)
const saving = ref(false)
const exporting = ref(false)
const showExport = ref(false)
const exportFormat = ref<'txt' | 'md' | 'html' | 'json' | 'csv'>('txt')
const exportWithSource = ref(false)
const sourceScrollRef = ref<HTMLElement | null>(null)
const transScrollRef = ref<HTMLElement | null>(null)

const id = computed(() => {
  if (props.translationId != null && props.translationId > 0) return props.translationId
  const raw = route.params.id
  return raw ? Number(raw) : 0
})

const pageCount = computed(() => Math.ceil(paragraphTotal.value / PAGE_SIZE) || 0)

const pageTabLabel = (page: number) => {
  const start = (page - 1) * PAGE_SIZE + 1
  const end = Math.min(page * PAGE_SIZE, paragraphTotal.value)
  return `${start}–${end}`
}

const activePageTab = computed({
  get: () => String(paragraphPage.value),
  set: (name: string) => {
    const page = Number(name)
    if (page && page !== paragraphPage.value) onPageChange(page)
  },
})

const selectedParagraph = computed(() =>
  paragraphs.value.find((item: any) => item.id === selectedParagraphId.value) || null
)

const selectParagraph = (para: any) => {
  selectedParagraphId.value = para.id
  nextTick(() => {
    document.getElementById(`result-trans-${para.id}`)?.scrollIntoView({ block: 'nearest' })
  })
}

const onRightModeChange = async (mode: string) => {
  if (mode === 'bulk') {
    miniEditId.value = null
    return
  }
  if (paragraphs.value.some((item: any) => item.dirty)) await save(false)
}

const setRightMode = async (mode: 'read' | 'bulk') => {
  if (rightMode.value === mode) return
  rightMode.value = mode
  await onRightModeChange(mode)
}

const toggleMiniEdit = async (para: any) => {
  if (miniEditId.value === para.id) {
    miniEditId.value = null
    return
  }
  miniEditId.value = para.id
  selectedParagraphId.value = para.id
}

const loadPage = async (page: number) => {
  if (!id.value) return
  const skip = (page - 1) * PAGE_SIZE
  const res = await literaryApi.getParagraphs(id.value, { skip, limit: PAGE_SIZE })
  paragraphPage.value = page
  paragraphTotal.value = res.data.total
  paragraphs.value = (res.data.items || []).map((item: any) => ({
    ...item,
    editedText: item.user_edited_text || item.step4_finalization || item.translated_text || item.step3_revision || item.step2_verification || item.step1_translation || '',
    dirty: false,
  }))
  if (!paragraphs.value.some((item: any) => item.id === selectedParagraphId.value)) {
    selectedParagraphId.value = paragraphs.value[0]?.id ?? null
  }
}

const load = async () => {
  if (!id.value) return
  loading.value = true
  compareMode.value = 'full'
  fullSource.value = ''
  fullTranslation.value = ''
  selectedParagraphId.value = null
  rightMode.value = 'read'
  miniEditId.value = null
  paragraphs.value = []
  try {
    const res = await literaryApi.getTranslation(id.value, false, false)
    task.value = res.data
    await loadFullText()
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const paragraphDisplayText = (item: any) =>
  item.user_edited_text || item.editedText || item.step4_finalization || item.translated_text || item.step3_revision || item.step2_verification || item.step1_translation || ''

const loadFullText = async () => {
  if (!id.value) return
  loadingFull.value = true
  try {
    const items: any[] = []
    const chunk = 200
    let skip = 0
    let total = Infinity
    while (skip < total) {
      const res = await literaryApi.getParagraphs(id.value, { skip, limit: chunk })
      const batch = res.data.items || []
      total = res.data.total
      items.push(...batch)
      if (!batch.length) break
      skip += batch.length
    }
    fullSource.value = items.map((item) => item.source_text || '').join('\n\n')
    fullTranslation.value = items.map((item) => paragraphDisplayText(item)).join('\n\n')
  } catch (e) {
    ElMessage.error('加载全文失败')
  } finally {
    loadingFull.value = false
  }
}

const onCompareModeChange = async (mode: string) => {
  if (mode !== 'full') return
  if (paragraphs.value.some((item: any) => item.dirty)) await save(false)
  await loadFullText()
}

const setCompareMode = async (mode: 'segment' | 'full') => {
  if (compareMode.value === mode) return
  compareMode.value = mode
  if (mode === 'full') {
    await onCompareModeChange(mode)
    return
  }
  if (!paragraphs.value.length) {
    loading.value = true
    try {
      await loadPage(1)
    } catch (e) {
      ElMessage.error('加载段落失败')
    } finally {
      loading.value = false
    }
  }
}

const onPageChange = async (page: number) => {
  const dirty = paragraphs.value.some((item: any) => item.dirty)
  if (dirty) await save(false)
  miniEditId.value = null
  loading.value = true
  try {
    await loadPage(page)
    sourceScrollRef.value?.scrollTo({ top: 0 })
    transScrollRef.value?.scrollTo({ top: 0 })
  } catch (e) {
    ElMessage.error('加载段落失败')
  } finally {
    loading.value = false
  }
}

const save = async (notify = true) => {
  if (!id.value) return
  const dirtyItems = paragraphs.value.filter((item: any) => item.dirty)
  if (dirtyItems.length === 0) {
    if (notify) ElMessage.success('已保存')
    return
  }
  saving.value = true
  try {
    await Promise.all(dirtyItems.map((item: any) =>
      literaryApi.updateParagraph(item.id, { user_edited_text: item.editedText })
    ))
    dirtyItems.forEach((item: any) => { item.dirty = false })
    if (notify) ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error('保存失败')
    throw e
  } finally {
    saving.value = false
  }
}

const retranslateParagraph = async (para: any) => {
  if (!para?.id || retranslatingId.value) return
  try {
    await ElMessageBox.confirm(
      `将对第 ${para.paragraph_index + 1} 段重新执行 AI 四步翻译，并覆盖该段现有译文。是否继续？`,
      'AI 重译',
      { type: 'warning', confirmButtonText: '重译', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  retranslatingId.value = para.id
  try {
    const res = await literaryApi.retranslateParagraph(para.id)
    const data = res.data
    Object.assign(para, data)
    para.editedText = data.user_edited_text || data.step4_finalization || data.translated_text || data.step3_revision || data.step2_verification || data.step1_translation || ''
    para.dirty = false
    if (compareMode.value === 'full') await loadFullText()
    ElMessage.success(`第 ${para.paragraph_index + 1} 段重译完成`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '重译失败')
  } finally {
    retranslatingId.value = null
  }
}

const doExport = async () => {
  if (!id.value) return
  await save(false)
  exporting.value = true
  try {
    const res = await literaryApi.exportTranslation(id.value, {
      format: exportFormat.value,
      include_source: exportWithSource.value
    })
    const blob = new Blob([res.data.content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = res.data.filename || `${task.value?.title || `translation_${id.value}`}.${exportFormat.value}`
    link.click()
    URL.revokeObjectURL(url)
    showExport.value = false
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

const TYPE_LABELS: Record<string, string> = {
  poetry: '诗歌', prose: '散文', novel: '小说', drama: '戏剧', general: '一般',
  tech: '科技', business: '商业', trade: '贸易', legal: '法律', medical: '医学',
}
const getTypeName = (type: string) => TYPE_LABELS[type] || type

const goBack = () => {
  if (props.translationId != null) emit('back')
  else router.push({ name: 'literary' })
}

watch(id, load, { immediate: true })
</script>

<style scoped lang="scss">
.literary-result-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--ins-bg);
  min-height: 0;
}

.result-header {
  background: var(--ins-surface);
  padding: 14px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--ins-line);
  flex-shrink: 0;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;

    .title {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
    }
  }

  .header-actions {
    display: flex;
    gap: 8px;
  }
}

.result-meta {
  background: var(--ins-surface);
  padding: 8px 20px;
  font-size: 13px;
  color: var(--ins-muted);
  border-bottom: 1px solid var(--ins-line);
  display: flex;
  align-items: center;

  .meta-divider {
    margin: 0 12px;
    color: var(--ins-line-strong);
  }

  .mode-switch {
    margin-left: auto;
    display: flex;
    gap: 6px;
  }
}

.icon-switch {
  display: flex;
  align-items: center;
  gap: 6px;
}

.segment-tab-bar {
  background: var(--ins-surface);
  padding: 0 20px;
  border-bottom: 1px solid var(--ins-line);
  border-bottom: 1px solid var(--ins-line);

  .segment-tabs {
    :deep(.el-tabs__header) {
      margin: 0;
    }

    :deep(.el-tabs__content) {
      display: none;
    }

    :deep(.el-tabs__nav-wrap::after) {
      display: none;
    }
  }
}

.result-body {
  flex: 1;
  min-height: 0;
  padding: 16px;
  display: flex;
  flex-direction: column;
  background: var(--ins-bg);
}

.compare-wrap {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 8px 1fr;
  grid-template-rows: 1fr;
  gap: 0;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--ins-surface);
  border-radius: 10px;
  box-shadow: var(--ins-shadow-sm);
  overflow: hidden;
  border: 1px solid var(--ins-line);
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--ins-line);
  font-weight: 700;
  color: var(--ins-ink);
  flex-shrink: 0;
  background: var(--ins-surface);

  .panel-label {
    font-size: 12px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ins-muted);
  }
}

.source-panel .panel-header {
  background: var(--ins-bg);
  border-bottom-color: var(--ins-line);
}

.translation-panel .panel-header {
  background: var(--el-color-primary-light-9);
  border-bottom-color: var(--ins-line);

  .el-radio-group {
    margin-left: auto;
  }
}

.panel-divider {
  width: 8px;
  background: transparent;
  flex-shrink: 0;
}

.panel-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 20px;

  pre {
    margin: 0;
    white-space: pre-wrap;
    font-family: inherit;
    font-size: 15px;
    line-height: 1.85;
    color: var(--ins-ink);
  }
}

.para-block {
  cursor: pointer;
  border-radius: 8px;
  padding: 8px 10px;
  margin: 0 -10px;
  border: 1px solid transparent;

  & + .para-block {
    margin-top: 8px;
  }

  &:hover {
    background: rgba(16, 18, 24, 0.03);
  }

  &.active {
    background: var(--ins-grad-soft);
    border-color: rgba(var(--ins-primary-rgb), 0.18);
  }

  .para-index {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ins-muted);
    margin-bottom: 6px;
  }

  pre {
    margin: 0;
    white-space: pre-wrap;
    font-family: inherit;
    font-size: 15px;
    line-height: 1.85;
    color: var(--ins-ink);
  }
}

.version-block {
  & + .version-block {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px dashed var(--ins-line-strong);
  }

  .version-label {
    font-size: 12px;
    font-weight: 700;
    color: var(--ins-muted);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .version-actions {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  pre {
    margin: 0;
    white-space: pre-wrap;
    font-family: inherit;
    font-size: 15px;
    line-height: 1.85;
    color: var(--ins-ink);
  }

  .version-empty {
    color: var(--ins-muted);
    font-size: 14px;
  }

  &.active {
    background: var(--ins-grad-soft);
    border-radius: 8px;
    padding: 10px 12px;
    margin-left: -12px;
    margin-right: -12px;
  }
}

.no-content {
  color: var(--ins-muted);
  text-align: center;
  padding: 48px 0;
}
</style>
