<template>
  <div class="literary-view">
    <!-- 左侧边栏：任务列表 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>
          <el-icon><Reading /></el-icon>
          文学翻译
        </h3>
        <el-button type="primary" size="small" circle @click="createNewTask">
          <el-icon><Plus /></el-icon>
        </el-button>
      </div>

      <div class="task-list" v-loading="loadingTasks">
        <div
          v-for="task in taskList"
          :key="task.id"
          :class="['task-item', { active: currentTask?.id === task.id }]"
          @click="selectTask(task)"
        >
          <div class="task-info">
            <div class="task-title">{{ task.title || `任务 #${task.id}` }}</div>
            <div class="task-meta">
              <el-tag size="small" :type="getStatusType(task.status)">
                {{ getStatusText(task.status) }}
              </el-tag>
              <span class="task-lang">{{ task.source_lang }} → {{ task.target_lang }}</span>
            </div>
          </div>
          <div class="task-actions" @click.stop>
            <el-tooltip content="修改" placement="top">
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
        <el-empty v-if="taskList.length === 0" description="暂无任务" :image-size="80" />
      </div>

      <div class="sidebar-footer">
        <el-button @click="showTermLibrary = true" class="term-library-btn">
          <el-icon><Collection /></el-icon>
          专业词库
        </el-button>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <LiteraryTranslator v-if="!currentTask" @create-task="createNewTask" />
      
      <template v-else>
        <div class="translation-workspace">
          <!-- 翻译编辑器组件 -->
          <div class="editor-container">
            <!-- 工具栏 -->
            <div class="toolbar">
              <div class="toolbar-left">
                <el-select v-model="currentTask.source_lang" size="small" style="width: 100px;">
                  <el-option v-for="lang in languages" :key="lang.code" :label="lang.name" :value="lang.code" />
                </el-select>
                <el-icon class="arrow"><ArrowRight /></el-icon>
                <el-select v-model="currentTask.target_lang" size="small" style="width: 100px;">
                  <el-option v-for="lang in targetLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
                </el-select>
              </div>
              <div class="toolbar-right">
                <el-button size="small" @click="showTermLibrary = true">
                  <el-icon><Collection /></el-icon>
                  词库
                </el-button>
              </div>
            </div>

            <!-- 工作流步骤 -->
            <div class="workflow-progress">
              <el-steps :active="currentStep" finish-status="success" simple>
                <el-step title="翻译" />
                <el-step title="校验" />
                <el-step title="修改" />
                <el-step title="定稿" />
              </el-steps>
              <div class="step-action">
                <el-button v-if="currentTask.status === 'pending'" type="primary" size="small" @click="startWorkflow" :loading="processing">
                  开始翻译
                </el-button>
                <el-button v-else-if="currentTask.current_step === 1" type="primary" size="small" @click="startWorkflow" :loading="processing">
                  执行翻译
                </el-button>
                <el-button v-else-if="currentTask.current_step === 2" type="primary" size="small" @click="verifyTranslation" :loading="processing">
                  执行校验
                </el-button>
                <el-button v-else-if="currentTask.current_step === 3" type="primary" size="small" @click="reviseTranslation" :loading="processing">
                  执行修改
                </el-button>
                <el-button v-else-if="currentTask.current_step === 4" type="primary" size="small" @click="finalizeTranslation" :loading="processing">
                  执行定稿
                </el-button>
                <el-tag v-else-if="currentTask.status === 'completed'" type="success">已完成</el-tag>
              </div>
            </div>

            <!-- 三美评分 -->
            <div class="beauty-scores" v-if="hasBeautyScores">
              <div class="score-item">
                <span>音美</span>
                <el-progress :percentage="beautyScores.sound" :color="getScoreColor(beautyScores.sound)" />
                <span>{{ beautyScores.sound.toFixed(1) }}</span>
              </div>
              <div class="score-item">
                <span>词美</span>
                <el-progress :percentage="beautyScores.word" :color="getScoreColor(beautyScores.word)" />
                <span>{{ beautyScores.word.toFixed(1) }}</span>
              </div>
              <div class="score-item">
                <span>意美</span>
                <el-progress :percentage="beautyScores.meaning" :color="getScoreColor(beautyScores.meaning)" />
                <span>{{ beautyScores.meaning.toFixed(1) }}</span>
              </div>
            </div>

            <!-- 编辑区域 -->
            <div class="edit-area">
              <div class="source-box">
                <div class="box-header">
                  <span>原文</span>
                  <el-tag size="small">{{ currentTask.source_lang }}</el-tag>
                </div>
                <pre class="box-content">{{ currentTask.source_text }}</pre>
              </div>
              <div class="translation-box">
                <div class="box-header">
                  <span>{{ getStepLabel(displayStep) }}</span>
                  <el-radio-group v-model="displayStep" size="small">
                    <el-radio-button :label="1">初译</el-radio-button>
                    <el-radio-button :label="2" :disabled="!step2Available">校验</el-radio-button>
                    <el-radio-button :label="3" :disabled="!step3Available">修改</el-radio-button>
                    <el-radio-button :label="4" :disabled="!step4Available">定稿</el-radio-button>
                  </el-radio-group>
                </div>
                <div class="box-content">
                  <el-input
                    v-if="isEditing"
                    v-model="editableText"
                    type="textarea"
                    :rows="15"
                  />
                  <template v-else>
                    <div v-for="para in paragraphs" :key="para.id" class="para-item">
                      <div class="para-num">段落 {{ para.paragraph_index + 1 }}</div>
                      <div class="para-source">{{ para.source_text }}</div>
                      <el-input
                        v-model="para.editedText"
                        type="textarea"
                        :rows="2"
                        @blur="saveParagraph(para)"
                      />
                    </div>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 专业词库侧边栏 -->
    <el-drawer v-model="showTermLibrary" title="专业词库" size="450px">
      <TermLibraryPanel
        :literary-type="currentTask?.literary_type"
        :source-lang="currentTask?.source_lang"
        :target-lang="currentTask?.target_lang"
      />
    </el-drawer>

    <!-- 导出对话框 -->
    <el-dialog v-model="showExport" title="导出译文" width="480px">
      <el-form label-position="top">
        <el-form-item label="选择格式">
          <el-radio-group v-model="exportFormat">
            <el-radio-button label="txt">纯文本</el-radio-button>
            <el-radio-button label="md">Markdown</el-radio-button>
            <el-radio-button label="html">HTML</el-radio-button>
            <el-radio-button label="json">JSON</el-radio-button>
            <el-radio-button label="csv">CSV</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="exportWithSource">包含原文对照</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExport = false">取消</el-button>
        <el-button type="primary" @click="exportTranslation" :loading="exporting">导出</el-button>
      </template>
    </el-dialog>

    <!-- 新建任务对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建翻译任务" width="640px" destroy-on-close>
      <el-form :model="newTaskForm" label-position="top">
        <el-form-item label="任务标题（选填）">
          <el-input v-model="newTaskForm.title" placeholder="如：第一章" maxlength="200" show-word-limit clearable />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="源语言">
              <el-select v-model="newTaskForm.source_lang" placeholder="源语言" style="width: 100%;">
                <el-option v-for="lang in languages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标语言">
              <el-select v-model="newTaskForm.target_lang" placeholder="目标语言" style="width: 100%;">
                <el-option v-for="lang in targetLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="文学类型">
          <el-radio-group v-model="newTaskForm.literary_type">
            <el-radio-button label="general">一般</el-radio-button>
            <el-radio-button label="poetry">诗歌</el-radio-button>
            <el-radio-button label="prose">散文</el-radio-button>
            <el-radio-button label="novel">小说</el-radio-button>
            <el-radio-button label="drama">戏剧</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="翻译需求（选填）">
          <el-input v-model="newTaskForm.user_requirements" type="textarea" :rows="2" placeholder="如：偏书面语、保留专有名词原文、统一某术语译法等" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="上传文件">
          <el-upload
            :auto-upload="false"
            :show-file-list="true"
            :accept="uploadAccept"
            :limit="1"
            :on-change="onCreateFileSelect"
            :on-exceed="() => ElMessage.warning('仅支持一个文件')"
          >
            <el-button type="default" size="small">
              <el-icon><Upload /></el-icon>
              选择文件（txt / docx / pdf / mobi 等）
            </el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="原文">
          <el-input v-model="newTaskForm.source_text" type="textarea" :rows="8" placeholder="粘贴要翻译的文本，或通过上方上传文件填入..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitNewTask" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEditTask" title="修改任务" width="420px" destroy-on-close>
      <el-form v-if="editingTask" label-position="top">
        <el-form-item label="任务标题">
          <el-input v-model="editForm.title" placeholder="选填" maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" placeholder="状态" style="width: 100%;">
            <el-option label="待开始" value="pending" />
            <el-option label="翻译中" value="translating" />
            <el-option label="校验中" value="verifying" />
            <el-option label="修改中" value="revising" />
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Delete, Upload } from '@element-plus/icons-vue'
import { literaryApi, translateApi } from '@/api'
import TermLibraryPanel from '@/components/TermLibraryPanel.vue'
import LiteraryTranslator from '@/components/LiteraryTranslator.vue'

