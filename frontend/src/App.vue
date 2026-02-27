<template>
  <el-container class="app-container">
    <!-- 侧边栏 -->
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <el-icon class="logo-icon"><Switch /></el-icon>
        <span class="logo-text">译智通</span>
      </div>
      
      <el-menu
        :default-active="$route.path"
        router
        class="nav-menu"
        background-color="transparent"
        text-color="#606266"
        active-text-color="#409eff"
      >
        <el-menu-item v-for="route in routes" :key="route.path" :index="route.path">
          <el-icon>
            <component :is="route.meta?.icon" />
          </el-icon>
          <span>{{ route.meta?.title }}</span>
        </el-menu-item>
      </el-menu>
      
      <div class="sidebar-footer">
        <el-divider />
        <div class="system-info">
          <el-tag size="small" type="info">{{ config.ai_provider }}</el-tag>
          <span class="version">v1.0.0</span>
        </div>
      </div>
    </el-aside>

    <!-- 主内容区 -->
    <el-main class="main-content">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { systemApi } from '@/api'

const route = useRoute()
const router = useRouter()

// 获取路由配置
const routes = router.getRoutes().filter(r => r.meta?.title)

// 系统配置
const config = ref<any>({})

onMounted(async () => {
  try {
    const response = await systemApi.getConfig()
    config.value = response.data
  } catch (error) {
    console.error('Failed to load config:', error)
  }
})
</script>

<style scoped lang="scss">
.app-container {
  height: 100vh;
}

.sidebar {
  background: linear-gradient(180deg, #f5f7fa 0%, #e4e7ed 100%);
  border-right: 1px solid #dcdfe6;
  display: flex;
  flex-direction: column;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  border-bottom: 1px solid #dcdfe6;
  
  .logo-icon {
    font-size: 32px;
    color: #409eff;
  }
  
  .logo-text {
    font-size: 24px;
    font-weight: 700;
    background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}

.nav-menu {
  flex: 1;
  border-right: none;
  padding: 12px 8px;
  
  .el-menu-item {
    border-radius: 8px;
    margin-bottom: 4px;
    
    &:hover {
      background-color: rgba(64, 158, 255, 0.1);
    }
    
    &.is-active {
      background-color: rgba(64, 158, 255, 0.15);
    }
    
    .el-icon {
      font-size: 18px;
    }
  }
}

.sidebar-footer {
  padding: 12px 20px;
  
  .system-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .version {
      font-size: 12px;
      color: #909399;
    }
  }
}

.main-content {
  background: #f5f7fa;
  padding: 0;
  overflow-y: auto;
}

// 过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
