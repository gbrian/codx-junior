import { createRouter, createWebHistory } from 'vue-router'
import { $storex } from '../store'
import Navigate from './navigate'
import QuickChatView from '@/views/QuickChatView.vue'
import HomeMobile from '@/views/HomeMobile.vue'
import TeamView from '@/views/TeamView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/quick-chat',
      name: 'quick-chat',
      component: QuickChatView
    },
    {
      path: '/mobile',
      name: 'mobile',
      component: HomeMobile
    },
    {
      // Catch-all: desktop/team view for all other paths
      path: '/:pathMatch(.*)*',
      name: 'codx-junior-split',
      component: TeamView
    },
  ]
})

router.$navigate = Navigate({ $storex, $router: router })

router.beforeEach((to, from) => {
  return router.$navigate.onRouteChanged({ from, to })
})

window.$router = router

export default router