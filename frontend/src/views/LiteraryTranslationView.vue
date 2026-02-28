<template>
  <div class="literary-view">
    <div class="page-header">
      <h2>
        <el-icon class="header-icon"><Reading /></el-icon>
        <span class="title-text">文学翻译</span>
        <el-tag type="success" size="small" class="beta-tag" effect="dark">AI四步翻译</el-tag>
      </h2>
      <p class="subtitle">翻译 → 校验 → 修改 → 定稿，追求音美、词美、意美的文学翻译品质</p>
    </div>

    <div class="content-container">
      <!-- 左侧：任务列表和创建 -->
      <div class="sidebar">
        <el-card class="create-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><Plus /></el-icon>
              <span>新建翻译任务</span>
            </div>
          </template>
          
          <el-form :model="newTaskForm" label-position="top" class="compact-form">
            <el-form-item label="文本标题">
              <el-input v-model="newTaskForm.title" placeholder="输入文本标题（可选）" size="small" />
            </el-form-item>
            
            <el-form-item label="文学体裁">
              <el-radio-group v-model="newTaskForm.literary_type" size="small">
                <el-radio-button label="general">一般</el-radio-button>
                <el-radio-button label="poetry">诗歌</el-radio-button>
                <el-radio-button label="prose">散文</el-radio-button>
                <el-radio-button label="novel">小说</el-radio-button>
                <el-radio-button label="drama">戏剧</el-radio-button>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="翻译语言">
              <div class="lang-select-row">
                <el-select v-model="newTaskForm.source_lang" placeholder="源语言" size="small">
                  <el-option v-for="lang in sourceLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
                </el-select>
                <el-icon class="arrow-icon"><ArrowRightBold /></el-icon>
                <el-select v-model="newTaskForm.target_lang" placeholder="目标语言" size="small">
                  <el-option v-for="lang in targetLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
                </el-select>
              </div>
            </el-form-item>
            
            <el-form-item label="参考文档">
              <div class="reference-section">
                <el-select v-model="newTaskForm.reference_document_ids" multiple placeholder="选择参考文档" size="small" class="reference-select">
                  <el-option v-for="doc in referenceDocs" :key="doc.id" :label="doc.name" :value="doc.id" />
                </el-select>
                <el-button link type="primary" size="small" @click="showRefDocManager = true" class="manage-btn">
                  <el-icon><Setting /></el-icon> 管理
                </el-button>
              </div>
            </el-form-item>
            
            <el-form-item label="原文内容">
              <el-input v-model="newTaskForm.source_text" type="textarea" :rows="5" placeholder="在此粘贴要翻译的文学文本..." class="source-input" />
              <div class="text-stats" v-if="newTaskForm.source_text">
                <el-tag size="small" type="info">
                  {{ newTaskForm.source_text.length }} 字符
                </el-tag>
              </div>
            </el-form-item>
            
            <el-button type="primary" size="default" :loading="creating" :disabled="!canCreate" @click="createTask" class="create-btn">
              <el-icon><VideoPlay /></el-icon> 创建并翻译
            </el-button>
          </el-form>
        </el-card>

        <el-card class="task-list-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon><List /></el-icon>
              <span>翻译任务列表</span>
              <el-tag size="small" type="info">{{ taskList.length }}</el-tag>
            </div>
          </template>
          
          <div class="task-list" v-if="taskList.length > 0">
            <div v-for="task in taskList" :key="task.id" :class="['task-item', { active: currentTask?.id === task.id }]" @click="selectTask(task.id)">
              <div class="task-header">
                <span class="task-title">{{ task.title || `任务 #${task.id}` }}</span>
                <el-tag size="small" :type="getStatusType(task.status)" effect="light">{{ getStatusText(task.status) }}</el-tag>
              </div>
              <div class="task-meta">
                <span class="lang-pair">{{ task.source_lang }} → {{ task.target_lang }}</span>
                <span class="task-type">{{ getLiteraryTypeText(task.literary_type) }}</span>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无翻译任务" :image-size="80" />
        </el-card>
      </div>

      <!-- 右侧：翻译工作区 -->
      <div class="workspace" v-if="currentTask">
        <div class="task-info-bar">
          <div class="info-left">
            <h3 class="task-title">{{ currentTask.title || `任务 #${currentTask.id}` }}</h3>
            <div class="info-tags">
              <el-tag size="small" type="info" effect="plain">{{ getLiteraryTypeText(currentTask.literary_type) }}</el-tag>
              <el-tag size="small" type="info" effect="plain">{{ currentTask.source_lang }} → {{ currentTask.target_lang }}</el-tag>
            </div>
          </div>
          <div class="info-right">
            <el-button-group>
              <el-button size="small" @click="refreshTask"><el-icon><Refresh /></el-icon></el-button>
              <el-button size="small" type="danger" @click="deleteCurrentTask"><el-icon><Delete /></el-icon></el-button>
            </el-button-group>
          </div>
        </div>

        <!-- 四步流程 -->
        <div class="workflow-section">
          <el-steps :active="currentTask.current_step" finish-status="success">
            <el-step title="初译" description="AI翻译" />
            <el-step title="校验" description="三美评估" />
            <el-step title="修改" description="润色提升" />
            <el-step title="定稿" description="出版品质" />
          </el-steps>
          
          <div class="step-actions">
            <el-button v-if="currentTask.status === 'pending'" type="primary" :loading="processing" @click="startWorkflow">开始翻译</el-button>
            <el-button v-else-if="currentTask.current_step === 1" type="primary" :loading="processing" @click="verifyTranslation">执行校验</el-button>
            <el-button v-else-if="currentTask.current_step === 2" type="primary" :loading="processing" @click="reviseTranslation">执行修改</el-button>
            <el-button v-else-if="currentTask.current_step === 3" type="primary" :loading="processing" @click="finalizeTranslation">执行定稿</el-button>
            <template v-else-if="currentTask.status === 'completed'">
              <el-button type="success" @click="showExport = true">导出译文</el-button>
              <el-button @click="restartWorkflow">重新翻译</el-button>
            </template>
          </div>
        </div>

        <!-- 三美评分 -->
        <div class="beauty-scores" v-if="currentTask.beauty_sound_score">
          <div class="score-header">三美评分</div>
          <div class="score-items">
            <div class="score-item">
              <span class="score-label">音美</span>
              <el-progress :percentage="currentTask.beauty_sound_score * 10" :color="getScoreColor(currentTask.beauty_sound_score)" :stroke-width="8" />
            </div>
            <div class="score-item">
              <span class="score-label">词美</span>
              <el-progress :percentage="currentTask.beauty_word_score * 10" :color="getScoreColor(currentTask.beauty_word_score)" :stroke-width="8" />
            </div>
            <div class="score-item">
              <span class="score-label">意美</span>
              <el-progress :percentage="currentTask.beauty_meaning_score * 10" :color="getScoreColor(currentTask.beauty_meaning_score)" :stroke-width="8" />
            </div>
          </div>
        </div>

        <!-- 编辑器 -->
        <div class="editor-section">
          <div class="editor-header">
            <el-radio-group v-model="viewMode" size="small">
              <el-radio-button label="paragraph">段落对照</el-radio-button>
              <el-radio-button label="side">全文对照</el-radio-button>
            </el-radio-group>
            <el-radio-group v-model="displayStep" size="small" v-if="currentTask.step1_translation">
              <el-radio-button :label="1">初译</el-radio-button>
              <el-radio-button :label="2" :disabled="!currentTask.step2_verification">校验</el-radio-button>
              <el-radio-button :label="3" :disabled="!currentTask.step3_revision">修改</el-radio-button>
              <el-radio-button :label="4" :disabled="!currentTask.step4_finalization">定稿</el-radio-button>
            </el-radio-group>
          </div>

          <!-- 段落对照模式 -->
          <div v-if="viewMode === 'paragraph'" class="paragraph-editor">
            <div class="editor-toolbar">
              <el-alert title="提示：点击译文可直接编辑，修改后会自动保存" type="info" :closable="false" show-icon />
            </div>
            
            <div class="paragraphs-container">
              <div v-for="(para, index) in editableParagraphs" :key="para.id" class="paragraph-item">
                <div class="para-header">
                  <span class="para-number">段落 {{ index + 1 }}</span>
                  <el-tag v-if="para.isEdited" size="small" type="success">已编辑</el-tag>
                </div>
                
                <div class="para-content">
                  <div class="para-source-box">
                    <div class="box-label">原文</div>
                    <div class="source-text">{{ para.sourceText }}</div>
                  </div>
                  
                  <div class="para-translation-box">
                    <div class="box-label">{{ getStepLabel(displayStep) }}</div>
                    <el-input v-model="para.editedText" type="textarea" :rows="3" :placeholder="para.currentText || '等待翻译...'" @blur="handleParaBlur(para)" class="translation-input" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 全文对照模式 -->
          <div v-else class="full-comparison">
            <div class="comparison-grid">
              <div class="source-panel">
                <div class="panel-header">原文</div>
                <div class="panel-content"><pre>{{ currentTask.source_text }}</pre></div>
              </div>
              <div class="translation-panel">
                <div class="panel-header">{{ getStepLabel(displayStep) }}</div>
                <div class="panel-content">
                  <el-input v-model="fullTextEdit" type="textarea" :rows="20" @blur="saveFullTextEdit" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="empty-workspace" v-else>
        <el-empty description="选择左侧任务或创建新任务">
          <el-button type="primary" @click="scrollToCreate">创建新任务</el-button>
        </el-empty>
      </div>
    </div>

    <el-dialog v-model="showRefDocManager" title="参考文档管理" width="700px">
      <ReferenceDocManager @close="showRefDocManager = false" @updated="loadReferenceDocs" />
    </el-dialog>

    <el-dialog v-model="showExport" title="导出译文" width="420px">
      <el-form label-position="top">
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportForm.format">
            <el-radio-button label="txt">纯文本</el-radio-button>
            <el-radio-button label="md">Markdown</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="exportForm.include_source">包含原文对照</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExport = false">取消</el-button>
        <el-button type="primary" @click="exportTranslation">导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { literaryApi, translateApi } from '@/api'