const languages = ref<{ code: string; name: string }[]>([])
const taskList = ref<any[]>([])
const currentTask = ref<any>(null)
const paragraphs = ref<any[]>([])
const loadingTasks = ref(false)
const processing = ref(false)
const creating = ref(false)
const exporting = ref(false)
const showTermLibrary = ref(false)
const showExport = ref(false)
const showCreateDialog = ref(false)
const showEditTask = ref(false)
const editingTask = ref<any>(null)
const editForm = ref({ title: '', status: '' })
const displayStep = ref(1)
const isEditing = ref(false)
const editableText = ref('')

const exportFormat = ref('txt')
const exportWithSource = ref(false)

const newTaskForm = ref({
  title: '',
  source_text: '',
  source_lang: 'en',
  target_lang: 'zh',
  literary_type: 'general' as string,
  user_requirements: ''
})
const uploadAccept = '.txt,.md,.doc,.docx,.pdf,.mobi,.azw,.html,.htm,.xml,.json,.csv,.yaml,.yml,.rst,.tex,.srt,.vtt,.log,.ini,.cfg'

const targetLanguages = computed(() => languages.value.filter(l => l.code !== 'auto'))
const currentStep = computed(() => currentTask.value?.current_step || 0)
const hasBeautyScores = computed(() => currentTask.value?.beauty_sound_score != null)

