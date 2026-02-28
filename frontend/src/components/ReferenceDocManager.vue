<template>
  <div class="reference-doc-manager">
    <div class="manager-header">
      <el-button type="primary" @click="showCreate = true">
        <el-icon><Plus /></el-icon>
        新建参考文档
      </el-button>
    </div>

    <div class="doc-list">
      <el-table :data="documents" style="width: 100%">
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="doc_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getDocTypeType(row.doc_type)" size="small">
              {{ getDocTypeText(row.doc_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_lang" label="语言对" width="120">
          <template #default="{ row }">
            <span v-if="row.source_lang && row.target_lang">
              {{ row.source_lang }} → {{ row.target_lang }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              @change="toggleActive(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDoc(row)">查看</el-button>
            <el-button link type="danger" @click="deleteDoc(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 创建对话框 -->
    <el-dialog
      v-model="showCreate"
      title="新建参考文档"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="form" label-position="top">
        <el-form-item label="文档名称">
          <el-input v-model="form.name" placeholder="输入文档名称" />
        </el-form-item>
        
        <el-form-item label="文档类型">
          <el-radio-group v-model="form.doc_type">
            <el-radio-button label="terminology">术语库</el-radio-button>
            <el-radio-button label="style_guide">风格指南</el-radio-button>
            <el-radio-button label="reference">参考译文</el-radio-button>
            <el-radio-button label="general">一般文档</el-radio-button>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="适用语言对（可选）">
          <div class="lang-pair">
            <el-select v-model="form.source_lang" placeholder="源语言" clearable>
              <el-option
                v-for="lang in languages"
                :key="lang.code"
                :label="lang.name"
                :value="lang.code"
              />
            </el-select>
            <span class="arrow">→</span>
            <el-select v-model="form.target_lang" placeholder="目标语言" clearable>
              <el-option
                v-for="lang in languages"
                :key="lang.code"
                :label="lang.name"
                :value="lang.code"
              />
            </el-select>
          </div>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="简短描述此文档的用途..."
          />
        </el-form-item>
        
        <el-form-item label="文档内容">
          <el-tabs v-model="inputMode">
            <el-tab-pane label="直接输入" name="input">
              <el-input
                v-model="form.content"
                type="textarea"
                :rows="10"
                placeholder="粘贴文档内容..."
              />
            </el-tab-pane>
            <el-tab-pane label="上传文件" name="upload">
              <el-upload
                drag
                action="#"
                :auto-upload="false"
                :on-change="handleFileChange"
                accept=".txt,.md,.doc,.docx,.pdf,.mobi,.azw,.html,.htm,.xml,.json,.csv,.yaml,.yml,.rst,.tex,.srt,.vtt,.log,.ini,.cfg"
                :limit="1"
              >
                <el-icon class="el-icon--upload"><Upload /></el-icon>
                <div class="el-upload__text">
                  拖拽文件到此处或 <em>点击上传</em>
                </div>
                <template #tip>
                  <div class="el-upload__tip">
                    支持 txt、docx、pdf、mobi 及 md/html/xml/json/csv 等
                  </div>
                </template>
              </el-upload>
            </el-tab-pane>
          </el-tabs>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="createDoc" :loading="creating">
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- 查看对话框 -->
    <el-dialog
      v-model="showView"
      title="查看文档"
      width="700px"
    >
      <div v-if="viewingDoc" class="doc-view">
        <h3>{{ viewingDoc.name }}</h3>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="类型">
            {{ getDocTypeText(viewingDoc.doc_type) }}
          </el-descriptions-item>
          <el-descriptions-item label="大小">
            {{ formatFileSize(viewingDoc.file_size) }}
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ formatDate(viewingDoc.created_at) }}
          </el-descriptions-item>
        </el-descriptions>
        <div class="doc-content">
          <pre>{{ viewingDoc.content }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { literaryApi, translateApi } from '@/api'

const emit = defineEmits(['close', 'updated'])

const languages = ref<{ code: string; name: string }[]>([])
const documents = ref<any[]>([])
const showCreate = ref(false)
const showView = ref(false)
const viewingDoc = ref<any>(null)
const inputMode = ref('input')
const creating = ref(false)

const form = ref({
  name: '',
  content: '',
  doc_type: 'general',
  source_lang: '',
  target_lang: '',
  description: ''
})

const loadLanguages = async () => {
  try {
    const response = await translateApi.getLanguages()
    languages.value = response.data.filter((l: any) => l.code !== 'auto')
  } catch (error) {
    console.error('Failed to load languages:', error)
  }
}

const loadDocuments = async () => {
  try {
    const response = await literaryApi.listReferences()
    documents.value = response.data
  } catch (error) {
    ElMessage.error('加载文档失败')
  }
}

const binaryExtensions = new Set(['doc', 'docx', 'pdf', 'mobi', 'azw'])
const handleFileChange = async (file: any) => {
  const raw = file?.raw
  if (!raw) return
  const ext = (file.name || '').split('.').pop()?.toLowerCase()
  if (binaryExtensions.has(ext)) {
    try {
      const formData = new FormData()
      formData.append('file', raw)
      const res = await literaryApi.parseFile(formData)
      form.value.content = res.data?.text ?? ''
      if (!form.value.name) form.value.name = (file.name || '').replace(/\.[^.]+$/, '')
      ElMessage.success('文件已解析')
    } catch (e) {
      ElMessage.error('文件解析失败')
    }
    return
  }
  const reader = new FileReader()
  reader.onload = (e) => {
    form.value.content = e.target?.result as string
    if (!form.value.name) form.value.name = file.name.replace(/\.[^/.]+$/, '')
    ElMessage.success('文件已读取')
  }
  reader.readAsText(raw, 'UTF-8')
}

const createDoc = async () => {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入文档名称')
    return
  }
  if (!form.value.content.trim()) {
    ElMessage.warning('请输入文档内容')
    return
  }

  creating.value = true
  try {
    await literaryApi.createReference(form.value)
    ElMessage.success('文档创建成功')
    showCreate.value = false
    resetForm()
    await loadDocuments()
    emit('updated')
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

const resetForm = () => {
  form.value = {
    name: '',
    content: '',
    doc_type: 'general',
    source_lang: '',
    target_lang: '',
    description: ''
  }
  inputMode.value = 'input'
}

const toggleActive = async (row: any) => {
  try {
    await literaryApi.updateReference(row.id, { is_active: row.is_active })
    ElMessage.success('状态已更新')
    emit('updated')
  } catch (error) {
    row.is_active = !row.is_active
    ElMessage.error('更新失败')
  }
}

const viewDoc = async (row: any) => {
  try {
    const response = await literaryApi.getReference(row.id)
    viewingDoc.value = response.data
    showView.value = true
  } catch (error) {
    ElMessage.error('加载失败')
  }
}

const deleteDoc = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 "${row.name}" 吗？`,
      '确认删除',
      { type: 'warning' }
    )
    await literaryApi.deleteReference(row.id)
    ElMessage.success('删除成功')
    await loadDocuments()
    emit('updated')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const getDocTypeType = (type: string) => {
  const types: Record<string, string> = {
    terminology: 'danger',
    style_guide: 'warning',
    reference: 'success',
    general: 'info'
  }
  return types[type] || 'info'
}

const getDocTypeText = (type: string) => {
  const texts: Record<string, string> = {
    terminology: '术语库',
    style_guide: '风格指南',
    reference: '参考译文',
    general: '一般文档'
  }
  return texts[type] || type
}

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatDate = (date: string) => {
  return new Date(date).toLocaleDateString('zh-CN')
}

onMounted(() => {
  loadLanguages()
  loadDocuments()
})
</script>

<style scoped lang="scss">
.reference-doc-manager {
  .manager-header {
    margin-bottom: 16px;
  }
  
  .lang-pair {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .el-select {
      flex: 1;
    }
    
    .arrow {
      color: var(--el-text-color-secondary);
    }
  }
  
  .doc-view {
    h3 {
      margin: 0 0 16px 0;
    }
    
    .doc-content {
      margin-top: 16px;
      max-height: 400px;
      overflow-y: auto;
      background: var(--el-fill-color-light);
      padding: 16px;
      border-radius: 8px;
      
      pre {
        margin: 0;
        white-space: pre-wrap;
        word-wrap: break-word;
        font-family: inherit;
        line-height: 1.6;
      }
    }
  }
}
</style>
