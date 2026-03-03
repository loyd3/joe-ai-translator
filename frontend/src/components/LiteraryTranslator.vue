<template>
  <div class="literary-translator">
    <!-- 顶部工具栏 -->
    <div class="top-toolbar">
      <div class="toolbar-left">
        <el-select
          :model-value="currentTask?.source_lang"
          placeholder="源语言"
          size="default"
          class="lang-select"
          @update:model-value="(v) => setTaskField('source_lang', v)"
        >
          <el-option v-for="lang in sourceLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
        </el-select>
        <el-button circle class="swap-btn" @click="swapLanguages">
          <el-icon><Switch /></el-icon>
        </el-button>
        <el-select
          :model-value="currentTask?.target_lang"
          placeholder="目标语言"
          size="default"
          class="lang-select"
          @update:model-value="(v) => setTaskField('target_lang', v)"
        >
          <el-option v-for="lang in targetLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
        </el-select>
      </div>

      <div class="toolbar-center">
        <el-steps :active="currentStep" finish-status="success" simple class="workflow-steps">
          <el-step title="翻译" />
          <el-step title="校验" />
          <el-step title="润色" />
          <el-step title="定稿" />
        </el-steps>
      </div>

      <div class="toolbar-right">
        <el-button-group>
          <el-button size="default" @click="showTermLibrary = true">
            <el-icon><Collection /></el-icon>
            词库
          </el-button>
          <el-button size="default" @click="showHistory = true">
            <el-icon><Clock /></el-icon>
            历史
          </el-button>
        </el-button-group>
      </div>
    </div>

    <!-- 主翻译区域 -->
    <div class="translation-area">
      <!-- 原文输入区 -->
      <div class="input-panel">
        <div class="panel-header">
          <span class="lang-label">{{ getLangName(currentTask?.source_lang || 'auto') }}</span>
          <div class="header-actions">
            <el-tooltip content="清空">
              <el-button link @click="clearInput">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="粘贴">
              <el-button link @click="pasteText">
                <el-icon><DocumentCopy /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>

        <div class="requirements-row">
          <span class="label">翻译需求（可选）</span>
          <el-input
            v-model="userRequirements"
            type="textarea"
            :rows="2"
            placeholder="如：偏书面语、保留专有名词原文、统一某术语译法等..."
            maxlength="500"
            show-word-limit
            class="requirements-input"
          />
        </div>
        <div class="textarea-wrapper">
          <el-input
            v-model="inputText"
            type="textarea"
            :autosize="{ minRows: 6 }"
            placeholder="在此输入要翻译的文学文本，或使用下方「上传文件」..."
            class="translation-textarea"
            :disabled="isTranslating"
          />
          <div class="char-count">{{ inputText.length }} 字符</div>
        </div>
        <div class="upload-row">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :show-file-list="false"
            :accept="uploadAccept"
            @change="onFileSelect"
          >
            <el-button type="default" size="small">
              <el-icon><Upload /></el-icon>
              上传文件翻译
            </el-button>
          </el-upload>
        </div>
        <div class="panel-footer">
          <div class="footer-left">
            <el-select v-model="selectedLiteraryType" placeholder="翻译类型" size="small" style="width: 140px;">
              <el-option-group label="文学">
                <el-option label="一般" value="general" />
                <el-option label="诗歌" value="poetry" />
                <el-option label="散文" value="prose" />
                <el-option label="小说" value="novel" />
                <el-option label="戏剧" value="drama" />
              </el-option-group>
              <el-option-group label="专业">
                <el-option label="科技" value="tech" />
                <el-option label="商业" value="business" />
                <el-option label="贸易" value="trade" />
                <el-option label="法律" value="legal" />
                <el-option label="医学" value="medical" />
              </el-option-group>
            </el-select>
          </div>
          <div class="footer-right">
            <el-button type="primary" size="default" :loading="isTranslating" @click="startTranslation">
              <el-icon><Promotion /></el-icon>
              开始翻译（自动执行四步）
            </el-button>
          </div>
        </div>
      </div>

      <!-- 译文输出区 -->
      <div class="output-panel">
        <div class="panel-header">
          <span class="lang-label">{{ getLangName(currentTask?.target_lang || 'en') }}</span>
          <div class="header-actions">
            <el-tooltip content="复制译文">
              <el-button link @click="copyOutput">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="朗读">
              <el-button link @click="speakOutput">
                <el-icon><Microphone /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>

        <div class="textarea-wrapper">
          <el-input
            v-model="outputText"
            type="textarea"
            :autosize="{ minRows: 6 }"
            placeholder="译文将显示在这里..."
            class="translation-textarea"
            :readonly="!isEditing"
          />
          <div v-if="isTranslating" class="loading-overlay">
            <el-skeleton :rows="6" animated />
          </div>
        </div>

        <div class="panel-footer">
          <div class="footer-left">
            <el-radio-group v-model="displayVersion" size="small" v-if="hasTranslations">
              <el-radio-button :label="1">初译</el-radio-button>
              <el-radio-button :label="2" :disabled="!step2Done">校验</el-radio-button>
              <el-radio-button :label="3" :disabled="!step3Done">润色</el-radio-button>
              <el-radio-button :label="4" :disabled="!step4Done">定稿</el-radio-button>
            </el-radio-group>
          </div>
          <div class="footer-right">
            <el-button
              v-if="canProceedToNext"
              type="primary"
              size="default"
              :loading="isProcessing"
              @click="proceedToNext"
            >
              {{ nextStepLabel }}
              <el-icon class="el-icon--right"><ArrowRight /></el-icon>
            </el-button>
            <el-button
              v-if="isWorkflowRunning"
              type="danger"
              size="default"
              :loading="isProcessing"
              @click="stopComponentWorkflow"
            >
              终止流程
            </el-button>
            <el-button-group v-if="isCompleted">
              <el-button type="success" size="default" @click="showExport = true">
                <el-icon><Download /></el-icon>
                导出
              </el-button>
              <el-button size="default" @click="toggleEdit">
                <el-icon><Edit /></el-icon>
                {{ isEditing ? '完成' : '编辑' }}
              </el-button>
            </el-button-group>
          </div>
        </div>
      </div>
    </div>

    <!-- 三美评分面板 -->
    <div class="beauty-scores-panel" v-if="hasBeautyScores">
      <div class="score-item">
        <div class="score-label">
          <el-icon><Headset /></el-icon>
          <span>音美</span>
        </div>
        <!-- <el-progress
          :percentage="beautyScores.sound"
          :color="getScoreColor(beautyScores.sound)"
          :stroke-width="10"
          class="score-progress"
        /> -->
        <span class="score-value">{{ beautyScores.sound.toFixed(1) }}</span>
      </div>
      <div class="score-item">
        <div class="score-label">
          <el-icon><EditPen /></el-icon>
          <span>词美</span>
        </div>
        <!-- <el-progress
          :percentage="beautyScores.word"
          :color="getScoreColor(beautyScores.word)"
          :stroke-width="10"
          class="score-progress"
        /> -->
        <span class="score-value">{{ beautyScores.word.toFixed(1) }}</span>
      </div>
      <div class="score-item">
        <div class="score-label">
          <el-icon><Sunrise /></el-icon>
          <span>意美</span>
        </div>
        <!-- <el-progress
          :percentage="beautyScores.meaning"
          :color="getScoreColor(beautyScores.meaning)"
          :stroke-width="10"
          class="score-progress"
        /> -->
        <span class="score-value">{{ beautyScores.meaning.toFixed(1) }}</span>
      </div>
    </div>

    <!-- 对照编辑模式 -->
    <div class="comparison-mode" v-if="showComparison">
      <el-divider content-position="left">
        <el-icon><DocumentCopy /></el-icon>
        段落对照编辑
      </el-divider>
      <div class="comparison-list">
        <div v-for="(para, index) in paragraphs" :key="index" class="comparison-item">
          <div class="comparison-header">
            <span class="para-index">段落 {{ index + 1 }}</span>
            <el-tag v-if="para.isEdited" type="success" size="small">已编辑</el-tag>
          </div>
          <div class="comparison-content">
            <div class="source-box">
              <div class="box-label">原文</div>
              <div class="box-text">{{ para.source }}</div>
            </div>
            <div class="target-box">
              <div class="box-label">
                <span>译文</span>
                <span class="edit-hint">点击编辑</span>
              </div>
              <el-input
                v-model="para.translation"
                type="textarea"
                :autosize="{ minRows: 2 }"
                @blur="saveParagraph(para)"
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 专业词库侧边栏 -->
    <el-drawer
      v-model="showTermLibrary"
      title="专业词库"
      size="450px"
      destroy-on-close
    >
      <TermLibraryPanel
        ref="termPanelRef"
        :literary-type="selectedLiteraryType"
        :source-lang="currentTask?.source_lang"
        :target-lang="currentTask?.target_lang"
      />
    </el-drawer>

    <!-- 历史记录侧边栏 -->
    <el-drawer
      v-model="showHistory"
      title="翻译历史"
      size="400px"
    >
      <div class="history-list">
        <div
          v-for="task in taskHistory"
          :key="task.id"
          class="history-item"
          @click="loadTask(task)"
        >
          <div class="history-main">
            <div class="history-title">{{ task.title || `任务 #${task.id}` }}</div>
            <div class="history-meta">
              <el-tag size="small" :type="getStatusType(task.status)">
                {{ getStatusText(task.status) }}
              </el-tag>
              <span class="history-date">{{ formatDate(task.created_at) }}</span>
            </div>
          </div>
          <div class="history-actions" @click.stop>
            <el-tooltip content="润色" placement="top">
              <el-button link type="primary" size="small" circle @click="openEditTaskDialog(task)">
                <el-icon><Edit /></el-icon>
              </el-button>
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <el-button link type="danger" size="small" circle @click="confirmDeleteTask(task)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-tooltip>
          </div>
        </div>
      </div>
    </el-drawer>

    <!-- 编辑任务对话框 -->
    <el-dialog v-model="showEditTask" title="修改任务" width="420px" destroy-on-close>
      <el-form v-if="editingTask" label-position="top">
        <el-form-item label="任务标题">
          <el-input v-model="editForm.title" placeholder="选填，如：第一章" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" placeholder="状态" style="width: 100%;">
            <el-option label="待开始" value="pending" />
            <el-option label="翻译中" value="translating" />
            <el-option label="校验中" value="verifying" />
            <el-option label="润色中" value="revising" />
            <el-option label="定稿中" value="finalizing" />
            <el-option label="已完成" value="completed" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditTask = false">取消</el-button>
        <el-button type="primary" @click="submitEditTask">保存</el-button>
      </template>
    </el-dialog>

    <!-- 导出对话框 -->
    <el-dialog v-model="showExport" title="导出译文" width="480px">
      <el-form label-position="top">
        <el-form-item label="选择格式">
          <div class="format-grid">
            <div
              v-for="fmt in exportFormats"
              :key="fmt.value"
              :class="['format-option', { active: exportFormat === fmt.value }]"
              @click="exportFormat = fmt.value"
            >
              <el-icon :size="24"><component :is="fmt.icon" /></el-icon>
              <span class="format-name">{{ fmt.label }}</span>
              <span class="format-ext">.{{ fmt.value }}</span>
            </div>
          </div>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="exportWithSource">包含原文对照</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExport = false">取消</el-button>
        <el-button type="primary" @click="exportResult" :loading="isExporting">
          导出
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Memo, Monitor, DataLine, Grid, Upload, Edit, Delete } from '@element-plus/icons-vue'
import { literaryApi, translateApi } from '@/api'
import TermLibraryPanel from './TermLibraryPanel.vue'

