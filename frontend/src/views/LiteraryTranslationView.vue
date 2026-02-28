<template>
  <div class="literary-view">
    <div class="page-header">
      <h2>
        <el-icon><Reading /></el-icon>
        文学翻译
        <el-tag type="success" size="small" class="beta-tag">AI四步翻译</el-tag>
      </h2>
      <p class="subtitle">翻译 → 校验 → 修改 → 定稿，追求音美、词美、意美</p>
    </div>

    <div class="content-container">
      <!-- 左侧：任务列表和创建 -->
      <div class="sidebar">
        <el-card class="create-card">
          <template #header>
            <span>新建翻译任务</span>
          </template>
          
          <el-form :model="newTaskForm" label-position="top">
            <el-form-item label="标题">
              <el-input v-model="newTaskForm.title" placeholder="输入文本标题（可选）" />
            </el-form-item>
            
            <el-form-item label="文学类型">
              <el-radio-group v-model="newTaskForm.literary_type">
                <el-radio-button label="general">一般</el-radio-button>
                <el-radio-button label="poetry">诗歌</el-radio-button>
                <el-radio-button label="prose">散文</el-radio-button>
                <el-radio-button label="novel">小说</el-radio-button>
                <el-radio-button label="drama">戏剧</el-radio-button>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item label="语言">
              <div class="lang-select-row">
                <el-select v-model="newTaskForm.source_lang" placeholder="源语言">
                  <el-option
                    v-for="lang in sourceLanguages"
                    :key="lang.code"
                    :label="lang.name"
                    :value="lang.code"
                  />
                </el-select>
                <el-icon class="arrow-icon"><ArrowRight /></el-icon>
                <el-select v-model="newTaskForm.target_lang" placeholder="目标语言">
                  <el-option
                    v-for="lang in targetLanguages"
                    :key="lang.code"
                    :label="lang.name"
                    :value="lang.code"
                  />
                </el-select>
              </div>
            </el-form-item>
            
            <el-form-item label="参考文档">
              <el-select
                v-model="newTaskForm.reference_document_ids"
                multiple
                placeholder="选择参考文档（可选）"
                style="width: 100%"
              >
                <el-option
                  v-for="doc in referenceDocs"
                  :key="doc.id"
                  :label="doc.name"
                  :value="doc.id"
                />
              </el-select>
              <el-button link type="primary" @click="showRefDocManager = true">
                <el-icon><Plus /></el-icon>
                管理参考文档
              </el-button>
            </el-form-item>
            
            <el-form-item label="原文">
              <el-input
                v-model="newTaskForm.source_text"
                type="textarea"
                :rows="6"
                placeholder="粘贴要翻译的文学文本..."
              />
            </el-form-item>
            
            <el-button
              type="primary"
              size="large"
              :loading="creating"
              :disabled="!canCreate"
              @click="createTask"
              style="width: 100%"
            >
              <el-icon><Plus /></el-icon>
              创建翻译任务
            </el-button>
          </el-form>
        </el-card>

        <el-card class="task-list-card">
          <template #header>
            <span>翻译任务</span>
          </template>
          
          <div class="task-list">
            <div
              v-for="task in taskList"
              :key="task.id"
              :class="['task-item', { active: currentTask?.id === task.id }]"
              @click="selectTask(task.id)"
            >
              <div class="task-title">{{ task.title || `任务 #${task.id}` }}</div>
              <div class="task-meta">
                <el-tag size="small" :type="getStatusType(task.status)">
                  {{ getStatusText(task.status) }}
                </el-tag>
                <span class="task-lang">{{ task.source_lang }} → {{ task.target_lang }}</span>
              </div>
              <div class="task-beauty" v-if="task.beauty_sound_score">
                <el-rate
                  :model-value="(task.beauty_sound_score + task.beauty_word_score + task.beauty_meaning_score) / 3 / 2"
                  disabled
                  show-score
                  :max="5"
                />
              </div>
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧：翻译工作区 -->
      <div class="workspace" v-if="currentTask">
        <!-- 四步流程指示器 -->
        <div class="workflow-steps">
          <el-steps :active="currentTask.current_step" finish-status="success">
            <el-step title="翻译" description="初译" />
            <el-step title="校验" description="评估三美" />
            <el-step title="修改" description="润色提升" />
            <el-step title="定稿" description="出版品质" />
          </el-steps>
          
          <div class="step-actions">
            <el-button
              v-if="currentTask.status === 'pending'"
              type="primary"
              :loading="processing"
              @click="startWorkflow"
            >
              <el-icon><VideoPlay /></el-icon>
              开始翻译
            </el-button>
            <el-button
              v-else-if="currentTask.current_step === 1"
              type="primary"
              :loading="processing"
              @click="verifyTranslation"
            >
              <el-icon><CircleCheck /></el-icon>
              执行校验
            </el-button>
            <el-button
              v-else-if="currentTask.current_step === 2"
              type="primary"
              :loading="processing"
              @click="reviseTranslation"
            >
              <el-icon><EditPen /></el-icon>
              执行修改
            </el-button>
            <el-button
              v-else-if="currentTask.current_step === 3"
              type="primary"
              :loading="processing"
              @click="finalizeTranslation"
            >
              <el-icon><DocumentChecked /></el-icon>
              执行定稿
            </el-button>
            <el-button
              v-else-if="currentTask.status === 'completed'"
              type="success"
              @click="showExport = true"
            >
              <el-icon><Download /></el-icon>
              导出译文
            </el-button>
          </div>
        </div>

        <!-- 三美评分 -->
        <div class="beauty-scores" v-if="currentTask.beauty_sound_score">
          <div class="score-item">
            <span class="score-label">音美</span>
            <el-progress
              :percentage="currentTask.beauty_sound_score * 10"
              :color="getScoreColor(currentTask.beauty_sound_score)"
              :stroke-width="16"
              :text-inside="true"
            />
          </div>
          <div class="score-item">
            <span class="score-label">词美</span>
            <el-progress
              :percentage="currentTask.beauty_word_score * 10"
              :color="getScoreColor(currentTask.beauty_word_score)"
              :stroke-width="16"
              :text-inside="true"
            />
          </div>
          <div class="score-item">
            <span class="score-label">意美</span>
            <el-progress
              :percentage="currentTask.beauty_meaning_score * 10"
              :color="getScoreColor(currentTask.beauty_meaning_score)"
              :stroke-width="16"
              :text-inside="true"
            />
          </div>
        </div>

        <!-- 对照查看 -->
        <div class="comparison-view">
          <div class="view-header">
            <el-radio-group v-model="viewMode" size="small">
              <el-radio-button label="side">左右对照</el-radio-button>
              <el-radio-button label="paragraph">段落对照</el-radio-button>
            </el-radio-group>
            <el-radio-group v-model="displayStep" size="small" v-if="currentTask.current_step > 1">
              <el-radio-button :label="1">初译</el-radio-button>
              <el-radio-button :label="2" v-if="currentTask.step2_verification">校验</el-radio-button>
              <el-radio-button :label="3" v-if="currentTask.step3_revision">修改</el-radio-button>
              <el-radio-button :label="4" v-if="currentTask.step4_finalization">定稿</el-radio-button>
            </el-radio-group>
          </div>

          <!-- 左右对照模式 -->
          <div v-if="viewMode === 'side'" class="side-by-side">
            <div class="source-panel">
              <div class="panel-header">原文</div>
              <div class="panel-content">
                <pre>{{ currentTask.source_text }}</pre>
              </div>
            </div>
            <div class="translation-panel">
              <div class="panel-header">
                译文
                <span class="step-label">{{ getStepLabel(displayStep) }}</span>
              </div>
              <div class="panel-content">
                <pre>{{ getDisplayTranslation }}</pre>
              </div>
            </div>
          </div>

          <!-- 段落对照模式 -->
          <div v-else class="paragraph-view">
            <div
              v-for="(para, index) in paragraphs"
              :key="para.id"
              class="paragraph-item"
            >
              <div class="para-number">{{ index + 1 }}</div>
              <div class="para-content">
                <div class="para-source">
                  <div class="para-label">原文</div>
                  <div class="para-text">{{ para.source_text }}</div>
                </div>
                <div class="para-translation">
                  <div class="para-label">
                    译文
                    <span v-if="para.is_edited" class="edited-badge">已编辑</span>
                  </div>
                  <el-input
                    v-model="para.user_edited_text"
                    type="textarea"
                    :rows="3"
                    :placeholder="getParagraphPlaceholder(para)"
                    @blur="saveParagraphEdit(para)"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div class="empty-state" v-else>
        <el-empty description="选择或创建一个翻译任务开始">
          <template #image>
            <el-icon :size="80" color="#dcdfe6"><Reading /></el-icon>
          </template>
        </el-empty>
      </div>
    </div>

    <!-- 参考文档管理对话框 -->
    <el-dialog
      v-model="showRefDocManager"
      title="参考文档管理"
      width="700px"
    >
      <ReferenceDocManager @close="showRefDocManager = false" @updated="loadReferenceDocs" />
    </el-dialog>

    <!-- 导出对话框 -->
    <el-dialog
      v-model="showExport"
      title="导出译文"
      width="400px"
    >
      <el-form label-position="top">
        <el-form-item label="导出格式">
          <el-radio-group v-model="exportForm.format">
            <el-radio-button label="txt">纯文本 (.txt)</el-radio-button>
            <el-radio-button label="md">Markdown (.md)</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="exportForm.include_source">
            包含原文对照
          </el-checkbox>
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

