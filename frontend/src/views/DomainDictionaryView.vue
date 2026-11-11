<template>
  <div class="domain-dict-view">
    <div class="page-header">
      <el-button class="back-btn" @click="emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <div class="header-text">
        <h1 class="title">专业词典</h1>
        <span class="subtitle">外部导入的权威词表，翻译时优先于经验词库命中</span>
      </div>
      <el-button type="primary" size="small" @click="openCreate">新建词典</el-button>
    </div>

    <div class="page-body">
      <div class="filters">
        <el-input v-model="keyword" clearable placeholder="搜索词典名" style="width: 200px" @change="loadList" />
        <el-select v-model="filterType" clearable placeholder="领域" style="width: 140px" @change="loadList">
          <el-option-group v-for="g in typeGroups" :key="g.label" :label="g.label">
            <el-option v-for="opt in g.options" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-option-group>
        </el-select>
        <el-button @click="loadList">刷新</el-button>
      </div>

      <el-table :data="dictionaries" v-loading="loading" stripe empty-text="暂无专业词典，可新建或导入 CSV/XLSX">
        <el-table-column prop="name" label="名称" min-width="140" />
        <el-table-column label="领域" width="100">
          <template #default="{ row }">{{ typeLabel(row.literary_type) }}</template>
        </el-table-column>
        <el-table-column label="语言对" width="110">
          <template #default="{ row }">{{ row.source_lang }} → {{ row.target_lang }}</template>
        </el-table-column>
        <el-table-column prop="term_count" label="词条" width="80" />
        <el-table-column label="默认挂载" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_default_for_domain ? 'success' : 'info'" effect="plain">
              {{ row.is_default_for_domain ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">词条</el-button>
            <el-button link @click="openEdit(row)">编辑</el-button>
            <el-button link @click="triggerImport(row)">导入</el-button>
            <el-button link type="danger" @click="removeDict(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showForm" :title="editing ? '编辑词典' : '新建词典'" width="520px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" maxlength="200" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="领域">
          <el-select v-model="form.literary_type" clearable placeholder="空=通用" style="width: 100%">
            <el-option-group v-for="g in typeGroups" :key="g.label" :label="g.label">
              <el-option v-for="opt in g.options" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="源语言" required>
              <el-select v-model="form.source_lang" style="width: 100%">
                <el-option v-for="l in languages" :key="l.code" :label="l.name" :value="l.code" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="目标语言" required>
              <el-select v-model="form.target_lang" style="width: 100%">
                <el-option v-for="l in languages.filter(x => x.code !== 'auto')" :key="l.code" :label="l.name" :value="l.code" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item>
          <el-checkbox v-model="form.is_default_for_domain">该领域+语言对新建任务时默认挂载</el-checkbox>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.is_active">启用</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDetail" :title="current ? `词条 · ${current.name}` : '词条'" width="720px" destroy-on-close>
      <div class="detail-toolbar">
        <el-input v-model="termKeyword" clearable placeholder="搜索词条" style="width: 200px" @change="loadTerms" />
        <el-button size="small" @click="showAddTerm = true">添加词条</el-button>
        <el-button size="small" @click="triggerImport(current!)">导入 CSV/XLSX</el-button>
      </div>
      <el-table :data="terms" v-loading="termsLoading" height="360" stripe>
        <el-table-column prop="source_term" label="原文" min-width="140" />
        <el-table-column prop="target_term" label="译名" min-width="140" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button link type="danger" @click="removeTerm(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="showAddTerm" title="添加词条" width="420px" destroy-on-close>
      <el-form :model="termForm" label-position="top">
        <el-form-item label="原文" required>
          <el-input v-model="termForm.source_term" />
        </el-form-item>
        <el-form-item label="译名" required>
          <el-input v-model="termForm.target_term" />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="termForm.category" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddTerm = false">取消</el-button>
        <el-button type="primary" :loading="savingTerm" @click="addTerm">添加</el-button>
      </template>
    </el-dialog>

    <input ref="fileInput" type="file" accept=".csv,.xlsx" style="display:none" @change="onImportFile" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { domainDictionaryApi } from '@/api'

const emit = defineEmits<{ back: [] }>()

const typeGroups = [
  { label: '文学', options: [
    { value: 'poetry', label: '诗歌' }, { value: 'prose', label: '散文' },
    { value: 'novel', label: '小说' }, { value: 'drama', label: '戏剧' }, { value: 'general', label: '一般文学' },
  ]},
  { label: '专业', options: [
    { value: 'tech', label: '科技' }, { value: 'business', label: '商业' },
    { value: 'trade', label: '贸易' }, { value: 'legal', label: '法律' }, { value: 'medical', label: '医学' },
  ]},
]
const languages = [
  { code: 'auto', name: '自动检测' },
  { code: 'en', name: '英语' }, { code: 'zh', name: '中文' },
  { code: 'ja', name: '日语' }, { code: 'ko', name: '韩语' },
  { code: 'fr', name: '法语' }, { code: 'de', name: '德语' },
  { code: 'es', name: '西班牙语' }, { code: 'ru', name: '俄语' },
]

const typeLabel = (t?: string | null) => {
  if (!t) return '通用'
  for (const g of typeGroups) {
    const hit = g.options.find((o) => o.value === t)
    if (hit) return hit.label
  }
  return t
}

const loading = ref(false)
const dictionaries = ref<any[]>([])
const keyword = ref('')
const filterType = ref<string | undefined>()

const showForm = ref(false)
const editing = ref<any | null>(null)
const saving = ref(false)
const form = ref({
  name: '',
  description: '',
  literary_type: '' as string,
  source_lang: 'en',
  target_lang: 'zh',
  is_default_for_domain: true,
  is_active: true,
})

const showDetail = ref(false)
const current = ref<any | null>(null)
const terms = ref<any[]>([])
const termsLoading = ref(false)
const termKeyword = ref('')
const showAddTerm = ref(false)
const savingTerm = ref(false)
const termForm = ref({ source_term: '', target_term: '', category: '' })

const fileInput = ref<HTMLInputElement | null>(null)
const importTargetId = ref<number | null>(null)

async function loadList() {
  loading.value = true
  try {
    const res = await domainDictionaryApi.list({
      keyword: keyword.value || undefined,
      literary_type: filterType.value || undefined,
    })
    dictionaries.value = res.data || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.value = {
    name: '',
    description: '',
    literary_type: '',
    source_lang: 'en',
    target_lang: 'zh',
    is_default_for_domain: true,
    is_active: true,
  }
  showForm.value = true
}

function openEdit(row: any) {
  editing.value = row
  form.value = {
    name: row.name,
    description: row.description || '',
    literary_type: row.literary_type || '',
    source_lang: row.source_lang,
    target_lang: row.target_lang,
    is_default_for_domain: !!row.is_default_for_domain,
    is_active: row.is_active !== false,
  }
  showForm.value = true
}

async function saveForm() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.value.name.trim(),
      description: form.value.description || undefined,
      literary_type: form.value.literary_type || null,
      source_lang: form.value.source_lang,
      target_lang: form.value.target_lang,
      is_default_for_domain: form.value.is_default_for_domain,
      is_active: form.value.is_active,
    }
    if (editing.value) {
      await domainDictionaryApi.update(editing.value.id, payload)
      ElMessage.success('已更新')
    } else {
      await domainDictionaryApi.create(payload)
      ElMessage.success('已创建')
    }
    showForm.value = false
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function removeDict(row: any) {
  try {
    await ElMessageBox.confirm(`删除词典「${row.name}」及其全部词条？`, '确认删除', { type: 'warning' })
    await domainDictionaryApi.remove(row.id)
    ElMessage.success('已删除')
    await loadList()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

async function openDetail(row: any) {
  current.value = row
  termKeyword.value = ''
  showDetail.value = true
  await loadTerms()
}

async function loadTerms() {
  if (!current.value) return
  termsLoading.value = true
  try {
    const res = await domainDictionaryApi.listTerms(current.value.id, {
      keyword: termKeyword.value || undefined,
      limit: 200,
    })
    terms.value = res.data || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '加载词条失败')
  } finally {
    termsLoading.value = false
  }
}

async function addTerm() {
  if (!current.value) return
  if (!termForm.value.source_term.trim() || !termForm.value.target_term.trim()) {
    ElMessage.warning('请填写原文和译名')
    return
  }
  savingTerm.value = true
  try {
    await domainDictionaryApi.createTerm(current.value.id, {
      source_term: termForm.value.source_term.trim(),
      target_term: termForm.value.target_term.trim(),
      category: termForm.value.category || undefined,
    })
    ElMessage.success('已添加')
    showAddTerm.value = false
    termForm.value = { source_term: '', target_term: '', category: '' }
    await loadTerms()
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '添加失败')
  } finally {
    savingTerm.value = false
  }
}

async function removeTerm(row: any) {
  if (!current.value) return
  try {
    await domainDictionaryApi.deleteTerm(current.value.id, row.id)
    ElMessage.success('已删除')
    await loadTerms()
    await loadList()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  }
}

function triggerImport(row: any) {
  importTargetId.value = row.id
  fileInput.value?.click()
}

async function onImportFile(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file || !importTargetId.value) return
  try {
    const { value } = await ElMessageBox.confirm(
      '重复源词如何处理？',
      '导入词典',
      {
        distinguishCancelAndClose: true,
        confirmButtonText: '跳过重复',
        cancelButtonText: '覆盖重复',
        type: 'info',
      },
    ).then(() => ({ value: 'skip' as const })).catch((action) => {
      if (action === 'cancel') return { value: 'overwrite' as const }
      throw action
    })
    const res = await domainDictionaryApi.importFile(importTargetId.value, file, value)
    const d = res.data || {}
    ElMessage.success(`导入完成：新增 ${d.created || 0}，更新 ${d.updated || 0}，跳过 ${d.skipped || 0}`)
    await loadList()
    if (showDetail.value && current.value?.id === importTargetId.value) await loadTerms()
  } catch (e: any) {
    if (e !== 'close') ElMessage.error(e?.response?.data?.detail || '导入失败')
  }
}

onMounted(loadList)
</script>

<style scoped>
.domain-dict-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px 24px;
  box-sizing: border-box;
}
.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.header-text { flex: 1; }
.title { margin: 0; font-size: 22px; font-weight: 650; }
.subtitle { color: var(--el-text-color-secondary); font-size: 13px; }
.page-body { flex: 1; overflow: auto; }
.filters {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.detail-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
</style>
