<script setup>
import MenubarSub from './MenubarSub.vue'
import MenubarItem from './MenubarItem.vue';
import AppIcon from '../apps/AppIcon.vue';
</script>
<template>
  <MenubarSub title="Workspaces">
    <template v-slot:menubaritem>
      <i class="fa-solid fa-server"></i>
      Workspaces
    </template>

    <!-- CHANGED: Group header -->
    <div class="font-bold px-2 py-1 text-xs text-base-content/50 uppercase tracking-wider">
      Workspaces
    </div>

    <!-- Workspace apps sub-menus -->
    <MenubarSub :title="workspaceName" v-for="(apps, workspaceName) in workspaces" :key="workspaceName">
      <div class="font-bold px-2">Apps</div>

      <MenubarItem
        class="flex gap-2 hover:bg-base-300"
        v-for="app in apps"
        :key="app.name"
        @click.stop="toggleAppPanel(app)"
      >
        <AppIcon :app="app" />
        {{ app.name }}
        <button class="btn btn-sm" @click.stop="$ui.openNewWindowAppPanel(app)">
          <i class="fa-solid fa-arrow-up-right-from-square"></i>
        </button>
      </MenubarItem>
    </MenubarSub>

    <!-- ADDED: Divider before actions -->
    <div class="divider my-1 px-2"></div>

    <!-- ADDED: Quick new workspace shortcut -->
    <MenubarItem
      class="flex gap-2 hover:bg-base-300"
      @click.stop="openWorkspaceManager({ create: true })"
    >
      <i class="fa-solid fa-plus text-success"></i>
      New workspace
    </MenubarItem>

    <!-- CHANGED: Manage workspaces link (was present before, restored + improved) -->
    <MenubarItem
      class="flex gap-2 hover:bg-base-300"
      @click.stop="openWorkspaceManager()"
    >
      <i class="fa-solid fa-sliders"></i>
      Manage workspaces
    </MenubarItem>
  </MenubarSub>
</template>
<script>
export default {
  computed: {
    workspaces() {
      return this.$storex.projects.projectApps.reduce((acc, app) => {
        const apps = acc[app.workspaceName] || []
        apps.push(app)
        return {
          ...acc,
          [app.workspaceName]: apps
        }
      }, {})
    }
  },
  methods: {
    toggleAppPanel(app) {
      app = this.$ui.openApps[app.key] || app
      this.$ui.showApp({
        ...app,
        left: !app?.left,
        ts: new Date().getTime(),
        params: {
          name: app.name,
          path: app.path
        }
      })
    },
    // ADDED: open the workspace manager, optionally pre-opening the create dialog
    openWorkspaceManager(params = {}) {
      this.$ui.showApp({
        tabId: 'workspaces-manager',
        name: 'Workspaces',
        component: 'workspaces',
        params
      })
    }
  }
}
</script>