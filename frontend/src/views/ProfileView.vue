<template>
  <div class="profile-page">
    <div class="profile-card">
      <h1 class="title">个人资料</h1>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100" class="form">
        <el-form-item label="邮箱">{{ user?.email }}</el-form-item>
        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="显示名称" clearable />
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="不修改请留空" show-password clearable />
        </el-form-item>
        <el-form-item label="确认密码" prop="password2">
          <el-input v-model="form.password2" type="password" placeholder="再次输入新密码" show-password clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="onSubmit">保存</el-button>
          <el-button @click="router.push('/')">返回</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const user = ref(auth.user)

const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({
  display_name: '',
  password: '',
  password2: ''
})
const rules: FormRules = {
  password2: [
    {
      validator: (_rule: any, value: string, cb: (e?: Error) => void) => {
        if (form.password && value !== form.password) cb(new Error('两次密码不一致'))
        else cb()
      },
      trigger: 'blur'
    }
  ]
}

watch(
  () => auth.user,
  (u) => {
    user.value = u
    if (u) {
      form.display_name = u.display_name || ''
    }
  },
  { immediate: true }
)

onMounted(async () => {
  if (!auth.isLoggedIn) {
    router.replace('/login')
    return
  }
  try {
    await auth.fetchMe()
    if (auth.user) form.display_name = auth.user.display_name || ''
  } catch {
    router.replace('/login')
  }
})

async function onSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    if (form.password && form.password.length < 6) {
      ElMessage.warning('密码至少 6 位')
      return
    }
    loading.value = true
    try {
      const payload: { display_name?: string; password?: string } = {
        display_name: form.display_name || undefined
      }
      if (form.password) payload.password = form.password
      await auth.updateMe(payload)
      ElMessage.success('保存成功')
      form.password = ''
      form.password2 = ''
    } catch (e: any) {
      ElMessage.error(e.response?.data?.detail || '保存失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
.profile-page {
  min-height: 100vh;
  padding: 24px;
  background: #f5f7fa;
}
.profile-card {
  max-width: 480px;
  margin: 0 auto;
  padding: 32px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
.title {
  font-size: 20px;
  margin-bottom: 24px;
  color: #303133;
}
.form :deep(.el-form-item__label) {
  color: #606266;
}
</style>