// ===== 状态 =====
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

// 表单
const newTaskForm = ref({
  title: '',
  source_text: '',
  source_lang: 'en',
  target_lang: 'zh',
  literary_type: 'general' as 'poetry' | 'prose' | 'novel' | 'drama' | 'general',
  reference_document_ids: [] as number[]
})

const exportForm = ref({
  format: 'txt',
  include_source: false
})

// ===== 计算属性 =====
const sourceLanguages = computed(() => languages.value)
const targetLanguages = computed(() => languages.value.filter(l => l.code !== 'auto'))

const canCreate = computed(() => {
  return newTaskForm.value.source_text.trim() && 
         newTaskForm.value.source_lang && 
         newTaskForm.value.target_lang
})

const getDisplayTranslation = computed(() => {
  if (!currentTask.value) return ''
  switch (displayStep.value) {
    case 1: return currentTask.value.step1_translation || '等待翻译...'
    case 2: return currentTask.value.step2_verification || currentTask.value.step1_translation || '等待校验...'
    case 3: return currentTask.value.step3_revision || currentTask.value.step2_verification || '等待修改...'
    case 4: return currentTask.value.step4_finalization || currentTask.value.step3_revision || '等待定稿...'
    default: return currentTask.value.final_translation || ''
  }
})

// ===== 方法 =====
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
  } catch (error) {
    ElMessage.error('加载任务失败')
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
    ElMessage.success('翻译完成，进入校验阶段')
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
    const response = await literaryApi.verifyTranslation(currentTask.value.id)
    ElMessage.success('校验完成，进入修改阶段')
    if (response.data.beauty_scores) {
      ElMessage.info(`三美评分 - 音美: ${response.data.beauty_scores.sound.toFixed(1)}, 词美: ${response.data.beauty_scores.word.toFixed(1)}, 意美: ${response.data.beauty_scores.meaning.toFixed(1)}`)
    }
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
    ElMessage.success('修改完成，进入定稿阶段')
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
    ElMessage.success('定稿完成！翻译任务结束')
    await selectTask(currentTask.value.id)
  } catch (error) {
    ElMessage.error('定稿失败')
  } finally {
    processing.value = false
  }
}

