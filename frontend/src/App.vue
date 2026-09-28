<template>
  <div class="app-container">
    <router-view />
    <ThemeSettingsDialog v-model="showThemeSettings" />
  </div>
</template>

<script setup lang="ts">
import { provide, ref } from 'vue'
import { useThemeStore } from '@/stores/theme'
import ThemeSettingsDialog from '@/components/ThemeSettingsDialog.vue'

useThemeStore()

const showThemeSettings = ref(false)
provide('openThemeSettings', () => {
  showThemeSettings.value = true
})
</script>

<style scoped>
.app-container {
  height: 100vh;
}
</style>
