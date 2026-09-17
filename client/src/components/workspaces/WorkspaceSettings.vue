<script setup>
import AppIcon from '../apps/AppIcon.vue'
import WorkspaceFileEditor from './WorkspaceFileEditor.vue';
import WorkspaceLogs from './WorkspaceLogs.vue'
</script>

<template>
  <div class="w-full flex flex-col h-full max-h-screen">

    <!-- Top Bar -->
    <div class="navbar bg-base-200 border-b border-base-300 min-h-0 px-4 py-2 shrink-0">
      <div class="flex-1 flex items-center gap-3">
        <button class="btn btn-ghost btn-sm btn-circle" @click="$emit('close')" title="Back to workspaces">
          <i class="fa-solid fa-arrow-left"></i>
        </button>
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
        <button class="btn btn-primary btn-sm" @click="$emit('save', workspace)">
          <i class="fa-solid fa-floppy-disk"></i> Save
        </button>
      </div>
    </div>

    <!-- Tab Navigation -->
    <div class="tabs tabs-bordered px-4 bg-base-100 shrink-0 border-b border-base-200">
      <a
        v-for="tab in tabs"
        :key="tab.id"
        class="tab gap-2"
        :class="activeTab === tab.id && 'tab-active'"
        @click="activeTab = tab.id"
      >
        <i :class="tab.icon"></i>
        {{ tab.label }}
      </a>
    </div>

    <!-- Tab Content -->
    <div class="flex-1 overflow-hidden">

      <!-- ── Basic Info Tab ── -->
      <div v-if="activeTab === 'basic'" class="h-full overflow-y-auto p-4 space-y-4 max-w-2xl">
        <div class="form-control">
          <label class="label"><span class="label-text font-semibold">Folder Path</span></label>
          <input
            v-model="workspace.folder_path"
            class="input input-bordered input-sm"
            placeholder="e.g., my-workspace"
          />
          <label class="label"><span class="label-text-alt">Unique folder under the workspaces root</span></label>
        </div>

        <div class="form-control">
          <label class="label"><span class="label-text font-semibold">Template</span></label>
          <select v-model="workspace.template" class="select select-bordered select-sm">
            <option value="custom">Custom</option>
            <option value="static-site">Static Site</option>
            <option value="dev-stack">Full-Stack Dev</option>
          </select>
        </div>

        <div class="form-control">
          <label class="label cursor-pointer justify-start gap-3">
            <input type="checkbox" v-model="workspace.use_sysbox" class="checkbox checkbox-sm" />
            <div>
              <span class="label-text font-semibold">Enable Sysbox Runtime</span>
              <p class="text-xs text-base-content/50">Allows Docker-in-Docker and systemd inside containers</p>
            </div>
          </label>
        </div>

        <!-- ADDED: Generate Files section -->
        <div class="divider"></div>

        <div class="space-y-3">
          <div>
            <h4 class="font-semibold flex items-center gap-2">
              <i class="fa-solid fa-wand-magic-sparkles text-secondary"></i>
              Generate Files
            </h4>
            <p class="text-xs text-base-content/50 mt-1">
              Regenerate workspace files (docker-compose.yaml, Dockerfile, etc.) from the template.
              Optionally override the container startup command.
            </p>
          </div>

          <div class="form-control">
            <label class="label"><span class="label-text text-sm">Startup Command <span class="text-base-content/40">(optional)</span></span></label>
            <input
              v-model="generateCommand"
              type="text"
              placeholder="e.g., npm run dev"
              class="input input-bordered input-sm font-mono"
            />
            <label class="label"><span class="label-text-alt">Overrides the default command defined in the template</span></label>
          </div>

          <button
            class="btn btn-secondary btn-sm gap-2"
            :disabled="isGenerating"
            @click="generateFiles"
          >
            <span v-if="isGenerating" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fa-solid fa-wand-magic-sparkles"></i>
            {{ isGenerating ? 'Generating...' : 'Generate Files' }}
          </button>

          <div v-if="generateResult" class="alert alert-sm" :class="generateResult.error ? 'alert-error' : 'alert-success'">
            <i :class="generateResult.error ? 'fa-solid fa-circle-xmark' : 'fa-solid fa-circle-check'"></i>
            <span class="text-sm">{{ generateResult.message }}</span>
          </div>
        </div>
      </div>

      <!-- ── Apps Tab ── -->
      <div v-else-if="activeTab === 'apps'" class="h-full overflow-y-auto p-4">
        <div class="flex items-center gap-2 mb-4">
          <h3 class="font-bold flex-1">Apps</h3>
          <button class="btn btn-xs btn-primary" @click="addApp">
            <i class="fa-solid fa-plus"></i> Add App
          </button>
        </div>

        <div v-if="!workspace.apps?.length" class="alert alert-info">
          <i class="fa-solid fa-lightbulb"></i>
          <span>Add apps to expose them through Traefik routing</span>
        </div>

        <div v-else class="flex flex-col gap-3">
          <div
            v-for="(app, index) in workspace.apps"
            :key="index"
            class="card bg-base-100 border border-base-200"
          >
            <div class="card-body p-4 space-y-3">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <AppIcon :app="app" />
                  <span class="font-semibold text-sm">{{ app.name || `App ${index + 1}` }}</span>
                </div>
                <button class="btn btn-ghost btn-xs text-error" @click="removeApp(index)">
                  <i class="fa-regular fa-trash-can"></i>
                </button>
              </div>

              <div class="grid grid-cols-2 gap-3">
                <div class="form-control">
                  <label class="label label-text-alt">Name *</label>
                  <input v-model="app.name" type="text" placeholder="My App" class="input input-bordered input-sm" />
                </div>
                <div class="form-control">
                  <label class="label label-text-alt">Icon (Font Awesome)</label>
                  <input v-model="app.icon" type="text" placeholder="fa-globe" class="input input-bordered input-sm" />
                </div>
                <div class="form-control">
                  <label class="label label-text-alt">Path *</label>
                  <input v-model="app.path" type="text" placeholder="/app" class="input input-bordered input-sm" />
                </div>
                <div class="form-control">
                  <label class="label label-text-alt">Port *</label>
                  <input v-model.number="app.port" type="number" placeholder="3000" class="input input-bordered input-sm" />
                </div>
              </div>

              <div class="form-control">
                <label class="label label-text-alt">App ID (for routing, auto from name if blank)</label>
                <input v-model="app.id" type="text" placeholder="my-app" class="input input-bordered input-sm" />
              </div>

              <div class="flex items-center gap-4 flex-wrap">
                <label class="label cursor-pointer gap-2">
                  <input type="checkbox" :checked="app.scheme === 'https'" class="checkbox checkbox-xs" @change="app.scheme = $event.target.checked ? 'https' : 'http'" />
                  <span class="label-text-alt">HTTPS scheme</span>
                </label>
                <label class="label cursor-pointer gap-2">
                  <input type="checkbox" v-model="app.is_vnc" class="checkbox checkbox-xs" />
                  <span class="label-text-alt">VNC app</span>
                </label>
              </div>

              <div class="form-control">
                <label class="label label-text-alt">Access Roles (empty = all roles)</label>
                <div class="flex gap-3">
                  <label class="label cursor-pointer gap-2">
                    <input type="checkbox" :checked="app.roles?.includes('user')" class="checkbox checkbox-xs" @change="toggleRole(app, 'user')" />
                    <span class="label-text-alt">user</span>
                  </label>
                  <label class="label cursor-pointer gap-2">
                    <input type="checkbox" :checked="app.roles?.includes('admin')" class="checkbox checkbox-xs" @change="toggleRole(app, 'admin')" />
                    <span class="label-text-alt">admin</span>
                  </label>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Projects Tab ── -->
      <div v-else-if="activeTab === 'projects'" class="h-full overflow-y-auto p-4 max-w-xl">
        <div class="flex items-center gap-2 mb-4">
          <h3 class="font-bold flex-1">Mounted Projects</h3>
          <span class="badge badge-ghost">{{ workspace.project_ids?.length || 0 }}</span>
        </div>

        <!-- All Projects toggle -->
        <label class="label cursor-pointer justify-start gap-3 mb-3">
          <input type="checkbox" :checked="workspace.project_ids?.includes('*')" class="checkbox checkbox-sm" @change="toggleAllProjects" />
          <span class="label-text font-medium">Mount all projects</span>
        </label>

        <div v-if="workspace.project_ids?.includes('*')" class="alert alert-info mb-3">
          <i class="fa-solid fa-star"></i>
          <span>All projects are mounted (identity-mounted at same host path)</span>
        </div>

        <div v-else class="flex flex-col gap-1 mb-4">
          <div
            v-for="projectId in workspace.project_ids"
            :key="projectId"
            class="flex items-center gap-2 px-3 py-2 rounded-lg bg-base-200 hover:bg-base-300 group"
          >
            <i class="fa-solid fa-folder text-warning text-xs"></i>
            <span class="text-sm flex-1">{{ getProjectName(projectId) }}</span>
            <button class="btn btn-ghost btn-xs text-error opacity-0 group-hover:opacity-100 transition-opacity" @click="removeProject(projectId)">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div v-if="!workspace.project_ids?.length" class="text-xs text-base-content/40 py-2 text-center">
            No projects linked
          </div>
        </div>

        <!-- Add project -->
        <div v-if="!workspace.project_ids?.includes('*')" class="join w-full">
          <select class="select select-bordered select-sm join-item flex-1" v-model="selectedProjectId">
            <option value="" disabled>Add project...</option>
            <option v-for="p in availableProjectsToAdd" :key="p.project_id" :value="p.project_id">
              {{ p.project_name }}
            </option>
          </select>
          <button class="btn btn-sm btn-primary join-item" :disabled="!selectedProjectId" @click="addProject">
            <i class="fa-solid fa-plus"></i>
          </button>
        </div>
      </div>

      <!-- ── Users Tab ── -->
      <div v-else-if="activeTab === 'users'" class="h-full overflow-y-auto p-4 max-w-xl">
        <div class="flex items-center gap-2 mb-1">
          <h3 class="font-bold flex-1">Access Control</h3>
          <div class="badge badge-sm" :class="workspaceUserIds.length ? 'badge-warning' : 'badge-success'">
            {{ workspaceUserIds.length ? 'restricted' : 'all users' }}
          </div>
        </div>
        <p class="text-xs text-base-content/40 mb-4">Empty list = all users allowed. Add specific users to restrict access.</p>

        <div class="flex flex-col gap-1 mb-4">
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
            <button class="btn btn-ghost btn-xs text-error opacity-0 group-hover:opacity-100 transition-opacity" @click="removeUser(username)">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div v-if="!workspaceUserIds.length" class="text-xs text-base-content/40 py-4 text-center">
            <i class="fa-solid fa-circle-check text-success text-lg block mb-1"></i>
            Open to all users
          </div>
        </div>

        <div class="join w-full">
          <select class="select select-bordered select-sm join-item flex-1" v-model="selectedUserId">
            <option value="" disabled>Add user...</option>
            <option v-for="u in availableUsersToAdd" :key="u.username" :value="u.username">{{ u.username }}</option>
          </select>
          <button class="btn btn-sm btn-warning join-item" :disabled="!selectedUserId" @click="addUser">
            <i class="fa-solid fa-plus"></i>
          </button>
        </div>
      </div>

      <!-- ── Environment Tab ── -->
      <div v-else-if="activeTab === 'env'" class="h-full overflow-y-auto p-4 max-w-2xl">
        <div class="flex items-center gap-2 mb-4">
          <h3 class="font-bold flex-1">Environment Variables</h3>
          <button class="btn btn-xs btn-primary" @click="addEnvVar">
            <i class="fa-solid fa-plus"></i> Add
          </button>
        </div>

        <p class="text-xs text-base-content/50 mb-4">
          Variables forwarded to docker-compose containers. Template-specific vars like <code class="bg-base-200 px-1 rounded">IMAGE</code> and <code class="bg-base-200 px-1 rounded">COMMAND</code> are defined here.
        </p>

        <div v-if="!envEntries.length" class="alert alert-ghost">
          <i class="fa-solid fa-leaf"></i>
          <span class="text-sm">No environment variables defined</span>
        </div>

        <div v-else class="flex flex-col gap-2">
          <div
            v-for="(entry, idx) in envEntries"
            :key="idx"
            class="flex items-center gap-2"
          >
            <input
              v-model="entry.key"
              class="input input-bordered input-sm w-40 font-mono text-info"
              placeholder="KEY"
              @input="syncEnv"
            />
            <span class="text-base-content/40">=</span>
            <input
              v-model="entry.value"
              class="input input-bordered input-sm flex-1 font-mono"
              placeholder="value"
              @input="syncEnv"
            />
            <button class="btn btn-ghost btn-xs text-error" @click="removeEnvVar(idx)">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- ── Resources Tab ── -->
      <div v-else-if="activeTab === 'resources'" class="h-full overflow-y-auto p-4 max-w-xl">
        <h3 class="font-bold mb-4">Resource Limits</h3>
        <p class="text-xs text-base-content/50 mb-4">
          Applied via docker-compose deploy.resources.limits. Leave blank for no limit.
        </p>

        <div class="grid grid-cols-2 gap-4">
          <div class="form-control">
            <label class="label"><span class="label-text font-semibold">CPU Limit</span></label>
            <input
              v-model="workspace.resources.cpus"
              type="text"
              placeholder='e.g., "2"'
              class="input input-bordered input-sm"
            />
            <label class="label"><span class="label-text-alt">Number of CPUs (e.g., 2)</span></label>
          </div>

          <div class="form-control">
            <label class="label"><span class="label-text font-semibold">Memory Limit</span></label>
            <input
              v-model="workspace.resources.memory"
              type="text"
              placeholder="e.g., 4g"
              class="input input-bordered input-sm"
            />
            <label class="label"><span class="label-text-alt">Docker memory limit (e.g., 4g, 512m)</span></label>
          </div>

          <div class="form-control">
            <label class="label"><span class="label-text font-semibold">Shared Memory</span></label>
            <input
              v-model="workspace.resources.shm_size"
              type="text"
              placeholder="512m"
              class="input input-bordered input-sm"
            />
            <label class="label"><span class="label-text-alt">shm_size for /dev/shm (default: 512m)</span></label>
          </div>
        </div>
      </div>

      <!-- ── Files Tab ── -->
      <div v-else-if="activeTab === 'files'" class="h-full overflow-hidden">
        <WorkspaceFileEditor
          :workspace="workspace"
        />
      </div>

      <!-- ── Logs Tab ── -->
      <div v-else-if="activeTab === 'logs'" class="h-full overflow-hidden p-4">
        <WorkspaceLogs
          :workspace="workspace"
          :project="theProject"
          :inline="true"
        />
      </div>

    </div>
  </div>
