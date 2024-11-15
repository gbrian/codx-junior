<script setup>
import KnowledgeViewVue from "../views/KnowledgeView.vue";
import ProfileViewVue from "../views/ProfileView.vue";
import ProjectProfileVue from "../views/ProjectProfile.vue";
import ProjectSettingsVue from "../views/ProjectSettings.vue";
import WikiViewVue from "../views/WikiView.vue";
import GlobalSettingsVue from "../views/GlobalSettings.vue";
import CodeEditorVue from "./CodeEditor.vue";
import KanbanVue from "./kanban/Kanban.vue";
import NoVNCVue from "./NoVNC.vue";
import LogViewerVue from "./LogViewer.vue";
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
  <modal v-if="$ui.showLogs">
    <LogViewerVue class="text-xs 2xl:text-md bg-base-300 p-2 2xl:p-10" v-bind="$attrs" />
  </modal>
</template>
<script>
export default {
}
</script>