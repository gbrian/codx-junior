<script setup>
import KnowledgeViewVue from "../views/KnowledgeView.vue"
import ProfileViewVue from "../views/ProfileView.vue"
import ProjectProfileVue from "../views/ProjectProfile.vue"
import ProjectSettingsVue from "../views/ProjectSettings.vue"
import WikiViewVue from "../views/WikiView.vue"
import GlobalSettingsVue from "../views/GlobalSettings.vue"
import CodeEditorVue from "./CodeEditor.vue"
import KanbanVue from "./kanban/Kanban.vue"
import NoVNCVue from "./NoVNC.vue"
import LogViewerVue from "./LogViewer.vue"
import Files from "./apps/Files.vue"
</script>
<template>
  <CodeEditorVue v-bind="$attrs" v-if="$ui.isMobile && $ui.showCoder" />
  <KanbanVue v-bind="$attrs" v-if="$ui.tabIx === 'tasks'" />
  <NoVNCVue v-bind="$attrs" v-if="$ui.isMobile && $ui.showBrowser" />
  <KnowledgeViewVue class="lg:w-2/3" v-bind="$attrs" v-if="$ui.tabIx === 'knowledge'" />
  <WikiViewVue v-bind="$attrs" v-if="$ui.tabIx == 'wiki'"></WikiViewVue>
  <ProjectSettingsVue  v-bind="$attrs" v-if="$ui.tabIx === 'settings'" />
  <GlobalSettingsVue v-bind="$attrs" v-if="$ui.tabIx === 'global-settings'" />
  <ProfileViewVue v-bind="$attrs" v-if="$ui.tabIx === 'profiles'" />
  <ProjectProfileVue v-bind="$attrs" v-if="$ui.tabIx == 'home'" />
  <Files class="w-full h-full" v-if="$ui.tabIx == 'files'" />
  <LogViewerVue class="text-xs bg-base-300 p-2 absolute top-0 left-0 right-0 bottom-0" v-bind="$attrs" v-if="$ui.showLogs" />
</template>
<script>
export default {
}
</script>