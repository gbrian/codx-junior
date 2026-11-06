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
const ChatsView = () => import('@/views/ChatsView.vue')
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
// WELCOME SCREEN
// "/" and "/<project_name>" are the landing routes, and both render the
// management dashboard (Pulse / Work / Blockers / Delivery / Team / Cost & AI).
// It is resolved through <AppRouteView> exactly like any other app screen, so
// the same key ('management-dashboard') opens a dockview panel on desktop and
// the routed screen in single/mobile mode (see config/apps.js).
// Its project filter is initialised from the route: opening "/<project_name>"
// starts with that project selected (see views/management/
// useManagementDashboard.js → initProjectFilter / syncProjectFilterWithRoute).
// ─────────────────────────────────────────────────────────────────────────────
const WELCOME_APP = 'management-dashboard'

// ─────────────────────────────────────────────────────────────────────────────
// MOBILE ROUTE METADATA
//
// The mobile shell (components/mobile/MobileShell.vue) reads `meta.mobile` to
// decide which bottom tab highlights, whether the generic app bar is rendered
// (screens with their own header hide it) and whether the tab bar should stay
// hidden for immersive screens (chat, browser, workspace…).
//
// Routes that only need a title fall back to config/mobile.js →
// MOBILE_ROUTE_TITLES, so this helper is used just where the defaults are not
// enough.
// ─────────────────────────────────────────────────────────────────────────────
function mobile(title: string, tab = 'more', extra: Record<string, any> = {}) {
  return { mobile: { title, tab, ...extra } }
}

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
      // Both render the welcome screen (management dashboard).
      path: '/',
      name: 'root',
      component: AppRouteView,
      meta: { app: WELCOME_APP, ...mobile('Home', 'home', { hideTopBar: true }) }
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
      component: SolopreneurView,
      meta: { ...mobile('Solopreneur', 'more', { fullScreen: true, hideTopBar: true, hideTabs: true }) }
    },
    {
      // Home — the welcome screen for "/<project_name>".
      // The dashboard initialises its project filter to THIS project (the URL
      // segment is the single source of truth for "where am I working").
      path: '/:projectName',
      name: 'home',
      component: AppRouteView,
      meta: { app: WELCOME_APP, ...mobile('Home', 'home', { hideTopBar: true }) }
    },
    {
      // Chat routes: router mode
      path: '/:projectName/chats',
      name: 'chats',
      component: ChatsView,
      meta: { ...mobile('Chats', 'chats', { hideTopBar: true }) }
    },
    {
      // "New chat" is a dedicated route instead of sending people to the
      // management dashboard (the old mobile bottom bar did exactly that).
      // QuickChatView with no :chatId is the composer/home surface.
      path: '/:projectName/new-chat',
      name: 'new-chat',
      component: QuickChatView,
      meta: { ...mobile('New chat', 'chats') }
    },
    {
      path: '/:projectName/chats/:chatId/:chatName',
      name: 'chat',
      component: QuickChatView,
      meta: { ...mobile('Chat', 'chats', { hideTopBar: true, hideTabs: true }) }
    },
    {
      path: '/:projectName/chats/:chatId/:chatName/workspace/:workspaceId/:workspaceName',
      name: 'chat-workspace',
      component: QuickChatView,
      meta: { ...mobile('Chat', 'chats', { hideTopBar: true, hideTabs: true }) }
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
      component: MeetView,
      meta: { ...mobile('Meeting', 'more', { hideTabs: true }) }
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
      component: WorkspaceView,
      meta: { ...mobile('Workspace', 'more', { hideTabs: true }) }
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
      component: BrowsersSessionManager,
      meta: { ...mobile('Browser', 'more', { hideTabs: true }) }
    },
    {
      // The optional board id + name segments let the URL carry the open board,
      // so a refresh or a back-navigation (non-desktop / single mode) reopens it.
      // Both are optional: the plain "/:projectName/kanban" still works.
      path: '/:projectName/kanban/:board?/:boardName?',
      name: 'kanban',
      component: KanbanBoardView,
      meta: { ...mobile('Task manager', 'tasks', { hideTopBar: true }) }
    },
    {
      path: '/:projectName/messenger',
      name: 'messenger',
      component: MessengerView,
      meta: { ...mobile('Messenger', 'chats', { hideTopBar: true, hideTabs: true }) }
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
    { path: '/:projectName/file-viewer/:filePath(.*)*', name: 'file-viewer', component: AppRouteView, meta: { app: 'file-viewer', ...mobile('File', 'more', { hideTabs: true }) } },
    { path: '/:projectName/logs', name: 'log-viewer', component: AppRouteView, meta: { app: 'log-viewer' } },
    { path: '/:projectName/chat-logs', name: 'chat-logs', component: AppRouteView, meta: { app: 'chat-logs' } },
    { path: '/:projectName/decision-model-logs', name: 'decision-model-logs', component: AppRouteView, meta: { app: 'decision-model-logs' } },
    { path: '/:projectName/metrics', name: 'metrics', component: AppRouteView, meta: { app: 'metrics' } },
    // Management dashboard — the cross-project "command center" for management:
    // work status, blockers, delivery forecast, team load and AI cost across
    // EVERY project, for a selectable time window (last 7 days by default) and
    // a selectable SET of projects (header filter, initialised from the route).
    // Same pattern as the other screens: <AppRouteView> resolves meta.app from
    // config/appComponentsMap.js and, on desktop, the very same key opens a
    // dockview panel (config/apps.js → management-dashboard).
    { path: '/:projectName/management-dashboard', name: 'management-dashboard', component: AppRouteView, meta: { app: 'management-dashboard', ...mobile('Management', 'home', { hideTopBar: true }) } },
    // Per-request API performance (latency / throughput / errors) recorded by the
    // backend and served from /api/api-logs/*. Same pattern as every other app:
    // <AppRouteView> resolves meta.app, and on desktop the very same key opens a
    // dockview panel (see config/apps.js + views/api-monitoring/).
    { path: '/:projectName/api-monitoring', name: 'api-monitoring', component: AppRouteView, meta: { app: 'api-monitoring' } },
    { path: '/:projectName/infra', name: 'infra', component: AppRouteView, meta: { app: 'infra' } },
    // Activity wall (components/wall/Wall.vue). It used to be the mobile home;
    // it now has a route of its own so the sidebar "Activity" item
    // (config/apps.js → activity) still opens it.
    // Activity is an app with its own bottom navigation (WallBottomNav); the
    // mobile shell gives it the whole viewport below the status bar.
    { path: '/:projectName/activity', name: 'activity', component: AppRouteView, meta: { app: 'activity', ...mobile('Activity', 'activity', { hideTopBar: true, hideTabs: true }) } },
    // Git repository view (branches, commits, merges and working-tree diffs).
    // The screen already exists (components/repo/GitView.vue) and is registered
    // in config/appComponentsMap.js as 'git-view'; only the route was missing,
    // which made the sidebar "Git" item a no-op in single / mobile mode. Same
    // pattern as every other app: <AppRouteView> resolves meta.app, and on
    // desktop the very same key opens a dockview panel.
    { path: '/:projectName/git-view', name: 'git-view', component: AppRouteView, meta: { app: 'git-view' } },
    { path: '/:projectName/team-channel/:channelId', name: 'team-channel', component: AppRouteView, meta: { app: 'team-channel', ...mobile('Channel', 'chats', { hideTabs: true }) } },
    { path: '/:projectName/team-dm/:dmId', name: 'team-dm', component: AppRouteView, meta: { app: 'team-dm', ...mobile('Direct message', 'chats', { hideTabs: true }) } },
    { path: '/:projectName/team-media-library/:teamId', name: 'team-media-library', component: AppRouteView, meta: { app: 'team-media-library' } },

    {
      // Desktop / team view (dockview panels)
      path: '/:projectName/desktop/:pathMatch(.*)*',
      name: 'codx-junior-split',
      component: Desktop,
      meta: { ...mobile('Desktop', 'more', { hideTopBar: true, hideTabs: true }) }
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
  // The dockview workspace is not a mobile screen. A deep link (or a stale
  // "desktop" link shared from a desktop) lands on the mobile home instead of
  // rendering a window manager that cannot be used with a finger.
  if ($storex.ui.isMobile && to.name === 'codx-junior-split') {
    const projectName = activeProjectSegment()
    return projectName
      ? { name: 'home', params: { projectName }, replace: true }
      : { name: 'root', replace: true }
  }

  return router.$navigation.onRouteChanged({ from, to })
})

$storex.$router = router
$storex.$navigation = router.$navigation

export default router
