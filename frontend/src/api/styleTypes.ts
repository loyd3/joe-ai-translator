/** 翻译风格（贴合原文 + 译者习惯） */

export interface StyleAgentConfig {
  sentence: string
  diction: string
  idiom: string
  register: string
  compactness: string
  taboo: string[]
  custom_text: string
  samples: string[]
}

export interface StyleAgent {
  id: number
  name: string
  description?: string
  preset_key?: string | null
  config: StyleAgentConfig
  is_default: boolean
  source?: string
  compiled_preview?: string
  created_at?: string
  updated_at?: string
}

export interface StyleAgentPreset {
  key: string
  name: string
  description: string
  config: StyleAgentConfig
}

export interface StyleAgentCreate {
  name: string
  description?: string
  config?: Partial<StyleAgentConfig>
  preset_key?: string
  is_default?: boolean
}

export interface StyleAgentUpdate {
  name?: string
  description?: string
  config?: Partial<StyleAgentConfig>
  is_default?: boolean
}

export interface StyleExtractResult {
  name: string
  description: string
  config: StyleAgentConfig
  compiled_preview: string
  source_chunks: number
  source_files?: number
  source_names?: string[]
  agent?: StyleAgent | null
}
