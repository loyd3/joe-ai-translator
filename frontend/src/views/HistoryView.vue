<template>
  <div class="history-view">
    <div class="page-header">
      <h2>
        <el-icon><Clock /></el-icon>
        翻译历史
      </h2>
      <div class="header-actions">
        <el-radio-group v-model="filterType" size="small">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="favorite">收藏</el-radio-button>
        </el-radio-group>
        <el-button type="danger" link @click="clearAll" :disabled="!history.length">
          <el-icon><Delete /></el-icon>
          清空历史
        </el-button>
      </div>
    </div>

    <div class="history-list">
      <el-empty v-if="!history.length" description="暂无翻译记录" />
      
      <div
        v-for="item in history"
        :key="item.id"
        class="history-item"
        :class="{ favorite: item.is_favorite }"
      >
        <div class="item-header">
          <div class="lang-pair">
            <el-tag size="small">{{ getLangName(item.source_lang) }}</el-tag>
            <el-icon><ArrowRight /></el-icon>
            <el-tag size="small" type="success">{{ getLangName(item.target_lang) }}</el-tag>
          </div>
          <div class="item-actions">
            <el-button
              link
              :type="item.is_favorite ? 'warning' : 'default'"
              @click="toggleFavorite(item)"
            >
              <el-icon><Star /></el-icon>
            </el-button>
            <el-button link @click="deleteItem(item)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
        
        <div class="item-content">
          <div class="source-text">{{ truncate(item.source_text, 200) }}</div>
          <div class="translated-text">{{ truncate(item.translated_text, 200) }}</div>
        </div>
        
        <div class="item-footer">
          <span class="timestamp">{{ formatTime(item.created_at) }}</span>
          <div class="footer-actions">
            <el-button link size="small" @click="copyText(item.translated_text)">
              <el-icon><CopyDocument /></el-icon>
              复制
            </el-button>
            <el-button link size="small" @click="useAgain(item)">
              <el-icon><RefreshRight /></el-icon>
              再次翻译
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载更多 -->
    <div v-if="history.length >= limit" class="load-more">
      <el-button link @click="loadMore">
        加载更多
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { translateApi } from '@/api'

const router = useRouter()

// 数据
const history = ref<any[]>([])
const filterType = ref('all')
const skip = ref(0)
const limit = ref(20)
const languages = ref<{ code: string; name: string }[]>([])

// 计算属性
const favoriteOnly = computed(() => filterType.value === 'favorite')

// 获取语言名称
const getLangName = (code: string) => {
  if (code === 'auto') return '自动检测'
  const lang = languages.value.find(l => l.code === code)
  return lang?.name || code
}

// 截断文本
const truncate = (text: string, maxLength: number) => {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

// 格式化时间
const formatTime = (isoString: string) => {
  const date = new Date(isoString)
  return date.toLocaleString('zh-CN')
}

// 加载历史记录
const loadHistory = async () => {
  try {
    const response = await translateApi.getHistory({
      skip: skip.value,
      limit: limit.value,
      favorite_only: favoriteOnly.value,
    })
    if (skip.value === 0) {
      history.value = response.data
    } else {
      history.value.push(...response.data)
    }
  } catch (error) {
    ElMessage.error('加载历史记录失败')
  }
}

// 加载更多
const loadMore = () => {
  skip.value += limit.value
  loadHistory()
}

// 切换收藏
const toggleFavorite = async (item: any) => {
  try {
    await translateApi.toggleFavorite(item.id)
    item.is_favorite = !item.is_favorite
    ElMessage.success(item.is_favorite ? '已添加到收藏' : '已取消收藏')
    
    if (favoriteOnly.value && !item.is_favorite) {
      history.value = history.value.filter(h => h.id !== item.id)
    }
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 删除记录
const deleteItem = async (item: any) => {
  try {
    await ElMessageBox.confirm('确定要删除这条翻译记录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    
    await translateApi.deleteHistory(item.id)
    history.value = history.value.filter(h => h.id !== item.id)
    ElMessage.success('已删除')
  } catch {
    // 用户取消
  }
}

// 清空所有
const clearAll = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有历史记录吗？此操作不可恢复。', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'danger',
    })
    
    // 逐个删除（实际应用应该有一个批量删除接口）
    for (const item of history.value) {
      await translateApi.deleteHistory(item.id)
    }
    history.value = []
    ElMessage.success('已清空所有历史记录')
  } catch {
    // 用户取消
  }
}

// 复制文本
const copyText = (text: string) => {
  navigator.clipboard.writeText(text)
  ElMessage.success('已复制到剪贴板')
}

// 再次翻译
const useAgain = (item: any) => {
  router.push({
    path: '/',
    query: {
      text: item.source_text,
      source: item.source_lang,
      target: item.target_lang,
    },
  })
}

// 监听筛选变化
watch(filterType, () => {
  skip.value = 0
  loadHistory()
})

// 加载语言列表
const loadLanguages = async () => {
  try {
    const response = await translateApi.getLanguages()
    languages.value = response.data
  } catch (error) {
    console.error('Failed to load languages:', error)
  }
}

onMounted(() => {
  loadLanguages()
  loadHistory()
})
</script>

<style scoped lang="scss">
.history-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
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

.header-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.history-item {
  background: var(--el-bg-color);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
  
  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  }
  
  &.favorite {
    border: 1px solid var(--el-color-warning-light);
    background: linear-gradient(135deg, var(--el-bg-color) 0%, var(--el-color-warning-light-9) 100%);
  }
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.lang-pair {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .el-icon {
    color: var(--el-text-color-secondary);
  }
}

.item-actions {
  display: flex;
  gap: 4px;
}

.item-content {
  margin-bottom: 12px;
}

.source-text {
  color: var(--el-text-color-regular);
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 8px;
  padding: 12px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

.translated-text {
  color: var(--el-text-color-primary);
  font-size: 14px;
  line-height: 1.6;
  padding: 12px;
  background: var(--el-color-primary-light-9);
  border-radius: 8px;
}

.item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.timestamp {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.footer-actions {
  display: flex;
  gap: 8px;
}

.load-more {
  text-align: center;
  margin-top: 24px;
}
</style>
