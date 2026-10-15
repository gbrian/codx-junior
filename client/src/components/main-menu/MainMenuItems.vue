<script setup>
import MenubarItem from './MenubarItem.vue'
import WorkspacesMenu from './WorkspacesMenu.vue'
import SettingsMenu from './SettingsMenu.vue'
import MenuDivider from './MenuDivider.vue'
</script>

<template>
  <MenubarItem @click="$ui.setActiveTab('home')">
    <i class="fa-solid fa-home"></i>
    Home
  </MenubarItem>
  <MenubarItem @click="$ui.setActiveTab('activity')">
    <i class="fa-solid fa-clock-rotate-left"></i>
    Activity
  </MenubarItem>
  <MenubarItem @click="$ui.showNewProject(true)">
    <i class="fa-solid fa-plus"></i>
    New project
  </MenubarItem>
  <MenubarItem @click="$ui.setActiveTab('wiki')">
    <i class="fa-solid fa-graduation-cap"></i> Wiki
  </MenubarItem>
  <MenubarItem @click="$ui.setActiveTab('tasks')">
    <i class="fa-brands fa-trello"></i>
    Task manager
  </MenubarItem>
  <MenubarItem @click="$ui.openPlanning()">
    <i class="fa-solid fa-diagram-project"></i>
    Planning
  </MenubarItem>
  <MenubarItem @click="$ui.setActiveTab('team')">
    <i class="fa-solid fa-people-group"></i>
    Team
  </MenubarItem>
  <MenubarItem @click="$ui.openMeet()">
    <i class="fa-solid fa-video"></i>
    Meet
  </MenubarItem>
  <MenubarItem @click="$ui.setActiveTab('file-explorer')">
    <i class="fa-regular fa-folder-open"></i>
    File explorer
  </MenubarItem>
  <MenubarItem @click="$ui.setActiveTab('browser-sessions')">
    <i class="fa-regular fa-compass"></i> Browser sessions
  </MenubarItem>
  <MenubarItem @click="$ui.openGitView()">
    <i class="fa-solid fa-code-branch"></i> Git
  </MenubarItem>
  <MenubarItem @click="$ui.setActiveTab('profiles')"
    v-if="$users.isProjectAdmin">
    <i class="fa-solid fa-id-badge"></i>
    Profiles
  </MenubarItem>
  <MenubarItem @click="$ui.setActiveTab('knowledge')"
    v-if="$users.isProjectAdmin">
    <i class="fa-solid fa-magnifying-glass"></i>
    Knowledge
  </MenubarItem>
  <MenubarItem @click="$ui.setActiveTab('analytics')">
    <i class="fa-solid fa-chart-area"></i>
    Analytics
  </MenubarItem>
  <MenuDivider />
  <WorkspacesMenu />
  <MenuDivider />
  <SettingsMenu />
  <MenuDivider />
  <MenubarItem>
    <a
      class="flex gap-1 tooltip text-error"
      data-tip="Log out"
      @click.stop="$users.logout()">
      <i class="fa-solid fa-right-from-bracket"></i>
      Log out
    </a>
  </MenubarItem>
</template>