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
}

export default api
