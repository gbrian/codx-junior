<script setup>
import KnowledgeViewVue from "../views/KnowledgeView.vue";
import ProfileViewVue from "../views/ProfileView.vue";
import ProjectProfileVue from "../views/ProjectProfile.vue";
import ProjectSettingsVue from "../views/ProjectSettings.vue";
import WikiViewVue from "../views/WikiView.vue";
import CoderVue from "./apps/Coder.vue";
import GlobalSettingsVue from "./board/GlobalSettings.vue";
import CodeEditorVue from "./CodeEditor.vue";
import KanbanVue from "./kanban/Kanban.vue";
import NoVNCVue from "./NoVNC.vue";
</script>
<template>
  <CodeEditorVue v-if="$ui.tabIx === 'editor'" />
  <KanbanVue v-if="$ui.tabIx === 'tasks'" />
  <KnowledgeViewVue v-if="$ui.tabIx === 'knowledge'" />
  <WikiViewVue v-if="$ui.tabIx == 'wiki'"></WikiViewVue>
  <ProjectSettingsVue  v-if="$ui.tabIx === 'settings'" />
  <GlobalSettingsVue v-if="$ui.tabIx === 'global-settings'" />
  <ProfileViewVue v-if="$ui.tabIx === 'profiles'" />
  <ProjectProfileVue v-if="$ui.tabIx == 'home'" />
  <CoderVue v-bind="$attrs" v-if="$ui.tabIx == 'coder'" />
  <NoVNCVue v-if="$ui.tabIx == 'preview'" />    
</template>