// 图标映射
const iconMap: Record<string, any> = {
  Document,
  Memo,
  Monitor,
  DataLine,
  Grid
}

// 状态
const languages = ref<{ code: string; name: string }[]>([])
const inputText = ref('')
const outputText = ref('')
const userRequirements = ref('')
const selectedLiteraryType = ref('general')
const uploadRef = ref<any>(null)
const currentTask = ref<any>(null)
const paragraphs = ref<any[]>([])
const isTranslating = ref(false)
const isProcessing = ref(false)
const isEditing = ref(false)
const isExporting = ref(false)
const showComparison = ref(false)
const showTermLibrary = ref(false)
const showHistory = ref(false)
const showExport = ref(false)
const showEditTask = ref(false)
const editingTask = ref<any>(null)
const editForm = ref({ title: '', status: '' })
const termPanelRef = ref<any>(null)
const taskHistory = ref<any[]>([])
const currentStep = ref(0)
const displayVersion = ref(1)

const exportFormat = ref('txt')
const exportWithSource = ref(false)

const exportFormats = [
  { value: 'txt', label: '纯文本', icon: 'Document' },
  { value: 'md', label: 'Markdown', icon: 'Memo' },
  { value: 'html', label: '网页', icon: 'Monitor' },
  { value: 'json', label: 'JSON', icon: 'DataLine' },
  { value: 'csv', label: '表格', icon: 'Grid' }
]

