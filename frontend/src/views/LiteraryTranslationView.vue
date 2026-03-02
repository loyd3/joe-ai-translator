<template>
  <div class="literary-view">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <div class="brand-wrap">
          <span class="brand">译智通</span>
          <span class="brand-sub">为翻译而生</span>
        </div>
        <div class="header-btns">
          <el-button v-if="batchMode" text size="small" @click="exitBatchMode">取消</el-button>
          <el-button
            v-if="batchMode && selectedTaskIds.length > 0"
            type="primary"
            size="small"
            @click="startBatchWorkflow"
            :loading="batchStarting"
          >翻译 {{ selectedTaskIds.length }} 项</el-button>
          <el-tooltip v-if="!batchMode" content="批量翻译" placement="top">
            <el-button size="small" circle @click="enterBatchMode">
              <el-icon><List /></el-icon>
            </el-button>
          </el-tooltip>
          <el-button type="primary" size="small" circle @click="createNewTask">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
      </div>

      <div class="category-filter">
        <el-radio-group v-model="categoryGroup" size="small" class="category-group">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="literary">文学</el-radio-button>
          <el-radio-button label="professional">专业</el-radio-button>
        </el-radio-group>
      </div>

      <div class="task-list" v-loading="loadingTasks">
        <div
          v-for="task in filteredTaskList"
          :key="task.id"
          :class="['task-item', { active: !batchMode && currentTask?.id === task.id, selected: batchMode && selectedTaskIds.includes(task.id) }]"
          @click="batchMode ? toggleTaskSelection(task.id) : selectTask(task)"
        >
          <el-checkbox
            v-if="batchMode"
            :model-value="selectedTaskIds.includes(task.id)"
            @click.stop
            @change="toggleTaskSelection(task.id)"
            class="task-checkbox"
            :disabled="isTaskRunning(task.status)"
          />
          <div class="task-info">
            <div class="task-title">{{ task.title || `任务 #${task.id}` }}</div>
            <div class="task-meta">
              <el-tag size="small" :type="getStatusType(task.status)">{{ getStatusText(task.status) }}</el-tag>
              <el-tag size="small" :type="isLiteraryType(task.literary_type) ? '' : 'warning'" effect="plain" round>{{ getTypeName(task.literary_type) }}</el-tag>
            </div>
          </div>
          <div class="task-actions" v-if="!batchMode" @click.stop>
            <el-button link size="small" @click="openEditTaskDialog(task)"><el-icon><Edit /></el-icon></el-button>
            <el-button link type="danger" size="small" @click="confirmDeleteTask(task)"><el-icon><Delete /></el-icon></el-button>
          </div>
        </div>
        <el-empty v-if="filteredTaskList.length === 0" description="暂无任务" :image-size="60" />
      </div>

      <div class="sidebar-footer" @click="openSettings">
        <el-icon><Setting /></el-icon>
        <span>大模型配置</span>
        <el-tag v-if="aiConfigInfo.provider" size="small" type="info" effect="plain" round>{{ aiConfigInfo.provider }}</el-tag>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 空状态 -->
      <div v-if="!currentTask" class="empty-state" @click="createNewTask">
        <div class="empty-card">
          <el-icon class="empty-icon"><Plus /></el-icon>
          <h2>{{ categoryGroup === 'professional' ? '创建专业翻译任务' : '创建文学翻译任务' }}</h2>
          <p>{{ categoryGroup === 'professional' ? '支持科技、商业、贸易、法律、医学等专业领域' : '诗歌、散文、小说、戏剧等文学作品精译' }}</p>
        </div>
      </div>

      <!-- 工作区 -->
      <template v-else>
        <div class="workspace">
          <!-- 顶栏 -->
          <div class="top-bar">
            <div class="bar-left">
              <el-select v-model="currentTask.source_lang" size="small" class="lang-sel">
                <el-option v-for="lang in languages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>
              <el-icon class="arrow"><ArrowRight /></el-icon>
              <el-select v-model="currentTask.target_lang" size="small" class="lang-sel">
                <el-option v-for="lang in targetLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>

              <el-tag
                size="small"
                :type="isLiteraryType(currentTask.literary_type) ? '' : 'warning'"
                effect="plain"
                round
                class="type-badge"
              >{{ getTypeName(currentTask.literary_type) }}</el-tag>

              <el-divider direction="vertical" />

              <div class="step-dots">
                <div v-for="(s, i) in stepItems" :key="i" :class="['dot-item', s.state]">
                  <span class="dot" />
                  <span class="dot-label">{{ s.label }}</span>
                </div>
              </div>

              <el-button v-if="canStartWorkflow" type="primary" size="small" @click="startWorkflow" :loading="processing">
                {{ currentTask.status === 'failed' ? '重新翻译' : '开始翻译' }}
              </el-button>
              <el-button v-else-if="isWorkflowRunning" type="primary" size="small" loading disabled>
                {{ getStatusText(currentTask.status) }}
              </el-button>
              <el-tag v-else-if="currentTask.status === 'completed'" type="success" size="small" effect="dark" round>已完成</el-tag>

              <el-tag v-if="isWorkflowRunning && paraProgress.total > 0" size="small" type="info" effect="plain" round>
                {{ paraProgress.done }}/{{ paraProgress.total }} 段
              </el-tag>
            </div>

            <div class="bar-right">
              <el-popover v-if="hasBeautyScores" placement="bottom" :width="200" trigger="hover">
                <template #reference>
                  <el-button size="small" link>
                    {{ isLiteraryType(currentTask.literary_type) ? '三美评分' : '质量评分' }}
                  </el-button>
                </template>
                <div class="score-popover">
                  <template v-if="isLiteraryType(currentTask.literary_type)">
                    <div class="score-row"><span>音美</span><span>{{ beautyScores.sound.toFixed(1) }}</span></div>
                    <div class="score-row"><span>词美</span><span>{{ beautyScores.word.toFixed(1) }}</span></div>
                    <div class="score-row"><span>意美</span><span>{{ beautyScores.meaning.toFixed(1) }}</span></div>
                  </template>
                  <template v-else>
                    <div class="score-row"><span>术语</span><span>{{ beautyScores.sound.toFixed(1) }}</span></div>
                    <div class="score-row"><span>规范</span><span>{{ beautyScores.word.toFixed(1) }}</span></div>
                    <div class="score-row"><span>完整</span><span>{{ beautyScores.meaning.toFixed(1) }}</span></div>
                  </template>
                </div>
              </el-popover>
              <el-button size="small" @click="goToResultPage">
                <el-icon><Document /></el-icon>
                定稿
              </el-button>
              <el-button size="small" @click="showTermLibrary = true">
                <el-icon><Collection /></el-icon>
                词库
              </el-button>
            </div>
          </div>

          <!-- 编辑区 -->
          <div class="edit-area">
            <div class="panel source-panel">
              <div class="panel-header">
                <span>原文</span>
                <el-tag size="small" type="info">{{ currentTask.source_lang }}</el-tag>
              </div>
              <div class="panel-body">
                <pre>{{ currentTask.source_text }}</pre>
              </div>
            </div>
            <div class="panel trans-panel">
              <div class="panel-header">
                <span>{{ getStepLabel(displayStep) }}</span>
                <el-radio-group v-model="displayStep" size="small">
                  <el-radio-button :label="1">初译</el-radio-button>
                  <el-radio-button :label="2" :disabled="!step2Available">校验</el-radio-button>
                  <el-radio-button :label="3" :disabled="!step3Available">修改</el-radio-button>
                  <el-radio-button :label="4" :disabled="!step4Available">定稿</el-radio-button>
                </el-radio-group>
              </div>
              <div class="panel-body">
                <div v-for="para in paragraphs" :key="para.id" class="para-item">
                  <div class="para-source">{{ para.source_text }}</div>
                  <el-input
                    v-model="para.editedText"
                    type="textarea"
                    :autosize="{ minRows: 2 }"
                    @blur="saveParagraph(para)"
                  />
                </div>
                <div v-if="paragraphs.length === 0" class="no-content">暂无翻译内容</div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- 抽屉 & 弹窗 -->
    <el-drawer v-model="showTermLibrary" title="专业词库" size="420px">
      <TermLibraryPanel
        :literary-type="currentTask?.literary_type"
        :source-lang="currentTask?.source_lang"
        :target-lang="currentTask?.target_lang"
      />
    </el-drawer>

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
          <el-checkbox v-model="exportWithSource">包含原文对照</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExport = false">取消</el-button>
        <el-button type="primary" @click="exportTranslation" :loading="exporting">导出</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCreateDialog" :title="categoryGroup === 'professional' ? '新建专业翻译任务' : '新建文学翻译任务'" width="600px" destroy-on-close>
      <el-form :model="newTaskForm" label-position="top">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="标题（选填）">
              <el-input v-model="newTaskForm.title" placeholder="如：第一章" maxlength="200" clearable />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="翻译类型">
              <el-select v-model="newTaskForm.literary_type" style="width: 100%;">
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
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="源语言">
              <el-select v-model="newTaskForm.source_lang" style="width: 100%;">
                <el-option v-for="lang in languages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标语言">
              <el-select v-model="newTaskForm.target_lang" style="width: 100%;">
                <el-option v-for="lang in targetLanguages" :key="lang.code" :label="lang.name" :value="lang.code" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="翻译需求（选填）">
          <el-input v-model="newTaskForm.user_requirements" type="textarea" :rows="2" placeholder="如：偏书面语、保留专有名词原文、统一某术语译法等" maxlength="500" show-word-limit />
        </el-form-item>
        <el-form-item label="原文">
          <el-upload
            :auto-upload="false"
            :show-file-list="true"
            :accept="uploadAccept"
            :limit="1"
            :on-change="onCreateFileSelect"
            :on-exceed="() => ElMessage.warning('仅支持一个文件')"
            class="inline-upload"
          >
            <el-button size="small" link type="primary">
              <el-icon><Upload /></el-icon>
              上传文件
            </el-button>
          </el-upload>
          <el-input v-model="newTaskForm.source_text" type="textarea" :rows="8" placeholder="粘贴要翻译的文本，或上传文件自动填入..." />
          <div class="text-stats" v-if="newTaskForm.source_text.length > 0">
            <span>{{ newTaskForm.source_text.length.toLocaleString() }} 字符</span>
            <span>·</span>
            <span>约 {{ estimatedParagraphs }} 段</span>
            <el-tag v-if="newTaskForm.source_text.length > 10000" size="small" type="info" effect="plain">大文本自动智能分段</el-tag>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="submitNewTask" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEditTask" title="修改任务" width="400px" destroy-on-close>
      <el-form v-if="editingTask" label-position="top">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" placeholder="选填" maxlength="200" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%;">
            <el-option label="待开始" value="pending" />
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

    <!-- 大模型配置对话框 -->
    <el-dialog v-model="showSettings" title="大模型配置" width="520px" destroy-on-close>
      <el-form :model="aiConfigForm" label-position="top">
        <el-form-item label="AI 提供商">
          <el-select v-model="aiConfigForm.provider" style="width: 100%;" @change="onProviderChange">
            <el-option label="DeepSeek" value="deepseek" />
            <el-option label="OpenAI" value="openai" />
            <el-option label="SiliconFlow (硅基流动)" value="siliconflow" />
            <el-option label="自定义 (Custom)" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="aiConfigForm.api_key"
            :placeholder="aiConfigInfo.has_api_key ? `已配置 (${aiConfigInfo.api_key_masked})` : '请输入 API Key'"
            show-password
          />
          <div class="form-hint" v-if="aiConfigInfo.has_api_key && !aiConfigForm.api_key">
            已有密钥，留空则保持不变
          </div>
        </el-form-item>
        <el-form-item label="模型名称">
          <el-input v-model="aiConfigForm.model" :placeholder="getDefaultModel(aiConfigForm.provider)" />
          <div class="form-hint">
            留空使用默认: {{ getDefaultModel(aiConfigForm.provider) }}
          </div>
        </el-form-item>
        <el-form-item v-if="aiConfigForm.provider === 'custom'" label="API 地址">
          <el-input v-model="aiConfigForm.base_url" placeholder="https://your-api.com/v1" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="温度 (Temperature)">
              <el-input-number v-model="aiConfigForm.temperature" :min="0" :max="2" :step="0.1" :precision="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大 Token">
              <el-input-number v-model="aiConfigForm.max_tokens" :min="256" :max="128000" :step="1024" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <div class="config-source" v-if="aiConfigInfo.source">
          <el-tag size="small" :type="aiConfigInfo.source === 'database' ? 'success' : 'info'" effect="plain">
            {{ aiConfigInfo.source === 'database' ? '使用自定义配置' : '使用默认配置' }}
          </el-tag>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showSettings = false">取消</el-button>
        <el-button type="primary" @click="saveAIConfig" :loading="savingConfig">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Delete, Upload, Document, Plus, List, Setting } from '@element-plus/icons-vue'
