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
</script>
<template>
  <CodeEditorVue v-bind="$attrs" v-if="$ui.isMobile && $ui.showCoder" />
  <KanbanVue v-bind="$attrs" v-if="$ui.tabIx === 'tasks'" />
  <NoVNCVue v-bind="$attrs" v-if="$ui.isMobile && $ui.showBrowser" />
  <KnowledgeViewVue class="" v-bind="$attrs" v-if="$ui.tabIx === 'knowledge'" />
  <KnowledgeSettingsVue class="" v-bind="$attrs" v-if="$ui.tabIx === 'knowledge_settings'" />
  <WikiViewVue v-bind="$attrs" v-if="$ui.tabIx == 'wiki'"></WikiViewVue>
  <ProjectSettingsVue  v-bind="$attrs" v-if="$ui.tabIx === 'settings'" />
  <GlobalSettingsVue v-bind="$attrs" v-if="$ui.tabIx === 'global-settings'" />
  <ProfileViewVue v-bind="$attrs" v-if="$ui.tabIx === 'profiles'" />
  <ProjectProfileVue v-bind="$attrs" v-if="$ui.tabIx == 'home'" />
  <Files class="w-full h-full" v-if="$ui.tabIx == 'files'" />
  <HelpView class="w-full h-full" v-if="$ui.tabIx == 'help'" />
  <PRView class="w-full h-full" v-if="$ui.tabIx == 'prview'" />
  <MetricsViewer class="w-full h-full" v-if="$ui.tabIx == 'metrics'" />
</template>
<script>
export default {
}
</script>