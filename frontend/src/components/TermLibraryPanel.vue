<template>
  <div class="term-panel">
    <!-- 搜索 + 添加 -->
    <div class="panel-toolbar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索词汇..."
        size="small"
        clearable
        class="search-input"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" size="small" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
      </el-button>
    </div>

    <!-- 分类筛选 -->
    <div class="category-bar" v-if="categories.length > 0">
      <el-tag
        v-for="cat in visibleCategories"
        :key="cat"
        :effect="selectedCategory === cat ? 'dark' : 'plain'"
        :type="selectedCategory === cat ? 'primary' : 'info'"
        size="small"
        round
        class="cat-tag"
        @click="selectedCategory = selectedCategory === cat ? '' : cat"
      >{{ cat }}</el-tag>
      <el-tag
        v-if="categories.length > maxVisibleCats && !catsExpanded"
        size="small"
        type="info"
        effect="plain"
        round
        class="cat-tag cat-toggle"
        @click="catsExpanded = true"
      >+{{ categories.length - maxVisibleCats }} 更多</el-tag>
      <el-tag
        v-if="catsExpanded && categories.length > maxVisibleCats"
        size="small"
        type="info"
        effect="plain"
        round
        class="cat-tag cat-toggle"
        @click="catsExpanded = false"
      >收起</el-tag>
    </div>

    <!-- 词汇列表 -->
    <div class="term-list" v-loading="loading">
      <div
        v-for="term in filteredTerms"
        :key="term.id"
        class="term-row"
        @mouseenter="hoveredTerm = term.id"
        @mouseleave="hoveredTerm = null"
      >
        <div class="term-pair">
          <span class="source">{{ term.source_term }}</span>
          <span class="sep">→</span>
          <span class="target">{{ term.target_term }}</span>
        </div>
        <div class="term-extra">
          <el-tag v-if="term.category" size="small" type="info" effect="plain" round>{{ term.category }}</el-tag>
          <span class="desc" v-if="term.description">{{ term.description }}</span>
        </div>
        <div class="term-actions" v-show="hoveredTerm === term.id">
          <el-button link size="small" @click="startEdit(term)"><el-icon><Edit /></el-icon></el-button>
          <el-button link type="danger" size="small" @click="deleteTerm(term)"><el-icon><Delete /></el-icon></el-button>
        </div>
      </div>

      <el-empty v-if="filteredTerms.length === 0 && !loading" description="暂无词汇" :image-size="60" />
    </div>

    <!-- 底栏 -->
    <div class="panel-footer">
      <span>{{ filteredTerms.length }} 条词汇</span>
    </div>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="showAddDialog" :title="isEditing ? '编辑词汇' : '添加词汇'" width="480px" destroy-on-close>
      <el-form :model="termForm" label-position="top" :rules="rules" ref="formRef">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="源词汇" prop="source_term">
              <el-input v-model="termForm.source_term" placeholder="源语言词汇" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="翻译" prop="target_term">
              <el-input v-model="termForm.target_term" placeholder="目标语言翻译" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="文学类型">
              <el-select v-model="termForm.literary_type" style="width: 100%;">
                <el-option label="一般" value="general" />
                <el-option label="诗歌" value="poetry" />
                <el-option label="散文" value="prose" />
                <el-option label="小说" value="novel" />
                <el-option label="戏剧" value="drama" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类">
              <el-select v-model="termForm.category" placeholder="选择或输入" allow-create filterable clearable style="width: 100%;">
                <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="说明（选填）">
          <el-input v-model="termForm.description" type="textarea" :rows="2" placeholder="词汇说明或使用语境" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTerm" :loading="saving">{{ isEditing ? '保存' : '添加' }}</el-button>
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

const terms = ref<any[]>([])
const categories = ref<string[]>([])
const loading = ref(false)
const saving = ref(false)
const hoveredTerm = ref<number | null>(null)
const editingId = ref<number | null>(null)
const showAddDialog = ref(false)
const searchQuery = ref('')
const selectedCategory = ref('')
const formRef = ref<any>(null)
const catsExpanded = ref(false)
const maxVisibleCats = 6

const visibleCategories = computed(() =>
  catsExpanded.value ? categories.value : categories.value.slice(0, maxVisibleCats)
)

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