// 计算属性
const sourceLanguages = computed(() => languages.value)
const targetLanguages = computed(() => languages.value.filter(l => l.code !== 'auto'))

const hasTranslations = computed(() => currentTask.value?.step1_translation)
const step2Done = computed(() => currentTask.value?.step2_verification)
const step3Done = computed(() => currentTask.value?.step3_revision)
const step4Done = computed(() => currentTask.value?.step4_finalization)
const isCompleted = computed(() => currentTask.value?.status === 'completed')

const canProceedToNext = computed(() => {
  if (!currentTask.value) return false
  return currentTask.value.status !== 'completed' && currentTask.value.status !== 'pending'
})

const nextStepLabel = computed(() => {
  const labels = ['', '执行校验', '执行润色', '执行定稿']
  return labels[currentStep.value] || ''
})

const hasBeautyScores = computed(() => {
  return currentTask.value?.beauty_sound_score !== null
})

const beautyScores = computed(() => ({
  sound: (currentTask.value?.beauty_sound_score || 0) * 10,
  word: (currentTask.value?.beauty_word_score || 0) * 10,
  meaning: (currentTask.value?.beauty_meaning_score || 0) * 10
}))

// 方法
const loadLanguages = async () => {
  try {
    const response = await translateApi.getLanguages()
    languages.value = response.data
  } catch (error) {
    console.error('Failed to load languages:', error)
  }
}

