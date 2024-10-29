<script setup>
import KnowledgeViewVue from "../views/KnowledgeView.vue";
import ProfileViewVue from "../views/ProfileView.vue";
import ProjectProfileVue from "../views/ProjectProfile.vue";
import ProjectSettingsVue from "../views/ProjectSettings.vue";
import WikiViewVue from "../views/WikiView.vue";
import CoderVue from "./apps/Coder.vue";
import GlobalSettingsVue from "../views/GlobalSettings.vue";
import CodeEditorVue from "./CodeEditor.vue";
import KanbanVue from "./kanban/Kanban.vue";
import NoVNCVue from "./NoVNC.vue";
import LogViewerVue from "./LogViewer.vue";
</script>
<template>
  <CodeEditorVue v-bind="$attrs" v-if="$ui.tabIx === 'editor'" />
  <KanbanVue v-bind="$attrs" v-if="$ui.tabIx === 'tasks'" />
  <CoderVue v-bind="$attrs" v-if="showCoder" />
  <NoVNCVue v-bind="$attrs" v-if="showPreview" />
  <KnowledgeViewVue v-bind="$attrs" v-if="$ui.tabIx === 'knowledge'" />
  <WikiViewVue v-bind="$attrs" v-if="$ui.tabIx == 'wiki'"></WikiViewVue>
  <ProjectSettingsVue  v-bind="$attrs" v-if="$ui.tabIx === 'settings'" />
  <GlobalSettingsVue v-bind="$attrs" v-if="$ui.tabIx === 'global-settings'" />
  <ProfileViewVue v-bind="$attrs" v-if="$ui.tabIx === 'profiles'" />
  <ProjectProfileVue v-bind="$attrs" v-if="$ui.tabIx == 'home'" />
  <LogViewerVue v-bind="$attrs" v-if="$ui.tabIx == 'logs'" />
</template>
<script>
export default {
  computed: {
    showCoder () {
      const { isMobile, tabIx, showApp } = this.$ui
      return isMobile && tabIx === 'app' && showApp == 'coder'
    },
    showPreview () {
      const { isMobile, tabIx, showApp } = this.$ui
      return isMobile && tabIx === 'app' && showApp == 'preview'
    }
  }
}
</script>