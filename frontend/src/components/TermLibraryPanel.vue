<template>
  <div class="term-panel">
    <div class="panel-toolbar">
      <el-select
        v-if="scope === 'global'"
        v-model="projectType"
        size="small"
        clearable
        placeholder="项目分类"
        class="type-select"
      >
        <el-option-group label="文学">
          <el-option label="一般" value="general" />
          <el-option label="诗歌" value="poetry" />
          <el-option label="散文" value="prose" />
          <el-option label="小说" value="novel" />
          <el-option label="戏剧" value="drama" />
        </el-option-group>
        <el-option-group label="专业">
          <el-option label="科技" value="tech" />
          <el-option label="商业" value="business" />
          <el-option label="贸易" value="trade" />
          <el-option label="法律" value="legal" />
          <el-option label="医学" value="medical" />
        </el-option-group>
      </el-select>
      <el-input
        v-model="searchQuery"
        placeholder="搜索源词、译文或说明..."
        size="small"
        clearable
        class="search-input"
      >
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" size="small" class="add-btn" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加
      </el-button>
    </div>

    <div class="category-bar" v-if="categories.length > 0">
      <button
        type="button"
        class="cat-chip"
        :class="{ active: !selectedCategory }"
        @click="selectedCategory = ''"
      >全部</button>
      <button
        v-for="cat in visibleCategories"
        :key="cat"
        type="button"
        class="cat-chip"
        :class="{ active: selectedCategory === cat }"
        @click="selectedCategory = selectedCategory === cat ? '' : cat"
      >{{ cat }}</button>
      <button
        v-if="categories.length > maxVisibleCats && !catsExpanded"
        type="button"
        class="cat-chip is-toggle"
        @click="catsExpanded = true"
      >+{{ categories.length - maxVisibleCats }}</button>
      <button
        v-if="catsExpanded && categories.length > maxVisibleCats"
        type="button"
        class="cat-chip is-toggle"
        @click="catsExpanded = false"
      >收起</button>
    </div>

    <div class="term-list" v-loading="loading">
      <div
        v-for="term in filteredTerms"
        :key="term.id"
        class="term-row"
      >
        <div class="term-main">
          <div class="term-pair">
            <span class="source">{{ term.source_term }}</span>
            <span class="sep" aria-hidden="true">→</span>
            <span class="target">{{ term.target_term }}</span>
          </div>
          <div class="term-extra">
            <el-tag v-if="scope === 'global'" size="small" effect="plain" round>{{ typeLabel(term.literary_type) }}</el-tag>
            <el-tag v-if="term.category" size="small" type="info" effect="plain" round>{{ term.category }}</el-tag>
            <span class="desc" v-if="term.description">{{ term.description }}</span>
          </div>
        </div>
        <div class="term-actions">
          <el-button v-if="scope === 'document'" link size="small" type="success" @click="promoteTerm(term)">入库</el-button>
          <el-button link size="small" @click="startEdit(term)"><el-icon><Edit /></el-icon></el-button>
          <el-button link type="danger" size="small" @click="deleteTerm(term)"><el-icon><Delete /></el-icon></el-button>
        </div>
      </div>

      <el-empty v-if="filteredTerms.length === 0 && !loading" :description="emptyText" :image-size="72" />
    </div>

    <div class="panel-footer">
      <span class="count">{{ filteredTerms.length }} 条词汇</span>
      <span class="footer-hint">{{ scope === 'document' ? '当前文档小词库' : '系统大词库' }}</span>
    </div>

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
            <el-form-item label="项目分类">
              <el-select v-model="termForm.literary_type" style="width: 100%;" :disabled="scope === 'document'">
                <el-option-group label="文学">
                  <el-option label="一般" value="general" />
                  <el-option label="诗歌" value="poetry" />
                  <el-option label="散文" value="prose" />
                  <el-option label="小说" value="novel" />
                  <el-option label="戏剧" value="drama" />
                </el-option-group>
                <el-option-group label="专业">
                  <el-option label="科技" value="tech" />
                  <el-option label="商业" value="business" />
                  <el-option label="贸易" value="trade" />
                  <el-option label="法律" value="legal" />
                  <el-option label="医学" value="medical" />
                </el-option-group>
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

const props = withDefaults(defineProps<{
  scope?: 'document' | 'global'
  translationId?: number
  literaryType?: string
  sourceLang?: string
  targetLang?: string
  reloadToken?: number
}>(), {
  scope: 'global',
  reloadToken: 0,
})

const TYPE_LABELS: Record<string, string> = {
  poetry: '诗歌', prose: '散文', novel: '小说', drama: '戏剧', general: '一般',
  tech: '科技', business: '商业', trade: '贸易', legal: '法律', medical: '医学',
}

const terms = ref<any[]>([])
const categories = ref<string[]>([])
const loading = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const showAddDialog = ref(false)
const searchQuery = ref('')
const selectedCategory = ref('')
const projectType = ref(props.literaryType || '')
const formRef = ref<any>(null)
const catsExpanded = ref(false)
const maxVisibleCats = 6

const visibleCategories = computed(() =>
  catsExpanded.value ? categories.value : categories.value.slice(0, maxVisibleCats)
)

const emptyText = computed(() =>
  props.scope === 'document' ? '当前文档暂无词汇' : '该分类下暂无词汇'
)

const termForm = ref({
  source_term: '',
  target_term: '',
  literary_type: props.literaryType || 'general',
  category: '',
  source_lang: props.sourceLang || 'en',
  target_lang: props.targetLang || 'zh',
  description: '',
})

const isEditing = computed(() => editingId.value !== null)
const rules = {
  source_term: [{ required: true, message: '请输入源词汇', trigger: 'blur' }],
  target_term: [{ required: true, message: '请输入翻译', trigger: 'blur' }],
}

