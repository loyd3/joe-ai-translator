<template>
  <div class="translator-view">
    <div class="translator-container">
      <!-- 语言选择栏 -->
      <div class="language-bar">
        <el-select v-model="sourceLang" placeholder="源语言" class="lang-select">
          <el-option
            v-for="lang in languages"
            :key="lang.code"
            :label="lang.name"
            :value="lang.code"
          />
        </el-select>
        
        <el-button circle class="swap-btn" @click="swapLanguages">
          <el-icon><Sort /></el-icon>
        </el-button>
        
        <el-select v-model="targetLang" placeholder="目标语言" class="lang-select">
          <el-option
            v-for="lang in targetLanguages"
            :key="lang.code"
            :label="lang.name"
            :value="lang.code"
          />
        </el-select>
      </div>

      <!-- 翻译区域 -->
      <div class="translation-area">
        <!-- 输入区 -->
        <div class="input-section">
          <div class="section-header">
            <span class="lang-label">{{ getLangName(sourceLang) }}</span>
            <div class="actions">
              <el-button link @click="clearInput">
                <el-icon><Delete /></el-icon>
              </el-button>
              <el-button link @click="pasteText">
                <el-icon><DocumentCopy /></el-icon>
              </el-button>
            </div>
          </div>
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="8"
            placeholder="请输入要翻译的文本..."
            class="translation-input"
            resize="none"
          />
          <div class="input-footer">
            <span class="char-count">{{ inputText.length }} 字符</span>
            <el-button type="primary" size="large" :loading="isTranslating" @click="translate">
              <el-icon><Promotion /></el-icon>
              翻译
            </el-button>
          </div>
        </div>

        <!-- 输出区 -->
        <div class="output-section">
          <div class="section-header">
            <span class="lang-label">{{ getLangName(targetLang) }}</span>
            <div class="actions">
              <el-button link @click="copyOutput" :disabled="!outputText">
                <el-icon><CopyDocument /></el-icon>
              </el-button>
              <el-button link @click="speakOutput" :disabled="!outputText">
                <el-icon><Microphone /></el-icon>
              </el-button>
            </div>
          </div>
          <div class="output-content">
            <el-input
              v-if="!isTranslating"
              v-model="outputText"
              type="textarea"
              :rows="8"
              placeholder="翻译结果将显示在这里..."
              class="translation-output"
              resize="none"
              readonly
            />
            <div v-else class="streaming-content">
              {{ streamingText }}<span class="cursor">|</span>
            </div>
          </div>
          <div class="output-footer">
            <el-button link type="primary" @click="saveToFavorites" :disabled="!outputText">
              <el-icon><Star /></el-icon>
              收藏
            </el-button>
          </div>
        </div>
      </div>

      <!-- 高级选项 -->
      <div class="advanced-options">
        <el-collapse>
          <el-collapse-item title="高级选项" name="advanced">
            <el-form label-width="100px">
              <el-form-item label="翻译场景">
                <el-radio-group v-model="translationContext">
                  <el-radio-button label="">通用</el-radio-button>
                  <el-radio-button label="technical">技术文档</el-radio-button>
                  <el-radio-button label="medical">医学</el-radio-button>
                  <el-radio-button label="legal">法律</el-radio-button>
                  <el-radio-button label="business">商务</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="自定义提示">
                <el-input
                  v-model="customContext"
                  type="textarea"
                  :rows="2"
                  placeholder="添加自定义翻译上下文或要求..."
                />
              </el-form-item>
            </el-form>
          </el-collapse-item>
        </el-collapse>
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
const outputText = ref('')
const streamingText = ref('')
const isTranslating = ref(false)
const translationContext = ref('')
const customContext = ref('')

// 目标语言（排除 auto）
const targetLanguages = computed(() => 
  languages.value.filter(l => l.code !== 'auto')
)

// 获取语言名称
const getLangName = (code: string) => {
  const lang = languages.value.find(l => l.code === code)
  return lang?.name || code
}