</template>

<script>
export default {
  props: {
    workspace: Object,
    availableProjects: {
      type: Array,
      default: () => []
    },
    project: {
      default: null
    }
  },
  emits: ['close', 'save', 'delete'],
  data() {
    return {
      activeTab: 'basic',
      selectedProjectId: '',
      selectedUserId: '',
      // Local copy of env as [{key, value}] array for editing
      envEntries: [],
      // ADDED: generate files state
      generateCommand: '',
      isGenerating: false,
      generateResult: null,
      tabs: [
        { id: 'basic',     label: 'Basic',     icon: 'fa-solid fa-info-circle' },
        { id: 'apps',      label: 'Apps',      icon: 'fa-solid fa-grid-2' },
        { id: 'projects',  label: 'Projects',  icon: 'fa-solid fa-folder' },
        { id: 'users',     label: 'Users',     icon: 'fa-solid fa-users' },
        { id: 'env',       label: 'Env Vars',  icon: 'fa-solid fa-leaf' },
        { id: 'resources', label: 'Resources', icon: 'fa-solid fa-microchip' },
        { id: 'files',     label: 'Files',     icon: 'fa-solid fa-file-code' },
        { id: 'logs',      label: 'Logs',      icon: 'fa-solid fa-list' }
      ]
    }
  },
  computed: {
    theProject() {
      return this.project || this.$project
    },
    availableUsers() {
      return this.$storex?.users?.users || []
    },
    workspaceUserIds() {
      return this.workspace.user_ids || []
    },
    availableUsersToAdd() {
      return this.availableUsers.filter(u => !this.workspaceUserIds.includes(u.username))
    },
    availableProjectsToAdd() {
      const linked = this.workspace.project_ids || []
      return this.availableProjects.filter(p => !linked.includes(p.project_id))
    },
    workspaceFolderPath() {
      return this.workspace.folder_path
    }
  },
  async mounted() {
    try {
      await this.$storex.users.loadUsers()
    } catch (error) {
      console.error('Failed to load users', error)
    }
    this.buildEnvEntries()
    // Ensure resources object exists
    if (!this.workspace.resources) {
      this.workspace.resources = { cpus: null, memory: null, shm_size: '512m' }
    }
  },
  methods: {
    // ── Env var helpers ──────────────────────────────────────────────────────
    buildEnvEntries() {
      const env = this.workspace.env || {}
      this.envEntries = Object.entries(env).map(([key, value]) => ({ key, value }))
    },
    syncEnv() {
      // Write envEntries back to workspace.env
      const env = {}
      this.envEntries.forEach(({ key, value }) => {
        if (key) env[key] = value
      })
      this.workspace.env = env
    },
    addEnvVar() {
      this.envEntries.push({ key: '', value: '' })
    },
    removeEnvVar(idx) {
      this.envEntries.splice(idx, 1)
      this.syncEnv()
    },

    // ── Generate Files ───────────────────────────────────────────────────────
    async generateFiles() {
      this.isGenerating = true
      this.generateResult = null
      try {
        await this.theProject.$api.projects.workspaces.lifecycle.generateFiles(
          this.workspace.id,
          this.generateCommand
        )
        this.generateResult = { message: 'Files generated successfully', error: false }
      } catch (error) {
        console.error('Failed to generate workspace files', error)
        this.generateResult = { message: `Failed to generate files: ${error.message}`, error: true }
      } finally {
        this.isGenerating = false
      }
    },

    // ── Apps ─────────────────────────────────────────────────────────────────
    addApp() {
      if (!this.workspace.apps) this.workspace.apps = []
      this.workspace.apps.push({
        id: '',
        name: '',
        icon: 'fa-globe',
        path: '',
        port: null,
        scheme: 'http',
        roles: ['admin'],
        is_vnc: false
      })
    },
    removeApp(index) {
      this.workspace.apps.splice(index, 1)
    },
    toggleRole(app, role) {
      if (!app.roles) app.roles = []
      const idx = app.roles.indexOf(role)
      idx > -1 ? app.roles.splice(idx, 1) : app.roles.push(role)
    },

    // ── Projects ─────────────────────────────────────────────────────────────
    toggleAllProjects(event) {
      if (event.target.checked) {
        this.workspace.project_ids = ['*']
      } else {
        this.workspace.project_ids = []
      }
    },
    addProject() {
      if (!this.selectedProjectId) return
      if (!this.workspace.project_ids) this.workspace.project_ids = []
      if (!this.workspace.project_ids.includes(this.selectedProjectId)) {
        this.workspace.project_ids.push(this.selectedProjectId)
      }
      this.selectedProjectId = ''
    },
    removeProject(projectId) {
      const idx = this.workspace.project_ids.indexOf(projectId)
      if (idx > -1) this.workspace.project_ids.splice(idx, 1)
    },
    getProjectName(projectId) {
      if (projectId === '*') return 'All Projects'
      return this.availableProjects.find(p => p.project_id === projectId)?.project_name || projectId
    },

    // ── Users ─────────────────────────────────────────────────────────────────
    addUser() {
      if (!this.selectedUserId) return
      if (!this.workspace.user_ids) this.workspace.user_ids = []
      if (!this.workspace.user_ids.includes(this.selectedUserId)) {
        this.workspace.user_ids.push(this.selectedUserId)
      }
      this.selectedUserId = ''
    },
    removeUser(username) {
      const idx = this.workspace.user_ids.indexOf(username)
      if (idx > -1) this.workspace.user_ids.splice(idx, 1)
    }
  }
}
</script>