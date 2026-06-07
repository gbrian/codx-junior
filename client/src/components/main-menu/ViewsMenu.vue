<script setup>
import {
  MenubarSub,
  MenubarSubContent,
  MenubarSubTrigger,
  MenubarPortal,
} from 'reka-ui'
import MenubarItem from './MenubarItem.vue'
import MenuDivider from './MenuDivider.vue'
</script>

<template>
  <MenubarSub>
    <MenubarSubTrigger class="w-full flex items-center gap-2 px-2 py-1 rounded cursor-pointer hover:bg-base-200">
      <i class="fa-solid fa-table-columns"></i>
      Views
      <i class="fa-solid fa-chevron-right ml-auto text-xs"></i>
    </MenubarSubTrigger>
    <MenubarPortal>
      <MenubarSubContent
        class="py-2 min-w-52 outline-none bg-base-100 rounded-lg px-2 border border-white/30 shadow-lg"
        :side-offset="8"
      >
        <!-- Create new view (admin only) -->
        <MenubarItem v-if="isProjectAdmin" @click.stop="openCreate">
          <i class="fa-solid fa-plus"></i>
          Create new view
        </MenubarItem>

        <!-- Save current view -->
        <MenubarItem @click="saveCurrentView">
          <i class="fa-solid fa-floppy-disk"></i>
          Save current view
        </MenubarItem>

        <MenuDivider v-if="views.length" />

        <!-- List of saved views -->
        <div v-if="views.length" class="max-h-64 overflow-y-auto">
          <div
            v-for="view in views"
            :key="view.name"
            class="flex items-center gap-1 group"
          >
            <MenubarItem class="flex-1" @click="loadView(view)">
              <i class="fa-regular fa-window-restore"></i>
              <span class="truncate max-w-36">{{ view.name }}</span>
            </MenubarItem>

            <!-- Edit (admin only) -->
            <button
              v-if="isProjectAdmin"
              class="opacity-0 group-hover:opacity-100 btn btn-ghost btn-xs"
              @click.stop="openEdit(view)"
              title="Edit view"
            >
              <i class="fa-solid fa-pen text-xs"></i>
            </button>

            <!-- Delete (admin only) -->
            <button
              v-if="isProjectAdmin"
              class="opacity-0 group-hover:opacity-100 btn btn-ghost btn-xs text-error"
              @click.stop="deleteView(view.name)"
              title="Delete view"
            >
              <i class="fa-solid fa-trash text-xs"></i>
            </button>
          </div>
        </div>

        <div v-else class="px-2 py-1 text-xs opacity-50">
          No saved views yet
        </div>
      </MenubarSubContent>
    </MenubarPortal>
  </MenubarSub>
</template>

<script>
export default {
  computed: {
    views() {
      return this.$storex.ui.views || []
    },
    isProjectAdmin() {
      return this.$storex.projects.activeProject?.permissions?.includes('admin') ||
        this.$storex.session.user?.role === 'admin'
    }
  },
  methods: {
    // Signal Desktop to open ViewProperties in create mode
    openCreate() {
      this.$storex.ui.openViewEditor(null)
    },
    // Signal Desktop to open ViewProperties in edit mode for the given view
    openEdit(view) {
      this.$storex.ui.openViewEditor(view)
    },
    // Save current layout — uses last view name if available, else open create editor
    async saveCurrentView() {
      const lastView = this.$storex.ui.lastView
      if (lastView?.name) {
        await this.$storex.ui.saveView(lastView.name)
      } else {
        this.openCreate()
      }
    },
    async loadView(view) {
      await this.$storex.ui.loadView(view)
    },
    async deleteView(name) {
      await this.$storex.ui.deleteView(name)
    }
  }
}
</script>