const beautyScores = computed(() => ({
  sound: (currentTask.value?.beauty_sound_score || 0) * 10,
  word: (currentTask.value?.beauty_word_score || 0) * 10,
  meaning: (currentTask.value?.beauty_meaning_score || 0) * 10
}))

const step2Available = computed(() => currentTask.value?.step2_verification)
const step3Available = computed(() => currentTask.value?.step3_revision)
const step4Available = computed(() => currentTask.value?.step4_finalization)

onMounted(() => {
  loadLanguages()
  loadTasks()
})

const loadLanguages = async () => {
  try {
    const response = await translateApi.getLanguages()
    languages.value = response.data
  } catch (error) {
    console.error('Failed to load languages:', error)
  }
}

const loadTasks = async () => {
  loadingTasks.value = true
  try {
    const response = await literaryApi.listTranslations({ limit: 50 })
    taskList.value = response.data
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loadingTasks.value = false
  }
}

const selectTask = async (task: any) => {
  try {
    const response = await literaryApi.getTranslation(task.id, true)
    currentTask.value = response.data
    paragraphs.value = response.data.paragraphs?.map((p: any) => ({
      ...p,
      editedText: p.user_edited_text || p.translated_text || ''
    })) || []
    displayStep.value = currentTask.value.current_step || 1
  } catch (error) {
    ElMessage.error('加载任务失败')
  }
}

const createNewTask = () => {
  newTaskForm.value = {
    title: '',
    source_text: '',
    source_lang: 'en',
    target_lang: 'zh',
    literary_type: 'general',
    user_requirements: ''
  }
  showCreateDialog.value = true
}

