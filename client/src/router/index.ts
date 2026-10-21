import { createRouter, createWebHistory } from 'vue-router'
import { $storex } from '../store'
import Navigate from './navigate'

// ─────────────────────────────────────────────────────────────────────────────
// LAZY ROUTE COMPONENTS
// Each screen is its own chunk: navigating fetches only what the route needs
// instead of evaluating the whole application on first paint.
// ─────────────────────────────────────────────────────────────────────────────
const AppRouteView = () => import('@/views/AppRouteView.vue')
const QuickChatView = () => import('@/views/QuickChatView.vue')
const WorkspaceView = () => import('@/views/WorkspaceView.vue')
const MessengerView = () => import('@/views/MessengerView.vue')
const MeetView = () => import('@/views/MeetView.vue')
const TeamView = () => import('@/views/TeamView.vue')
const MetricsDashboard = () => import('@/components/analytics/MetricsDashboard.vue')
const Desktop = () => import('@/components/desktop/Desktop.vue')
const KanbanBoardView = () => import('@/components/kanban/board/KanbanBoardView.vue')
const BrowsersSessionManager = () => import('@/components/browsers/BrowsersSessionManager.vue')
const SolopreneurView = () => import('@/views/SolopreneurView.vue')

// ─────────────────────────────────────────────────────────────────────────────
// PROJECT-SCOPED ROUTES
// Every route is mounted under the active project's *escaped* name so the URL
// always reflects which project you are working in, e.g.
//   /codx-junior/chats      → project "codx-junior" chat list
//   /my.project/desktop     → project "my.project"  desktop view
//   /my-project/settings    → project "my-project"  settings
// The first segment is the project_name; vue-router percent-encodes it while
// building the URL, so names containing dots, dashes, spaces… stay valid.
// ─────────────────────────────────────────────────────────────────────────────