const getLangName = (code: string) => {
  const lang = languages.value.find(l => l.code === code)
  return lang?.name || code
}

const swapLanguages = () => {
  if (currentTask.value) {
    const temp = currentTask.value.source_lang
    currentTask.value.source_lang = currentTask.value.target_lang
    currentTask.value.target_lang = temp
  }
}

const setTaskField = (field: 'source_lang' | 'target_lang', value: string) => {
  if (currentTask.value) (currentTask.value as Record<string, string>)[field] = value
}

const clearInput = () => {
  inputText.value = ''
}

const pasteText = async () => {
  try {
    const text = await navigator.clipboard.readText()
    inputText.value = text
    ElMessage.success('已粘贴')
  } catch {
    ElMessage.error('无法读取剪贴板')
  }
}

const copyOutput = () => {
  navigator.clipboard.writeText(outputText.value)
  ElMessage.success('已复制到剪贴板')
}

const speakOutput = () => {
  const utterance = new SpeechSynthesisUtterance(outputText.value)
  utterance.lang = currentTask.value?.target_lang || 'en'
  speechSynthesis.speak(utterance)
}

const startTranslation = async () => {
  if (!inputText.value.trim()) {
    ElMessage.warning('请输入要翻译的文本')
    return
  }

  isTranslating.value = true
  try {
    const response = await literaryApi.createTranslation({
      title: '',
      source_text: inputText.value,
      source_lang: currentTask.value?.source_lang || 'auto',
      target_lang: currentTask.value?.target_lang || 'en',
      literary_type: selectedLiteraryType.value as any,
      user_requirements: userRequirements.value.trim() || undefined
    })
    currentTask.value = response.data
    currentStep.value = 1
    await literaryApi.startWorkflow(currentTask.value.id)
    startComponentPolling()
  } catch (error) {
    ElMessage.error('翻译失败')
    isTranslating.value = false
  }
}

