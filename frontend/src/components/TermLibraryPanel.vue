<!-- 专业词库管理组件 - 参考 DeepL/Google Translate 风格 -->
<template>
  <div class="term-library-panel">
    <div class="panel-header">
      <div class="header-title">
        <el-icon><Collection /></el-icon>
        <span>专业词库</span>
        <el-tag size="small" type="success" effect="dark" v-if="currentType">
          {{ getTypeLabel(currentType) }}
        </el-tag>
      </div>
      <div class="header-actions">
        <el-input
          v-model="searchQuery"
          placeholder="搜索词汇..."
          size="small"
          clearable
          class="search-input"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button type="primary" size="small" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          添加
        </el-button>
      </div>
    </div>

    <!-- 分类筛选标签 -->
    <div class="category-tags">
      <el-tag
        v-for="cat in categories"
        :key="cat"
        :type="selectedCategory === cat ? 'primary' : 'info'"
        size="small"
        class="category-tag"
        @click="selectedCategory = selectedCategory === cat ? '' : cat"
      >
        {{ cat }}
      </el-tag>
      <el-tag
        v-if="categories.length === 0"
        type="info"
        size="small"
      >
        暂无分类
      </el-tag>
    </div>

    <!-- 词汇列表 -->
    <div class="terms-list" v-loading="loading">
      <div
        v-for="term in filteredTerms"
        :key="term.id"
        :class="['term-card', { 'is-editing': editingId === term.id }]"
        @mouseenter="hoveredTerm = term.id"
        @mouseleave="hoveredTerm = null"
      >
        <div class="term-main">
          <div class="term-source">
            <span class="term-text">{{ term.source_term }}</span>
            <el-tag size="small" type="info" effect="plain" class="lang-tag">
              {{ term.source_lang }}
            </el-tag>
          </div>
          <div class="term-arrow">
            <el-icon><Right /></el-icon>
          </div>
          <div class="term-target">
            <span class="term-text">{{ term.target_term }}</span>
            <el-tag size="small" type="success" effect="plain" class="lang-tag">
              {{ term.target_lang }}
            </el-tag>
          </div>
        </div>

        <div class="term-meta">
          <el-tag v-if="term.category" size="small" type="warning" effect="light">
            {{ term.category }}
          </el-tag>
          <span class="usage-count" title="使用次数">
            <el-icon><View /></el-icon>
            {{ term.usage_count }}
          </span>
        </div>

        <div class="term-actions" v-show="hoveredTerm === term.id || editingId === term.id">
          <el-button link type="primary" size="small" @click="startEdit(term)">
            <el-icon><Edit /></el-icon>
          </el-button>
          <el-button link type="danger" size="small" @click="deleteTerm(term)">
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>

      <el-empty v-if="filteredTerms.length === 0" description="暂无词汇" :image-size="80" />
    </div>

    <!-- 统计信息 -->
    <div class="panel-footer">
      <span class="stats-text">共 {{ terms.length }} 个词汇</span>
      <span class="stats-text" v-if="newTermsCount > 0">
        <el-tag size="small" type="success">+{{ newTermsCount }} 新增</el-tag>
      </span>
    </div>

    <!-- 添加/编辑词汇对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="isEditing ? '编辑词汇' : '添加词汇'"
      width="500px"
      destroy-on-close
    >
      <el-form :model="termForm" label-position="top" :rules="rules" ref="formRef">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="源词汇" prop="source_term">
              <el-input v-model="termForm.source_term" placeholder="输入源语言词汇">
                <template #append>{{ termForm.source_lang }}</template>
              </el-input>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="翻译" prop="target_term">
              <el-input v-model="termForm.target_term" placeholder="输入目标语言翻译">
                <template #append>{{ termForm.target_lang }}</template>
              </el-input>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="文学类型">
          <el-radio-group v-model="termForm.literary_type" size="small">
            <el-radio-button label="general">一般</el-radio-button>
            <el-radio-button label="poetry">诗歌</el-radio-button>
            <el-radio-button label="prose">散文</el-radio-button>
            <el-radio-button label="novel">小说</el-radio-button>
            <el-radio-button label="drama">戏剧</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="分类">
          <el-select
            v-model="termForm.category"
            placeholder="选择或输入分类"
            allow-create
            filterable
            clearable
            style="width: 100%"
          >
            <el-option
              v-for="cat in categories"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="说明/例句">
          <el-input
            v-model="termForm.description"
            type="textarea"
            :rows="3"
            placeholder="可选：词汇说明、使用语境或例句"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTerm" :loading="saving">
          {{ isEditing ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog v-model="showImportDialog" title="批量导入词汇" width="600px">
      <el-alert
        title="格式说明"
        type="info"
        description="每行一个词汇，格式：源词汇 -> 翻译 | 分类 | 说明"
        :closable="false"
        style="margin-bottom: 16px;"
      />
      <el-input
        v-model="importText"
        type="textarea"
        :rows="10"
        placeholder="例如：&#10;metaphor -> 隐喻 | 修辞手法 | 比喻的一种&#10;sonnet -> 十四行诗 | 诗歌体裁 | 英国传统诗歌形式"
      />
      <template #footer>
        <el-button @click="showImportDialog = false">取消</el-button>
        <el-button type="primary" @click="batchImport" :loading="importing">
          导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { literaryApi } from '@/api'

const props = defineProps<{
  literaryType?: string;
  sourceLang?: string;
  targetLang?: string;
}>()

// 状态
const terms = ref<any[]>([])
const categories = ref<string[]>([])
const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const hoveredTerm = ref<number | null>(null)
const editingId = ref<number | null>(null)
const showAddDialog = ref(false)
const showImportDialog = ref(false)
const searchQuery = ref('')
const selectedCategory = ref('')
const importText = ref('')
const formRef = ref<any>(null)

const newTermsCount = computed(() => terms.value.filter(t => t.usage_count === 1).length)

const currentType = computed(() => props.literaryType || 'general')

// 表单
const termForm = ref({
  source_term: '',
  target_term: '',
  literary_type: props.literaryType || 'general',
  category: '',
  source_lang: props.sourceLang || 'en',
  target_lang: props.targetLang || 'zh',
  description: ''
})

const isEditing = computed(() => editingId.value !== null)

const rules = {
  source_term: [{ required: true, message: '请输入源词汇', trigger: 'blur' }],
  target_term: [{ required: true, message: '请输入翻译', trigger: 'blur' }]
}

// 筛选后的词汇
const filteredTerms = computed(() => {
  let result = terms.value

  // 按文学类型筛选
  if (props.literaryType) {
    result = result.filter(t => t.literary_type === props.literaryType)
  }

  // 按分类筛选
  if (selectedCategory.value) {
    result = result.filter(t => t.category === selectedCategory.value)
  }

  // 按搜索词筛选
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      t.source_term.toLowerCase().includes(query) ||
      t.target_term.toLowerCase().includes(query) ||
      (t.description && t.description.toLowerCase().includes(query))
    )
  }

  // 按使用次数排序
  return result.sort((a, b) => b.usage_count - a.usage_count)
})