// Return the RAW active project name. vue-router encodes route params when it
// builds the URL, so pre-encoding here would double-encode names with special
// characters (e.g. "my project" → "my%2520project"), and the segment would no
// longer decode back to the real project name on reload.
function activeProjectSegment() {
  return $storex.projects.activeProject?.project_name || ''
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      // Unscoped bootstrap home. The navigation guard replaces it with the
      // project-scoped home ("/:projectName") as soon as a project is active.
      path: '/',
      name: 'root',
      component: AppRouteView,
      meta: { app: 'activity' }
    },
    {
      // Solopreneur mode — a top-level, project-INDEPENDENT screen that re-frames
      // the workspace around a solo operator (venture overview, modules and the
      // AI co-founder). The optional ":module" segment makes a module
      // deep-linkable ("/solopreneur/tasks"); without it the dashboard is shown.
      //
      // It is a STATIC segment, so vue-router ranks it above the dynamic
      // "/:projectName" route, and it is never project-prefixed: `withProject()`
      // only injects a project into routes whose path contains ":projectName".
      path: '/solopreneur/:module?',
      name: 'solopreneur',
      component: SolopreneurView
    },
    {
      // Home (project launcher)
      path: '/:projectName',
      name: 'home',
      component: AppRouteView,
      meta: { app: 'activity' }
    },
    {
      // Chat routes: router mode
      path: '/:projectName/chats',
      name: 'chats',
      component: QuickChatView
    },
    {
      path: '/:projectName/chats/:chatId/:chatName',
      name: 'chat',
      component: QuickChatView
    },
    {
      path: '/:projectName/chats/:chatId/:chatName/workspace/:workspaceId/:workspaceName',
      name: 'chat-workspace',
      component: QuickChatView
    },
    {
      // Meet routes: router mode
      path: '/:projectName/meet',
      name: 'meet',
      component: MeetView
    },
    {
      path: '/:projectName/meet/:meetId',
      name: 'meet-session',
      component: MeetView
    },
    {
      // Workspace routes: router mode
      path: '/:projectName/workspaces',
      name: 'workspaces',
      component: WorkspaceView
    },
    {
      path: '/:projectName/workspaces/:workspaceId/:workspaceName',
      name: 'workspace',
      component: WorkspaceView
    },
    {
      // Browser routes: router mode
      path: '/:projectName/browsers',
      name: 'browsers',
      component: BrowsersSessionManager
    },
    {
      path: '/:projectName/browsers/:sessionId/:sessionName',
      name: 'browser-session',
      component: BrowsersSessionManager
    },
    {
      // The optional board id + name segments let the URL carry the open board,
      // so a refresh or a back-navigation (non-desktop / single mode) reopens it.
      // Both are optional: the plain "/:projectName/kanban" still works.
      path: '/:projectName/kanban/:board?/:boardName?',
      name: 'kanban',
      component: KanbanBoardView
    },
    {
      path: '/:projectName/messenger',
      name: 'messenger',
      component: MessengerView
    },
    {
      // Team view (used by setActiveTab('team') / openTeam() / openTeams()).
      // The optional :teamId makes an individual team deep-linkable
      // ("/:projectName/team/<teamId>"); without it the view opens every team
      // (see views/TeamView.vue).
      path: '/:projectName/team/:teamId?',
      name: 'team',
      component: TeamView
    },

    // ── Generic app routes ────────────────────────────────────────────────
    // Each app maps to <AppRouteView> which resolves the component from
    // config/apps.js (route meta.app) and feeds it its params.
    { path: '/:projectName/vibe-coding', name: 'vibe-coding', component: AppRouteView, meta: { app: 'vibe-coding' } },
    { path: '/:projectName/wiki', name: 'wiki', component: AppRouteView, meta: { app: 'wiki' } },
    { path: '/:projectName/docs', name: 'docs', component: AppRouteView, meta: { app: 'docs' } },
    { path: '/:projectName/knowledge', name: 'knowledge', component: AppRouteView, meta: { app: 'knowledge' } },
    { path: '/:projectName/knowledge-settings', name: 'knowledge-settings', component: AppRouteView, meta: { app: 'knowledge_settings' } },
    { path: '/:projectName/projects', name: 'projects', component: AppRouteView, meta: { app: 'projects' } },
    { path: '/:projectName/settings', name: 'settings', component: AppRouteView, meta: { app: 'settings' } },
    { path: '/:projectName/global-settings', name: 'global-settings', component: AppRouteView, meta: { app: 'global-settings' } },
    { path: '/:projectName/account', name: 'account', component: AppRouteView, meta: { app: 'account' } },
    { path: '/:projectName/file-explorer', name: 'file-explorer', component: AppRouteView, meta: { app: 'file-explorer' } },
    { path: '/:projectName/file-viewer/:filePath(.*)*', name: 'file-viewer', component: AppRouteView, meta: { app: 'file-viewer' } },
    { path: '/:projectName/logs', name: 'log-viewer', component: AppRouteView, meta: { app: 'log-viewer' } },
    { path: '/:projectName/chat-logs', name: 'chat-logs', component: AppRouteView, meta: { app: 'chat-logs' } },
    { path: '/:projectName/decision-model-logs', name: 'decision-model-logs', component: AppRouteView, meta: { app: 'decision-model-logs' } },
    { path: '/:projectName/metrics', name: 'metrics', component: AppRouteView, meta: { app: 'metrics' } },
    { path: '/:projectName/infra', name: 'infra', component: AppRouteView, meta: { app: 'infra' } },
    { path: '/:projectName/team-channel/:channelId', name: 'team-channel', component: AppRouteView, meta: { app: 'team-channel' } },
    { path: '/:projectName/team-dm/:dmId', name: 'team-dm', component: AppRouteView, meta: { app: 'team-dm' } },
    { path: '/:projectName/team-media-library/:teamId', name: 'team-media-library', component: AppRouteView, meta: { app: 'team-media-library' } },

    {
      // Desktop / team view (dockview panels)
      path: '/:projectName/desktop/:pathMatch(.*)*',
      name: 'codx-junior-split',
      component: Desktop
    },
    {
      path: '/:projectName/analytics',
      name: 'analytics',
      component: MetricsDashboard
    },
    {
      // Catch-all: redirect everything else to the project bootstrap
      path: '/:pathMatch(.*)*',
      redirect: '/'
    },
  ]
})

// ─────────────────────────────────────────────────────────────────────────────
// BASE-PATH ENFORCEMENT
// Any navigation by *name* to a project-scoped route automatically gets the
// active project name injected as the first URL segment. Centralising it here
// means call sites only ever specify the route name/params, and the project
// prefix is never forgotten (works for $router.push, $router.replace and
// <RouterLink> alike, since they all funnel through these two methods).
// ─────────────────────────────────────────────────────────────────────────────

// Names of routes that live under the "/:projectName" base path.
let scopedRouteNames = new Set()

function refreshScopedRouteNames() {
  scopedRouteNames = new Set(
    router.getRoutes()
      .filter(route => typeof route.name === 'string' && route.path.includes(':projectName'))
      .map(route => route.name)
  )
}

function withProject(location: any): any {
  // String paths are already fully qualified (or external) – leave them as-is.
  if (!location || typeof location === 'string') {
    return location
  }
  const loc = { ...location }
  if (scopedRouteNames.has(loc.name) && !(loc.params && loc.params.projectName)) {
    loc.params = { ...(loc.params || {}), projectName: activeProjectSegment() }
  }
  return loc
}

refreshScopedRouteNames()

const _push = router.push.bind(router)
const _replace = router.replace.bind(router)
;(router as any).push = (to: any) => _push(withProject(to))
;(router as any).replace = (to: any) => _replace(withProject(to))

// Initialize navigation API with both $router and $storex
router.$navigation = Navigate({ $router: router, $storex })
router.$navigation.$storex = $storex
router.$navigation.init()

router.beforeEach((to, from) => {
  return router.$navigation.onRouteChanged({ from, to })
})

$storex.$router = router
$storex.$navigation = router.$navigation

export default router