const allowedUploadExtensions = new Set(['txt', 'md', 'markdown', 'text', 'doc', 'docx', 'pdf', 'mobi', 'azw', 'html', 'htm', 'xml', 'json', 'csv', 'log', 'rst', 'tex', 'srt', 'sub', 'vtt', 'yaml', 'yml', 'ini', 'cfg', 'properties'])
const binaryUploadExtensions = new Set(['doc', 'docx', 'pdf', 'mobi', 'azw'])
const onCreateFileSelect = async (opts: { raw: File }) => {
  const file = opts?.raw
  if (!file) return
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!ext || !allowedUploadExtensions.has(ext)) {
    ElMessage.warning('请选择支持的文件：txt、docx、pdf、mobi 或常见文本格式')
    return
  }
  if (binaryUploadExtensions.has(ext)) {
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await literaryApi.parseFile(form)
      newTaskForm.value.source_text = res.data?.text ?? ''
      if (!newTaskForm.value.title) newTaskForm.value.title = (file.name || '').replace(/\.[^.]+$/, '')
      if (newTaskForm.value.source_text) ElMessage.success('文件已解析，可点击创建')
    } catch (e) {
      ElMessage.error('文件解析失败')
    }
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    newTaskForm.value.source_text = (reader.result as string) || ''
    if (!newTaskForm.value.title) newTaskForm.value.title = file.name.replace(/\.[^.]+$/, '')
  }
  reader.readAsText(file, 'UTF-8')
}

