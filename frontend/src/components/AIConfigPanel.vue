<template>
  <div class="ai-config-panel" v-loading="loading">
    <div class="status-card">
      <div class="status-main">
        <div class="provider-badge">{{ currentProviderMeta?.name?.charAt(0) || '?' }}</div>
        <div>
          <div class="status-title">
            {{ currentProviderMeta?.name || '未选择提供商' }}
            <el-tag v-if="info.has_api_key || form.provider === 'ollama'" size="small" type="success">可用</el-tag>
            <el-tag v-else size="small" type="warning">待配置</el-tag>
          </div>
          <div class="status-sub">{{ form.model || '请填写模型' }}</div>
        </div>
      </div>
      <el-tag size="small" :type="info.source === 'database' ? 'success' : 'info'" effect="plain">
        {{ info.source === 'database' ? '使用已保存配置' : '使用环境默认' }}
      </el-tag>
    </div>

    <p class="hint">
      选择提供商，手填模型名与 API Key，并按需调整采样参数。翻译全流程会使用这里保存的配置。
    </p>

    <div class="provider-grid">
      <button
        v-for="p in providers"
        :key="p.id"
        type="button"
        class="provider-card"
        :class="{ active: form.provider === p.id }"
        @click="selectProvider(p.id)"
      >
        <strong>{{ p.name }}</strong>
        <span>{{ p.description }}</span>
      </button>
    </div>

    <el-form :model="form" label-position="top" class="config-form">
      <el-form-item :label="form.provider === 'ollama' ? 'API Key（可选）' : 'API Key'">
        <el-input
          v-model="form.api_key"
          type="password"
          show-password
          :placeholder="info.has_api_key ? `已配置（${info.api_key_masked}），留空保持不变` : '请输入 API Key'"
        />
      </el-form-item>

      <el-form-item label="模型">
        <el-input
          v-model="form.model"
          placeholder="例如 deepseek-chat、gpt-4o"
          clearable
        />
        <div class="form-hint" v-if="currentProviderMeta?.models?.length">
          常用参考：{{ currentProviderMeta.models.slice(0, 4).join('、') }}
        </div>
      </el-form-item>

      <el-form-item
        v-if="showBaseUrl"
        :label="form.provider === 'ollama' ? 'Ollama 地址' : 'API 地址'"
      >
        <el-input
          v-model="form.base_url"
          :placeholder="currentProviderMeta?.base_url || 'https://api.example.com/v1'"
        />
        <div class="form-hint" v-if="form.provider !== 'custom'">
          默认 {{ currentProviderMeta?.base_url || '—' }}，一般无需修改
        </div>
      </el-form-item>

      <el-collapse v-model="advancedOpen">
        <el-collapse-item title="采样与请求参数" name="advanced">
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="Temperature">
                <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
                <div class="slider-labels"><span>更稳</span><span>更活</span></div>
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Max Tokens">
                <el-input-number
                  v-model="form.max_tokens"
                  :min="256"
                  :max="256000"
                  :step="512"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Top P">
                <el-slider v-model="form.top_p" :min="0" :max="1" :step="0.05" show-input />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="超时（秒）">
                <el-input-number
                  v-model="form.timeout_seconds"
                  :min="10"
                  :max="600"
                  :step="10"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Frequency Penalty">
                <el-slider v-model="form.frequency_penalty" :min="-2" :max="2" :step="0.1" show-input />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="Presence Penalty">
                <el-slider v-model="form.presence_penalty" :min="-2" :max="2" :step="0.1" show-input />
              </el-form-item>
            </el-col>
          </el-row>
        </el-collapse-item>
      </el-collapse>

      <div class="actions">
        <el-button :loading="testing" @click="testConnection">测试连接</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
      </div>
    </el-form>

    <el-alert
      v-if="testResult"
      class="test-alert"
      :title="testResult.success ? '连接成功' : '连接失败'"
      :type="testResult.success ? 'success' : 'error'"
      :closable="true"
      show-icon
      @close="testResult = null"
    >
      <div>{{ testResult.message }}</div>
      <div v-if="testResult.response" class="test-response">响应：{{ testResult.response }}</div>
    </el-alert>

    <div v-if="helpLinks.length" class="help-box">
      <div class="help-title">获取 API Key</div>
      <ul>
        <li v-for="item in helpLinks" :key="item.href">
          <a :href="item.href" target="_blank" rel="noopener noreferrer">{{ item.label }}</a>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { systemApi } from '@/api'

interface ProviderMeta {
  id: string
  name: string
  description: string
  base_url: string
  docs_url?: string
  requires_api_key: boolean
  allow_base_url_override?: boolean
  models: string[]
  default_model: string
}

const emit = defineEmits<{ saved: [] }>()

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const advancedOpen = ref<string[]>(['advanced'])
const providers = ref<ProviderMeta[]>([])
const info = ref<any>({
  provider: 'deepseek',
  has_api_key: false,
  api_key_masked: '',
  source: 'env',
})
const testResult = ref<{ success: boolean; message: string; response?: string } | null>(null)

const form = ref({
  provider: 'deepseek',
  api_key: '',
  model: 'deepseek-chat',
  base_url: '',
  temperature: 0.3,
  max_tokens: 4096,
  top_p: 1,
  frequency_penalty: 0,
  presence_penalty: 0,
  timeout_seconds: 120,
})

const currentProviderMeta = computed(() =>
  providers.value.find((p) => p.id === form.value.provider)
)

const showBaseUrl = computed(() => {
  const p = form.value.provider
  return p === 'custom' || p === 'ollama' || !!currentProviderMeta.value?.allow_base_url_override
})

