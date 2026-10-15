// Shared app-to-component mapping for desktop views
import Window from '../components/desktop/Window.vue'
import AppWindow from '../components/windowManager/AppWindow.vue'
import LogViewer from '../components/LogViewer.vue'
import KnowledgeViewVue from '../views/KnowledgeView.vue'
import KnowledgeSettingsVue from '../views/KnowledgeSettings.vue'
import TeamViewVue from '../views/TeamView.vue'
import CodxWelcomeView from '../views/CodxWelcomeView.vue'
import ProjectSettingsVue from '../views/ProjectSettings.vue'
import WikiViewVue from '../views/WikiView.vue'
import DocsViewVue from '../views/DocsView.vue'
import GlobalSettingsVue from '../views/GlobalSettings.vue'
import MetricsViewer from '../components/metrics/MetricsViewer.vue'
import AccountSettings from '../components/security/AccountSettings.vue'
import FileExplorerPanel from '../components/filebrowser/FileExplorerPanel.vue'
import FileViewer from '../components/filebrowser/FileViewer.vue'
import ProjectOverview from '../components/project/ProjectOverview.vue'
import Wall from '../components/wall/Wall.vue'
import ChatView from '../views/ChatView.vue'
import ViewProperties from '../components/main-menu/ViewProperties.vue'
import MetricsDashboard from '../components/analytics/MetricsDashboard.vue'
import LogsAnalyzerDashboard from '../components/logs/LogsAnalyzerDashboard.vue'
import TeamChannel from '../components/teams/TeamChannel.vue'
import TeamDM from '../components/teams/TeamDM.vue'
import TeamMediaLibrary from '../components/teams/TeamMediaLibrary.vue'
import VibeCodingView from '../views/VibeCodingView.vue'
import WorkspacesManager from '../components/workspaces/WorkspacesManager.vue'
import EmptyStateWelcome from '../components/desktop/EmptyStateWelcome.vue'
import Tab from '../components/desktop/Tab.vue'
import KanbanBoardView from '../components/kanban/board/KanbanBoardView.vue'
import BrowserSessionList from '../components/browsers/BrowserSessionList.vue'
import MessengerView from '../views/MessengerView.vue'
import MeetView from '../views/MeetView.vue'
import GitView from '../components/repo/GitView.vue'

// Component registration map
export const APP_COMPONENTS_MAP = {
  'window': Window,
  'app-window': AppWindow,
  'workspace': AppWindow,
  'browser-sessions': BrowserSessionList,
  'log-viewer': LogViewer,
  'knowledge': KnowledgeViewVue,
  'knowledge_settings': KnowledgeSettingsVue,
  'team': TeamViewVue,
  'home': CodxWelcomeView,
  'settings': ProjectSettingsVue,
  'wiki': WikiViewVue,
  'docs': DocsViewVue,
  'global-settings': GlobalSettingsVue,
  'tasks': KanbanBoardView,
  'metrics': MetricsViewer,
  'account': AccountSettings,
  'file-explorer': FileExplorerPanel,
  'file-viewer': FileViewer,
  'git-view': GitView,
  'messenger': MessengerView,
  'meet': MeetView,
  'projects': ProjectOverview,
  'activity': Wall,
  'chat': ChatView,
  'analytics': MetricsDashboard,
  'chat-logs': LogsAnalyzerDashboard,
  'team-channel': TeamChannel,
  'team-dm': TeamDM,
  'team-media-library': TeamMediaLibrary,
  'vibe-coding': VibeCodingView,
  'workspaces': WorkspacesManager
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