import { literaryApi, translateApi, systemApi } from '@/api'
import TermLibraryPanel from '@/components/TermLibraryPanel.vue'

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
const exportFormat = ref('txt')
const exportWithSource = ref(false)

const batchMode = ref(false)
const selectedTaskIds = ref<number[]>([])
const batchStarting = ref(false)

const LITERARY_TYPES = new Set(['poetry', 'prose', 'novel', 'drama', 'general'])
const categoryGroup = ref<string>('literary')

const showSettings = ref(false)
const savingConfig = ref(false)
const aiConfigInfo = ref<any>({ provider: '', source: '', has_api_key: false, api_key_masked: '' })
const aiConfigForm = ref({
  provider: 'deepseek',
  api_key: '',
  model: '',
  base_url: '',
  temperature: 0.3,
  max_tokens: 4096,
})

const DEFAULT_MODELS: Record<string, string> = {
  openai: 'gpt-4',
  deepseek: 'deepseek-chat',
  siliconflow: 'deepseek-ai/DeepSeek-V3',
  custom: '',
}

function getDefaultModel(provider: string) {
  return DEFAULT_MODELS[provider] || ''
}

function onProviderChange(_provider: string) {
  aiConfigForm.value.model = ''
  aiConfigForm.value.base_url = ''
}