const uploadAccept = '.txt,.md,.doc,.docx,.pdf,.mobi,.azw,.html,.htm,.xml,.json,.csv,.yaml,.yml,.rst,.tex,.srt,.vtt,.log,.ini,.cfg'
const allowedUploadExtensions = new Set(['txt', 'md', 'markdown', 'text', 'doc', 'docx', 'pdf', 'mobi', 'azw', 'html', 'htm', 'xml', 'json', 'csv', 'yaml', 'yml', 'rst', 'tex', 'srt', 'sub', 'vtt', 'log', 'ini', 'cfg', 'properties'])
const onFileSelect = async (opts: { file: File }) => {
  const file = opts?.file
  if (!file) return
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!ext || !allowedUploadExtensions.has(ext)) {
    ElMessage.warning('请选择支持的文件：txt、docx、pdf、mobi 或常见文本格式')
    return
  }
  isTranslating.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    form.append('source_lang', currentTask.value?.source_lang || 'auto')
    form.append('target_lang', currentTask.value?.target_lang || 'en')
    form.append('literary_type', selectedLiteraryType.value)
    form.append('auto_run', 'true')
    if (userRequirements.value.trim()) form.append('user_requirements', userRequirements.value.trim())
    const res = await literaryApi.uploadAndTranslate(form)
    const id = res.data?.translation_id
    if (!id) throw new Error('未返回任务 ID')
    currentTask.value = (await literaryApi.getTranslation(id, true)).data
    currentStep.value = currentTask.value.current_step
    outputText.value = currentTask.value.final_translation ||
      currentTask.value.step4_finalization ||
      currentTask.value.step3_revision ||
      currentTask.value.step2_verification ||
      currentTask.value.step1_translation ||
      ''
    ElMessage.success('文件已上传并完成四步翻译，可在线编辑或导出')
  } catch (e) {
    ElMessage.error('上传或翻译失败')
  } finally {
    isTranslating.value = false
    uploadRef.value?.clearFiles?.()
  }
}

const refreshTask = async () => {
  if (!currentTask.value) return
  try {
    const response = await literaryApi.getTranslation(currentTask.value.id, true)
    currentTask.value = response.data
    outputText.value = currentTask.value.final_translation ||
                       currentTask.value.step4_finalization ||
                       currentTask.value.step3_revision ||
                       currentTask.value.step2_verification ||
                       currentTask.value.step1_translation || ''
    currentStep.value = currentTask.value.current_step
  } catch (error) {
    console.error('Failed to refresh task:', error)
  }
}

let componentPollTimer: ReturnType<typeof setInterval> | null = null

const startComponentPolling = () => {
  stopComponentPolling()
  componentPollTimer = setInterval(async () => {
    if (!currentTask.value) return stopComponentPolling()
    try {
      const res = await literaryApi.getWorkflowStatus(currentTask.value.id)
      const data = res.data
      currentTask.value.status = data.overall_status
      currentStep.value = data.current_step

      if (data.overall_status === 'completed' || data.overall_status === 'failed') {
        stopComponentPolling()
        await refreshTask()
        isTranslating.value = false
        isProcessing.value = false
        if (data.overall_status === 'completed') {
          ElMessage.success('四步流程已完成，可在线编辑或导出')
        } else {
          ElMessage.error('翻译流程失败')
        }
      }
    } catch (error) {
      console.error('Polling error:', error)
    }
  }, 12000)
}

const stopComponentPolling = () => {
  if (componentPollTimer) {
    clearInterval(componentPollTimer)
    componentPollTimer = null
  }
}

const isWorkflowRunning = computed(() =>
  ['translating', 'verifying', 'revising', 'finalizing'].includes(currentTask.value?.status)
)

const stopComponentWorkflow = async () => {
  if (!currentTask.value) return
  isProcessing.value = true
  try {
    await literaryApi.stopWorkflow(currentTask.value.id)
    stopComponentPolling()
    await refreshTask()
    isTranslating.value = false
    isProcessing.value = false
    ElMessage.success('已终止')
  } catch (error) {
    ElMessage.error('中止失败')
    isProcessing.value = false
  }
}

