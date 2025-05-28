import { createRouter, createWebHistory } from 'vue-router'
import { $storex } from '../store'
import SplitView from '@/views/SplitView.vue'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/*',
      name: 'codx-junior-split',
      component: SplitView
    },    
  ]
})

router.beforeEach(async (to, from, next) => {
  next()
})

export default router
