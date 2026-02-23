<script setup>
import { v4 as uuidv4 } from 'uuid'
import WorkspaceSettings from './WorkspaceSettings.vue'
</script>

<template>
  <div>
    <div class="text-2xl flex justify-between gap-2">
      Workspaces
      <div class="grow"></div>
      <button class="btn btn-success btn-sm" @click="addWorkspace">Add Workspace</button>
      <button class="btn btn-sm" @click="showSettings = true">
        <i class="fa-solid fa-gear"></i>
      </button>
    </div>

    <modal close="true" @close="showSettings = false" class="my-4 p-4 border rounded-md bg-base-100" v-if="showSettings">
      <h3 class="text-lg font-bold">Settings</h3>
      <div class="form-control mt-4">
        <label class="label">
          <span class="label-text">Workspace Docker Settings</span>
        </label>
        <div v-for="(value, key) in settings.workspace_docker_settings" :key="key" class="flex gap-2 items-center mt-2">
          <input :value="key" placeholder="Key" 
            readonly class="input input-bordered w-32 text-info border-0" />
          <input v-model="settings.workspace_docker_settings[key]" placeholder="Value" class="input input-bordered w-32" />
          <button class="btn btn-error btn-xs" @click="addDockerSetting">
            <i class="fa-solid fa-circle-xmark"></i>
          </button>
        </div>
        <div class="flex gap-2 items-center mt-2">
          <input v-model="newDockerSetting.key" placeholder="Key" class="input input-bordered w-32" />
          <input v-model="newDockerSetting.value" placeholder="Value" class="input input-bordered w-32" />
          <button class="btn btn-primary btn-xs" @click="addDockerSetting">Add</button>
        </div>
      </div>
    </modal>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 p-4">
      <div v-for="workspace in workspaces" :key="workspace.id" class="card bg-base-100">
        <div class="card-body p-6 border rounded-md click" @click="editWorkspace(workspace)">
          <h2 class="card-title">{{ workspace.name }}</h2>
          {{ workspace.description }}
          <div class="flex justify-end gap-2 items-center">
            {{ workspace.project_ids.length }} projects
          </div>
        </div>
      </div>

      <modal close="true" @close="showModal = false" v-if="showModal">
        <WorkspaceSettings
          :workspace="selectedWorkspace"
          :availableProjects="availableProjects"
          @close="showModal = false"
          @delete="deleteWorkspace"
          @save="saveWorkspace"
        />
      </modal>
    </div>
  </div>
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
      showModal: false,
      newDockerSetting: { key: '', value: '' },
      newApp: { name: '', description: '', port: null, is_vnc: false },
      selectedWorkspace: {
        name: '',
        description: '',
        project_ids: [],
        apps: []
      },
      selectedProjectId: null,
      showSettings: false
    }
  },
  computed: {
    workspaces() {
      return this.settings.workspaces
    },
    availableProjects() {
      return this.$projects.allProjects
    }
  },
  methods: {
    addWorkspace() {
      this.selectedWorkspace = { name: '', description: '', project_ids: [], apps: [] }
      this.showModal = true
    },
    editWorkspace(workspace) {
      this.selectedWorkspace = { ...workspace }
      this.showModal = true
    },
    deleteWorkspace(workspaceId) {
      const index = this.settings.workspaces.findIndex(ws => ws.id === workspaceId)
      if (index !== -1) {
        this.settings.workspaces.splice(index, 1)
      }
    },
    saveWorkspace() {
      if (!this.selectedWorkspace.id) {
        this.settings.workspaces.push({ ...this.selectedWorkspace, id: uuidv4() })
      } else {
        const index = this.settings.workspaces.findIndex(ws => ws.id === this.selectedWorkspace.id)
        if (index !== -1) {
          this.settings.workspaces[index] = { ...this.selectedWorkspace }
        }
      }
      this.showModal = false
    },
    toggleProjectSelection(projectId) {
      const index = this.selectedWorkspace.project_ids.indexOf(projectId)
      if (index > -1) {
        this.selectedWorkspace.project_ids.splice(index, 1)
      } else {
        this.selectedWorkspace.project_ids.push(projectId)
      }
    },
    getProjectName(projectId) {
      if (projectId === '*') {
        return "All projects";
      }
      const project = this.availableProjects.find(p => p.project_id === projectId)
      return project ? project.project_name : 'Unknown'
    },
    addDockerSetting() {
      if (this.newDockerSetting.key && this.newDockerSetting.value) {
        this.settings.workspace_docker_settings = {
          ...this.settings.workspace_docker_settings,
          [this.newDockerSetting.key]: this.newDockerSetting.value 
        }
        this.newDockerSetting = { key: '', value: '' }
      }
    },
    removeDockerSetting(key) {
      this.$delete(this.settings.workspace_docker_settings, key)
    }
  }
}
</script>