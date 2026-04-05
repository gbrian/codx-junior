<script setup>
import {
  MenubarContent,
  MenubarMenu,
  MenubarPortal,
  MenubarRoot,
  MenubarTrigger,
} from 'reka-ui'
import MenubarItem from './MenubarItem.vue'
import WorkspacesMenu from './WorkspacesMenu.vue';
import SettingsMenu from  './SettingsMenu.vue';
import ProjectLabel from './ProjectLabel.vue';
import ProjectDetailt from '../ProjectDetailt.vue';
</script>

<template>
  <MenubarRoot
    class="flex p-[3px] rounded-lg shadow-sm"
  >
    <MenubarMenu class="MenubarMenu">
      <MenubarTrigger
        class="click py-2 px-3 text-xl select-none font-bold leading-none border border-white/30 rounded flex items-center justify-between gap-2 tooltip"
        :data-tip="$storex.session.connected ? '' : 'API is not connected!'"
        v-if="$project"
      >
        <ProjectLabel :project="$project"
          :class="[!$storex.session.connected && 'disabled']"
        />
        <span class="text-error animate-pulse"
          v-if="!$storex.session.connected"
        >
          <i class="fa-solid fa-circle-exclamation"></i>
        </span>
      </MenubarTrigger>
      <MenubarPortal>
        <MenubarContent
          class="py-4 min-w-60 outline-none bg-base-100 rounded-lg px-2 pb-4 border border-white/30 shadow-sm [animation-duration:_400ms] [animation-timing-function:_cubic-bezier(0.16,_1,_0.3,_1)] will-change-[transform,opacity]"
          :side-offset="5"
          :align-offset="-3"
        >
          <ProjectDetailt @click.stop=""
            :project="$project" 
            :options="{ folders: true, showIcon: true }"
            @select="$projects.setActiveProject($event)"
          />

          <MenubarItem @click="$ui.setActiveTab('home')">
            <i class="fa-solid fa-home"></i>
            Home
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
          <div class="divider"></div>
          <WorkspacesMenu />
          <div class="divider"></div>
          <MenubarItem @click="$ui.setActiveTab('settings')"
            v-if="$users.isProjectAdmin">
            <i class="fa-solid fa-sliders"></i>
            Project
          </MenubarItem>
          <SettingsMenu />
        </MenubarContent>
      </MenubarPortal>
    </MenubarMenu>
  </MenubarRoot>
</template>
