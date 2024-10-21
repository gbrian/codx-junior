import { createRouter, createWebHistory } from 'vue-router'
import CodxJuniorVue from '../views/CodxJunior.vue'
import SplitView from '../views/SplitView.vue'

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
      component: CodxJuniorVue
    },    
  ]
})

router.beforeEach(async (to, from, next) => {
  console.log("On router change", to)
  next()
})

export default router
