<script setup>
import AppIcon from '../apps/AppIcon.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <div class="w-full flex flex-col max-h-screen">

    <!-- Top Bar -->
    <div class="navbar bg-base-200 border-b border-base-300 min-h-0 px-4 py-2">
      <div class="flex-1 flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-primary/20 text-primary flex items-center justify-center shrink-0">
          <i class="fa-solid fa-cubes text-sm"></i>
        </div>
        <input
          v-model="workspace.name"
          class="input input-sm input-ghost font-bold text-lg w-48 focus:bg-base-100"
          placeholder="Workspace Name"
        />
        <span class="text-base-content/30">/</span>
        <input
          v-model="workspace.description"
          class="input input-sm input-ghost text-sm text-base-content/60 flex-1 focus:bg-base-100"
          placeholder="Description..."
        />
      </div>
      <div class="flex gap-2">
        <button class="btn btn-error btn-sm btn-outline" @click="$emit('delete', workspace.id)">
          <i class="fa-regular fa-trash-can"></i>
        </button>
        <button class="btn btn-ghost btn-sm" @click="$emit('close')">Cancel</button>
        <button class="btn btn-primary btn-sm" @click="$emit('save', workspace)">
          <i class="fa-solid fa-floppy-disk"></i> Save
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-4 grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">

      <!-- Apps Card -->
      <div class="card bg-base-100 border border-base-300 lg:col-span-2">
        <div class="card-body p-4">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-7 h-7 rounded-lg bg-info/20 text-info flex items-center justify-center text-xs">
              <i class="fa-solid fa-grid-2"></i>
            </div>
            <h3 class="font-bold">Apps</h3>
            <div class="flex-1"></div>
            <button class="btn btn-xs btn-primary" @click="addApp">
              <i class="fa-solid fa-plus"></i> Add
            </button>
          </div>

          <div v-if="!workspace.apps?.length" class="text-center py-6 text-base-content/30 text-sm">
            <i class="fa-solid fa-grid-2 text-3xl mb-2"></i>
            <p>No apps yet</p>
          </div>

          <div v-else class="flex flex-col gap-2">
            <div
              v-for="(app, index) in workspace.apps"
              :key="index"
              class="flex items-center gap-2 p-2 rounded-lg bg-base-200/60 hover:bg-base-200"
            >
              <AppIcon :app="app" />
              <input v-model="app.name" class="input input-xs input-bordered w-24 font-medium" placeholder="Name" />
              <input v-model="app.icon" class="input input-xs input-bordered w-28 text-xs" placeholder="fa-..." />
              <input v-model="app.description" class="input input-xs input-bordered flex-1" placeholder="Description" />
              <input v-model="app.path" class="input input-xs input-bordered w-28" placeholder="/path" />
              <input v-model.number="app.port" type="number" class="input input-xs input-bordered w-16" placeholder="port" />
              <label class="flex items-center gap-1 text-xs cursor-pointer whitespace-nowrap">
                <input type="checkbox" v-model="app.is_vnc" class="checkbox checkbox-xs" />
                VNC
              </label>
              <div class="dropdown dropdown-end">
                <div tabindex="0" role="button" class="btn btn-xs btn-ghost whitespace-nowrap">
                  <i class="fa-solid fa-shield-halved"></i>
                  <span class="badge badge-xs">{{ app.roles?.length || 0 }}</span>
                </div>
                <ul tabindex="-1" class="dropdown-content menu bg-base-100 rounded-box z-50 w-36 p-2 shadow border border-base-300">
                  <li @click="toggleRole(app, 'user')">
                    <a><i class="fa-solid fa-check text-success" v-if="app.roles?.includes('user')"></i> user</a>
                  </li>
                  <li @click="toggleRole(app, 'admin')">
                    <a><i class="fa-solid fa-check text-success" v-if="app.roles?.includes('admin')"></i> admin</a>
                  </li>
                </ul>
              </div>
              <button class="btn btn-ghost btn-xs text-error shrink-0" @click="removeApp(index)">
                <i class="fa-regular fa-trash-can"></i>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Projects Card -->
      <div class="card bg-base-100 border border-base-300">
        <div class="card-body p-4">
          <div class="flex items-center gap-2 mb-3">
            <div class="w-7 h-7 rounded-lg bg-warning/20 text-warning flex items-center justify-center text-xs">
              <i class="fa-solid fa-folder"></i>
            </div>
            <h3 class="font-bold">Projects</h3>
            <span class="badge badge-ghost badge-sm ml-auto">{{ workspace.project_ids?.length || 0 }}</span>
          </div>

          <div class="flex flex-col gap-1 mb-3 max-h-48 overflow-y-auto">
            <div v-if="!workspace.project_ids?.length" class="text-xs text-base-content/40 py-2 text-center">
              No projects linked
            </div>
            <div
              v-for="projectId in workspace.project_ids"
              :key="projectId"
              class="flex items-center gap-2 px-3 py-2 rounded-lg bg-base-200 hover:bg-base-300 group"
            >
              <i class="fa-solid fa-folder text-warning text-xs"></i>
              <span class="text-sm flex-1">{{ getProjectName(projectId) }}</span>
              <button
                class="btn btn-ghost btn-xs text-error opacity-0 group-hover:opacity-100 transition-opacity"
                @click="toggleProjectSelection(projectId)"
              >
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
          </div>

          <!-- CHANGED: Replace dropdown with ProjectDetailt component -->
          <div class="mb-2">
            <p class="text-xs text-base-content/50 mb-2">Click to add project:</p>
            <ProjectDetailt
              :options="availableProjects"
              @select="onProjectSelected"
            />
          </div>
        </div>
      </div>

      <!-- Users Card -->
      <div class="card bg-base-100 border border-base-300">
        <div class="card-body p-4">
          <div class="flex items-center gap-2 mb-1">
            <div
              class="w-7 h-7 rounded-lg flex items-center justify-center text-xs"
              :class="workspaceUserIds.length ? 'bg-warning/20 text-warning' : 'bg-success/20 text-success'"
            >
              <i class="fa-solid fa-users"></i>
            </div>
            <h3 class="font-bold">Access</h3>
            <div class="badge badge-sm ml-auto" :class="workspaceUserIds.length ? 'badge-warning' : 'badge-success'">
              {{ workspaceUserIds.length ? 'restricted' : 'all users' }}
            </div>
          </div>
          <p class="text-xs text-base-content/40 mb-3">Empty list = all users allowed</p>

          <div class="flex flex-col gap-1 mb-3 max-h-48 overflow-y-auto">
            <div v-if="!workspaceUserIds.length" class="text-xs text-base-content/40 py-4 text-center">
              <i class="fa-solid fa-circle-check text-success text-lg block mb-1"></i>
              Open to all users
            </div>
            <div
              v-for="username in workspaceUserIds"
              :key="username"
              class="flex items-center gap-2 px-3 py-2 rounded-lg bg-warning/10 hover:bg-warning/20 group"
            >
              <div class="avatar placeholder shrink-0">
                <div class="bg-warning text-warning-content rounded-full w-6">
                  <span class="text-xs">{{ username[0].toUpperCase() }}</span>
                </div>
              </div>
              <span class="text-sm flex-1">{{ username }}</span>
              <button
                class="btn btn-ghost btn-xs text-error opacity-0 group-hover:opacity-100 transition-opacity"
                @click="toggleUserAccess(username)"
              >
                <i class="fa-solid fa-xmark"></i>
              </button>
            </div>
          </div>

          <div class="join w-full">
            <select class="select select-bordered select-xs join-item flex-1" v-model="selectedUserId">
              <option value="" disabled>Add user...</option>
              <option v-for="u in availableUsersToAdd" :key="u.username" :value="u.username">{{ u.username }}</option>
            </select>
            <button class="btn btn-xs btn-warning join-item" :disabled="!selectedUserId" @click="toggleUserAccess(selectedUserId)">
              <i class="fa-solid fa-plus"></i>
            </button>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