const saveParagraphEdit = async (para: any) => {
  try {
    await literaryApi.updateParagraph(para.id, {
      user_edited_text: para.user_edited_text
    })
    para.is_edited = true
    ElMessage.success('段落已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const exportTranslation = async () => {
  if (!currentTask.value) return
  try {
    const response = await literaryApi.exportTranslation(
      currentTask.value.id,
      exportForm.value
    )
    
    // 下载文件
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

const getParagraphPlaceholder = (para: any) => {
  switch (displayStep.value) {
    case 1: return para.step1_translation || '等待翻译...'
    case 2: return para.step2_verification || para.step1_translation || '等待校验...'
    case 3: return para.step3_revision || para.step2_verification || '等待修改...'
    case 4: return para.step4_finalization || para.step3_revision || '等待定稿...'
    default: return para.translated_text || '等待翻译...'
  }
}

const getStepLabel = (step: number) => {
  const labels = ['', '初译', '校验版', '修改版', '定稿']
  return labels[step] || ''
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'info',
    translating: 'warning',
    verifying: 'warning',
    revising: 'warning',
    finalizing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '待开始',
    translating: '翻译中',
    verifying: '校验中',
    revising: '修改中',
    finalizing: '定稿中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

const getScoreColor = (score: number) => {
  if (score >= 9) return '#67c23a'
  if (score >= 7) return '#409eff'
  if (score >= 5) return '#e6a23c'
  return '#f56c6c'
}

// ===== 生命周期 =====
onMounted(() => {
  loadLanguages()
  loadReferenceDocs()
  loadTaskList()
})

// 监听当前任务变化，同步显示步骤
watch(() => currentTask.value?.current_step, (newStep) => {
  if (newStep) {
    displayStep.value = newStep
  }
})
</script>

<style scoped lang="scss">
.literary-view {
  max-width: 1600px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
  
  h2 {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 0 0 8px 0;
    font-size: 24px;
    
    .el-icon {
      color: var(--el-color-primary);
    }
  }
  
  .beta-tag {
    font-size: 12px;
  }
  
  .subtitle {
    margin: 0;
    color: var(--el-text-color-secondary);
    font-size: 14px;
  }
}

.content-container {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.create-card {
  .lang-select-row {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .el-select {
      flex: 1;
    }
    
    .arrow-icon {
      color: var(--el-text-color-secondary);
    }
  }
}

.task-list-card {
  flex: 1;
  
  :deep(.el-card__body) {
    padding: 0;
    max-height: 400px;
    overflow-y: auto;
  }
}

.task-list {
  .task-item {
    padding: 12px 16px;
    border-bottom: 1px solid var(--el-border-color-lighter);
    cursor: pointer;
    transition: background-color 0.2s;
    
    &:hover {
      background-color: var(--el-fill-color-light);
    }
    
    &.active {
      background-color: var(--el-color-primary-light-9);
    }
    
    .task-title {
      font-weight: 500;
      margin-bottom: 4px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    
    .task-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
      
      .task-lang {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
    
    .task-beauty {
      :deep(.el-rate__text) {
        font-size: 12px;
        margin-left: 4px;
      }
    }
  }
}

.workspace {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.workflow-steps {
  margin-bottom: 20px;
  
  :deep(.el-steps) {
    margin-bottom: 16px;
  }
  
  .step-actions {
    text-align: center;
    padding: 12px;
    background: var(--el-fill-color-light);
    border-radius: 8px;
  }
}

.beauty-scores {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
  padding: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
  border-radius: 8px;
  
  .score-item {
    .score-label {
      display: block;
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-bottom: 8px;
    }
  }
}

.comparison-view {
  .view-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--el-border-color-light);
  }
}

.side-by-side {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  
  .source-panel,
  .translation-panel {
    border: 1px solid var(--el-border-color);
    border-radius: 8px;
    overflow: hidden;
  }
  
  .panel-header {
    padding: 12px 16px;
    background: var(--el-fill-color-light);
    border-bottom: 1px solid var(--el-border-color);
    font-weight: 500;
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .step-label {
      font-size: 12px;
      color: var(--el-color-primary);
      background: var(--el-color-primary-light-9);
      padding: 2px 8px;
      border-radius: 4px;
    }
  }
  
  .panel-content {
    padding: 16px;
    min-height: 400px;
    max-height: 600px;
    overflow-y: auto;
    
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: inherit;
      line-height: 1.8;
      font-size: 15px;
    }
  }
}

.paragraph-view {
  .paragraph-item {
    display: flex;
    gap: 12px;
    padding: 16px;
    margin-bottom: 12px;
    background: var(--el-fill-color-light);
    border-radius: 8px;
    
    .para-number {
      width: 28px;
      height: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: var(--el-color-primary);
      color: white;
      border-radius: 50%;
      font-size: 12px;
      font-weight: 600;
      flex-shrink: 0;
    }
    
    .para-content {
      flex: 1;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    
    .para-label {
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .edited-badge {
      font-size: 10px;
      color: var(--el-color-success);
      background: var(--el-color-success-light-9);
      padding: 2px 6px;
      border-radius: 4px;
    }
    
    .para-source,
    .para-translation {
      .para-text {
        line-height: 1.8;
        font-size: 15px;
      }
    }
    
    .para-source .para-text {
      color: var(--el-text-color-regular);
    }
    
    .para-translation {
      :deep(.el-textarea__inner) {
        font-size: 15px;
        line-height: 1.8;
      }
    }
  }
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 500px;
  background: var(--el-bg-color);
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

@media (max-width: 1200px) {
  .content-container {
    grid-template-columns: 1fr;
  }
  
  .sidebar {
    order: 2;
  }
  
  .workspace {
    order: 1;
  }
  
  .side-by-side {
    grid-template-columns: 1fr;
  }
  
  .paragraph-item .para-content {
    grid-template-columns: 1fr;
  }
}
</style>
