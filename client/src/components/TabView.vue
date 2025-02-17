<script setup>
import KnowledgeViewVue from "../views/KnowledgeView.vue"
import KnowledgeSettingsVue from "../views/KnowledgeSettings.vue"
import ProfileViewVue from "../views/ProfileView.vue"
import ProjectProfileVue from "../views/ProjectProfile.vue"
import ProjectSettingsVue from "../views/ProjectSettings.vue"
import WikiViewVue from "../views/WikiView.vue"
import GlobalSettingsVue from "../views/GlobalSettings.vue"
import CodeEditorVue from "./CodeEditor.vue"
import KanbanVue from "./kanban/Kanban.vue"
import NoVNCVue from "./NoVNC.vue"
import Files from "./apps/Files.vue"
import HelpView from "@/views/HelpView.vue"
import PRView from "@/views/PRView.vue"
import MetricsViewer from "./metrics/MetricsViewer.vue"
import PreviewVue from "./apps/Preview.vue"
</script>
<template>
  <CodeEditorVue v-bind="$attrs" v-if="$ui.isMobile && $ui.showCoder":class="$ui.tabIx" />
  <KanbanVue v-bind="$attrs" v-if="$ui.tabIx === 'tasks'":class="$ui.tabIx" />
  <KnowledgeViewVue class="" v-bind="$attrs" v-if="$ui.tabIx === 'knowledge'":class="$ui.tabIx" />
  <KnowledgeSettingsVue class="" v-bind="$attrs" v-if="$ui.tabIx === 'knowledge_settings'":class="$ui.tabIx" />
  <WikiViewVue v-bind="$attrs" v-if="$ui.tabIx == 'wiki'"></WikiViewVue>
  <ProjectSettingsVue  v-bind="$attrs" v-if="$ui.tabIx === 'settings'":class="$ui.tabIx" />
  <GlobalSettingsVue v-bind="$attrs" v-if="$ui.tabIx === 'global-settings'":class="$ui.tabIx" />
  <ProfileViewVue v-bind="$attrs" v-if="$ui.tabIx === 'profiles'":class="$ui.tabIx" />
  <ProjectProfileVue v-bind="$attrs" v-if="$ui.tabIx == 'home'":class="$ui.tabIx" />
  <Files class="w-full h-full" v-if="$ui.tabIx == 'files'":class="$ui.tabIx" />
  <HelpView class="w-full h-full" v-if="$ui.tabIx == 'help'":class="$ui.tabIx" />
  <PRView class="w-full h-full" v-if="$ui.tabIx == 'prview'":class="$ui.tabIx" />
  <MetricsViewer class="w-full h-full" v-if="$ui.tabIx == 'metrics'":class="$ui.tabIx" />
  <PreviewVue class="h-full w-full" :token="$ui.monitorToken" v-if="$ui.showBrowser && $ui.isMobile" />
</template>
<script>
export default {
}
</script>