async function loadAIConfig() {
  try {
    const res = await systemApi.getAIConfig()
    aiConfigInfo.value = res.data
  } catch { /* ignore */ }
}

function openSettings() {
  loadAIConfig().then(() => {
    const info = aiConfigInfo.value
    aiConfigForm.value = {
      provider: info.provider || 'deepseek',
      api_key: '',
      model: info.model || '',
      base_url: info.base_url || '',
      temperature: info.temperature ?? 0.3,
      max_tokens: info.max_tokens || 4096,
    }
    showSettings.value = true
  })
}

async function saveAIConfig() {
  savingConfig.value = true
  try {
    const payload: any = {
      provider: aiConfigForm.value.provider,
      model: aiConfigForm.value.model || undefined,
      base_url: aiConfigForm.value.base_url || undefined,
      temperature: aiConfigForm.value.temperature,
      max_tokens: aiConfigForm.value.max_tokens,
    }
    if (aiConfigForm.value.api_key) {
      payload.api_key = aiConfigForm.value.api_key
    }
    await systemApi.updateAIConfig(payload)
    ElMessage.success('配置已保存')
    showSettings.value = false
    await loadAIConfig()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    savingConfig.value = false
  }
}

const filteredTaskList = computed(() => {
  if (categoryGroup.value === 'all') return taskList.value
  if (categoryGroup.value === 'literary') return taskList.value.filter((t: any) => LITERARY_TYPES.has(t.literary_type || 'general'))
  return taskList.value.filter((t: any) => !LITERARY_TYPES.has(t.literary_type || 'general'))
})