import ReferenceDocManager from '@/components/ReferenceDocManager.vue'

const languages = ref<{ code: string; name: string }[]>([])
const referenceDocs = ref<any[]>([])
const taskList = ref<any[]>([])
const currentTask = ref<any>(null)
const paragraphs = ref<any[]>([])
const viewMode = ref<'side' | 'paragraph'>('paragraph')
const displayStep = ref(1)
const processing = ref(false)
const creating = ref(false)
const showRefDocManager = ref(false)
const showExport = ref(false)

const newTaskForm = ref({
  title: '',
  source_text: '',
  source_lang: 'en',
  target_lang: 'zh',
  literary_type: 'general' as 'poetry' | 'prose' | 'novel' | 'drama' | 'general',
  reference_document_ids: [] as number[]
})

const exportForm = ref({
  format: 'txt' as 'txt' | 'md',
  include_source: false
})

const fullTextEdit = ref('')

const sourceLanguages = computed(() => languages.value)
const targetLanguages = computed(() => languages.value.filter(l => l.code !== 'auto'))

const canCreate = computed(() => {
  return newTaskForm.value.source_text.trim() && newTaskForm.value.source_lang && newTaskForm.value.target_lang
})

const editableParagraphs = computed(() => {
  return paragraphs.value.map(para => {
    const currentText = getStepText(para, displayStep.value)
    return {
      id: para.id,
      sourceText: para.source_text,
      currentText: currentText,
      editedText: para.user_edited_text || currentText || '',
      isEdited: para.is_edited
    }
  })
})

