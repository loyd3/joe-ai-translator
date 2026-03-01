<template>
  <div class="term-library-manager">
    <div class="manager-header">
      <div class="header-left">
        <h3>专业词库</h3>
        <el-tag size="small" type="info">{{ totalTerms }} 个词汇</el-tag>
      </div>
      <div class="header-right">
        <el-button type="primary" size="small" @click="showAddDialog = true">
          <el-icon><Plus /></el-icon>
          添加词汇
        </el-button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-select v-model="filter.literary_type" placeholder="文学类型" clearable size="small" style="width: 120px;">
        <el-option label="诗歌" value="poetry" />
        <el-option label="散文" value="prose" />
        <el-option label="小说" value="novel" />
        <el-option label="戏剧" value="drama" />
        <el-option label="一般" value="general" />
      </el-select>
      <el-select v-model="filter.category" placeholder="分类" clearable size="small" style="width: 120px;">
        <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
      </el-select>
      <el-input v-model="filter.keyword" placeholder="搜索词汇..." clearable size="small" style="width: 200px;">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button size="small" @click="loadTerms">刷新</el-button>
    </div>

    <!-- 词汇列表 -->
    <el-table :data="terms" style="width: 100%" v-loading="loading" size="small">
      <el-table-column type="index" width="50" />
      <el-table-column prop="source_term" label="源词汇" min-width="150" show-overflow-tooltip />
      <el-table-column prop="target_term" label="翻译" min-width="150" show-overflow-tooltip />
      <el-table-column prop="category" label="分类" width="120">
        <template #default="{ row }">
          <el-tag v-if="row.category" size="small" type="info">{{ row.category }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="usage_count" label="使用次数" width="90" align="center" />
      <el-table-column label="操作" width="120" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="editTerm(row)">编辑</el-button>
          <el-button link type="danger" size="small" @click="deleteTerm(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="showAddDialog" :title="editingTerm ? '编辑词汇' : '添加词汇'" width="500px">
      <el-form :model="termForm" label-position="top">
        <el-form-item label="源词汇">
          <el-input v-model="termForm.source_term" placeholder="输入源语言词汇" />
        </el-form-item>
        <el-form-item label="翻译">
          <el-input v-model="termForm.target_term" placeholder="输入目标语言翻译" />
        </el-form-item>
        <el-form-item label="翻译类型">
          <el-select v-model="termForm.literary_type" style="width: 100%;">
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
        <el-form-item label="分类">
          <el-input v-model="termForm.category" placeholder="可选：词汇分类，如修辞手法、文化词汇等" />
        </el-form-item>
        <el-form-item label="说明/例句">
          <el-input v-model="termForm.description" type="textarea" :rows="3" placeholder="可选：词汇说明或使用例句" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTerm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
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
const totalTerms = ref(0)
const showAddDialog = ref(false)
const editingTerm = ref<any>(null)

const filter = ref({
  literary_type: props.literaryType || '',
  category: '',
  keyword: ''
})

const termForm = ref({
  source_term: '',
  target_term: '',
  literary_type: props.literaryType || 'general',
  category: '',
  source_lang: props.sourceLang || 'en',
  target_lang: props.targetLang || 'zh',
  description: ''
})

const loadTerms = async () => {
  loading.value = true
  try {
    const response = await literaryApi.listTerms({
      literary_type: filter.value.literary_type || undefined,
      category: filter.value.category || undefined,
      keyword: filter.value.keyword || undefined,
      source_lang: props.sourceLang,
      target_lang: props.targetLang,
      limit: 100
    })
    terms.value = response.data
    totalTerms.value = response.data.length
  } catch (error) {
    ElMessage.error('加载词汇失败')
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    const response = await literaryApi.getTermCategories({
      literary_type: filter.value.literary_type || undefined
    })
    categories.value = response.data
  } catch (error) {
    console.error('Failed to load categories:', error)
  }
}

const editTerm = (term: any) => {
  editingTerm.value = term
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
  if (!termForm.value.source_term || !termForm.value.target_term) {
    ElMessage.warning('请输入源词汇和翻译')
    return
  }

  try {
    if (editingTerm.value) {
      await literaryApi.updateTerm(editingTerm.value.id, {
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
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const deleteTerm = async (term: any) => {
  try {
    await ElMessageBox.confirm(`确定要删除 "${term.source_term}" 吗？`, '确认删除', { type: 'warning' })
    await literaryApi.deleteTerm(term.id)
    ElMessage.success('词汇已删除')
    loadTerms()
  } catch (error: any) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const resetForm = () => {
  editingTerm.value = null
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

watch(() => filter.value.literary_type, () => {
  loadCategories()
})

onMounted(() => {
  loadTerms()
  loadCategories()
})
</script>

<style scoped lang="scss">
.term-library-manager {
  .manager-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
      h3 { margin: 0; }
    }
  }
  .filter-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
  }
}
</style>