const submitNewTask = async () => {
  if (!newTaskForm.value.source_text.trim()) {
    ElMessage.warning('请粘贴原文或上传文件')
    return
  }
  creating.value = true
  try {
    const payload = {
      title: newTaskForm.value.title || undefined,
      source_text: newTaskForm.value.source_text,
      source_lang: newTaskForm.value.source_lang,
      target_lang: newTaskForm.value.target_lang,
      literary_type: newTaskForm.value.literary_type,
      user_requirements: newTaskForm.value.user_requirements?.trim() || undefined
    }
    const response = await literaryApi.createTranslation(payload)
    ElMessage.success('任务创建成功')
    showCreateDialog.value = false
    await loadTasks()
    await selectTask(response.data)
  } catch (error) {
    ElMessage.error('创建任务失败')
  } finally {
    creating.value = false
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
    await loadTasks()
    if (currentTask.value?.id === id) {
      const t = taskList.value.find((x: any) => x.id === id)
      if (t) await selectTask(t)
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
    taskList.value = taskList.value.filter((t: any) => t.id !== task.id)
    if (currentTask.value?.id === task.id) {
      currentTask.value = null
      paragraphs.value = []
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const startWorkflow = async () => {
  processing.value = true
  try {
    await literaryApi.startWorkflow(currentTask.value.id)
    ElMessage.success('翻译完成')
    await refreshTask()
  } catch (error) {
    ElMessage.error('翻译失败')
  } finally {
    processing.value = false
  }
}

const verifyTranslation = async () => {
  processing.value = true
  try {
    await literaryApi.verifyTranslation(currentTask.value.id)
    ElMessage.success('校验完成')
    await refreshTask()
  } catch (error) {
    ElMessage.error('校验失败')
  } finally {
    processing.value = false
  }
}

const reviseTranslation = async () => {
  processing.value = true
  try {
    await literaryApi.reviseTranslation(currentTask.value.id)
    ElMessage.success('修改完成')
    await refreshTask()
  } catch (error) {
    ElMessage.error('修改失败')
  } finally {
    processing.value = false
  }
}

const finalizeTranslation = async () => {
  processing.value = true
  try {
    await literaryApi.finalizeTranslation(currentTask.value.id)
    ElMessage.success('定稿完成')
    await refreshTask()
  } catch (error) {
    ElMessage.error('定稿失败')
  } finally {
    processing.value = false
  }
}

const refreshTask = async () => {
  if (currentTask.value) {
    await selectTask(currentTask.value)
  }
}

const saveParagraph = async (para: any) => {
  try {
    await literaryApi.updateParagraph(para.id, { user_edited_text: para.editedText })
    ElMessage.success('段落已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const exportTranslation = async () => {
  exporting.value = true
  try {
    const response = await literaryApi.exportTranslation(currentTask.value.id, {
      format: exportFormat.value as any,
      include_source: exportWithSource.value
    })
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
    exporting.value = false
  }
}

const getStepLabel = (step: number) => {
  const labels = ['', '初译', '校验', '修改', '定稿']
  return labels[step] || ''
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    pending: 'info', translating: 'warning', verifying: 'warning',
    revising: 'warning', finalizing: 'warning', completed: 'success', failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '待开始', translating: '翻译中', verifying: '校验中',
    revising: '修改中', finalizing: '定稿中', completed: '已完成', failed: '失败'
  }
  return texts[status] || status
}

const getScoreColor = (score: number) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#409eff'
  if (score >= 40) return '#e6a23c'
  return '#f56c6c'
}
</script>

<style scoped lang="scss">
.literary-view {
  display: flex;
  height: 100vh;
  background: #f5f7fa;

  .sidebar {
    width: 280px;
    background: #fff;
    border-right: 1px solid #e4e7ed;
    display: flex;
    flex-direction: column;

    .sidebar-header {
      padding: 16px 20px;
      border-bottom: 1px solid #e4e7ed;
      display: flex;
      justify-content: space-between;
      align-items: center;

      h3 {
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 18px;

        .el-icon {
          color: #409eff;
        }
      }
    }

    .task-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px;

      .task-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        padding: 12px;
        border-radius: 8px;
        cursor: pointer;
        margin-bottom: 8px;

        &:hover {
          background: #f5f7fa;
        }

        &.active {
          background: #e8f4ff;
          border: 1px solid #409eff;
        }

        .task-info {
          flex: 1;
          min-width: 0;
        }

        .task-title {
          font-weight: 500;
          margin-bottom: 6px;
        }

        .task-meta {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
        }

        .task-actions {
          flex-shrink: 0;
        }
      }
    }

    .sidebar-footer {
      padding: 12px;
      border-top: 1px solid #e4e7ed;

      .term-library-btn {
        width: 100%;
        display: flex;
        align-items: center;
        gap: 8px;
        justify-content: flex-start;
      }
    }
  }

  .main-content {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .translation-workspace {
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 20px;
    gap: 16px;

    .editor-container {
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.1);
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;

      .toolbar {
        padding: 12px 16px;
        border-bottom: 1px solid #ebeef5;
        display: flex;
        justify-content: space-between;
        align-items: center;

        .toolbar-left {
          display: flex;
          align-items: center;
          gap: 12px;

          .arrow {
            color: #c0c4cc;
          }
        }
      }

      .workflow-progress {
        padding: 16px;
        border-bottom: 1px solid #ebeef5;
        display: flex;
        align-items: center;
        gap: 24px;

        .el-steps {
          flex: 1;
        }
      }

      .beauty-scores {
        padding: 16px 24px;
        border-bottom: 1px solid #ebeef5;
        display: flex;
        gap: 40px;

        .score-item {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 12px;
        }
      }

      .edit-area {
        flex: 1;
        display: grid;
        grid-template-columns: 1fr 1fr;
        overflow: hidden;

        .source-box,
        .translation-box {
          display: flex;
          flex-direction: column;
          overflow: hidden;

          .box-header {
            padding: 12px 16px;
            border-bottom: 1px solid #ebeef5;
            display: flex;
            justify-content: space-between;
            align-items: center;
          }

          .box-content {
            flex: 1;
            overflow-y: auto;
            padding: 16px;

            pre {
              margin: 0;
              white-space: pre-wrap;
              font-family: inherit;
              line-height: 1.8;
            }

            .para-item {
              margin-bottom: 20px;
              padding-bottom: 20px;
              border-bottom: 1px dashed #e4e7ed;

              .para-num {
                color: #409eff;
                font-weight: 500;
                margin-bottom: 8px;
              }

              .para-source {
                color: #909399;
                font-size: 13px;
                margin-bottom: 8px;
                padding: 8px;
                background: #f5f7fa;
                border-radius: 4px;
              }
            }
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
</style>