const filteredTerms = computed(() => {
  let result = terms.value
  if (props.literaryType) result = result.filter(t => t.literary_type === props.literaryType)
  if (selectedCategory.value) result = result.filter(t => t.category === selectedCategory.value)
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(t =>
      t.source_term.toLowerCase().includes(q) ||
      t.target_term.toLowerCase().includes(q) ||
      (t.description && t.description.toLowerCase().includes(q))
    )
  }
  return result.sort((a: any, b: any) => b.usage_count - a.usage_count)
})

const loadTerms = async () => {
  loading.value = true
  try {
    const response = await literaryApi.listTerms({ literary_type: props.literaryType, source_lang: props.sourceLang, target_lang: props.targetLang, limit: 500 })
    terms.value = response.data
  } catch { ElMessage.error('加载词汇失败') }
  finally { loading.value = false }
}

const loadCategories = async () => {
  try {
    const response = await literaryApi.getTermCategories({ literary_type: props.literaryType })
    categories.value = response.data
  } catch { /* ignore */ }
}

const startEdit = (term: any) => {
  editingId.value = term.id
  termForm.value = { source_term: term.source_term, target_term: term.target_term, literary_type: term.literary_type, category: term.category || '', source_lang: term.source_lang, target_lang: term.target_lang, description: term.description || '' }
  showAddDialog.value = true
}

const saveTerm = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEditing.value && editingId.value) {
      await literaryApi.updateTerm(editingId.value, { target_term: termForm.value.target_term, category: termForm.value.category, description: termForm.value.description })
      ElMessage.success('已更新')
    } else {
      await literaryApi.createTerm(termForm.value)
      ElMessage.success('已添加')
    }
    showAddDialog.value = false
    resetForm()
    loadTerms()
    loadCategories()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally { saving.value = false }
}

const deleteTerm = async (term: any) => {
  try {
    await ElMessageBox.confirm(`确定删除「${term.source_term}」？`, '确认', { confirmButtonText: '删除', type: 'warning' })
    await literaryApi.deleteTerm(term.id)
    ElMessage.success('已删除')
    loadTerms()
  } catch (e: any) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

const resetForm = () => {
  editingId.value = null
  termForm.value = { source_term: '', target_term: '', literary_type: props.literaryType || 'general', category: '', source_lang: props.sourceLang || 'en', target_lang: props.targetLang || 'zh', description: '' }
}

watch(() => props.literaryType, () => { loadTerms(); loadCategories() })
watch(showAddDialog, (val) => { if (!val) resetForm() })

defineExpose({
  refresh: loadTerms,
  addTerm: (source: string, target: string) => { termForm.value.source_term = source; termForm.value.target_term = target; showAddDialog.value = true }
})

onMounted(() => { loadTerms(); loadCategories() })
</script>

<style scoped lang="scss">
.term-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-toolbar {
  display: flex;
  gap: 8px;
  padding: 0 0 12px;
  .search-input { flex: 1; }
}

.category-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-bottom: 12px;

  .cat-tag {
    cursor: pointer;
    transition: all 0.15s;
  }

  .cat-toggle {
    color: #909399;
    border-style: dashed;
  }
}

.term-list {
  flex: 1;
  overflow-y: auto;
  margin: 0 -4px;
  padding: 0 4px;
}

.term-row {
  padding: 10px 12px;
  border-radius: 8px;
  position: relative;
  transition: background 0.15s;

  &:hover { background: #f5f7fa; }

  & + .term-row { border-top: 1px solid #f0f0f0; }

  .term-pair {
    display: flex;
    align-items: baseline;
    gap: 8px;
    font-size: 14px;

    .source { font-weight: 500; color: #303133; }
    .sep { color: #c0c4cc; font-size: 12px; flex-shrink: 0; }
    .target { color: #409eff; font-weight: 500; }
  }

  .term-extra {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-top: 4px;

    .desc {
      font-size: 12px;
      color: #999;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }

  .term-actions {
    position: absolute;
    top: 8px;
    right: 8px;
    display: flex;
    gap: 2px;
    background: #f5f7fa;
    border-radius: 4px;
    padding: 2px;
  }
}

.panel-footer {
  padding: 10px 0 0;
  border-top: 1px solid #f0f0f0;
  font-size: 12px;
  color: #999;
}
</style>
