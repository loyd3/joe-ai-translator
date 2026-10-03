<template>
  <el-dialog
    :model-value="modelValue"
    title="管理分组"
    width="520px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="group-manager">
      <div class="create-row">
        <el-input
          v-model="newName"
          maxlength="200"
          clearable
          placeholder="输入新分组名称"
          @keyup.enter="createGroup"
        />
        <el-button type="primary" :loading="creating" @click="createGroup">新建</el-button>
      </div>

      <div class="group-list" v-loading="loading">
        <el-empty v-if="!loading && groups.length === 0" description="暂无自定义分组" :image-size="56" />
        <div v-for="g in groups" :key="g.id" class="group-item">
          <template v-if="editingId === g.id">
            <el-input v-model="editingName" maxlength="200" size="small" @keyup.enter="saveRename(g)" />
            <el-button link type="primary" :loading="savingId === g.id" @click="saveRename(g)">保存</el-button>
            <el-button link @click="cancelRename">取消</el-button>
          </template>
          <template v-else>
            <div class="group-main">
              <span class="group-name">{{ g.name }}</span>
              <el-tag size="small" type="info" effect="plain" round>{{ g.count }} 篇</el-tag>
            </div>
            <div class="group-actions">
              <el-button link size="small" @click="startRename(g)">重命名</el-button>
              <el-button link type="danger" size="small" :loading="deletingId === g.id" @click="removeGroup(g)">
                删除
              </el-button>
            </div>
          </template>
        </div>
      </div>
      <p class="hint">删除分组时，该组内文档会变为「未分组」。空组也可预先创建，供新建任务选用。</p>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { literaryApi } from '@/api'

export type GroupItem = {
  id?: number | null
  name: string
  count: number
  sort_order?: number
}

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  changed: []
}>()

const loading = ref(false)
const creating = ref(false)
const groups = ref<GroupItem[]>([])
const newName = ref('')
const editingId = ref<number | null>(null)
const editingName = ref('')
const savingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)

const loadGroups = async () => {
  loading.value = true
  try {
    const res = await literaryApi.listTranslationGroups()
    groups.value = (res.data || []).filter((g) => g.id != null && g.name)
  } catch {
    ElMessage.error('加载分组失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      newName.value = ''
      cancelRename()
      loadGroups()
    }
  }
)

const createGroup = async () => {
  const name = newName.value.trim()
  if (!name) {
    ElMessage.warning('请输入分组名称')
    return
  }
  creating.value = true
  try {
    await literaryApi.createTranslationGroup(name)
    ElMessage.success('已新建分组')
    newName.value = ''
    await loadGroups()
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '新建失败')
  } finally {
    creating.value = false
  }
}

const startRename = (g: GroupItem) => {
  if (!g.id) return
  editingId.value = g.id
  editingName.value = g.name
}

const cancelRename = () => {
  editingId.value = null
  editingName.value = ''
}

const saveRename = async (g: GroupItem) => {
  if (!g.id) return
  const name = editingName.value.trim()
  if (!name) {
    ElMessage.warning('分组名称不能为空')
    return
  }
  savingId.value = g.id
  try {
    await literaryApi.renameTranslationGroup(g.id, name)
    ElMessage.success('已重命名')
    cancelRename()
    await loadGroups()
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '重命名失败')
  } finally {
    savingId.value = null
  }
}

const removeGroup = async (g: GroupItem) => {
  if (!g.id) return
  try {
    await ElMessageBox.confirm(
      `确定删除分组「${g.name}」？该组内 ${g.count} 篇文档将变为未分组。`,
      '删除分组',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  deletingId.value = g.id
  try {
    await literaryApi.deleteTranslationGroup(g.id, true)
    ElMessage.success('分组已删除')
    await loadGroups()
    emit('changed')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.detail || '删除失败')
  } finally {
    deletingId.value = null
  }
}
</script>

<style scoped lang="scss">
.group-manager {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.create-row {
  display: flex;
  gap: 8px;
}

.group-list {
  min-height: 160px;
  max-height: 360px;
  overflow: auto;
  border: 1px solid var(--ins-line, #e5e7eb);
  border-radius: 10px;
  padding: 6px;
}

.group-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 10px;
  border-radius: 8px;

  &:hover {
    background: rgba(var(--ins-primary-rgb, 64, 158, 255), 0.06);
  }
}

.group-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-name {
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.group-actions {
  display: flex;
  flex-shrink: 0;
}

.hint {
  margin: 0;
  font-size: 12px;
  color: var(--ins-muted, #909399);
  line-height: 1.5;
}
</style>