// 方法
const loadTerms = async () => {
  loading.value = true
  try {
    const response = await literaryApi.listTerms({
      literary_type: props.literaryType,
      source_lang: props.sourceLang,
      target_lang: props.targetLang,
      limit: 500
    })
    terms.value = response.data
  } catch (error) {
    ElMessage.error('加载词汇失败')
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    const response = await literaryApi.getTermCategories({
      literary_type: props.literaryType
    })
    categories.value = response.data
  } catch (error) {
    console.error('Failed to load categories:', error)
  }
}

const startEdit = (term: any) => {
  editingId.value = term.id
  termForm.value = {
    source_term: term.source_term,
    target_term: term.target_term,
    literary_type: term.literary_type,
    category: term.category || '',
    source_lang: term.source_lang,
    target_lang: term.target_lang,
    description: term.description || ''
  }
  showAddDialog.value = true
}

const saveTerm = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    if (isEditing.value && editingId.value) {
      await literaryApi.updateTerm(editingId.value, {
        target_term: termForm.value.target_term,
        category: termForm.value.category,
        description: termForm.value.description
      })
      ElMessage.success('词汇已更新')
    } else {
      await literaryApi.createTerm(termForm.value)
      ElMessage.success('词汇已添加')
    }
    showAddDialog.value = false
    resetForm()
    loadTerms()
    loadCategories()
  } catch (error: any) {
    if (error.response?.data?.detail) {
      ElMessage.error(error.response.data.detail)
    } else {
      ElMessage.error('保存失败')
    }
  } finally {
    saving.value = false
  }
}

