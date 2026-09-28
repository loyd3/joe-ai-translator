<template>
  <div class="style-agent-picker" :class="{ compact }">
    <span v-if="label" class="picker-label">{{ label }}</span>
    <div class="picker-chips">
      <button
        type="button"
        class="style-chip"
        :class="{ active: modelValue == null }"
        @click="emit('update:modelValue', undefined)"
      >
        {{ defaultLabel }}
      </button>
      <button
        v-for="a in agents"
        :key="a.id"
        type="button"
        class="style-chip"
        :class="{ active: modelValue === a.id }"
        :title="a.is_default ? `${a.name}（默认）` : (a.description || a.name)"
        @click="emit('update:modelValue', a.id)"
      >
        {{ a.name }}
        <span v-if="a.is_default" class="chip-badge">默</span>
      </button>
      <button
        v-if="showManageLink"
        type="button"
        class="manage-link"
        @click="emit('manage')"
      >
        管理风格
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { styleAgentApi } from '@/api'
import type { StyleAgent } from '@/api/styleTypes'

const props = withDefaults(
  defineProps<{
    modelValue?: number
    label?: string
    defaultLabel?: string
    compact?: boolean
    showManageLink?: boolean
    autoSelectDefault?: boolean
    /** 外部递增时重新拉取文风列表（例如从文风面板返回） */
    reloadToken?: number
  }>(),
  {
    label: '翻译风格',
    defaultLabel: '默认（贴原文）',
    compact: false,
    showManageLink: true,
    autoSelectDefault: true,
    reloadToken: 0,
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: number | undefined]
  manage: []
}>()

const agents = ref<StyleAgent[]>([])

async function load() {
  try {
    const { data } = await styleAgentApi.list()
    agents.value = Array.isArray(data) ? data : []
    if (props.autoSelectDefault && props.modelValue == null) {
      const def = agents.value.find((a) => a.is_default)
      if (def) emit('update:modelValue', def.id)
    }
  } catch {
    agents.value = []
  }
}

onMounted(load)
watch(() => props.reloadToken, () => { load() })

defineExpose({ reload: load, agents })
</script>

<style scoped lang="scss">
.style-agent-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;

  &.compact {
    flex-direction: row;
    align-items: flex-start;
    gap: 10px;

    .picker-label {
      padding-top: 6px;
      flex-shrink: 0;
    }
  }
}

.picker-label {
  font-size: 13px;
  color: var(--ins-muted);
  font-weight: 500;
}

.picker-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.style-chip {
  appearance: none;
  border: 1px solid var(--ins-line-strong);
  background: var(--ins-surface);
  color: var(--ins-ink);
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 12px;
  line-height: 1.4;
  cursor: pointer;
  font-weight: 600;

  &:hover {
    border-color: var(--el-color-primary);
  }

  &.active {
    border-color: transparent;
    background: var(--el-color-primary);
    color: #fff;
    font-weight: 700;
  }
}

.chip-badge {
  margin-left: 2px;
  font-size: 10px;
  opacity: 0.75;
}

.manage-link {
  appearance: none;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 700;
  color: var(--el-color-primary);
  cursor: pointer;
  margin-left: 4px;
  padding: 0;

  &:hover {
    text-decoration: underline;
  }
}
</style>
