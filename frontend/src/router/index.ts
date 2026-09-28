import { createRouter, createWebHistory } from 'vue-router'
import LiteraryTranslationView from '@/views/LiteraryTranslationView.vue'
import LiteraryResultView from '@/views/LiteraryResultView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
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
    // 旧独立路由：回到主界面，避免书签落到空白页
    { path: '/terms', redirect: '/' },
    { path: '/literary/:id/story', redirect: '/' },
  ],
})

export default router
