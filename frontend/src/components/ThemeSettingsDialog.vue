<template>
  <el-dialog
    v-model="visible"
    title="主题设置"
    width="440px"
    class="theme-dialog"
    :close-on-click-modal="true"
    @closed="onClosed"
  >
    <div class="theme-section">
      <div class="section-label">外观模式</div>
      <el-radio-group :model-value="themeStore.mode" class="mode-group" @change="onModeChange">
        <el-radio-button value="light">
          <el-icon><Sunny /></el-icon> 浅色
        </el-radio-button>
        <el-radio-button value="dark">
          <el-icon><Moon /></el-icon> 深色
        </el-radio-button>
        <el-radio-button value="system">
          <el-icon><Monitor /></el-icon> 跟随系统
        </el-radio-button>
      </el-radio-group>
    </div>
    <div class="theme-section">
      <div class="section-label">预设主题</div>
      <div class="preset-list">
        <button
          v-for="preset in THEME_PRESETS"
          :key="preset.id"
          type="button"
          class="preset-item"
          :class="{ active: themeStore.presetId === preset.id }"
          @click="themeStore.setPreset(preset.id)"
        >
          <span class="preset-swatch" :style="{ background: preset.primary }" />
          <span class="preset-name">{{ preset.name }}</span>
        </button>
      </div>
    </div>
    <div class="theme-section">
      <div class="section-label">自定义主题色</div>
      <div class="custom-row">
        <el-color-picker
          v-model="customColorLocal"
          :predefine="predefineColors"
          @change="onCustomColorChange"
        />
        <el-input
          v-model="customColorLocal"
          class="custom-hex-input"
          placeholder="#6B76DC"
          maxlength="9"
          @change="onCustomColorChange"
        />
      </div>
      <div class="custom-hint">选择颜色后将自动应用为「自定义」主题</div>
    </div>
    <template #footer>
      <el-button type="primary" @click="visible = false">完成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Sunny, Moon, Monitor } from '@element-plus/icons-vue'
import { useThemeStore, THEME_PRESETS, type ThemeMode } from '@/stores/theme'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
}>()

const themeStore = useThemeStore()
const visible = ref(props.modelValue)
const customColorLocal = ref(themeStore.customColor)

const predefineColors = [
  '#6B76DC',
  '#8F4E22',
  '#B04F6A',
  '#3F9575',
  '#6B5899',
  '#457FA0',
  '#C46B83',
  '#5AAF8F',
  '#8574B2',
  '#5E9AB8',
]

watch(
  () => props.modelValue,
  (v) => {
    visible.value = v
    if (v) customColorLocal.value = themeStore.customColor
  }
)
watch(visible, (v) => emit('update:modelValue', v))

function onModeChange(val: string | number | boolean | undefined) {
  themeStore.setMode(val as ThemeMode)
}

function onCustomColorChange(val: string | undefined) {
  const v = (val ?? (customColorLocal.value || '')).trim()
  if (!v) return
  if (/^#[0-9A-Fa-f]{6}$/.test(v) || /^#[0-9A-Fa-f]{8}$/.test(v)) {
    themeStore.setCustomColor(v)
  }
}

function onClosed() {
  emit('update:modelValue', false)
}
</script>

<style scoped lang="scss">
.theme-section {
  margin-bottom: 20px;

  &:last-of-type {
    margin-bottom: 0;
  }
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ins-ink);
  margin-bottom: 10px;
}

.mode-group {
  width: 100%;
  display: flex;

  :deep(.el-radio-button) {
    flex: 1;

    .el-radio-button__inner {
      width: 100%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
    }
  }
}

.preset-list {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.preset-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border: 2px solid var(--ins-line-strong);
  border-radius: 10px;
  background: var(--ins-surface);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--el-color-primary-light-5);
    background: var(--ins-bg-deep);
  }

  &.active {
    border-color: var(--el-color-primary);
    background: var(--ins-bg-deep);
    box-shadow: 0 0 0 1px var(--el-color-primary);
  }

  .preset-swatch {
    width: 24px;
    height: 24px;
    border-radius: 6px;
    flex-shrink: 0;
  }

  .preset-name {
    font-size: 14px;
    color: var(--ins-ink);
  }
}

.custom-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.custom-hex-input {
  flex: 1;
  max-width: 140px;
}

.custom-hint {
  font-size: 12px;
  color: var(--ins-muted);
  margin-top: 8px;
}
</style>
