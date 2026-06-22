<script setup>
import Window from './Window.vue'
import AppWindow from '../windowManager/AppWindow.vue'
import LogViewer from '../LogViewer.vue'
import KnowledgeViewVue from "../../views/KnowledgeView.vue"
import KnowledgeSettingsVue from "../../views/KnowledgeSettings.vue"
import ProfileViewVue from "../../views/ProfileView.vue"
import CodxWelcomeView from "../../views/CodxWelcomeView.vue"
import ProjectSettingsVue from "../../views/ProjectSettings.vue"
import WikiViewVue from "../../views/WikiView.vue"
import DocsViewVue from "../../views/DocsView.vue"
import GlobalSettingsVue from "../../views/GlobalSettings.vue"
import KanbanContainerVue from "../kanban/KanbanContainer.vue"
import Files from "../apps/Files.vue"
import MetricsViewer from "../metrics/MetricsViewer.vue"
import AccountSettings from '../security/AccountSettings.vue'
import FileFinderVue from '../filebrowser/FileFinder.vue'
import ProjectOverview from "../project/ProjectOverview.vue"
import Wall from "../wall/Wall.vue"
import ChatView from '@/views/ChatView.vue'
import ViewProperties from '../main-menu/ViewProperties.vue'
import AnalyticsDashboard from '../analytics/index.vue'
import LogsAnalyzerDashboard from '../logs/LogsAnalyzerDashboard.vue'
import TeamChannel from '../teams/TeamChannel.vue'
import TeamDM from '../teams/TeamDM.vue'
import TeamMediaLibrary from '../teams/TeamMediaLibrary.vue'
import VibeCodingView from '@/views/VibeCodingView.vue'
import EmptyStateWelcome from './EmptyStateWelcome.vue'
</script>

<template>
  <div class="w-full h-full relative">
    <!-- Single app view container - renders activeApp only -->
    <div v-if="activeApp" class="w-full h-full">
      <component 
        :is="activeApp.component || 'app-window'" 
        :params="{ ...activeApp.params, app: activeApp, tabName: activeApp.name }"
        class="w-full h-full"
      />
    </div>

    <!-- Welcome state when no app is active -->
    <div v-else class="w-full h-full">
      <EmptyStateWelcome />
    </div>

    <!-- ViewProperties modal -->
    <modal close="true" @close="closeViewEditor" v-if="viewEditor">
      <ViewProperties
        :view="viewEditor.view"
        @close="closeViewEditor"
        @confirm="closeViewEditor"
      />
    </modal>
  </div>
</template>

<script>
export default {
  name: 'VibeDesktop',
  components: {
    'window': Window,
    'app-window': AppWindow,
    'log-viewer': LogViewer,
    'knowledge': KnowledgeViewVue,
    'knowledge_settings': KnowledgeSettingsVue,
    'profiles': ProfileViewVue,
    'home': CodxWelcomeView,
    'settings': ProjectSettingsVue,
    'wiki': WikiViewVue,
    'docs': DocsViewVue,
    'global-settings': GlobalSettingsVue,
    'tasks': KanbanContainerVue,
    'files': Files,
    'metrics': MetricsViewer,
    'account': AccountSettings,
    'file-finder': FileFinderVue,
    'projects': ProjectOverview,
    'activity': Wall,
    'chat': ChatView,
    'analytics': AnalyticsDashboard,
    'chat-logs': LogsAnalyzerDashboard,
    'team-channel': TeamChannel,
    'team-dm': TeamDM,
    'team-media-library': TeamMediaLibrary,
    'vibe-coding': VibeCodingView,
    ViewProperties,
    EmptyStateWelcome
  },
  computed: {
    activeApp() {
      return this.$storex.ui.activeApp
    },
    viewEditor() {
      return this.$storex.ui.viewEditor
    }
  },
  methods: {
    closeViewEditor() {
      this.$storex.ui.closeViewEditor()
    }
  }
}
</script>