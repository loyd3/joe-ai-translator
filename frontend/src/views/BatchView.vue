<template>
  <div class="batch-view">
    <div class="page-header">
      <h2>
        <el-icon><DocumentCopy /></el-icon>
        批量翻译
      </h2>
    </div>

    <div class="batch-container">
      <!-- 配置区 -->
      <div class="config-section">
        <el-card>
          <template #header>
            <span>翻译设置</span>
          </template>
          
          <el-form label-width="100px">
            <el-form-item label="源语言">
              <el-select v-model="sourceLang" placeholder="选择源语言" style="width: 200px;">
                <el-option
                  v-for="lang in languages"
                  :key="lang.code"
                  :label="lang.name"
                  :value="lang.code"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="目标语言">
              <el-select v-model="targetLang" placeholder="选择目标语言" style="width: 200px;">
                <el-option
                  v-for="lang in targetLanguages"
                  :key="lang.code"
                  :label="lang.name"
                  :value="lang.code"
                />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>
      </div>

      <!-- 输入区 -->
      <div class="input-section">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>输入文本</span>
              <div class="header-actions">
                <el-upload
                  action=""
                  :auto-upload="false"
                  :on-change="handleFileUpload"
                  :show-file-list="false"
                  accept=".txt,.md,.json"
                >
                  <el-button link>
                    <el-icon><Upload /></el-icon>
                    上传文件
                  </el-button>
                </el-upload>
                <el-button link @click="loadExample">
                  <el-icon><Document /></el-icon>
                  加载示例
                </el-button>
                <el-button link type="danger" @click="clearAll">
                  <el-icon><Delete /></el-icon>
                  清空
                </el-button>
              </div>
            </div>
          </template>
          
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="10"
            placeholder="请输入要翻译的文本，每行一个段落，或使用空行分隔不同段落..."
          />
          
          <div class="input-stats">
            共 {{ items.length }} 个段落
          </div>
        </el-card>
      </div>

      <!-- 操作区 -->
      <div class="action-section">
        <el-button
          type="primary"
          size="large"
          :loading="isTranslating"
          :disabled="!canTranslate"
          @click="startBatch"
        >
          <el-icon><VideoPlay /></el-icon>
          开始批量翻译
        </el-button>
      </div>

      <!-- 结果区 -->
      <div v-if="batchResult" class="result-section">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>翻译结果</span>
              <el-button link @click="downloadResult">
                <el-icon><Download /></el-icon>
                下载结果
              </el-button>
            </div>
          </template>
          
          <div class="result-list">
            <div
              v-for="(item, index) in batchResult.items"
              :key="index"
              class="result-item"
            >
              <div class="item-number">{{ index + 1 }}</div>
              <div class="item-content">
                <div class="source">{{ item.source_text }}</div>
                <el-divider>
                  <el-icon><Bottom /></el-icon>
                </el-divider>
                <div class="target">
                  <span v-if="item.translated_text">{{ item.translated_text }}</span>
                  <el-skeleton v-else :rows="1" animated />
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { translateApi } from '@/api'

// 语言列表
const languages = ref<{ code: string; name: string }[]>([])
const sourceLang = ref('auto')
const targetLang = ref('en')
const inputText = ref('')
const isTranslating = ref(false)
const batchResult = ref<any>(null)

// 目标语言
const targetLanguages = computed(() => 
  languages.value.filter(l => l.code !== 'auto')
)

// 解析的翻译项目
const items = computed(() => {
  if (!inputText.value.trim()) return []
  return inputText.value
    .split(/\n\s*\n/)
    .map(t => t.trim())
    .filter(t => t.length > 0)
})

// 是否可以翻译
const canTranslate = computed(() => 
  items.value.length > 0 && targetLang.value && !isTranslating.value
)

// 加载示例
const loadExample = () => {
  inputText.value = `人工智能正在改变我们的生活方式。从智能手机到自动驾驶汽车，AI 技术无处不在。

机器学习是人工智能的一个分支，它使计算机能够从数据中学习，而无需明确编程。

深度学习使用神经网络来模拟人脑的工作方式，在图像识别和自然语言处理方面取得了突破性进展。`
  ElMessage.success('已加载示例文本')
}

// 清空
const clearAll = () => {
  inputText.value = ''
  batchResult.value = null
}

// 处理文件上传
const handleFileUpload = (file: any) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    inputText.value = e.target?.result as string
    ElMessage.success(`已加载文件: ${file.name}`)
  }
  reader.readAsText(file.raw)
}

// 开始批量翻译
const startBatch = async () => {
  if (!items.value.length) {
    ElMessage.warning('请输入要翻译的文本')
    return
  }
  
  isTranslating.value = true
  batchResult.value = null
  
  try {
    const response = await translateApi.createBatch({
      items: items.value,
      source_lang: sourceLang.value,
      target_lang: targetLang.value,
    })
    
    batchResult.value = response.data
    
    // 模拟逐个翻译（实际应用应该有 WebSocket 或轮询）
    for (let i = 0; i < batchResult.value.items.length; i++) {
      await translateItem(i)
    }
    
    ElMessage.success('批量翻译完成')
  } catch (error) {
    ElMessage.error('批量翻译失败')
    console.error(error)
  } finally {
    isTranslating.value = false
  }
}

// 翻译单个项目
const translateItem = async (index: number) => {
  const item = batchResult.value.items[index]
  try {
    const response = await translateApi.translate({
      text: item.source_text,
      source_lang: sourceLang.value,
      target_lang: targetLang.value,
      stream: false,
    })
    item.translated_text = response.data.translated_text
    item.status = 'completed'
  } catch (error) {
    item.status = 'failed'
  }
}

// 下载结果
const downloadResult = () => {
  if (!batchResult.value) return
  
  const content = batchResult.value.items
    .map((item: any) => `${item.source_text}\n\n${item.translated_text || '[翻译失败]'}\n---`)
    .join('\n\n')
  
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `translation_${Date.now()}.txt`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('已下载翻译结果')
}

// 加载语言列表
onMounted(async () => {
  try {
    const response = await translateApi.getLanguages()
    languages.value = response.data
  } catch (error) {
    console.error('Failed to load languages:', error)
  }
})
</script>

<style scoped lang="scss">
.batch-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  margin-bottom: 24px;
  
  h2 {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0;
    font-size: 24px;
    
    .el-icon {
      color: var(--el-color-primary);
    }
  }
}

.batch-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.input-stats {
  margin-top: 12px;
  text-align: right;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.action-section {
  text-align: center;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.item-number {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--el-color-primary);
  color: white;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.item-content {
  flex: 1;
  
  .source {
    color: var(--el-text-color-regular);
    line-height: 1.6;
  }
  
  .target {
    color: var(--el-color-primary);
    font-weight: 500;
    line-height: 1.6;
  }
}
</style>
