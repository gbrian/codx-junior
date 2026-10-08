import { createRouter, createWebHistory } from 'vue-router'
import { $storex } from '../store'
import Navigate from './navigate'
import QuickChatView from '@/views/QuickChatView.vue'
import WorkspaceView from '@/views/WorkspaceView.vue'
import MessengerView from '@/views/MessengerView.vue'
import MeetView from '@/views/MeetView.vue'
import MetricsDashboard from '@/components/analytics/MetricsDashboard.vue'
import Desktop from '@/components/desktop/Desktop.vue'
import KanbanBoardView from '@/components/kanban/board/KanbanBoardView.vue'
import BrowsersSessionManager from '@/components/browsers/BrowsersSessionManager.vue'
import TeamView from '@/views/TeamView.vue'
import AppRouteView from '@/views/AppRouteView.vue'

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
      // Meet routes: router mode
      path: '/meet',
      name: 'meet',
      component: MeetView
    },
    {
      path: '/meet/:meetId',
      name: 'meet-session',
      component: MeetView
    },
    {
      // Workspace routes: router mode
      path: '/workspaces',
      name: 'workspaces',
      component: WorkspaceView
    },
    {
      path: '/workspaces/:workspaceId/:workspaceName',
      name: 'workspace',
      component: WorkspaceView
    },
    {
      // Browser routes: router mode
      path: '/browsers',
      name: 'browsers',
      component: BrowsersSessionManager
    },
    {
      path: '/browsers/:sessionId/:sessionName',
      name: 'browser-session',
      component: BrowsersSessionManager
    },
    {
      path: '/kanban',
      name: 'kanban',
      component: KanbanBoardView
    },
    {
      path: '/messenger',
      name: 'messenger',
      component: MessengerView
    },
    {
      // Team view (used by setActiveTab('team') / openTeam())
      path: '/team',
      name: 'team',
      component: TeamView
    },

    // ── Generic app routes ────────────────────────────────────────────────
    // Each app maps to <AppRouteView> which resolves the component from
    // config/apps.js (route meta.app) and feeds it its params.
    { path: '/vibe-coding', name: 'vibe-coding', component: AppRouteView, meta: { app: 'vibe-coding' } },
    { path: '/wiki', name: 'wiki', component: AppRouteView, meta: { app: 'wiki' } },
    { path: '/docs', name: 'docs', component: AppRouteView, meta: { app: 'docs' } },
    { path: '/knowledge', name: 'knowledge', component: AppRouteView, meta: { app: 'knowledge' } },
    { path: '/knowledge-settings', name: 'knowledge-settings', component: AppRouteView, meta: { app: 'knowledge_settings' } },
    { path: '/profiles', name: 'profiles', component: AppRouteView, meta: { app: 'profiles' } },
    { path: '/projects', name: 'projects', component: AppRouteView, meta: { app: 'projects' } },
    { path: '/activity', name: 'activity', component: AppRouteView, meta: { app: 'activity' } },
    { path: '/settings', name: 'settings', component: AppRouteView, meta: { app: 'settings' } },
    { path: '/global-settings', name: 'global-settings', component: AppRouteView, meta: { app: 'global-settings' } },
    { path: '/account', name: 'account', component: AppRouteView, meta: { app: 'account' } },
    { path: '/file-explorer', name: 'file-explorer', component: AppRouteView, meta: { app: 'file-explorer' } },
    { path: '/file-viewer/:filePath(.*)*', name: 'file-viewer', component: AppRouteView, meta: { app: 'file-viewer' } },
    { path: '/logs', name: 'log-viewer', component: AppRouteView, meta: { app: 'log-viewer' } },
    { path: '/chat-logs', name: 'chat-logs', component: AppRouteView, meta: { app: 'chat-logs' } },
    { path: '/metrics', name: 'metrics', component: AppRouteView, meta: { app: 'metrics' } },
    { path: '/team-channel/:channelId', name: 'team-channel', component: AppRouteView, meta: { app: 'team-channel' } },
    { path: '/team-dm/:dmId', name: 'team-dm', component: AppRouteView, meta: { app: 'team-dm' } },
    { path: '/team-media-library/:teamId', name: 'team-media-library', component: AppRouteView, meta: { app: 'team-media-library' } },

    {
      // Desktop / team view (dockview panels)
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
$storex.$navigation = router.$navigation

export default router