import { createRouter, createWebHistory } from 'vue-router'
import { $storex } from '../store'
import SplitView from '@/views/SplitView.vue'
import Navigate from './navigate'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/*',
      name: 'codx-junior-split',
      component: SplitView
    },
  ]
});

router.$navigate = Navigate({ $storex, $router: router })

router.beforeEach(async (to, from, next) => {
  router.$navigate.onRouteChanged({ from, to, next })
})


window.$router = router

export default router