const getDisplayTranslation = computed(() => {
  if (!currentTask.value) return ''
  switch (displayStep.value) {
    case 1: return currentTask.value.step1_translation || ''
    case 2: return currentTask.value.step2_verification || ''
    case 3: return currentTask.value.step3_revision || ''
    case 4: return currentTask.value.step4_finalization || ''
    default: return currentTask.value.final_translation || ''
  }
})

const getStepText = (para: any, step: number) => {
  switch (step) {
    case 1: return para.step1_translation || ''
    case 2: return para.step2_verification || ''
    case 3: return para.step3_revision || ''
    case 4: return para.step4_finalization || ''
    default: return para.translated_text || ''
  }
}

const loadLanguages = async () => {
  try {
    const response = await translateApi.getLanguages()
    languages.value = response.data
  } catch (error) {
    console.error('Failed to load languages:', error)
  }
}

const loadReferenceDocs = async () => {
  try {
    const response = await literaryApi.listReferences()
    referenceDocs.value = response.data
  } catch (error) {
    console.error('Failed to load reference docs:', error)
  }
}

const loadTaskList = async () => {
  try {
    const response = await literaryApi.listTranslations()
    taskList.value = response.data
  } catch (error) {
    console.error('Failed to load task list:', error)
  }
}

const selectTask = async (id: number) => {
  try {
    const response = await literaryApi.getTranslation(id, true)
    currentTask.value = response.data
    paragraphs.value = response.data.paragraphs || []
    displayStep.value = currentTask.value.current_step
    fullTextEdit.value = getDisplayTranslation.value
  } catch (error) {
    ElMessage.error('加载任务失败')
  }
}

