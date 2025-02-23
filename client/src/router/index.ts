import { createRouter, createWebHistory } from 'vue-router'
import SplitView from '@/views/SplitView.vue'
import HomeView from '@/views/HomeView.vue'
import SharedView from '@/views/SharedView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'codx-junior-split',
      component: SplitView
    },
    {
      path: '/codx-junior',
      name: 'codx-junior',
      component: HomeView
    },
    {
      path: '/shared',
      name: 'codx-junior-shared',
      component: SharedView
    },    
  ]
})

router.beforeEach(async (to, from, next) => {
  console.log("On router change", to)
  next()
})

export default router
