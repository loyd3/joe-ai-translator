<template>
  <div class="document-library">
    <div class="page-header">
      <el-button class="back-btn" @click="emit('back')">
        <el-icon><ArrowLeft /></el-icon>
        返回
      </el-button>
      <h1 class="title">文档库</h1>
      <span class="subtitle">浏览、分组与管理全部翻译文档</span>
    </div>

    <div class="page-body">
      <div class="toolbar">
        <el-input
          v-model="keyword"
          clearable
          placeholder="搜索标题"
          class="search-input"
          @keyup.enter="onFilterChange"
          @clear="onFilterChange"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-radio-group v-model="category" size="small" @change="onFilterChange">
          <el-radio-button label="all">全部</el-radio-button>
          <el-radio-button label="literary">文学</el-radio-button>
          <el-radio-button label="professional">专业</el-radio-button>
        </el-radio-group>
        <el-select
          v-model="selectedGroup"
          clearable
          filterable
          placeholder="全部分组"
          class="group-select"
          size="small"
          @change="onFilterChange"
        >
          <el-option label="全部分组" value="" />
          <el-option label="未分组" value="__ungrouped__" />
          <el-option
            v-for="g in namedGroups"
            :key="g.name"
            :label="`${g.name} (${g.count})`"
            :value="g.name"
          />
        </el-select>
        <el-button size="small" @click="showGroupManager = true">管理分组</el-button>
        <el-button size="small" @click="reloadAll" :loading="loading">刷新</el-button>
      </div>

      <div class="bulk-bar" v-if="selectedRows.length > 0">
        <span>已选 {{ selectedRows.length }} 项</span>
        <el-select
          v-model="bulkGroupName"
          clearable
          filterable
          allow-create
          default-first-option
          size="small"
          placeholder="目标分组"
          class="bulk-group-select"
        >
          <el-option label="未分组" value="" />
          <el-option v-for="g in namedGroups" :key="g.name" :label="g.name" :value="g.name" />
        </el-select>
        <el-button size="small" type="primary" :loading="bulkSaving" @click="submitBulkAssign">
          批量改分组
        </el-button>
      </div>

      <div class="table-wrap" v-loading="loading">
        <el-table
          :data="items"
          stripe
          style="width: 100%"
          empty-text="暂无文档"
          height="100%"
          @selection-change="onSelectionChange"
        >
          <el-table-column type="selection" width="44" />
          <el-table-column prop="title" label="标题" min-width="200">
            <template #default="{ row }">
              <button class="title-link" type="button" @click="openDoc(row)">
                {{ row.title || `任务 #${row.id}` }}
              </button>
            </template>
          </el-table-column>
          <el-table-column label="分组" width="120">
            <template #default="{ row }">
              <el-tag v-if="row.group_name" size="small" type="info" effect="plain" round>
                {{ row.group_name }}
              </el-tag>
              <span v-else class="muted">未分组</span>
            </template>
          </el-table-column>
          <el-table-column label="类型" width="90">
            <template #default="{ row }">
              <el-tag
                size="small"
                :type="isLiteraryType(row.literary_type) ? '' : 'warning'"
                effect="plain"
                round
              >
                {{ getTypeName(row.literary_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="getStatusType(row.status)">
                {{ getStatusText(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="语言" width="110">
            <template #default="{ row }">
              <span class="muted">{{ row.source_lang }} → {{ row.target_lang }}</span>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" width="160">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openDoc(row)">打开</el-button>
              <el-button link @click="openEdit(row)">改分组</el-button>
              <el-button link type="danger" @click="removeDoc(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pager" v-if="total > 0">
        <el-pagination
          background
          layout="total, prev, pager, next, sizes"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          :page-sizes="[10, 20, 50]"
          @current-change="onPageChange"
          @size-change="onSizeChange"
        />
      </div>
    </div>

    <el-dialog v-model="showEdit" title="修改分组" width="400px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" maxlength="200" />
        </el-form-item>
        <el-form-item label="分组">
          <el-select
            v-model="editForm.group_name"
            style="width: 100%;"
            filterable
            allow-create
            clearable
            default-first-option
            placeholder="选择或输入分组名"
          >
            <el-option v-for="g in namedGroups" :key="g.name" :label="g.name" :value="g.name" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <GroupManagerDialog v-model="showGroupManager" @changed="onGroupsChanged" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, Search } from '@element-plus/icons-vue'
import { literaryApi } from '@/api'
import GroupManagerDialog from '@/components/GroupManagerDialog.vue'

const emit = defineEmits<{
  back: []
  open: [task: any]
  changed: []
}>()

const LITERARY_TYPES = new Set(['poetry', 'prose', 'novel', 'drama', 'general'])
const TYPE_LABELS: Record<string, string> = {
  poetry: '诗歌', prose: '散文', novel: '小说', drama: '戏剧', general: '一般',
  tech: '科技', business: '商业', trade: '贸易', legal: '法律', medical: '医学',
}

const loading = ref(false)
const saving = ref(false)
const bulkSaving = ref(false)
const items = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const category = ref('all')
const selectedGroup = ref('')
const groupOptions = ref<Array<{ id?: number | null; name: string; count: number }>>([])
const showEdit = ref(false)
const showGroupManager = ref(false)
const editing = ref<any>(null)
const editForm = ref({ title: '', group_name: '' })
const selectedRows = ref<any[]>([])
const bulkGroupName = ref('')

const namedGroups = computed(() => groupOptions.value.filter((g) => g.name))

const getTypeName = (type: string) => TYPE_LABELS[type] || type
const isLiteraryType = (type: string) => LITERARY_TYPES.has(type || 'general')
const getStatusType = (status: string) =>
  ({ pending: 'info', translating: 'warning', verifying: 'warning', revising: 'warning', finalizing: 'warning', completed: 'success', failed: 'danger' } as Record<string, string>)[status] || 'info'
const getStatusText = (status: string) =>
  ({ pending: '待开始', translating: '翻译中', verifying: '校验中', revising: '润色中', finalizing: '定稿勘误中', completed: '已完成', failed: '失败' } as Record<string, string>)[status] || status

const formatDate = (value?: string) => {
  if (!value) return '-'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}

const buildParams = () => {
  const params: Record<string, string | number> = {
    skip: (page.value - 1) * pageSize.value,
    limit: pageSize.value,
  }
  if (category.value !== 'all') params.category = category.value
  if (selectedGroup.value) params.group_name = selectedGroup.value
  if (keyword.value.trim()) params.q = keyword.value.trim()
  return params
}

const loadGroups = async () => {
  try {
    const response = await literaryApi.listTranslationGroups({
      category: category.value !== 'all' ? category.value : undefined,
    })
    groupOptions.value = response.data || []
  } catch {
    groupOptions.value = []
  }
}

const loadList = async () => {
  loading.value = true
  try {
    const response = await literaryApi.listTranslations(buildParams())
    items.value = response.data.items || []
    total.value = response.data.total || 0
  } catch {
    ElMessage.error('加载文档失败')
  } finally {
    loading.value = false
  }
}

const reloadAll = async () => {
  await loadGroups()
  await loadList()
}

const onGroupsChanged = async () => {
  await reloadAll()
  if (
    selectedGroup.value &&
    selectedGroup.value !== '__ungrouped__' &&
    !namedGroups.value.some((g) => g.name === selectedGroup.value)
  ) {
    selectedGroup.value = ''
    await loadList()
  }
  emit('changed')
}

const onSelectionChange = (rows: any[]) => {
  selectedRows.value = rows
}

const submitBulkAssign = async () => {
  if (!selectedRows.value.length) return
  bulkSaving.value = true
  try {
    const ids = selectedRows.value.map((r) => r.id)
    const name = bulkGroupName.value?.trim() || null
    await literaryApi.bulkAssignTranslationGroup(ids, name)
    ElMessage.success(`已更新 ${ids.length} 篇文档分组`)
    selectedRows.value = []
    bulkGroupName.value = ''
    await reloadAll()
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '批量改分组失败')
  } finally {
    bulkSaving.value = false
  }
}

const onFilterChange = async () => {
  page.value = 1
  await reloadAll()
}

const onPageChange = async (p: number) => {
  page.value = p
  await loadList()
}

const onSizeChange = async (size: number) => {
  pageSize.value = size
  page.value = 1
  await loadList()
}

const openDoc = (row: any) => {
  emit('open', row)
}

const openEdit = (row: any) => {
  editing.value = row
  editForm.value = {
    title: row.title || '',
    group_name: row.group_name || '',
  }
  showEdit.value = true
}

const submitEdit = async () => {
  if (!editing.value) return
  saving.value = true
  try {
    await literaryApi.updateTranslation(editing.value.id, {
      title: editForm.value.title || undefined,
      group_name: editForm.value.group_name?.trim() || null,
    })
    ElMessage.success('已保存')
    showEdit.value = false
    editing.value = null
    await reloadAll()
    emit('changed')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const removeDoc = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title || `任务 #${row.id}`}」？`, '删除确认', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await literaryApi.deleteTranslation(row.id)
    ElMessage.success('已删除')
    if (items.value.length === 1 && page.value > 1) {
      page.value -= 1
    }
    await reloadAll()
    emit('changed')
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

onMounted(reloadAll)
</script>

<style scoped lang="scss">
.document-library {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
  min-height: 0;
  color: var(--ins-ink);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 24px 12px;
  flex-shrink: 0;

  .back-btn {
    flex-shrink: 0;
  }

  .title {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
  }

  .subtitle {
    font-size: 13px;
    color: var(--ins-muted);
    font-weight: 500;
  }
}

.page-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0 24px 20px;
  gap: 12px;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  flex-shrink: 0;

  .search-input {
    width: 220px;
  }

  .group-select {
    width: 160px;
  }
}

.bulk-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  padding: 8px 12px;
  border: 1px solid var(--ins-line);
  border-radius: 10px;
  background: rgba(var(--ins-primary-rgb), 0.06);
  font-size: 13px;

  .bulk-group-select {
    width: 180px;
  }
}

.table-wrap {
  flex: 1;
  min-height: 0;
  background: var(--ins-surface, rgba(255, 255, 255, 0.72));
  border: 1px solid var(--ins-line);
  border-radius: 14px;
  overflow: hidden;
  padding: 4px;
}

.title-link {
  border: 0;
  background: transparent;
  color: var(--ins-ink);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  text-align: left;

  &:hover {
    color: var(--el-color-primary);
  }
}

.muted {
  color: var(--ins-muted);
  font-size: 13px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .page-header {
    padding: 12px 16px;
    flex-wrap: wrap;
  }

  .page-body {
    padding: 0 16px 16px;
  }

  .toolbar .search-input,
  .toolbar .group-select {
    width: 100%;
  }
}
</style>