const refreshTask = async () => {
  if (!currentTask.value) return
  await selectTask(currentTask.value.id)
  ElMessage.success('已刷新')
}

const deleteCurrentTask = async () => {
  if (!currentTask.value) return
  try {
    await ElMessageBox.confirm('确定要删除这个翻译任务吗？', '确认删除', { type: 'warning' })
    await literaryApi.deleteTranslation(currentTask.value.id)
    ElMessage.success('删除成功')
    currentTask.value = null
    await loadTaskList()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const createTask = async () => {
  creating.value = true
  try {
    const response = await literaryApi.createTranslation(newTaskForm.value)
    ElMessage.success('翻译任务创建成功')
    newTaskForm.value.source_text = ''
    newTaskForm.value.title = ''
    await loadTaskList()
    await selectTask(response.data.id)
  } catch (error) {
    ElMessage.error('创建任务失败')
  } finally {
    creating.value = false
  }
}

const startWorkflow = async () => {
  if (!currentTask.value) return
  processing.value = true
  try {
    await literaryApi.startWorkflow(currentTask.value.id)
    ElMessage.success('初译完成')
    await selectTask(currentTask.value.id)
  } catch (error) {
    ElMessage.error('翻译失败')
  } finally {
    processing.value = false
  }
}

const verifyTranslation = async () => {
  if (!currentTask.value) return
  processing.value = true
  try {
    await literaryApi.verifyTranslation(currentTask.value.id)
    ElMessage.success('校验完成')
    await selectTask(currentTask.value.id)
  } catch (error) {
    ElMessage.error('校验失败')
  } finally {
    processing.value = false
  }
}

const reviseTranslation = async () => {
  if (!currentTask.value) return
  processing.value = true
  try {
    await literaryApi.reviseTranslation(currentTask.value.id)
    ElMessage.success('修改完成')
    await selectTask(currentTask.value.id)
  } catch (error) {
    ElMessage.error('修改失败')
  } finally {
    processing.value = false
  }
}

const finalizeTranslation = async () => {
  if (!currentTask.value) return
  processing.value = true
  try {
    await literaryApi.finalizeTranslation(currentTask.value.id)
    ElMessage.success('定稿完成')
    await selectTask(currentTask.value.id)
  } catch (error) {
    ElMessage.error('定稿失败')
  } finally {
    processing.value = false
  }
}

const restartWorkflow = async () => {
  if (!currentTask.value) return
  try {
    await ElMessageBox.confirm('确定要重新翻译吗？', '确认', { type: 'warning' })
    await literaryApi.startWorkflow(currentTask.value.id)
    ElMessage.success('重新开始翻译')
    await selectTask(currentTask.value.id)
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('操作失败')
  }
}

const handleParaBlur = async (para: any) => {
  try {
    await literaryApi.updateParagraph(para.id, { user_edited_text: para.editedText })
    para.isEdited = true
    ElMessage.success('修改已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const saveFullTextEdit = async () => {
  if (!currentTask.value) return
  try {
    await literaryApi.updateTranslation(currentTask.value.id, { final_translation: fullTextEdit.value })
    ElMessage.success('修改已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const exportTranslation = async () => {
  if (!currentTask.value) return
  try {
    const response = await literaryApi.exportTranslation(currentTask.value.id, exportForm.value)
    const blob = new Blob([response.data.content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = response.data.filename
    link.click()
    URL.revokeObjectURL(url)
    showExport.value = false
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const scrollToCreate = () => {
  document.querySelector('.create-card')?.scrollIntoView({ behavior: 'smooth' })
}

const getStepLabel = (step: number) => {
  const labels = ['', '初译版', '校验版', '修改版', '定稿版']
  return labels[step] || ''
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = { pending: 'info', translating: 'warning', verifying: 'warning', revising: 'warning', finalizing: 'warning', completed: 'success', failed: 'danger' }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = { pending: '待开始', translating: '翻译中', verifying: '校验中', revising: '修改中', finalizing: '定稿中', completed: '已完成', failed: '失败' }
  return texts[status] || status
}

const getLiteraryTypeText = (type: string) => {
  const texts: Record<string, string> = { poetry: '诗歌', prose: '散文', novel: '小说', drama: '戏剧', general: '一般文学' }
  return texts[type] || type
}

const getScoreColor = (score: number) => {
  if (score >= 9) return '#67c23a'
  if (score >= 7) return '#409eff'
  if (score >= 5) return '#e6a23c'
  return '#f56c6c'
}

onMounted(() => {
  loadLanguages()
  loadReferenceDocs()
  loadTaskList()
})

watch(() => currentTask.value?.current_step, (newStep) => {
  if (newStep) displayStep.value = newStep
})
</script>

<style scoped lang="scss">
.literary-view { max-width: 1600px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 24px;
  h2 { display: flex; align-items: center; gap: 12px; margin: 0 0 8px 0; font-size: 24px;
    .header-icon { color: var(--el-color-primary); }
    .beta-tag { font-size: 12px; }
  }
  .subtitle { margin: 0; color: var(--el-text-color-secondary); font-size: 14px; }
}
.content-container { display: grid; grid-template-columns: 380px 1fr; gap: 20px; }
.sidebar { display: flex; flex-direction: column; gap: 16px; }
.create-card {
  .card-header { display: flex; align-items: center; gap: 8px; font-weight: 500; }
  .lang-select-row { display: flex; align-items: center; gap: 8px;
    .el-select { flex: 1; }
    .arrow-icon { color: var(--el-text-color-secondary); }
  }
  .reference-section { display: flex; gap: 8px; .reference-select { flex: 1; } }
  .create-btn { width: 100%; }
}
.task-list-card { flex: 1; :deep(.el-card__body) { padding: 0; max-height: 400px; overflow-y: auto; } }
.task-list {
  .task-item { padding: 12px 16px; border-bottom: 1px solid var(--el-border-color-lighter); cursor: pointer;
    &:hover { background-color: var(--el-fill-color-light); }
    &.active { background-color: var(--el-color-primary-light-9); }
    .task-header { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .task-meta { display: flex; gap: 8px; font-size: 12px; color: var(--el-text-color-secondary); }
  }
}
.workspace { background: var(--el-bg-color); border-radius: 8px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
.task-info-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--el-border-color-light);
  .info-left { .task-title { margin: 0 0 8px 0; } .info-tags { display: flex; gap: 8px; } }
}
.workflow-section { margin-bottom: 20px; .step-actions { margin-top: 16px; text-align: center; } }
.beauty-scores { display: flex; gap: 24px; margin-bottom: 20px; padding: 16px; background: var(--el-fill-color-light); border-radius: 8px;
  .score-header { font-weight: 500; margin-bottom: 12px; }
  .score-items { display: flex; flex: 1; gap: 24px; }
  .score-item { flex: 1; }
}
.editor-section {
  .editor-header { display: flex; justify-content: space-between; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--el-border-color-light); }
}
.paragraph-editor {
  .paragraphs-container { max-height: 600px; overflow-y: auto; }
  .paragraph-item { padding: 16px; margin-bottom: 12px; background: var(--el-fill-color-light); border-radius: 8px;
    .para-header { display: flex; justify-content: space-between; margin-bottom: 12px; }
    .para-content { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    .para-source-box, .para-translation-box { 
      .box-label { font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 8px; }
    }
  }
}
.full-comparison {
  .comparison-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
    .source-panel, .translation-panel { border: 1px solid var(--el-border-color); border-radius: 8px;
      .panel-header { padding: 12px 16px; background: var(--el-fill-color-light); border-bottom: 1px solid var(--el-border-color); }
      .panel-content { padding: 16px; min-height: 400px; }
    }
  }
}
.empty-workspace { display: flex; align-items: center; justify-content: center; min-height: 500px; background: var(--el-bg-color); border-radius: 8px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }
</style>
