<script setup>
import {
  MenubarMenu,
  MenubarTrigger,
  MenubarContent,
  MenubarPortal,
} from 'reka-ui'
import MenubarItem from '@/components/main-menu/MenubarItem.vue'
import MenuDivider from '@/components/main-menu/MenuDivider.vue'
</script>

<template>
  <MenubarMenu>
    <MenubarTrigger
      class="click py-1 px-2 text-sm select-none leading-none border border-white/20 rounded flex items-center gap-2 hover:bg-base-200 transition-all tooltip"
      data-tip="Switch role view"
    >
      <i :class="activeRole.icon" :style="{ color: activeRole.color }"></i>
      <span class="hidden @lg:inline text-xs font-medium">{{ activeRole.label }}</span>
      <i class="fa-solid fa-chevron-down text-xs opacity-50"></i>
    </MenubarTrigger>
    <MenubarPortal>
      <MenubarContent
        class="py-2 min-w-56 outline-none bg-base-100 rounded-lg px-2 border border-white/30 shadow-lg z-50"
        :side-offset="5"
      >
        <div class="px-2 py-1 text-xs font-bold text-base-content-ERROR-40 uppercase tracking-wider mb-1">
          Role Presets
        </div>

        <div
          v-for="role in roles" :key="role.id"
          class="flex items-center gap-3 px-2 py-2 rounded-lg cursor-pointer hover:bg-base-200 transition-all group"
          :class="{ 'bg-primary/10 border border-primary/30': activeRoleId === role.id }"
          @click="selectRole(role)"
        >
          <div
            class="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm flex-shrink-0"
            :style="{ backgroundColor: role.color }">
            <i :class="role.icon"></i>
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium">{{ role.label }}</div>
            <div class="text-xs text-base-content/50 truncate">{{ role.desc }}</div>
          </div>
          <i
            v-if="activeRoleId === role.id"
            class="fa-solid fa-check text-primary text-xs flex-shrink-0"
          ></i>
        </div>

        <MenuDivider />

        <MenubarItem @click="$ui.setActiveTab('account')">
          <i class="fa-solid fa-sliders"></i>
          Account Settings
        </MenubarItem>
      </MenubarContent>
    </MenubarPortal>
  </MenubarMenu>
</template>

<script>
const ROLES = [
  {
    id: 'pm',
    label: 'Project Manager',
    desc: 'Tasks, activity & analytics',
    icon: 'fa-solid fa-chart-gantt',
    color: '#6366f1'
  },
  {
    id: 'designer',
    label: 'Designer / Vibe Coder',
    desc: 'Chats, files & AI profiles',
    icon: 'fa-solid fa-wand-magic-sparkles',
    color: '#a855f7'
  },
  {
    id: 'developer',
    label: 'FullStack Developer',
    desc: 'Code, tasks, logs & knowledge',
    icon: 'fa-solid fa-code',
    color: '#22c55e'
  },
  {
    id: 'business',
    label: 'Business User',
    desc: 'Overview, reports & docs',
    icon: 'fa-solid fa-briefcase',
    color: '#0ea5e9'
  }
]

const STORAGE_KEY = 'codx-user-role'

export default {
  data() {
    return {
      roles: ROLES,
      activeRoleId: localStorage.getItem(STORAGE_KEY) || 'developer'
    }
  },
  computed: {
    activeRole() {
      return this.roles.find(r => r.id === this.activeRoleId) || this.roles[2]
    }
  },
  methods: {
    selectRole(role) {
      this.activeRoleId = role.id
      localStorage.setItem(STORAGE_KEY, role.id)
      // Navigate home tab which will render the role-specific view
      this.$ui.setActiveTab('home')
      // Emit for CodxWelcomeView to react
      this.$storex.ui.setUserRole(role.id)
    }
  }
}
</script>