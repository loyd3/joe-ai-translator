<template>
  <div class="literary-result-view">
    <div class="result-header">
      <div class="header-left">
        <el-button link type="primary" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h1 class="title">{{ task?.title || `定稿 #${task?.id}` }}</h1>
        <el-tag v-if="task?.status" :type="task.status === 'completed' ? 'success' : 'info'">
          {{ task?.status === 'completed' ? '定稿完成' : task?.status }}
        </el-tag>
      </div>
      <div class="header-actions">
        <el-button type="primary" :loading="saving" @click="save">
          <el-icon><Select /></el-icon>
          保存修改
        </el-button>
        <el-button :loading="exporting" @click="showExport = true">
          <el-icon><Download /></el-icon>
          导出译文
        </el-button>
      </div>
    </div>

    <div class="result-meta" v-if="task">
      <span>{{ task.source_lang }} → {{ task.target_lang }}</span>
      <span class="meta-divider">|</span>
      <span>文学类型：{{ task.literary_type }}</span>
    </div>

    <div class="result-body" v-loading="loading">
      <div class="compare-wrap">
        <div class="panel source-panel">
          <div class="panel-header">
            <span class="panel-label">原文</span>
            <el-tag size="small" type="info">{{ task?.source_lang || '' }}</el-tag>
          </div>
          <div class="panel-scroll">
            <el-input
              v-model="sourceText"
              type="textarea"
              placeholder="原文"
              class="panel-textarea"
              resize="none"
            />
          </div>
        </div>
        <div class="panel-divider" />
        <div class="panel translation-panel">
          <div class="panel-header">
            <span class="panel-label">译文</span>
            <el-tag size="small" type="success">{{ task?.target_lang || '' }}</el-tag>
          </div>
          <div class="panel-scroll">
            <el-input
              v-model="translationText"
              type="textarea"
              placeholder="译文（定稿，可修改后保存并导出）"
              class="panel-textarea"
              resize="none"
            />
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showExport" title="导出译文" width="440px">
      <el-form label-position="top">
        <el-form-item label="格式">
          <el-radio-group v-model="exportFormat">
            <el-radio-button label="txt">TXT</el-radio-button>
            <el-radio-button label="md">Markdown</el-radio-button>
            <el-radio-button label="html">HTML</el-radio-button>
            <el-radio-button label="json">JSON</el-radio-button>
            <el-radio-button label="csv">CSV</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="exportWithSource">同时导出原文对照</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExport = false">取消</el-button>
        <el-button type="primary" :loading="exporting" @click="doExport">导出</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Select, Download } from '@element-plus/icons-vue'
import { literaryApi } from '@/api'

const route = useRoute()
const router = useRouter()

const task = ref<any>(null)
const sourceText = ref('')
const translationText = ref('')
const loading = ref(false)
const saving = ref(false)
const exporting = ref(false)
const showExport = ref(false)
const exportFormat = ref<'txt' | 'md' | 'html' | 'json' | 'csv'>('txt')
const exportWithSource = ref(false)

const id = computed(() => {
  const raw = route.params.id
  return raw ? Number(raw) : 0
})

const load = async () => {
  if (!id.value) return
  loading.value = true
  try {
    const res = await literaryApi.getTranslation(id.value, false)
    task.value = res.data
    sourceText.value = task.value.source_text || ''
    translationText.value =
      task.value.final_translation ||
      task.value.step4_finalization ||
      task.value.step3_revision ||
      task.value.step2_verification ||
      task.value.step1_translation ||
      ''
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

const save = async () => {
  if (!id.value) return
  saving.value = true
  try {
    await literaryApi.updateTranslation(id.value, {
      source_text: sourceText.value,
      final_translation: translationText.value
    })
    task.value = { ...task.value, source_text: sourceText.value, final_translation: translationText.value }
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const doExport = async () => {
  if (!id.value) return
  await save()
  exporting.value = true
  try {
    const res = await literaryApi.exportTranslation(id.value, {
      format: exportFormat.value,
      include_source: exportWithSource.value
    })
    const blob = new Blob([res.data.content], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = res.data.filename || `translation_${id.value}.${exportFormat.value}`
    link.click()
    URL.revokeObjectURL(url)
    showExport.value = false
    ElMessage.success('导出成功')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

const goBack = () => {
  router.push({ name: 'literary' })
}

watch(id, load, { immediate: true })
</script>

<style scoped lang="scss">
.literary-result-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.result-header {
  background: #fff;
  padding: 16px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e4e7ed;
  flex-shrink: 0;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;

    .title {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
  }

  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.result-meta {
  background: #fff;
  padding: 8px 24px;
  font-size: 13px;
  color: #909399;
  border-bottom: 1px solid #ebeef5;

  .meta-divider {
    margin: 0 12px;
    color: #dcdfe6;
  }
}

.result-body {
  flex: 1;
  min-height: 0;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.compare-wrap {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 8px 1fr;
  grid-template-rows: 1fr;
  gap: 0;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  border: 1px solid #ebeef5;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 600;
  color: #303133;
  flex-shrink: 0;
  background: #fafafa;

  .panel-label {
    font-size: 15px;
  }
}

.source-panel .panel-header {
  background: linear-gradient(to bottom, #f8fafc 0%, #f1f5f9 100%);
  border-bottom-color: #e2e8f0;
}

.translation-panel .panel-header {
  background: linear-gradient(to bottom, #f0fdf4 0%, #dcfce7 100%);
  border-bottom-color: #bbf7d0;
}

.panel-divider {
  width: 8px;
  background: linear-gradient(to right, #e4e7ed 0%, #ebeef5 50%, #e4e7ed 100%);
  border-radius: 4px;
  flex-shrink: 0;
}

.panel-scroll {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 0;
}

.panel-textarea {
  flex: 1;
  display: flex;
  min-height: 0;

  :deep(.el-textarea) {
    flex: 1;
    display: flex;
  }

  :deep(.el-textarea__inner) {
    flex: 1;
    border: none;
    border-radius: 0;
    resize: none;
    font-size: 14px;
    line-height: 1.85;
    padding: 16px 18px;
    box-shadow: none;
    background: #fafafa;
  }
}

.translation-panel :deep(.el-textarea__inner) {
  background: #f8fff8;
}
</style>
