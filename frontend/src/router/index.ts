import { createRouter, createWebHistory } from 'vue-router'
import TranslatorView from '@/views/TranslatorView.vue'
import HistoryView from '@/views/HistoryView.vue'
import BatchView from '@/views/BatchView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'translator',
      component: TranslatorView,
      meta: { title: '智能翻译', icon: 'Translate' }
    },
    {
      path: '/history',
      name: 'history',
      component: HistoryView,
      meta: { title: '翻译历史', icon: 'Clock' }
    },
    {
      path: '/batch',
      name: 'batch',
      component: BatchView,
      meta: { title: '批量翻译', icon: 'DocumentCopy' }
    },
  ],
})

export default router
