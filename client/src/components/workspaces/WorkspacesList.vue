<script setup>
import WorkspaceCard from './WorkspaceCard.vue'
import WorkspaceCreate from './WorkspaceCreate.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col bg-base-50">

    <!-- Header -->
    <div class="navbar bg-base-100 border-b border-base-200 sticky top-0 z-40">
      <div class="flex-1">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-primary/50 flex items-center justify-center text-white">
            <i class="fa-solid fa-cubes text-lg"></i>
          </div>
          <div>
            <h1 class="font-bold text-lg">Workspaces</h1>
            <p class="text-xs text-base-content/50">{{ theProject.project_name }}</p>
          </div>
        </div>
      </div>

      <div class="flex gap-2">
        <div class="form-control">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search workspaces..."
            class="input input-sm input-bordered w-48"
          />
        </div>
        <button class="btn btn-primary btn-sm" @click="showCreateDialog = true">
          <i class="fa-solid fa-plus"></i> New Workspace
        </button>
        <button class="btn btn-ghost btn-sm" @click="refreshWorkspaces">
          <i class="fa-solid fa-arrows-rotate" :class="{ 'animate-spin': isLoading }"></i>
        </button>
      </div>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-4">
      <div v-if="isLoading" class="flex items-center justify-center h-full">
        <div class="flex flex-col items-center gap-3">
          <span class="loading loading-spinner loading-lg text-primary"></span>
          <p class="text-base-content/50">Loading workspaces...</p>
        </div>
      </div>

      <div v-else-if="filteredWorkspaces.length === 0" class="flex items-center justify-center h-full">
        <div class="text-center">
          <i class="fa-solid fa-inbox text-6xl text-base-content/10 mb-4"></i>
          <h3 class="font-bold text-lg mb-1">No workspaces yet</h3>
          <p class="text-sm text-base-content/50 mb-4">Create your first workspace to get started</p>
          <button class="btn btn-primary btn-sm" @click="showCreateDialog = true">
            <i class="fa-solid fa-plus"></i> Create Workspace
          </button>
        </div>
      </div>

      <div v-else class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        <WorkspaceCard
          v-for="workspace in filteredWorkspaces"
          :key="workspace.id"
          :workspace="workspace"
          :project="theProject"
          @select="selectedWorkspace = workspace"
          @edit="editWorkspace(workspace)"
          @delete="deleteWorkspaceConfirm(workspace)"
          @start="startWorkspace(workspace)"
          @stop="stopWorkspace(workspace)"
        />
      </div>
    </div>

    <!-- Create Dialog -->
    <WorkspaceCreate
      v-if="showCreateDialog"
      :project="theProject"
      @close="showCreateDialog = false"
      @created="onWorkspaceCreated"
    />

    <!-- Edit Dialog -->
    <div v-if="editingWorkspace" class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
      <div class="bg-base-100 rounded-xl shadow-2xl w-full max-h-screen overflow-hidden flex flex-col" style="width: 90vw; max-width: 1200px; height: 90vh">
        <WorkspaceSettings
          :workspace="editingWorkspace"
          :available-projects="allProjects"
          @close="editingWorkspace = null"
          @save="saveWorkspaceChanges"
          @delete="deleteWorkspaceConfirm(editingWorkspace)"
        />
      </div>
    </div>

    <!-- Delete Confirmation -->
    <div v-if="deleteConfirmWorkspace" class="modal modal-open">
      <div class="modal-box">
        <h3 class="font-bold text-lg">Delete Workspace?</h3>
        <p class="py-4 text-sm">
          Are you sure you want to delete <strong>{{ deleteConfirmWorkspace.name }}</strong>?
          This action cannot be undone.
        </p>
        <div class="modal-action">
          <button class="btn btn-ghost" @click="deleteConfirmWorkspace = null">Cancel</button>
          <button class="btn btn-error" @click="confirmDelete">Delete</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @click="deleteConfirmWorkspace = null"></form>
    </div>

    <!-- Toast notifications -->
    <div v-if="notification" class="toast toast-top toast-end z-50">
      <div :class="['alert', notificationClass]">
        <span>{{ notification }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['project'],
  data() {
    return {
      workspaces: [],
      isLoading: false,
      showCreateDialog: false,
      editingWorkspace: null,
      deleteConfirmWorkspace: null,
      searchQuery: '',
      notification: null,
      notificationClass: 'alert-info',
      selectedWorkspace: null,
      allProjects: []
    }
  },
  computed: {
    theProject() {
      return this.project || this.$project
    },
    filteredWorkspaces() {
      return this.workspaces.filter(w =>
        w.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        w.description?.toLowerCase().includes(this.searchQuery.toLowerCase())
      )
    }
  },
  async mounted() {
    await this.loadWorkspaces()
    await this.loadProjects()
  },
  methods: {
    async loadWorkspaces() {
      this.isLoading = true
      try {
        this.workspaces = await this.theProject.$api.workspaces.list()
      } catch (error) {
        this.showNotification('Failed to load workspaces', 'alert-error')
        console.error(error)
      } finally {
        this.isLoading = false
      }
    },
    async loadProjects() {
      try {
        this.allProjects = await this.theProject.$api.projects.list()
      } catch (error) {
        console.error('Failed to load projects', error)
      }
    },
    async refreshWorkspaces() {
      await this.loadWorkspaces()
      this.showNotification('Workspaces refreshed', 'alert-success')
    },
    editWorkspace(workspace) {
      this.editingWorkspace = JSON.parse(JSON.stringify(workspace))
    },
    async saveWorkspaceChanges(workspace) {
      try {
        await this.theProject.$api.workspaces.update(workspace)
        await this.loadWorkspaces()
        this.editingWorkspace = null
        this.showNotification('Workspace updated successfully', 'alert-success')
      } catch (error) {
        this.showNotification('Failed to update workspace', 'alert-error')
        console.error(error)
      }
    },
    async onWorkspaceCreated(workspace) {
      this.showCreateDialog = false
      await this.loadWorkspaces()
      this.showNotification(`Workspace "${workspace.name}" created`, 'alert-success')
    },
    deleteWorkspaceConfirm(workspace) {
      this.deleteConfirmWorkspace = workspace
    },
    async confirmDelete() {
      if (!this.deleteConfirmWorkspace) return
      try {
        await this.theProject.$api.workspaces.delete(this.deleteConfirmWorkspace.id)
        await this.loadWorkspaces()
        this.showNotification('Workspace deleted', 'alert-success')
        this.deleteConfirmWorkspace = null
      } catch (error) {
        this.showNotification('Failed to delete workspace', 'alert-error')
        console.error(error)
      }
    },
    async startWorkspace(workspace) {
      try {
        await this.theProject.$api.workspaces.lifecycle.start(workspace.id)
        await this.loadWorkspaces()
        this.showNotification('Workspace starting...', 'alert-info')
      } catch (error) {
        this.showNotification('Failed to start workspace', 'alert-error')
        console.error(error)
      }
    },
    async stopWorkspace(workspace) {
      try {
        await this.theProject.$api.workspaces.lifecycle.stop(workspace.id)
        await this.loadWorkspaces()
        this.showNotification('Workspace stopped', 'alert-success')
      } catch (error) {
        this.showNotification('Failed to stop workspace', 'alert-error')
        console.error(error)
      }
    },
    showNotification(message, type = 'alert-info') {
      this.notification = message
      this.notificationClass = type
      setTimeout(() => {
        this.notification = null
      }, 4000)
    }
  }
}
</script>