const helpLinks = computed(() => {
  const meta = currentProviderMeta.value
  if (!meta?.docs_url) return []
  return [{ href: meta.docs_url, label: `打开 ${meta.name} 控制台` }]
})

async function load() {
  loading.value = true
  try {
    const res = await systemApi.getAIConfig()
    const data = res.data
    info.value = data
    providers.value = Array.isArray(data.available_providers) ? data.available_providers : []
    if (!providers.value.length) {
      const catalog = await systemApi.listAIProviders()
      providers.value = catalog.data?.providers || []
    }
    form.value = {
      provider: data.provider || 'deepseek',
      api_key: '',
      model: data.model || '',
      base_url: data.base_url || '',
      temperature: data.temperature ?? 0.3,
      max_tokens: data.max_tokens || 4096,
      top_p: data.top_p ?? 1,
      frequency_penalty: data.frequency_penalty ?? 0,
      presence_penalty: data.presence_penalty ?? 0,
      timeout_seconds: data.timeout_seconds || 120,
    }
    if (!form.value.model) {
      form.value.model = currentProviderMeta.value?.default_model || ''
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载配置失败')
  } finally {
    loading.value = false
  }
}

function selectProvider(id: string) {
  if (form.value.provider === id) return
  form.value.provider = id
  const meta = providers.value.find((p) => p.id === id)
  form.value.model = meta?.default_model || meta?.models?.[0] || ''
  form.value.base_url = meta?.base_url || ''
  form.value.api_key = ''
  testResult.value = null
}

async function save() {
  if (form.value.provider !== 'ollama' && !form.value.api_key && !info.value.has_api_key) {
    ElMessage.warning('请先填写 API Key')
    return
  }
  if (form.value.provider === 'custom' && !form.value.base_url.trim()) {
    ElMessage.warning('自定义提供商需要填写 API 地址')
    return
  }
  saving.value = true
  try {
    const payload: any = {
      provider: form.value.provider,
      model: form.value.model || undefined,
      base_url: form.value.base_url || undefined,
      temperature: form.value.temperature,
      max_tokens: form.value.max_tokens,
      top_p: form.value.top_p,
      frequency_penalty: form.value.frequency_penalty,
      presence_penalty: form.value.presence_penalty,
      timeout_seconds: form.value.timeout_seconds,
    }
    if (form.value.api_key) payload.api_key = form.value.api_key
    await systemApi.updateAIConfig(payload)
    ElMessage.success('配置已保存')
    await load()
    emit('saved')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function testConnection() {
  if (form.value.provider !== 'ollama' && !form.value.api_key && !info.value.has_api_key) {
    ElMessage.warning('请先填写 API Key')
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const res = await systemApi.testAIConfig({
      provider: form.value.provider,
      api_key: form.value.api_key || undefined,
      model: form.value.model || undefined,
      base_url: form.value.base_url || undefined,
      temperature: form.value.temperature,
      timeout_seconds: Math.min(form.value.timeout_seconds || 30, 60),
    })
    testResult.value = res.data
    if (res.data.success) ElMessage.success('连接成功')
    else ElMessage.error('连接失败')
  } catch (e: any) {
    testResult.value = {
      success: false,
      message: e?.response?.data?.detail || e?.message || '测试请求失败',
    }
  } finally {
    testing.value = false
  }
}

onMounted(load)

defineExpose({ reload: load })
</script>

<style scoped lang="scss">
.ai-config-panel {
  height: 100%;
  overflow-y: auto;
  padding: 20px 24px 32px;
  max-width: 960px;
  margin: 0 auto;
}

.status-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--ins-line);
  border-radius: 12px;
  background: var(--ins-surface);
  margin-bottom: 14px;
}

.status-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.provider-badge {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  background: var(--ins-grad);
  color: #fff;
  font-weight: 700;
  flex-shrink: 0;
}

.status-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: var(--ins-ink);
}

.status-sub {
  margin-top: 2px;
  font-size: 13px;
  color: var(--ins-muted);
  word-break: break-all;
}

.hint {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--ins-muted);
  line-height: 1.55;
}

.provider-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 18px;
}

.provider-card {
  text-align: left;
  border: 1px solid var(--ins-line-strong);
  border-radius: 10px;
  background: var(--ins-surface);
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;

  strong {
    display: block;
    font-size: 14px;
    color: var(--ins-ink);
    margin-bottom: 4px;
  }

  span {
    display: block;
    font-size: 12px;
    color: var(--ins-muted);
    line-height: 1.45;
  }

  &:hover {
    border-color: var(--el-color-primary-light-5);
    background: var(--ins-bg-deep);
  }

  &.active {
    border-color: var(--el-color-primary);
    background: var(--el-color-primary-light-9);
    box-shadow: 0 0 0 1px var(--el-color-primary);
  }
}

.config-form {
  background: var(--ins-surface);
  border: 1px solid var(--ins-line);
  border-radius: 12px;
  padding: 16px 18px 8px;
}

.form-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--ins-muted);
  line-height: 1.4;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ins-muted);
  margin-top: -4px;
}

.actions {
  display: flex;
  gap: 10px;
  padding: 8px 0 12px;
}

.test-alert {
  margin-top: 14px;
}

.test-response {
  margin-top: 6px;
  font-size: 12px;
  opacity: 0.85;
  word-break: break-word;
}

.help-box {
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--ins-bg-deep);
  border: 1px solid var(--ins-line);

  .help-title {
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
    color: var(--ins-ink);
  }

  ul {
    margin: 0;
    padding-left: 18px;
    color: var(--ins-muted);
    font-size: 13px;
  }

  a {
    color: var(--el-color-primary);
    text-decoration: none;
    &:hover { text-decoration: underline; }
  }
}
</style>