// 交换语言
const swapLanguages = () => {
  if (sourceLang.value === 'auto') {
    ElMessage.warning('无法交换，源语言为自动检测')
    return
  }
  const temp = sourceLang.value
  sourceLang.value = targetLang.value
  targetLang.value = temp
  // 同时交换文本
  if (outputText.value) {
    inputText.value = outputText.value
    outputText.value = ''
  }
}

// 清空输入
const clearInput = () => {
  inputText.value = ''
  outputText.value = ''
}

// 粘贴文本
const pasteText = async () => {
  try {
    const text = await navigator.clipboard.readText()
    inputText.value = text
    ElMessage.success('已粘贴')
  } catch {
    ElMessage.error('无法读取剪贴板')
  }
}

// 复制输出
const copyOutput = () => {
  navigator.clipboard.writeText(outputText.value)
  ElMessage.success('已复制到剪贴板')
}

// 朗读输出（简单实现）
const speakOutput = () => {
  if (!outputText.value) return
  const utterance = new SpeechSynthesisUtterance(outputText.value)
  utterance.lang = targetLang.value
  speechSynthesis.speak(utterance)
}

// 翻译
const translate = async () => {
  if (!inputText.value.trim()) {
    ElMessage.warning('请输入要翻译的文本')
    return
  }
  
  isTranslating.value = true
  outputText.value = ''
  streamingText.value = ''
  
  try {
    const context = translationContext.value || customContext.value || undefined
    const response = await translateApi.translateStream({
      text: inputText.value,
      source_lang: sourceLang.value,
      target_lang: targetLang.value,
      context,
    })
    
    const reader = response.body?.getReader()
    if (!reader) throw new Error('No reader')
    
    const decoder = new TextDecoder()
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const text = decoder.decode(value)
      const lines = text.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6))
          if (data.chunk) {
            streamingText.value += data.chunk
          }
          if (data.done) {
            outputText.value = streamingText.value
            streamingText.value = ''
          }
        }
      }
    }
    
    ElMessage.success('翻译完成')
  } catch (error) {
    ElMessage.error('翻译失败，请稍后重试')
    console.error(error)
  } finally {
    isTranslating.value = false
  }
}

// 保存到收藏
const saveToFavorites = () => {
  ElMessage.success('已添加到收藏')
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
.translator-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.translator-container {
  background: var(--el-bg-color);
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.language-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  padding: 20px;
  background: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-light);
}

.lang-select {
  width: 180px;
}

.swap-btn {
  transform: rotate(90deg);
}

.translation-area {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  min-height: 400px;
}

.input-section,
.output-section {
  display: flex;
  flex-direction: column;
}

.input-section {
  border-right: 1px solid var(--el-border-color-light);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--el-fill-color-lighter);
  border-bottom: 1px solid var(--el-border-color-light);
}

.lang-label {
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.actions {
  display: flex;
  gap: 8px;
}

.translation-input,
.translation-output {
  flex: 1;
  
  :deep(.el-textarea__inner) {
    border: none;
    border-radius: 0;
    font-size: 16px;
    line-height: 1.6;
    padding: 16px;
    min-height: 300px !important;
  }
}

.output-content {
  flex: 1;
  position: relative;
}

.streaming-content {
  padding: 16px;
  font-size: 16px;
  line-height: 1.6;
  min-height: 300px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.cursor {
  animation: blink 1s infinite;
  color: var(--el-color-primary);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.input-footer,
.output-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-top: 1px solid var(--el-border-color-light);
}

.char-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.advanced-options {
  padding: 0 20px 20px;
  border-top: 1px solid var(--el-border-color-light);
}

@media (max-width: 768px) {
  .translation-area {
    grid-template-columns: 1fr;
  }
  
  .input-section {
    border-right: none;
    border-bottom: 1px solid var(--el-border-color-light);
  }
}
</style>