const TYPE_LABELS: Record<string, string> = {
  poetry: '诗歌', prose: '散文', novel: '小说', drama: '戏剧', general: '一般',
  tech: '科技', business: '商业', trade: '贸易', legal: '法律', medical: '医学',
}
const getTypeName = (type: string) => TYPE_LABELS[type] || type
const isLiteraryType = (type: string) => LITERARY_TYPES.has(type || 'general')

const newTaskForm = ref({
  title: '',
  source_text: '',
  source_lang: 'en',
  target_lang: 'zh',
  literary_type: 'general' as string,
  user_requirements: ''
})
const uploadAccept = '.txt,.md,.doc,.docx,.pdf,.mobi,.azw,.html,.htm,.xml,.json,.csv,.yaml,.yml,.rst,.tex,.srt,.vtt,.log,.ini,.cfg'
const MAX_FILE_SIZE = 10 * 1024 * 1024
const MAX_TEXT_CHARS = 500000

const estimatedParagraphs = computed(() => {
  const text = newTaskForm.value.source_text
  if (!text) return 0
  const paras = text.split(/\n\n+/).filter((p: string) => p.trim())
  let count = 0
  for (const p of paras) {
    count += Math.max(1, Math.ceil(p.length / 2000))
  }
  return count || 1
})

