<script setup>
import MenubarItem from './MenubarItem.vue'
import WorkspacesMenu from './WorkspacesMenu.vue'
import SettingsMenu from './SettingsMenu.vue'
</script>

<template>
  <!-- Search -->
  <div class="p-3 border-b border-base-content/10">
    <label class="input input-sm input-bordered flex items-center gap-2 bg-base-100/60">
      <i class="fa-solid fa-magnifying-glass opacity-50"></i>
      <input
        v-model="search"
        type="text"
        class="grow bg-transparent"
        placeholder="Search apps & commands"
      />
      <button v-if="search" class="btn btn-ghost btn-xs" @click="search = ''">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </label>
  </div>

  <!-- Apps grid -->
  <div
    class="p-2 grid grid-cols-2 gap-1 text-sm"
    :class="mobile ? '' : 'overflow-y-auto max-h-[360px]'"
  >
    <MenubarItem
      v-for="item in filteredItems"
      :key="item.action"
      class="rounded-lg"
      @click="run(item)"
    >
      <i :class="item.icon" class="w-5 text-center"></i>
      {{ item.label }}
    </MenubarItem>

    <div v-if="!filteredItems.length" class="col-span-2 px-3 py-2 text-xs opacity-50">
      No results
    </div>

    <template v-if="!search">
      <div class="col-span-2 px-3 pt-3 pb-1 text-[11px] font-bold uppercase tracking-wide opacity-50">
        Workspaces
      </div>
      <div class="col-span-2">
        <WorkspacesMenu />
      </div>

      <div class="col-span-2 px-3 pt-3 pb-1 text-[11px] font-bold uppercase tracking-wide opacity-50">
        Settings
      </div>
      <div class="col-span-2">
        <SettingsMenu />
      </div>
    </template>
  </div>
</template>

<script>
export default {
  props: {
    // Mobile layout: drop the internal max-height/scroll so the whole
    // WindowsMenu sheet scrolls as a single unit instead of nested areas.
    mobile: { type: Boolean, default: false }
  },
  emits: ['close'],
  data() {
    return {
      search: '',
      items: [
        { label: 'Home', icon: 'fa-solid fa-home', action: 'home' },
        { label: 'New project', icon: 'fa-solid fa-plus', action: 'new-project' },
        { label: 'Wiki', icon: 'fa-solid fa-graduation-cap', action: 'wiki' },
        { label: 'Task manager', icon: 'fa-brands fa-trello', action: 'tasks' },
        { label: 'Planning', icon: 'fa-solid fa-diagram-project', action: 'planning' },
        { label: 'Team', icon: 'fa-solid fa-people-group', action: 'team' },
        { label: 'Meet', icon: 'fa-solid fa-video', action: 'meet' },
        { label: 'File explorer', icon: 'fa-regular fa-folder-open', action: 'file-explorer' },
        { label: 'Browser sessions', icon: 'fa-regular fa-compass', action: 'browser-sessions' },
        { label: 'Profiles', icon: 'fa-solid fa-id-badge', action: 'profiles', admin: true },
        { label: 'Knowledge', icon: 'fa-solid fa-magnifying-glass', action: 'knowledge', admin: true },
        { label: 'Analytics', icon: 'fa-solid fa-chart-area', action: 'analytics' },
        // Docker infrastructure (containers, stacks, images, volumes,
        // networks, events) — see config/apps.js → infra.
        // NOTE: `/api/infra/*` is admin-only on the backend; add
        // `admin: true` here once the role is enforced server-side.
        { label: 'Infrastructure', icon: 'fa-solid fa-server', action: 'infra' }
      ]
    }
  },
  computed: {
    isProjectAdmin() {
      return this.$users.isProjectAdmin
    },
    filteredItems() {
      const term = this.search.trim().toLowerCase()
      return this.items
        .filter(item => !item.admin || this.isProjectAdmin)
        .filter(item => !term || item.label.toLowerCase().includes(term))
    }
  },
  methods: {
    run(item) {
      const actions = {
        home: () => this.$ui.setActiveTab('home'),
        'new-project': () => this.$ui.showNewProject(true),
        wiki: () => this.$ui.setActiveTab('wiki'),
        tasks: () => this.$ui.setActiveTab('tasks'),
        planning: () => this.$ui.openPlanning(),
        team: () => this.$ui.setActiveTab('team'),
        meet: () => this.$ui.openMeet(),
        'file-explorer': () => this.$ui.setActiveTab('file-explorer'),
        'browser-sessions': () => this.$ui.setActiveTab('browser-sessions'),
        profiles: () => this.$ui.setActiveTab('profiles'),
        knowledge: () => this.$ui.setActiveTab('knowledge'),
        analytics: () => this.$ui.setActiveTab('analytics'),
        infra: () => this.$ui.openInfra()
      }
      actions[item.action]?.()
      this.$emit('close')
    }
  }
}
</script>