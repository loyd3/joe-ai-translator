import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'

const TOKEN_KEY = 'ai_translator_token'

export interface UserInfo {
  id: number
  email: string
  display_name: string | null
  is_active: boolean
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)

  function setToken(newToken: string | null) {
    token.value = newToken
    if (newToken) {
      localStorage.setItem(TOKEN_KEY, newToken)
    } else {
      localStorage.removeItem(TOKEN_KEY)
      user.value = null
    }
  }

  async function login(email: string, password: string) {
    const { data } = await api.post<{ access_token: string; user: UserInfo }>('/auth/login', {
      email,
      password
    })
    setToken(data.access_token)
    user.value = data.user
    return data
  }

  async function register(email: string, password: string, display_name?: string) {
    const { data } = await api.post<{ access_token: string; user: UserInfo }>('/auth/register', {
      email,
      password,
      display_name: display_name || undefined
    })
    setToken(data.access_token)
    user.value = data.user
    return data
  }

  async function fetchMe() {
    if (!token.value) return
    const { data } = await api.get<UserInfo>('/auth/me')
    user.value = data
    return data
  }

  async function updateMe(payload: { display_name?: string; password?: string }) {
    const { data } = await api.put<UserInfo>('/auth/me', payload)
    user.value = data
    return data
  }

  function logout() {
    setToken(null)
  }

  /** 从 localStorage 恢复 token 并拉取用户信息（用于刷新后保持登录） */
  async function initFromStorage() {
    const saved = localStorage.getItem(TOKEN_KEY)
    if (saved) {
      token.value = saved
      try {
        await fetchMe()
      } catch {
        setToken(null)
      }
    }
  }

  return {
    token,
    user,
    isLoggedIn,
    setToken,
    login,
    register,
    fetchMe,
    updateMe,
    logout,
    initFromStorage
  }
})