const router = useRouter()
const targetLanguages = computed(() => languages.value.filter(l => l.code !== 'auto'))

const currentStep = computed(() => {
  const task = currentTask.value
  if (!task) return 0
  if (task.status === 'completed') return 4
  return Math.max(0, (task.current_step || 1) - 1)
})

const canStartWorkflow = computed(() => {
  const s = currentTask.value?.status
  return s === 'pending' || s === 'failed'
})

const isWorkflowRunning = computed(() =>
  ['translating', 'verifying', 'revising', 'finalizing'].includes(currentTask.value?.status)
)

const paraProgress = ref<{ total: number; done: number }>({ total: 0, done: 0 })

const stepItems = computed(() => {
  const labels = ['翻译', '校验', '修改', '定稿']
  const statusMap: Record<string, number> = { translating: 0, verifying: 1, revising: 2, finalizing: 3 }
  const active = currentStep.value
  const runningIdx = statusMap[currentTask.value?.status] ?? -1

  return labels.map((label, i) => {
    let state = 'pending'
    if (i < active) state = 'done'
    else if (i === runningIdx) state = 'running'
    else if (currentTask.value?.status === 'completed') state = 'done'
    else if (currentTask.value?.status === 'failed' && i <= runningIdx) state = 'failed'
    return { label, state }
  })
})

const goToResultPage = () => {
  if (currentTask.value?.id) router.push({ name: 'literary-result', params: { id: String(currentTask.value.id) } })
}

const hasBeautyScores = computed(() => currentTask.value?.beauty_sound_score != null)
const beautyScores = computed(() => ({
  sound: (currentTask.value?.beauty_sound_score || 0) * 10,
  word: (currentTask.value?.beauty_word_score || 0) * 10,
  meaning: (currentTask.value?.beauty_meaning_score || 0) * 10
}))

const step2Available = computed(() => currentTask.value?.step2_verification)
const step3Available = computed(() => currentTask.value?.step3_revision)
const step4Available = computed(() => currentTask.value?.step4_finalization)

onMounted(async () => {
  loadLanguages()
  loadAIConfig()
  await loadTasks(true)
  if (taskList.value.some((t: any) => isTaskRunning(t.status))) startBatchPolling()
})

const loadLanguages = async () => {
  try {
    const response = await translateApi.getLanguages()
    languages.value = response.data
  } catch (error) {
    console.error('Failed to load languages:', error)
  }
}

const loadTasks = async (autoSelect = false) => {
  loadingTasks.value = true
  try {
    const response = await literaryApi.listTranslations({ limit: 50 })
    taskList.value = response.data
    if (autoSelect && taskList.value.length > 0 && !currentTask.value) {
      await selectTask(taskList.value[0])
    }
  } catch (error) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loadingTasks.value = false
  }
}

const selectTask = async (task: any) => {
  stopPolling()
  try {
    const response = await literaryApi.getTranslation(task.id, true)
    currentTask.value = response.data
    paragraphs.value = response.data.paragraphs?.map((p: any) => ({
      ...p,
      editedText: p.user_edited_text || p.translated_text || ''
    })) || []
    displayStep.value = currentTask.value.current_step || 1
    if (isWorkflowRunning.value) {
      startPolling()
    }
  } catch (error) {
    ElMessage.error('加载任务失败')
  }
}

const createNewTask = () => {
  const defaultType = categoryGroup.value === 'professional' ? 'tech' : 'general'
  newTaskForm.value = { title: '', source_text: '', source_lang: 'en', target_lang: 'zh', literary_type: defaultType, user_requirements: '' }
  showCreateDialog.value = true
}