const filteredTerms = computed(() => {
  let result = terms.value
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

const typeLabel = (type: string) => TYPE_LABELS[type] || type

const activeLiteraryType = computed(() =>
  props.scope === 'document' ? props.literaryType : (projectType.value || undefined)
)

const loadTerms = async () => {
  if (props.scope === 'document' && !props.translationId) {
    terms.value = []
    return
  }
  loading.value = true
  try {
    const response = await literaryApi.listTerms({
      scope: props.scope,
      translation_id: props.scope === 'document' ? props.translationId : undefined,
      literary_type: activeLiteraryType.value,
      source_lang: props.scope === 'document' ? props.sourceLang : undefined,
      target_lang: props.scope === 'document' ? props.targetLang : undefined,
      limit: 500,
    })
    terms.value = response.data
  } catch {
    ElMessage.error('加载词汇失败')
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    const response = await literaryApi.getTermCategories({
      scope: props.scope,
      translation_id: props.scope === 'document' ? props.translationId : undefined,
      literary_type: activeLiteraryType.value,
    })
    categories.value = (response.data || []).filter(Boolean)
  } catch { /* ignore */ }
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
    description: term.description || '',
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
        description: termForm.value.description,
      })
      ElMessage.success('已更新')
    } else {
      await literaryApi.createTerm({
        ...termForm.value,
        translation_id: props.scope === 'document' ? props.translationId : undefined,
      })
      ElMessage.success(props.scope === 'document' ? '已加入小词库' : '已加入大词库')
    }
    showAddDialog.value = false
    resetForm()
    loadTerms()
    loadCategories()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

const promoteTerm = async (term: any) => {
  try {
    await ElMessageBox.confirm(`将「${term.source_term}」提升到系统大词库？`, '入库', {
      confirmButtonText: '提升',
      type: 'info',
    })
    await literaryApi.promoteTerm(term.id)
    ElMessage.success('已入库大词库')
    loadTerms()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('提升失败')
  }
}

const deleteTerm = async (term: any) => {
  try {
    await ElMessageBox.confirm(`确定删除「${term.source_term}」？`, '确认', {
      confirmButtonText: '删除',
      type: 'warning',
    })
    await literaryApi.deleteTerm(term.id)
    ElMessage.success('已删除')
    loadTerms()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const resetForm = () => {
  editingId.value = null
  termForm.value = {
    source_term: '',
    target_term: '',
    literary_type: props.literaryType || projectType.value || 'general',
    category: '',
    source_lang: props.sourceLang || 'en',
    target_lang: props.targetLang || 'zh',
    description: '',
  }
}

watch(
  () => [props.scope, props.translationId, props.literaryType, projectType.value, props.reloadToken],
  () => {
    selectedCategory.value = ''
    loadTerms()
    loadCategories()
  }
)
watch(showAddDialog, (val) => { if (!val) resetForm() })

defineExpose({
  refresh: loadTerms,
  addTerm: (source: string, target: string) => {
    termForm.value.source_term = source
    termForm.value.target_term = target
    showAddDialog.value = true
  },
})

onMounted(() => {
  projectType.value = props.literaryType || ''
  loadTerms()
  loadCategories()
})
</script>

<style scoped lang="scss">
.term-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.panel-toolbar {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 0 0 12px;
  flex-shrink: 0;

  .type-select {
    width: 132px;
    flex-shrink: 0;
  }

  .search-input {
    flex: 1;
    min-width: 0;
  }

  .add-btn {
    flex-shrink: 0;
  }
}

.category-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding-bottom: 12px;
  flex-shrink: 0;
}

.cat-chip {
  border: 1px solid var(--ins-line-strong, var(--ins-line));
  background: transparent;
  color: var(--ins-muted);
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;

  &:hover {
    color: var(--ins-ink);
    border-color: rgba(var(--ins-primary-rgb), 0.35);
  }

  &.active {
    color: #fff;
    background: var(--el-color-primary);
    border-color: var(--el-color-primary);
  }

  &.is-toggle {
    border-style: dashed;
  }
}

.term-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding-right: 2px;
}

.term-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 12px;
  border-radius: 10px;
  border: 1px solid transparent;
  transition: background 0.15s, border-color 0.15s;

  & + .term-row {
    margin-top: 2px;
  }

  &:hover {
    background: rgba(var(--ins-primary-rgb), 0.05);
    border-color: rgba(var(--ins-primary-rgb), 0.12);

    .term-actions {
      opacity: 1;
    }
  }
}

.term-main {
  flex: 1;
  min-width: 0;
}

.term-pair {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 15px;
  line-height: 1.4;

  .source {
    font-weight: 600;
    color: var(--ins-ink);
  }

  .sep {
    color: var(--ins-muted);
    font-size: 12px;
    flex-shrink: 0;
  }

  .target {
    color: var(--el-color-primary);
    font-weight: 700;
  }
}

.term-extra {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  min-width: 0;

  .desc {
    font-size: 12px;
    color: var(--ins-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.term-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  opacity: 0.35;
  transition: opacity 0.15s;
  padding-top: 2px;
}

.panel-footer {
  padding: 12px 2px 0;
  margin-top: 8px;
  border-top: 1px solid var(--ins-line);
  font-size: 12px;
  color: var(--ins-muted);
  display: flex;
  justify-content: space-between;
  flex-shrink: 0;

  .count {
    font-weight: 600;
    color: var(--ins-ink);
  }

  .footer-hint {
    color: var(--ins-muted);
  }
}

@media (max-width: 640px) {
  .term-actions {
    opacity: 1;
  }

  .panel-toolbar {
    flex-wrap: wrap;

    .type-select,
    .search-input,
    .add-btn {
      width: 100%;
    }
  }
}
</style>
