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
});

router.beforeEach(async (to, from, next) => {
    if (to.path.startsWith("/auth")) {
      const { code, state } = to.query
      const provider = to.path.split("/").reverse()[0]

      if (!provider || !code) {
        $storex.session.onError("Missing OAuth provider or code");
        return next('/');
      }

      try {
        await $storex.users.oauthLogin({ provider, code, state });
        next('/');
      } catch (error) {
        $storex.session.onError("Failed to complete OAuth login");
        next('/');
      }
    } else {
      next()
    }
})

export default router
