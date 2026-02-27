import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useTranslatorStore = defineStore('translator', () => {
  // 状态
  const sourceLang = ref('auto')
  const targetLang = ref('en')
  const recentLanguages = ref<string[]>(['zh', 'en', 'ja'])
  
  // Getters
  const languagePair = computed(() => `${sourceLang.value}-${targetLang.value}`)
  
  // Actions
  const setLanguagePair = (source: string, target: string) => {
    sourceLang.value = source
    targetLang.value = target
  }
  
  const addRecentLanguage = (code: string) => {
    if (!recentLanguages.value.includes(code)) {
      recentLanguages.value.unshift(code)
      if (recentLanguages.value.length > 5) {
        recentLanguages.value.pop()
      }
    }
  }
  
  return {
    sourceLang,
    targetLang,
    recentLanguages,
    languagePair,
    setLanguagePair,
    addRecentLanguage,
  }
})