const proceedToNext = async () => {
  if (!currentTask.value) return
  isProcessing.value = true
  try {
    await literaryApi.startWorkflow(currentTask.value.id)
    startComponentPolling()
  } catch (error) {
    ElMessage.error('处理失败')
    isProcessing.value = false
  }
}

const toggleEdit = () => {
  isEditing.value = !isEditing.value
  if (!isEditing.value) {
    // 保存编辑
    saveTranslation()
  }
}

const saveTranslation = async () => {
  if (!currentTask.value) return
  try {
    await literaryApi.updateTranslation(currentTask.value.id, {
      final_translation: outputText.value
    })
    ElMessage.success('翻译已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const saveParagraph = async (para: any) => {
  try {
    await literaryApi.updateParagraph(para.id, {
      user_edited_text: para.translation
    })
    para.isEdited = true
    ElMessage.success('段落已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const exportResult = async () => {
  if (!currentTask.value) return
  isExporting.value = true
  try {
    const response = await literaryApi.exportTranslation(
      currentTask.value.id,
      {
        format: exportFormat.value as any,
        include_source: exportWithSource.value
      }
    )

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
  } finally {
    isExporting.value = false
  }
}

const loadHistory = async () => {
  try {
    const response = await literaryApi.listTranslations({ limit: 20 })
    taskHistory.value = response.data
  } catch (error) {
    console.error('Failed to load history:', error)
  }
}

const openEditTaskDialog = (task: any) => {
  editingTask.value = task
  editForm.value = { title: task.title || '', status: task.status || 'pending' }
  showEditTask.value = true
}

const submitEditTask = async () => {
  if (!editingTask.value) return
  const id = editingTask.value.id
  try {
    await literaryApi.updateTranslation(id, {
      title: editForm.value.title || undefined,
      status: editForm.value.status || undefined
    })
    ElMessage.success('已保存')
    showEditTask.value = false
    editingTask.value = null
    await loadHistory()
    if (currentTask.value?.id === id) {
      const t = taskHistory.value.find((x: any) => x.id === id)
      if (t) currentTask.value = t
    }
  } catch (e) {
    ElMessage.error('保存失败')
  }
}

const confirmDeleteTask = async (task: any) => {
  try {
    await ElMessageBox.confirm('确定删除该翻译任务？删除后不可恢复。', '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await literaryApi.deleteTranslation(task.id)
    ElMessage.success('已删除')
    taskHistory.value = taskHistory.value.filter((t: any) => t.id !== task.id)
    if (currentTask.value?.id === task.id) {
      currentTask.value = null
      inputText.value = ''
      outputText.value = ''
      currentStep.value = 0
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const loadTask = async (task: any) => {
  currentTask.value = task
  inputText.value = task.source_text
  await refreshTask()
  showHistory.value = false
}

const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString('zh-CN')
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
    revising: '润色中',
    finalizing: '定稿中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

const getScoreColor = (score: number) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#409eff'
  if (score >= 40) return '#e6a23c'
  return '#f56c6c'
}

onMounted(() => {
  loadLanguages()
  loadHistory()
})

onUnmounted(() => {
  stopComponentPolling()
})
</script>

<style scoped lang="scss">
.literary-translator {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;

  .top-toolbar {
    background: #fff;
    padding: 12px 24px;
    border-bottom: 1px solid #e4e7ed;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .lang-select {
        width: 140px;
      }

      .swap-btn {
        transform: rotate(90deg);
      }
    }

    .toolbar-center {
      flex: 1;
      max-width: 500px;
      margin: 0 24px;

      .workflow-steps {
        :deep(.el-step__title) {
          font-size: 13px;
        }
      }
    }

    .toolbar-right {
      display: flex;
      gap: 8px;
    }
  }

  .translation-area {
    flex: 1;
    display: flex;
    padding: 24px;
    gap: 24px;
    overflow: hidden;

    .input-panel,
    .output-panel {
      flex: 1;
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
      display: flex;
      flex-direction: column;
      overflow: hidden;

      .panel-header {
        padding: 16px 20px;
        border-bottom: 1px solid #ebeef5;
        display: flex;
        justify-content: space-between;
        align-items: center;

        .lang-label {
          font-weight: 600;
          color: #303133;
          font-size: 15px;
        }

        .header-actions {
          display: flex;
          gap: 4px;
        }
      }

      .textarea-wrapper {
        flex: 1;
        position: relative;
        padding: 20px;

        .translation-textarea {
          height: 100%;

          :deep(.el-textarea__inner) {
            height: 100%;
            border: none;
            resize: none;
            font-size: 16px;
            line-height: 1.8;
            padding: 0;
            box-shadow: none;

            &::placeholder {
              color: #c0c4cc;
            }
          }
        }

        .char-count {
          position: absolute;
          bottom: 20px;
          right: 20px;
          font-size: 13px;
          color: #909399;
          background: rgba(255, 255, 255, 0.9);
          padding: 4px 8px;
          border-radius: 4px;
        }

        .loading-overlay {
          position: absolute;
          top: 20px;
          left: 20px;
          right: 20px;
          bottom: 20px;
          background: rgba(255, 255, 255, 0.9);
          display: flex;
          align-items: center;
          justify-content: center;
        }
      }

      .requirements-row {
        margin-bottom: 12px;
        .label { font-size: 13px; color: #606266; margin-right: 8px; }
        .requirements-input { margin-top: 6px; }
      }
      .upload-row {
        margin-top: 10px;
        margin-bottom: 4px;
      }

      .panel-footer {
        padding: 16px 20px;
        border-top: 1px solid #ebeef5;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
    }
  }

  .beauty-scores-panel {
    background: #fff;
    margin: 0 24px 24px;
    padding: 20px 24px;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
    display: flex;
    gap: 40px;

    .score-item {
      flex: 1;
      display: flex;
      align-items: center;
      gap: 12px;

      .score-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 14px;
        color: #606266;
        min-width: 60px;

        .el-icon {
          font-size: 18px;
        }
      }

      .score-progress {
        flex: 1;
      }

      .score-value {
        font-size: 18px;
        font-weight: 600;
        min-width: 50px;
        text-align: right;
      }
    }
  }

  .comparison-mode {
    background: #fff;
    margin: 0 24px 24px;
    padding: 24px;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);

    .comparison-list {
      display: flex;
      flex-direction: column;
      gap: 16px;

      .comparison-item {
        border: 1px solid #ebeef5;
        border-radius: 8px;
        overflow: hidden;

        .comparison-header {
          padding: 12px 16px;
          background: #f5f7fa;
          display: flex;
          justify-content: space-between;
          align-items: center;

          .para-index {
            font-weight: 500;
            color: #303133;
          }
        }

        .comparison-content {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 0;

          .source-box,
          .target-box {
            padding: 16px;

            .box-label {
              font-size: 12px;
              color: #909399;
              margin-bottom: 8px;
              display: flex;
              justify-content: space-between;

              .edit-hint {
                color: #409eff;
              }
            }

            .box-text {
              font-size: 14px;
              line-height: 1.6;
              color: #606266;
            }
          }

          .source-box {
            background: #fafafa;
            border-right: 1px solid #ebeef5;
          }
        }
      }
    }
  }

  .format-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;

    .format-option {
      border: 2px solid #e4e7ed;
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        border-color: #409eff;
        background: #f5f7fa;
      }

      &.active {
        border-color: #409eff;
        background: #e8f4ff;
      }

      .format-name {
        font-size: 14px;
        font-weight: 500;
      }

      .format-ext {
        font-size: 12px;
        color: #909399;
      }
    }
  }

  .history-list {
    .history-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      padding: 16px;
      border-bottom: 1px solid #ebeef5;
      cursor: pointer;
      transition: background 0.2s;

      &:hover {
        background: #f5f7fa;
      }
    }
    .history-main {
      flex: 1;
      min-width: 0;
    }
    .history-title {
      font-weight: 500;
      margin-bottom: 8px;
    }
    .history-meta {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .history-date {
        font-size: 13px;
        color: #909399;
      }
    }
    .history-actions {
      flex-shrink: 0;
    }
  }
}
</style>
