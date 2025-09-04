<script setup>
import KnowledgeViewVue from "../views/KnowledgeView.vue"
import KnowledgeSettingsVue from "../views/KnowledgeSettings.vue"
import ProfileViewVue from "../views/ProfileView.vue"
import CodxWelcomeView from "../views/CodxWelcomeView.vue"
import ProjectSettingsVue from "../views/ProjectSettings.vue"
import WikiViewVue from "../views/WikiView.vue"
import DocsViewVue from "../views/DocsView.vue"
import GlobalSettingsVue from "../views/GlobalSettings.vue"
import CodeEditorVue from "./CodeEditor.vue"
import KanbanVue from "./kanban/Kanban.vue"
import Files from "./apps/Files.vue"
import MetricsViewer from "./metrics/MetricsViewer.vue"
import PreviewVue from "./apps/Preview.vue"
import AccountSettings from './security/AccountSettings.vue'
import FileFinderVue from './filebrowser/FileFinder.vue'
</script>
<template>
  <CodeEditorVue v-bind="$attrs" v-if="$ui.isMobile && $ui.showCoder" :class="$ui.activeTab" />
  <KanbanVue v-if="$ui.activeTab === 'tasks'" />
  <KnowledgeViewVue class="" v-bind="$attrs" v-if="$ui.activeTab === 'knowledge'" :class="$ui.activeTab" />
  <KnowledgeSettingsVue class="px-2" v-bind="$attrs" v-if="['knowledge_settings', 'wiki_settings'].includes($ui.activeTab)" :class="$ui.activeTab" />
  <WikiViewVue v-bind="$attrs" v-if="$ui.activeTab == 'wiki'"></WikiViewVue>
  <DocsViewVue v-bind="$attrs" v-if="$ui.activeTab == 'docs'"></DocsViewVue>
  <ProjectSettingsVue  v-bind="$attrs" v-if="$ui.activeTab === 'settings'" :class="$ui.activeTab" />
  <GlobalSettingsVue v-bind="$attrs" v-if="$ui.activeTab === 'global-settings'" :class="$ui.activeTab" />
  <ProfileViewVue v-bind="$attrs" v-if="$ui.activeTab === 'profiles'" :class="$ui.activeTab" />
  <CodxWelcomeView v-bind="$attrs" v-if="$ui.activeTab == 'home'" :class="$ui.activeTab" />
  <Files class="w-full h-full" v-if="$ui.activeTab == 'files'" :class="$ui.activeTab" />
  <MetricsViewer class="w-full h-full" v-if="$ui.activeTab == 'metrics'" :class="$ui.activeTab" />
  <PreviewVue class="h-full w-full" :token="$ui.monitorToken" v-if="$ui.showBrowser && $ui.isMobile" />
  <FileFinderVue v-if="$ui.activeTab === 'file-finder'" />
  <AccountSettings v-if="$ui.activeTab == 'account'" :class="$ui.activeTab" />

</template>
<script>
export default {
  computed: {
  }
}
</script>