const allowedUploadExtensions = new Set(['txt', 'md', 'markdown', 'text', 'doc', 'docx', 'pdf', 'mobi', 'azw', 'html', 'htm', 'xml', 'json', 'csv', 'log', 'rst', 'tex', 'srt', 'sub', 'vtt', 'yaml', 'yml', 'ini', 'cfg', 'properties'])
const binaryUploadExtensions = new Set(['doc', 'docx', 'pdf', 'mobi', 'azw'])
const onCreateFileSelect = async (opts: { raw: File }) => {
  const file = opts?.raw
  if (!file) return
  if (file.size > MAX_FILE_SIZE) {
    ElMessage.warning(`文件过大（${(file.size / 1024 / 1024).toFixed(1)}MB），最大支持 ${MAX_FILE_SIZE / 1024 / 1024}MB`)
    return
  }
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (!ext || !allowedUploadExtensions.has(ext)) {
    ElMessage.warning('请选择支持的文件格式')
    return
  }
  if (binaryUploadExtensions.has(ext)) {
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await literaryApi.parseFile(form)
      const text = res.data?.text ?? ''
      if (text.length > MAX_TEXT_CHARS) {
        ElMessage.warning(`文件内容过长（${(text.length / 10000).toFixed(1)}万字），已截取前 ${MAX_TEXT_CHARS / 10000} 万字符`)
        newTaskForm.value.source_text = text.slice(0, MAX_TEXT_CHARS)
      } else {
        newTaskForm.value.source_text = text
      }
      if (!newTaskForm.value.title) newTaskForm.value.title = (file.name || '').replace(/\.[^.]+$/, '')
      if (newTaskForm.value.source_text) ElMessage.success('文件已解析')
    } catch (e) {
      ElMessage.error('文件解析失败')
    }
    return
  }
  const reader = new FileReader()
  reader.onload = () => {
    let text = (reader.result as string) || ''
    if (text.length > MAX_TEXT_CHARS) {
      ElMessage.warning(`文件内容过长（${(text.length / 10000).toFixed(1)}万字），已截取前 ${MAX_TEXT_CHARS / 10000} 万字符`)
      text = text.slice(0, MAX_TEXT_CHARS)
    }
    newTaskForm.value.source_text = text
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
    await literaryApi.updateTranslation(id, { title: editForm.value.title || undefined, status: editForm.value.status || undefined })
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
    await ElMessageBox.confirm('确定删除该翻译任务？', '删除确认', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' })
    await literaryApi.deleteTranslation(task.id)
    ElMessage.success('已删除')
    taskList.value = taskList.value.filter((t: any) => t.id !== task.id)
    if (currentTask.value?.id === task.id) { currentTask.value = null; paragraphs.value = [] }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const isTaskRunning = (status: string) => ['translating', 'verifying', 'revising', 'finalizing'].includes(status)

const enterBatchMode = () => {
  batchMode.value = true
  selectedTaskIds.value = filteredTaskList.value
    .filter((t: any) => !isTaskRunning(t.status))
    .filter((t: any) => t.status === 'pending' || t.status === 'failed')
    .map((t: any) => t.id)
}

const exitBatchMode = () => {
  batchMode.value = false
  selectedTaskIds.value = []
}

const toggleTaskSelection = (id: number) => {
  const task = taskList.value.find((t: any) => t.id === id)
  if (task && isTaskRunning(task.status)) return
  const idx = selectedTaskIds.value.indexOf(id)
  if (idx >= 0) selectedTaskIds.value.splice(idx, 1)
  else selectedTaskIds.value.push(id)
}

const startBatchWorkflow = async () => {
  if (selectedTaskIds.value.length === 0) return
  batchStarting.value = true
  try {
    await literaryApi.startBatchWorkflow(selectedTaskIds.value)
    ElMessage.success(`已启动 ${selectedTaskIds.value.length} 个任务的翻译队列`)
    exitBatchMode()
    await loadTasks()
    startBatchPolling()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '批量启动失败')
  } finally {
    batchStarting.value = false
  }
}

let pollTimer: ReturnType<typeof setInterval> | null = null
let lastPolledStep = 0

const startWorkflow = async () => {
  processing.value = true
  try {
    await literaryApi.startWorkflow(currentTask.value.id)
    currentTask.value.status = 'translating'
    currentTask.value.current_step = 1
    startPolling()
  } catch (error: any) {
    const msg = error?.response?.data?.detail || '启动翻译失败'
    ElMessage.error(msg)
  } finally {
    processing.value = false
  }
}

const startPolling = () => {
  stopPolling()
  lastPolledStep = currentTask.value?.current_step || 0
  pollTimer = setInterval(async () => {
    if (!currentTask.value) return stopPolling()
    try {
      const res = await literaryApi.getWorkflowStatus(currentTask.value.id)
      const data = res.data
      const prevStep = lastPolledStep
      currentTask.value.status = data.overall_status
      currentTask.value.current_step = data.current_step
      lastPolledStep = data.current_step

      const taskInList = taskList.value.find((t: any) => t.id === currentTask.value.id)
      if (taskInList) { taskInList.status = data.overall_status; taskInList.current_step = data.current_step }

      paraProgress.value = { total: data.paragraph_total || 0, done: data.paragraph_done || 0 }

      if (data.current_step !== prevStep) await refreshTask()

      if (data.overall_status === 'completed' || data.overall_status === 'failed') {
        stopPolling()
        paraProgress.value = { total: 0, done: 0 }
        await refreshTask()
        await loadTasks()
        ElMessage[data.overall_status === 'completed' ? 'success' : 'error'](
          data.overall_status === 'completed' ? '翻译流程已完成' : '翻译流程失败'
        )
      }
    } catch (error) {
      console.error('Polling error:', error)
    }
  }, 3000)
}

const stopPolling = () => { if (pollTimer) { clearInterval(pollTimer); pollTimer = null } }

let batchPollTimer: ReturnType<typeof setInterval> | null = null

const startBatchPolling = () => {
  stopBatchPolling()
  batchPollTimer = setInterval(async () => {
    try {
      await loadTasks()
      const hasRunning = taskList.value.some((t: any) => isTaskRunning(t.status))
      if (!hasRunning) {
        stopBatchPolling()
        ElMessage.success('批量翻译全部完成')
      }
      if (currentTask.value) {
        const updated = taskList.value.find((t: any) => t.id === currentTask.value.id)
        if (updated && updated.status !== currentTask.value.status) await refreshTask()
      }
    } catch { /* ignore */ }
  }, 4000)
}

const stopBatchPolling = () => { if (batchPollTimer) { clearInterval(batchPollTimer); batchPollTimer = null } }

onUnmounted(() => { stopPolling(); stopBatchPolling() })

const refreshTask = async () => { if (currentTask.value) await selectTask(currentTask.value) }

const saveParagraph = async (para: any) => {
  try {
    await literaryApi.updateParagraph(para.id, { user_edited_text: para.editedText })
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const exportTranslation = async () => {
  exporting.value = true
  try {
    const response = await literaryApi.exportTranslation(currentTask.value.id, { format: exportFormat.value as any, include_source: exportWithSource.value })
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

const getStepLabel = (step: number) => ['', '初译', '校验', '修改', '定稿'][step] || ''
const getStatusType = (status: string) => ({ pending: 'info', translating: 'warning', verifying: 'warning', revising: 'warning', finalizing: 'warning', completed: 'success', failed: 'danger' } as Record<string, string>)[status] || 'info'
const getStatusText = (status: string) => ({ pending: '待开始', translating: '翻译中', verifying: '校验中', revising: '修改中', finalizing: '定稿中', completed: '已完成', failed: '失败' } as Record<string, string>)[status] || status
</script>

<style scoped lang="scss">
.literary-view {
  display: flex;
  height: 100vh;
  background: #f0f2f5;
}

/* ===== 侧边栏 ===== */
.sidebar {
  width: 280px;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px 18px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;

  .brand-wrap {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .brand {
    font-size: 18px;
    font-weight: 700;
    color: #1d1d1f;
    line-height: 1.2;
  }

  .brand-sub {
    font-size: 11px;
    color: #b0b0b0;
    font-weight: 400;
  }

  .header-btns {
    display: flex;
    align-items: center;
    gap: 6px;
  }
}

.category-filter {
  padding: 10px 14px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;

  .category-group {
    width: 100%;
    display: flex;

    :deep(.el-radio-button) {
      flex: 1;
    }

    :deep(.el-radio-button__inner) {
      width: 100%;
    }
  }
}

.sidebar-footer {
  padding: 12px 18px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: #888;
  flex-shrink: 0;
  transition: background .2s;
  &:hover {
    background: #f5f5f5;
    color: #555;
  }
  .el-icon { font-size: 16px; }
  .el-tag { margin-left: auto; }
}

.task-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 2px;
  transition: background 0.15s;

  &:hover { background: #f5f5f5; }
  &.active { background: #e6f4ff; }
  &.selected { background: #f0f7ff; }

  .task-checkbox { margin-right: 4px; flex-shrink: 0; }

  .task-info { flex: 1; min-width: 0; }
  .task-title { font-size: 14px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .task-meta { display: flex; align-items: center; gap: 6px; margin-top: 5px; font-size: 12px; color: #999; }

  .task-actions { opacity: 0; transition: opacity 0.15s; flex-shrink: 0; display: flex; gap: 2px; }
  &:hover .task-actions { opacity: 1; }
}

/* ===== 主内容区 ===== */
.main-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;

  .empty-card {
    text-align: center;
    padding: 40px 56px;
    border-radius: 12px;
    border: 2px dashed #d9d9d9;
    background: #fff;
    transition: all 0.2s;

    &:hover {
      border-color: #409eff;
      background: #f0f7ff;
      .empty-icon { color: #409eff; }
      h2 { color: #409eff; }
    }

    .empty-icon { font-size: 44px; color: #bfbfbf; transition: color 0.2s; }
    h2 { margin: 12px 0 6px; font-size: 18px; font-weight: 600; color: #303133; transition: color 0.2s; }
    p { margin: 0; font-size: 14px; color: #999; }
  }
}

/* ===== 工作区 ===== */
.workspace {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.top-bar {
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;

  .bar-left, .bar-right {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .lang-sel { width: 100px; }
  .arrow { color: #bfbfbf; font-size: 13px; }
}

.step-dots {
  display: flex;
  align-items: center;
  gap: 4px;

  .dot-item {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 8px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.25s;

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
      transition: all 0.25s;
    }

    &.pending {
      color: #c0c4cc;
      .dot { background: #dcdfe6; }
    }

    &.running {
      color: #409eff;
      background: #ecf5ff;
      .dot { background: #409eff; box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.2); animation: pulse 1.5s infinite; }
    }

    &.done {
      color: #67c23a;
      .dot { background: #67c23a; }
    }

    &.failed {
      color: #f56c6c;
      .dot { background: #f56c6c; }
    }
  }
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.2); }
  50% { box-shadow: 0 0 0 6px rgba(64, 158, 255, 0.08); }
}

.score-popover {
  .score-row {
    display: flex;
    justify-content: space-between;
    padding: 5px 0;
    font-size: 14px;
    & + .score-row { border-top: 1px solid #f5f5f5; }
  }
}

/* ===== 编辑区 ===== */
.edit-area {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  overflow: hidden;
}

.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-header {
  padding: 10px 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  font-weight: 500;
  color: #606266;
  background: #fafafa;
  flex-shrink: 0;
}

.panel-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 20px;

  pre {
    margin: 0;
    white-space: pre-wrap;
    font-family: inherit;
    font-size: 15px;
    line-height: 1.85;
    color: #303133;
  }
}

.source-panel {
  background: #fafbfc;
  border-right: 1px solid #f0f0f0;
}

.trans-panel {
  background: #fff;
}

.para-item {
  & + .para-item {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px dashed #e8e8e8;
  }

  .para-source {
    font-size: 14px;
    color: #909399;
    padding: 8px 10px;
    background: #f5f7fa;
    border-radius: 4px;
    margin-bottom: 10px;
    line-height: 1.7;
    white-space: pre-wrap;
  }
}

.no-content {
  color: #bfbfbf;
  text-align: center;
  padding: 48px 0;
  font-size: 15px;
}

.inline-upload {
  margin-bottom: 8px;
}

.text-stats {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 6px;
  font-size: 12px;
  color: #999;
}

.form-hint {
  font-size: 12px;
  color: #aaa;
  margin-top: 2px;
  line-height: 1.4;
}

.config-source {
  margin-top: 8px;
  text-align: right;
}
</style>