const deleteTerm = async (term: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 "${term.source_term}" 吗？`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除' }
    )
    await literaryApi.deleteTerm(term.id)
    ElMessage.success('词汇已删除')
    loadTerms()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const batchImport = async () => {
  if (!importText.value.trim()) {
    ElMessage.warning('请输入要导入的词汇')
    return
  }

  importing.value = true
  const lines = importText.value.split('\\n').filter(line => line.trim())
  let successCount = 0
  let failCount = 0

  for (const line of lines) {
    try {
      const parts = line.split('|').map(p => p.trim())
      const termParts = parts[0].split('->').map(p => p.trim())

      if (termParts.length === 2) {
        await literaryApi.createTerm({
          source_term: termParts[0],
          target_term: termParts[1],
          literary_type: props.literaryType || 'general',
          category: parts[1] || '',
          source_lang: props.sourceLang || 'en',
          target_lang: props.targetLang || 'zh',
          description: parts[2] || ''
        })
        successCount++
      } else {
        failCount++
      }
    } catch (error) {
      failCount++
    }
  }

  importing.value = false
  showImportDialog.value = false
  importText.value = ''

  ElMessage.success(`导入完成：成功 ${successCount} 个，失败 ${failCount} 个`)
  loadTerms()
  loadCategories()
}

const resetForm = () => {
  editingId.value = null
  termForm.value = {
    source_term: '',
    target_term: '',
    literary_type: props.literaryType || 'general',
    category: '',
    source_lang: props.sourceLang || 'en',
    target_lang: props.targetLang || 'zh',
    description: ''
  }
}

const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    poetry: '诗歌',
    prose: '散文',
    novel: '小说',
    drama: '戏剧',
    general: '一般'
  }
  return labels[type] || type
}

// 监听
watch(() => props.literaryType, () => {
  loadTerms()
  loadCategories()
})

watch(showAddDialog, (val) => {
  if (!val) {
    resetForm()
  }
})

// 暴露方法给父组件
defineExpose({
  refresh: loadTerms,
  addTerm: (source: string, target: string) => {
    termForm.value.source_term = source
    termForm.value.target_term = target
    showAddDialog.value = true
  }
})

onMounted(() => {
  loadTerms()
  loadCategories()
})
</script>

<style scoped lang="scss">
.term-library-panel {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  height: 100%;
  display: flex;
  flex-direction: column;

  .panel-header {
    padding: 16px 20px;
    border-bottom: 1px solid #ebeef5;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-title {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 16px;
      font-weight: 600;
      color: #303133;

      .el-icon {
        font-size: 20px;
        color: #409eff;
      }
    }

    .header-actions {
      display: flex;
      gap: 10px;
      align-items: center;

      .search-input {
        width: 180px;
      }
    }
  }

  .category-tags {
    padding: 12px 20px;
    border-bottom: 1px solid #ebeef5;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;

    .category-tag {
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        transform: translateY(-1px);
      }
    }
  }

  .terms-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px;

    .term-card {
      background: #f5f7fa;
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 8px;
      position: relative;
      transition: all 0.2s;
      border: 1px solid transparent;

      &:hover {
        background: #e8f4ff;
        border-color: #409eff;
        transform: translateX(4px);
      }

      &.is-editing {
        border-color: #409eff;
        background: #e8f4ff;
      }

      .term-main {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;

        .term-source,
        .term-target {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 8px;

          .term-text {
            font-size: 14px;
            font-weight: 500;
          }

          .lang-tag {
            font-size: 11px;
          }
        }

        .term-source .term-text {
          color: #606266;
        }

        .term-target .term-text {
          color: #409eff;
        }

        .term-arrow {
          color: #c0c4cc;
        }
      }

      .term-meta {
        display: flex;
        align-items: center;
        gap: 12px;

        .usage-count {
          font-size: 12px;
          color: #909399;
          display: flex;
          align-items: center;
          gap: 4px;

          .el-icon {
            font-size: 14px;
          }
        }
      }

      .term-actions {
        position: absolute;
        top: 8px;
        right: 8px;
        display: flex;
        gap: 4px;
      }
    }
  }

  .panel-footer {
    padding: 12px 20px;
    border-top: 1px solid #ebeef5;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .stats-text {
      font-size: 13px;
      color: #909399;
    }
  }
}
</style>
