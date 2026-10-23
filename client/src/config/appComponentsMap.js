// Shared app-to-component mapping for desktop views
//
// Every app screen is code-split: `AppRouteView` resolves the component from
// this map at render time, and importing all of them eagerly put the entire
// application (plus the monaco / syntax-highlighting graph behind it) into the
// entry chunk.
import { defineAsyncComponent } from 'vue'

// Small desktop shell helpers stay eager: they are cheap and rendered with the
// first paint of the desktop layout.
import ViewProperties from '../components/main-menu/ViewProperties.vue'
import EmptyStateWelcome from '../components/desktop/EmptyStateWelcome.vue'
import Tab from '../components/desktop/Tab.vue'

const lazy = (loader) => defineAsyncComponent(loader)

// Component registration map
export const APP_COMPONENTS_MAP = {
  'window': lazy(() => import('../components/desktop/Window.vue')),
  'app-window': lazy(() => import('../components/windowManager/AppWindow.vue')),
  'workspace': lazy(() => import('../components/windowManager/AppWindow.vue')),
  'browser-sessions': lazy(() => import('../components/browsers/BrowserSessionList.vue')),
  'log-viewer': lazy(() => import('../components/LogViewer.vue')),
  'knowledge': lazy(() => import('../views/KnowledgeView.vue')),
  'knowledge_settings': lazy(() => import('../views/KnowledgeSettings.vue')),
  'team': lazy(() => import('../views/TeamView.vue')),
  'home': lazy(() => import('../views/CodxWelcomeView.vue')),
  'settings': lazy(() => import('../views/ProjectSettings.vue')),
  'wiki': lazy(() => import('../views/WikiView.vue')),
  'docs': lazy(() => import('../views/DocsView.vue')),
  'global-settings': lazy(() => import('../views/GlobalSettings.vue')),
  'tasks': lazy(() => import('../components/kanban/board/KanbanBoardView.vue')),
  'metrics': lazy(() => import('../components/metrics/MetricsViewer.vue')),
  'account': lazy(() => import('../components/security/AccountSettings.vue')),
  'file-explorer': lazy(() => import('../components/filebrowser/FileExplorerPanel.vue')),
  'file-viewer': lazy(() => import('../components/filebrowser/FileViewer.vue')),
  'git-view': lazy(() => import('../components/repo/GitView.vue')),
  'messenger': lazy(() => import('../views/MessengerView.vue')),
  'meet': lazy(() => import('../views/MeetView.vue')),
  'projects': lazy(() => import('../components/project/ProjectOverview.vue')),
  'activity': lazy(() => import('../components/wall/Wall.vue')),
  'chat': lazy(() => import('../views/ChatView.vue')),
  'analytics': lazy(() => import('../components/analytics/MetricsDashboard.vue')),
  'chat-logs': lazy(() => import('../components/logs/LogsAnalyzerDashboard.vue')),
  'decision-model-logs': lazy(() => import('../components/DecisionModelLogs.vue')),
  'team-channel': lazy(() => import('../components/teams/TeamChannel.vue')),
  'team-dm': lazy(() => import('../components/teams/TeamDM.vue')),
  'team-media-library': lazy(() => import('../components/teams/TeamMediaLibrary.vue')),
  'vibe-coding': lazy(() => import('../views/VibeCodingView.vue')),
  'workspaces': lazy(() => import('../components/workspaces/WorkspacesManager.vue')),
  'infra': lazy(() => import('../views/infra/InfraView.vue')),
  // Solopreneur mode as a desktop panel (single/mobile mode uses the
  // "/solopreneur" route — see router/index.ts).
  'solopreneur': lazy(() => import('../views/SolopreneurView.vue'))
}

// Additional components not mapped to apps
export const ADDITIONAL_COMPONENTS = {
  ViewProperties,
  EmptyStateWelcome,
  tabComponent: Tab
}

// Combined map for Vue component registration
export const ALL_COMPONENTS = {
  ...APP_COMPONENTS_MAP,
  ...ADDITIONAL_COMPONENTS
}

export default APP_COMPONENTS_MAP