<script setup>
  import AppIcon from '../apps/AppIcon.vue'
</script>

<template>
  <div>
    <div class="p-4">
      <div>
        <div class="form-control">
          <label class="label">
            <span class="label-text">Workspace Name</span>
          </label>
          <input v-model="workspace.name" type="text" placeholder="Workspace Name" class="input input-bordered w-full max-w-xs" required />
        </div>
        <div class="form-control mt-4">
          <label class="label">
            <span class="label-text">Description</span>
          </label>
          <textarea v-model="workspace.description" placeholder="Workspace Description" class="textarea textarea-bordered w-full max-w-xs" required></textarea>
        </div>
        <div class="form-control mt-4 flex flex-col gap-2">
          <label class="label">
            <span class="label-text">Apps</span>
          </label>
          <div v-for="(app, index) in workspace.apps" :key="index" class="flex gap-2 justify-between items-center mt-2">
            <AppIcon :app="app" />
            <input v-model="app.icon" placeholder="App Icon" class="input input-bordered w-36" />
            <input v-model="app.name" placeholder="App Name" class="input input-bordered w-36" />
            <input v-model="app.description" placeholder="App Description" class="input input-bordered w-36" />
            <input v-model="app.path" type="text" placeholder="Path" class="input input-bordered w-36" />
            <input v-model="app.port" type="number" placeholder="Port" class="input input-bordered w-20" />
            <div class="dropdown dropdown-start">
              <div tabindex="0" role="button" class="btn m-1">Roles {{ app.roles?.length }}</div>
              <ul tabindex="-1" class="dropdown-content menu bg-base-100 rounded-box z-50 w-52 p-2 shadow-sm">
                <li @click="toggleRole(app, 'user')">
                  <a><i class="fa-solid fa-check" v-if="app.roles?.includes('user')"></i> user</a>
                </li>
                <li @click="toggleRole(app, 'admin')">
                  <a><i class="fa-solid fa-check" v-if="app.roles?.includes('admin')"></i>  admin</a>
                </li>
              </ul>
            </div>
            <label class="flex items-center">
              <input type="checkbox" v-model="app.is_vnc" class="checkbox checkbox-xs" />
              <span class="ml-1">VNC</span>
            </label>
            <div class="grow"></div>
            <button class="btn btn-error btn-xs" @click="removeApp(index)">
              <i class="fa-regular fa-trash-can"></i>
            </button>
          </div>
          <div class="flex justify-end">
            <button class="btn btn-sm btn-primary" @click="addApp">
              <i class="fa-solid fa-plus"></i> App
            </button>
          </div>
        </div>
        <div class="form-control mt-4 flex flex-col gap-2">
          <label class="label">
            <span class="label-text">Associated Projects</span>
          </label>
          <ul class="list-disc">
            <li v-for="projectId in workspace.project_ids" :key="projectId" class="flex items-center gap-2">
              <button class="btn btn-error btn-sm" @click="toggleProjectSelection(projectId)">
                <i class="fa-solid fa-circle-xmark"></i>
              </button>
              <span>{{ getProjectName(projectId) }}</span>
            </li>
          </ul>
          <div class="flex gap-1 items-center">
            <select class="select select-sm select-bordered grow" v-model="selectedProjectId">
              <option value="*">All</option>
              <option v-for="project in availableProjects" :key="project.project_id" :value="project.project_id">
                {{ project.project_name }}
              </option>
            </select>
            <button class="btn btn-sm btn-primary" @click="toggleProjectSelection(selectedProjectId)">
              <i class="fa-solid fa-plus"></i>
            </button>
          </div>
        </div>
        <div class="flex justify-end mt-4">
          <button class="btn btn-error" @click="deleteWorkspace(workspace.id)">Delete</button>
          <div class="grow"></div>
          <button class="btn btn-primary mr-2" @click="saveWorkspace">Save</button>
          <button type="button" class="btn btn-ghost" @click="closeModal">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['workspace', 'availableProjects'],
  data () {
    return {
      selectedProjectId: null
    }
  },
  methods: {
    toggleProjectSelection(projectId) {
      const index = this.workspace.project_ids.indexOf(projectId)
      if (index > -1) {
        this.workspace.project_ids.splice(index, 1)
      } else {
        this.workspace.project_ids.push(projectId)
      }
    },
    getProjectName(projectId) {
      if (projectId === '*') {
        return "All projects"
      }
      const project = this.availableProjects.find(p => p.project_id === projectId)
      return project ? project.project_name : 'Unknown'
    },
    addApp() {
      this.workspace.apps.push({})
    },
    removeApp(index) {
      this.workspace.apps.splice(index, 1)
    },
    toggleRole(app, role) {
      if (app.roles?.includes(role)) {
        app.roles = app.roles.filter(r => r != role)
      } else {
        app.roles = [...app.roles || [], role]
      }
    },
    closeModal() {
      this.$emit('close')
    },
    deleteWorkspace(workspaceId) {
      this.$emit('delete', workspaceId)
    },
    saveWorkspace() {
      this.$emit('save', this.workspace)
    }
  }
}
</script>