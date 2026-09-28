import axios from 'axios'
import { ElLoading, ElMessage } from 'element-plus'
import type {
  StyleAgent,
  StyleAgentCreate,
  StyleAgentPreset,
  StyleAgentUpdate,
  StyleExtractResult,
} from './styleTypes'

export type {
  StyleAgent,
  StyleAgentConfig,
  StyleAgentCreate,
  StyleAgentPreset,
  StyleAgentUpdate,
  StyleExtractResult,
} from './styleTypes'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

let globalLoading: any = null
let globalLoadingRefCount = 0
const shouldShowGlobalLoading = (config: any) => {
  const url = config?.url || ''
  const method = (config?.method || 'get').toLowerCase()
  const params = config?.params || {}
  return method === 'get' &&
    typeof url === 'string' &&
    url.startsWith('/literary/translations/') &&
    params?.include_paragraphs
}
api.interceptors.request.use((config) => {
  if (shouldShowGlobalLoading(config)) {
    if (globalLoadingRefCount === 0) {
      globalLoading = ElLoading.service({ fullscreen: true, text: '加载任务中...' })
    }
    globalLoadingRefCount += 1
  }
  return config
})
api.interceptors.response.use(
  (response) => {
    if (shouldShowGlobalLoading(response.config)) {
      globalLoadingRefCount = Math.max(0, globalLoadingRefCount - 1)
      if (globalLoadingRefCount === 0 && globalLoading) {
        globalLoading.close()
        globalLoading = null
      }
    }
    return response
  },
  (error) => {
    try {
      if (shouldShowGlobalLoading(error?.config)) {
        globalLoadingRefCount = Math.max(0, globalLoadingRefCount - 1)
        if (globalLoadingRefCount === 0 && globalLoading) {
          globalLoading.close()
          globalLoading = null
        }
      }
      // 后台未启动或代理不可达时给出明确提示
      const isNetworkError =
        !error.response &&
        (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error'))
      if (isNetworkError) {
        ElMessage.error('后台接口连接失败，请确认已启动后端服务（运行 python start.py 或在后端目录运行 uvicorn，端口 8000）')
      }
    } catch {}
    return Promise.reject(error)
  }
)

// 翻译 API
export const translateApi = {
  // 获取支持的语言
  getLanguages: () => api.get('/translate/languages'),
  
  // 翻译文本
  translate: (data: {
    text: string
    source_lang: string
    target_lang: string
    context?: string
    stream?: boolean
  }) => api.post('/translate/', data),
  
  // 流式翻译
  translateStream: (data: {
    text: string
    source_lang: string
    target_lang: string
    context?: string
  }) => fetch('/api/translate/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }),
  
  // 获取翻译历史
  getHistory: (params?: { skip?: number; limit?: number; favorite_only?: boolean }) => 
    api.get('/translate/history', { params }),
  
  // 切换收藏状态
  toggleFavorite: (id: number) => api.post(`/translate/history/${id}/favorite`),
  
  // 删除历史记录
  deleteHistory: (id: number) => api.delete(`/translate/history/${id}`),
  
  // 创建批量翻译任务
  createBatch: (data: {
    items: string[]
    source_lang: string
    target_lang: string
    context?: string
  }) => api.post('/translate/batch', data),
  
  // 获取批量翻译任务
  getBatch: (id: number) => api.get(`/translate/batch/${id}`),
}

// 系统 API
export const systemApi = {
  getConfig: () => api.get('/system/config'),
  healthCheck: () => api.get('/system/health'),
  listAIProviders: () => api.get('/system/ai-providers'),
  getAIConfig: () => api.get('/system/ai-config'),
  updateAIConfig: (data: {
    provider: string
    api_key?: string
    model?: string
    base_url?: string
    temperature?: number
    max_tokens?: number
    top_p?: number
    frequency_penalty?: number
    presence_penalty?: number
    timeout_seconds?: number
  }) => api.put('/system/ai-config', data),
  testAIConfig: (data: {
    provider: string
    api_key?: string
    model?: string
    base_url?: string
    temperature?: number
    timeout_seconds?: number
  }) => api.post('/system/ai-config/test', data),
}

// 文学翻译 API
export const literaryApi = {
  // ===== 参考文档管理 =====
  
  // 创建参考文档
  createReference: (data: {
    name: string
    content: string
    doc_type: 'terminology' | 'style_guide' | 'reference' | 'general'
    source_lang?: string
    target_lang?: string
    description?: string
  }) => api.post('/literary/references', data),
  
  // 上传参考文档文件
  uploadReference: (formData: FormData) => api.post('/literary/references/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  
  // 获取参考文档列表
  listReferences: (params?: { doc_type?: string; is_active?: boolean }) => 
    api.get('/literary/references', { params }),
  
  // 获取参考文档详情
  getReference: (id: number) => api.get(`/literary/references/${id}`),
  
  // 更新参考文档
  updateReference: (id: number, data: {
    name?: string
    content?: string
    doc_type?: string
    description?: string
    is_active?: boolean
  }) => api.put(`/literary/references/${id}`, data),
  
  // 删除参考文档
  deleteReference: (id: number) => api.delete(`/literary/references/${id}`),
  
  // ===== 文学翻译任务 =====
  
  // 创建翻译任务
  createTranslation: (data: {
    title?: string
    source_text: string
    source_lang: string
    target_lang: string
    literary_type: 'poetry' | 'prose' | 'novel' | 'drama' | 'general' | string
    reference_document_ids?: number[]
    user_requirements?: string
    style_agent_id?: number
  }) => api.post('/literary/translations', data),
  
  // 获取翻译任务列表
  listTranslations: (params?: { skip?: number; limit?: number; status?: string }) => 
    api.get('/literary/translations', { params }),
  
  // 获取翻译任务详情。浏览长文时 includeParagraphs 与 includeSource 都传 false，再分页拉段落。
  getTranslation: (id: number, includeParagraphs?: boolean, includeSource = true) =>
    api.get(`/literary/translations/${id}`, {
      params: { include_paragraphs: includeParagraphs, include_source: includeSource },
    }),
  
  // 更新翻译任务（改）
  updateTranslation: (id: number, data: {
    title?: string
    source_text?: string
    final_translation?: string
    status?: string
    style_agent_id?: number | null
    user_requirements?: string
  }) => api.put(`/literary/translations/${id}`, data),
  
  // 删除翻译任务
  deleteTranslation: (id: number) => api.delete(`/literary/translations/${id}`),
  
  // ===== 翻译流程 =====

  // 启动四步翻译流程（后台执行，立即返回）
  startWorkflow: (id: number) => api.post(`/literary/translations/${id}/workflow/start`),

  // 终止四步翻译流程
  stopWorkflow: (id: number) => api.post(`/literary/translations/${id}/workflow/stop`),

  // 批量启动翻译流程（按顺序依次处理）
  startBatchWorkflow: (ids: number[]) => api.post('/literary/translations/batch/workflow/start', { translation_ids: ids }),

  // 获取工作流状态（轮询用）
  getWorkflowStatus: (id: number) => api.get(`/literary/translations/${id}/workflow`),
  
  // ===== 段落管理 =====
  
  // 分页获取段落
  getParagraphs: (translationId: number, params?: { skip?: number; limit?: number }) =>
    api.get<{ items: any[]; total: number; skip: number; limit: number }>(
      `/literary/translations/${translationId}/paragraphs`,
      { params }
    ),
  
  // 更新段落（用户编辑）
  updateParagraph: (paragraphId: number, data: { user_edited_text: string }) => 
    api.put(`/literary/paragraphs/${paragraphId}`, data),

  // 单段 AI 重译（四步流程，耗时较长）
  retranslateParagraph: (paragraphId: number) =>
    api.post(`/literary/paragraphs/${paragraphId}/retranslate`, null, { timeout: 300000 }),
  
  // ===== 导出 =====

  // 导出翻译结果
  exportTranslation: (id: number, data: { format: 'txt' | 'md' | 'html' | 'json' | 'csv'; include_source?: boolean }) =>
    api.post(`/literary/translations/${id}/export`, data),

  // ===== 专业词库 =====

  // 获取专业词汇列表
  listTerms: (params?: {
    literary_type?: string;
    category?: string;
    source_lang?: string;
    target_lang?: string;
    keyword?: string;
    is_verified?: boolean;
    translation_id?: number;
    scope?: 'document' | 'global';
    skip?: number;
    limit?: number;
  }) => api.get('/literary/terms', { params }),

  // 创建专业词汇
  createTerm: (data: {
    source_term: string;
    target_term: string;
    literary_type: string;
    category?: string;
    source_lang: string;
    target_lang: string;
    description?: string;
    translation_id?: number;
  }) => api.post('/literary/terms', data),

  // 更新专业词汇
  updateTerm: (id: number, data: {
    target_term?: string;
    category?: string;
    description?: string;
    is_verified?: boolean;
    translation_id?: number | null;
  }) => api.put(`/literary/terms/${id}`, data),

  // 删除专业词汇
  deleteTerm: (id: number) => api.delete(`/literary/terms/${id}`),

  // 小词库提升到大词库
  promoteTerm: (id: number) => api.post(`/literary/terms/${id}/promote`),

  // 把各项目小词典归并进系统大词典
  syncGlobalTerms: () => api.post('/literary/terms/sync-global'),

  // 获取词汇分类列表
  getTermCategories: (params?: {
    literary_type?: string;
    translation_id?: number;
    scope?: 'document' | 'global';
  }) => api.get('/literary/terms/categories', { params }),

  // 获取翻译任务的词汇总结
  getTermSummary: (translationId: number) =>
    api.get(`/literary/translations/${translationId}/terms`),

  // 手动触发词汇提取
  extractTerms: (translationId: number) =>
    api.post(`/literary/translations/${translationId}/terms/extract`),

  // ===== 长文件翻译 =====

  // 解析上传文件为正文（不创建任务，用于新建任务时填充原文）
  parseFile: (formData: FormData) =>
    api.post<{ text: string; filename: string }>('/literary/parse-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
  // 上传文件创建翻译任务
  uploadAndTranslate: (formData: FormData) =>
    api.post('/literary/translations/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
  // 批量上传文件创建多个翻译任务
  uploadAndTranslateBatch: (formData: FormData) =>
    api.post<{ message: string; results: Array<{ filename: string; translation_id: number | null; error: string | null; total_chunks: number; total_chars: number; current_step: number; status: string }> }>(
      '/literary/translations/upload-batch',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    ),

  // 一键翻译所有段落
  translateAllChunks: (translationId: number) =>
    api.post(`/literary/translations/${translationId}/translate-all`),

  // 获取翻译进度
  getTranslationProgress: (translationId: number) =>
    api.get(`/literary/translations/${translationId}/progress`),

  getStoryProfile: (translationId: number) =>
    api.get(`/literary/translations/${translationId}/story`),

  updateStoryProfile: (translationId: number, profile: Record<string, unknown>) =>
    api.put(`/literary/translations/${translationId}/story`, { profile }),

  regenerateStoryProfile: (translationId: number) =>
    api.post(`/literary/translations/${translationId}/story/regenerate`, null, { timeout: 600000 }),
}

// ========== 文风智能体 API（系统级） ==========
export const styleAgentApi = {
  listPresets: () => api.get<StyleAgentPreset[]>('/style-agent-presets'),
  list: () => api.get<StyleAgent[]>('/style-agents'),
  create: (data: StyleAgentCreate) => api.post<StyleAgent>('/style-agents', data),
  fromPreset: (presetKey: string, setDefault = false) =>
    api.post<StyleAgent>('/style-agents/from-preset', {
      preset_key: presetKey,
      set_default: setDefault,
    }),
  update: (agentId: number, data: StyleAgentUpdate) =>
    api.put<StyleAgent>(`/style-agents/${agentId}`, data),
  setDefault: (agentId: number) =>
    api.post<StyleAgent>(`/style-agents/${agentId}/set-default`),
  delete: (agentId: number) => api.delete(`/style-agents/${agentId}`),
  parseFiles: (files: File[]) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    return api.post<{
      sources: { name: string; text: string; chars: number; format: string }[]
      errors: string[]
      count: number
    }>('/style-agents/parse-files', form, {
      timeout: 120000,
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  extractFromText: (data: {
    text?: string
    texts?: string[]
    sources?: { name: string; text: string }[]
    name?: string
    save?: boolean
    set_default?: boolean
  }) =>
    api.post<StyleExtractResult>('/style-agents/extract-from-text', data, {
      timeout: 180000,
    }),
}

export default api
