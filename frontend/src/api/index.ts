import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

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
  getAIConfig: () => api.get('/system/ai-config'),
  updateAIConfig: (data: {
    provider: string;
    api_key?: string;
    model?: string;
    base_url?: string;
    temperature?: number;
    max_tokens?: number;
  }) => api.put('/system/ai-config', data),
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
    literary_type: 'poetry' | 'prose' | 'novel' | 'drama' | 'general'
    reference_document_ids?: number[]
    user_requirements?: string
  }) => api.post('/literary/translations', data),
  
  // 获取翻译任务列表
  listTranslations: (params?: { skip?: number; limit?: number; status?: string }) => 
    api.get('/literary/translations', { params }),
  
  // 获取翻译任务详情
  getTranslation: (id: number, includeParagraphs?: boolean) => 
    api.get(`/literary/translations/${id}`, { params: { include_paragraphs: includeParagraphs } }),
  
  // 更新翻译任务（改）
  updateTranslation: (id: number, data: {
    title?: string
    source_text?: string
    final_translation?: string
    status?: string
  }) => api.put(`/literary/translations/${id}`, data),
  
  // 删除翻译任务
  deleteTranslation: (id: number) => api.delete(`/literary/translations/${id}`),
  
  // ===== 翻译流程 =====

  // 启动四步翻译流程（后台执行，立即返回）
  startWorkflow: (id: number) => api.post(`/literary/translations/${id}/workflow/start`),

  // 批量启动翻译流程（按顺序依次处理）
  startBatchWorkflow: (ids: number[]) => api.post('/literary/translations/batch/workflow/start', { translation_ids: ids }),

  // 获取工作流状态（轮询用）
  getWorkflowStatus: (id: number) => api.get(`/literary/translations/${id}/workflow`),
  
  // ===== 段落管理 =====
  
  // 获取所有段落
  getParagraphs: (translationId: number) => 
    api.get(`/literary/translations/${translationId}/paragraphs`),
  
  // 更新段落（用户编辑）
  updateParagraph: (paragraphId: number, data: { user_edited_text: string }) => 
    api.put(`/literary/paragraphs/${paragraphId}`, data),
  
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
  }) => api.post('/literary/terms', data),

  // 更新专业词汇
  updateTerm: (id: number, data: {
    target_term?: string;
    category?: string;
    description?: string;
    is_verified?: boolean;
  }) => api.put(`/literary/terms/${id}`, data),

  // 删除专业词汇
  deleteTerm: (id: number) => api.delete(`/literary/terms/${id}`),

  // 获取词汇分类列表
  getTermCategories: (params?: { literary_type?: string }) =>
    api.get('/literary/terms/categories', { params }),

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

  // 一键翻译所有段落
  translateAllChunks: (translationId: number) =>
    api.post(`/literary/translations/${translationId}/translate-all`),

  // 获取翻译进度
  getTranslationProgress: (translationId: number) =>
    api.get(`/literary/translations/${translationId}/progress`),
}

export default api
