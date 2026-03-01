<template>
  <div class="app-container">
    <router-view />
  </div>
</template>

<style scoped>
.app-container {
  height: 100vh;
  background: #f5f7fa;
}
</style>

<style>
:root {
  --el-font-size-base: 15px;
  --el-font-size-small: 13px;
  --el-font-size-extra-small: 12px;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  font-size: 15px;
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>
