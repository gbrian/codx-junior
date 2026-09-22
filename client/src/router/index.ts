import { createRouter, createWebHistory } from 'vue-router'
import { $storex } from '../store'
import Navigate from './navigate'
import QuickChatView from '@/views/QuickChatView.vue'
import MessengerView from '@/views/MessengerView.vue'
import HomeMobile from '@/views/HomeMobile.vue'
import TeamView from '@/views/TeamView.vue'
import AppHomeView from '@/views/AppHomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      // Teams-like launcher home page
      path: '/',
      name: 'home',
      component: AppHomeView
    },
    {
      path: '/quick-chat',
      name: 'quick-chat',
      component: QuickChatView
    },
    {
      path: '/messenger',
      name: 'messenger',
      component: MessengerView
    },
    {
      path: '/mobile',
      name: 'mobile',
      component: HomeMobile
    },
    {
      // Desktop / team view (previously the catch-all)
      path: '/desktop/:pathMatch(.*)*',
      name: 'codx-junior-split',
      component: TeamView
    },
    {
      // Catch-all: redirect everything else to home
      path: '/:pathMatch(.*)*',
      redirect: '/'
    },
  ]
})

router.$navigate = Navigate({ $storex, $router: router })
router.$navigate.init()
router.beforeEach((to, from) => {
  return router.$navigate.onRouteChanged({ from, to })
})

window.$router = router

export default router