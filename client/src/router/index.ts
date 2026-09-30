import { createRouter, createWebHistory } from 'vue-router'
import { $storex } from '../store'
import Navigate from './navigate'
import QuickChatView from '@/views/QuickChatView.vue'
import WorkspaceView from '@/views/WorkspaceView.vue'
import MessengerView from '@/views/MessengerView.vue'
import MetricsDashboard from '@/components/analytics/MetricsDashboard.vue'
import Desktop from '@/components/desktop/Desktop.vue'
import KanbanBoardView from '@/components/kanban/board/KanbanBoardView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      // Teams-like launcher home page
      path: '/',
      name: 'home',
      component: QuickChatView
    },
    {
      // Chat routes: router mode
      path: '/chats',
      name: 'chats',
      component: QuickChatView
    },
    {
      path: '/chats/:chatId/:chatName',
      name: 'chat',
      component: QuickChatView
    },
    {
      path: '/chats/:chatId/:chatName/workspace/:workspaceId/:workspaceName',
      name: 'chat-workspace',
      component: QuickChatView
    },
    {
      // Workspace routes: router mode
      path: '/workspaces',
      name: 'workspaces',
      component: WorkspaceView
    },
    {
      path: '/kanban',
      name: 'kanban',
      component: KanbanBoardView
    },
    {
      path: '/workspaces/:workspaceId/:workspaceName',
      name: 'workspace',
      component: WorkspaceView
    },
    {
      path: '/messenger',
      name: 'messenger',
      component: MessengerView
    },
    {
      // Desktop / team view (previously the catch-all)
      path: '/desktop/:pathMatch(.*)*',
      name: 'codx-junior-split',
      component: Desktop
    },
    {
      path: '/analytics',
      name: 'analytics',
      component: MetricsDashboard
    },
    {
      // Catch-all: redirect everything else to home
      path: '/:pathMatch(.*)*',
      redirect: '/'
    },
  ]
})

// Initialize navigation API with both $router and $storex
router.$navigation = Navigate({ $router: router, $storex })
router.$navigation.init()

router.beforeEach((to, from) => {
  return router.$navigation.onRouteChanged({ from, to })
})

$storex.$router = router

export default router