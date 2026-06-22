<script setup>
import {
  MenubarContent,
  MenubarMenu,
  MenubarPortal,
  MenubarRoot,
  MenubarTrigger,
} from 'reka-ui'
import MenubarItem from './MenubarItem.vue'
import WorkspacesMenu from './WorkspacesMenu.vue'
import SettingsMenu from './SettingsMenu.vue'
import MenuDivider from './MenuDivider.vue'
import ViewsMenu from './ViewsMenu.vue'
</script>

<template>
  <div class="flex gap-2 items-center">
    <MenubarRoot
      class="flex p-[3px]"
    >
      <MenubarMenu class="MenubarMenu">
        <MenubarTrigger
          class="click py-2 px-3 text-xl select-none font-bold leading-none flex items-center justify-between gap-2 tooltip"
          :data-tip="$storex.session.connected ? '' : 'API is not connected!'"
        >

          <div class="p-2 relative click select-none font-bold leading-none border border-white/30 rounded flex items-center justify-between gap-2 indicator">
            <span class="absolute left-6 -top-2 text-error animate-pulse tooltip" 
              title="API disconnected!"
              v-if="!$storex.session.connected">
              <i class="fa-solid fa-circle-exclamation"></i>
            </span>
            <div class="avatar">
              <img class="w-6 rpounded-full" src="/only_icon.png" />
            </div>
          </div>
          
        </MenubarTrigger>
        <MenubarPortal>
          <MenubarContent
            class="py-4 min-w-60 outline-none bg-base-100 rounded-lg px-2 pb-4 border border-white/30 shadow-sm [animation-duration:_400ms] [animation-timing-function:_cubic-bezier(0.16,_1,_0.3,_1)] will-change-[transform,opacity]"
            :side-offset="5"
            :align-offset="-3"
          >
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
            <MenubarItem @click="$ui.setActiveTab('team')">
              <i class="fa-solid fa-people-group"></i>
              Team
            </MenubarItem>
            <MenubarItem @click="$ui.setActiveTab('file-finder')">
              <i class="fa-regular fa-folder-open"></i>
              File explorer
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
            <!-- Views submenu -->
            <ViewsMenu />
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
          </MenubarContent>
        </MenubarPortal>
      </MenubarMenu>
    </MenubarRoot>
  </div>
</template>

<script>
export default {
}
</script>