import { createRouter, createWebHistory } from 'vue-router'
import LiteraryTranslationView from '@/views/LiteraryTranslationView.vue'
import LiteraryResultView from '@/views/LiteraryResultView.vue'
import LoginView from '@/views/LoginView.vue'
import RegisterView from '@/views/RegisterView.vue'
import ProfileView from '@/views/ProfileView.vue'

const TOKEN_KEY = 'ai_translator_token'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { public: true }
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { public: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: ProfileView,
      meta: { title: '个人资料' }
    },
    {
      path: '/',
      name: 'literary',
      component: LiteraryTranslationView,
      meta: { title: '文学翻译', icon: 'Reading' }
    },
    {
      path: '/literary/result/:id',
      name: 'literary-result',
      component: LiteraryResultView
    },
  ],
})

router.beforeEach((to, _from, next) => {
  const isPublic = to.meta.public === true
  const hasToken = !!localStorage.getItem(TOKEN_KEY)
  if (!isPublic && !hasToken) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }
  if (isPublic && hasToken && (to.name === 'login' || to.name === 'register')) {
    next('/')
    return
  }
  next()
})

export default router