export default {
  props: ['workspace', 'availableProjects'],
  emits: ['close', 'save', 'delete'],
  data() {
    return {
      selectedUserId: ''
    }
  },
  computed: {
    availableUsers() {
      return this.$storex?.users?.users || []
    },
    workspaceUserIds() {
      return this.workspace.user_ids || []
    },
    availableUsersToAdd() {
      return this.availableUsers.filter(u => !this.workspaceUserIds.includes(u.username))
    }
  },
  async mounted() {
    try {
      await this.$storex.users.loadUsers()
    } catch (error) {
      console.error('Failed to load users', error)
    }
  },
  methods: {
    onProjectSelected(project) {
      if (!project || !project.project_id) return
      if (!this.workspace.project_ids) this.workspace.project_ids = []
      // Avoid duplicates
      if (!this.workspace.project_ids.includes(project.project_id)) {
        this.workspace.project_ids.push(project.project_id)
      }
    },
    toggleProjectSelection(projectId) {
      if (!this.workspace.project_ids) this.workspace.project_ids = []
      const idx = this.workspace.project_ids.indexOf(projectId)
      idx > -1
        ? this.workspace.project_ids.splice(idx, 1)
        : this.workspace.project_ids.push(projectId)
    },
    getProjectName(projectId) {
      if (projectId === '*') return 'All Projects'
      return this.availableProjects.find(p => p.project_id === projectId)?.project_name || 'Unknown'
    },
    toggleUserAccess(username) {
      if (!username) return
      if (!this.workspace.user_ids) this.workspace.user_ids = []
      const idx = this.workspace.user_ids.indexOf(username)
      idx > -1
        ? this.workspace.user_ids.splice(idx, 1)
        : this.workspace.user_ids.push(username)
      if (idx === -1) this.selectedUserId = ''
    },
    addApp() {
      if (!this.workspace.apps) this.workspace.apps = []
      this.workspace.apps.push({
        name: '',
        icon: 'fa-globe',
        description: '',
        path: '',
        port: null,
        roles: ['admin']
      })
    },
    removeApp(index) {
      this.workspace.apps.splice(index, 1)
    },
    toggleRole(app, role) {
      if (!app.roles) app.roles = []
      const idx = app.roles.indexOf(role)
      idx > -1 ? app.roles.splice(idx, 1) : app.roles.push(role)
    }
  }
}
</script>