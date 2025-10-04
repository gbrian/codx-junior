# [[{"id": "a7be8200-dae5-4029-aad9-655dbc44e946", "doc_id": null, "project_id": null, "parent_id": null, "message_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/client/src/components/workspaces/Workspaces.vue"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Workspace Apps", "pinned": false, "description": "The user requested assistance in adding manager controls for managing the `selectedWorkspace.apps` collection. Each `WorkspaceApp` within this collection has the properties: `name` (a string), `description` (a string), `port` (a number), and `is_vnc` (a boolean). The details provided suggest a focus on developing or modifying application management functionality within a workspace context.", "created_at": "2025-09-18 13:26:27.900252", "updated_at": "2025-09-18T13:37:01.389641", "mode": "task", "kanban_id": "", "column_id": "", "board": "Global Settings", "column": "ToDo", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/client/.codx/tasks/Global Settings/ToDo/workspace-apps.a7be8200-dae5-4029-aad9-655dbc44e946.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": [], "chat_links": [], "pr_view": {}}]]
## [[{"doc_id": "01f931f6-6bae-4a41-bfc0-f75a0006f247", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-18 13:26:27.897740", "updated_at": "2025-09-18 13:26:27.897767", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Add the apps manager controls to manage the selectedWorkspace.apps collection
A WorkspaceApp has:
 * name: string
 * description: string
 * port: number
 * is_vnc: boolean 
## [[{"doc_id": "872c0a41-14ea-4158-9326-f1d0f9d30ac7", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-18 13:26:27.897740", "updated_at": "2025-09-18 13:26:27.897767", "images": [], "files": [], "meta_data": {"time_taken": 118.95966386795044, "first_chunk_time_taken": 0.0002048015594482422, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To manage the `selectedWorkspace.apps` collection, we need to add controls to the template and methods to handle the addition, editing, and removal of `WorkspaceApp` entries within the `selectedWorkspace`. Here's how you can do it:

```vue /shared/codx-junior/client/src/components/workspaces/Workspaces.vue
<script setup>
import { v4 as uuidv4 } from 'uuid'
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
          <span class="label-text">Workspace Start Port</span>
        </label>
        <input v-model="settings.workspace_start_port" type="number" placeholder="Start Port" class="input input-bordered w-full max-w-xs" required />
      </div>
      <div class="form-control mt-4">
        <label class="label">
          <span class="label-text">Workspace End Port</span>
        </label>
        <input v-model="settings.workspace_end_port" type="number" placeholder="End Port" class="input input-bordered w-full max-w-xs" required />
      </div>
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
        <div class="p-4">
          <div>
            <div class="form-control">
              <label class="label">
                <span class="label-text">Workspace Name</span>
              </label>
              <input v-model="selectedWorkspace.name" type="text" placeholder="Workspace Name" class="input input-bordered w-full max-w-xs" required />
            </div>
            <div class="form-control mt-4">
              <label class="label">
                <span class="label-text">Description</span>
              </label>
              <textarea v-model="selectedWorkspace.description" placeholder="Workspace Description" class="textarea textarea-bordered w-full max-w-xs" required></textarea>
            </div>
            <div class="form-control mt-4">
              <label class="label">
                <span class="label-text">Apps</span>
              </label>
              <div v-for="(app, index) in selectedWorkspace.apps" :key="index" class="flex gap-2 items-center mt-2">
                <input v-model="app.name" placeholder="App Name" class="input input-bordered w-24" />
                <input v-model="app.description" placeholder="App Description" class="input input-bordered w-36" />
                <input v-model="app.port" type="number" placeholder="Port" class="input input-bordered w-20" />
                <label class="flex items-center">
                  <input type="checkbox" v-model="app.is_vnc" class="checkbox checkbox-xs" />
                  <span class="ml-1">VNC</span>
                </label>
                <button class="btn btn-error btn-xs" @click="removeApp(index)">
                  <i class="fa-solid fa-circle-xmark"></i>
                </button>
              </div>
              <div class="flex gap-2 items-center mt-2">
                <input v-model="newApp.name" placeholder="App Name" class="input input-bordered w-24" />
                <input v-model="newApp.description" placeholder="App Description" class="input input-bordered w-36" />
                <input v-model="newApp.port" type="number" placeholder="Port" class="input input-bordered w-20" />
                <label class="flex items-center">
                  <input type="checkbox" v-model="newApp.is_vnc" class="checkbox checkbox-xs" />
                  <span class="ml-1">VNC</span>
                </label>
                <button class="btn btn-primary btn-xs" @click="addApp">Add</button>
              </div>
            </div>
            <div class="form-control mt-4">
              <label class="label">
                <span class="label-text">Associated Projects</span>
              </label>
              <div class="flex gap-1 items-center">
                <select class="select select-sm select-bordered grow" v-model="selectedProjectId">
                  <option v-for="project in availableProjects" :key="project.project_id" :value="project.project_id">
                    {{ project.project_name }}
                  </option>
                </select>
                <button class="btn btn-sm btn-primary" @click="toggleProjectSelection(selectedProjectId)">
                  <i class="fa-solid fa-plus"></i>
                </button>
              </div>
              <ul class="list-disc pl-5 mt-2">
                <li v-for="projectId in selectedWorkspace.project_ids" :key="projectId" class="flex items-center">
                  <span>{{ getProjectName(projectId) }}</span>
                  <button class="btn btn-error btn-sm ml-2" @click="toggleProjectSelection(projectId)">
                    <i class="fa-solid fa-circle-xmark"></i>
                  </button>
                </li>
              </ul>
            </div>
            <div class="flex justify-end mt-4">
              <button class="btn btn-error" @click="deleteWorkspace(selectedWorkspace.id)">Delete</button>
              <div class="grow"></div>
              <button class="btn btn-primary mr-2" @click="saveWorkspace">Save</button>
              <button type="button" class="btn btn-ghost" @click="showModal = false">Cancel</button>
            </div>
          </div>
        </div>
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
        apps: [] // Initialize apps array
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
    },
    addApp() {
      if (this.newApp.name && this.newApp.port) {
        this.selectedWorkspace.apps.push({ ...this.newApp })
        this.newApp = { name: '', description: '', port: null, is_vnc: false }
      }
    },
    removeApp(index) {
      this.selectedWorkspace.apps.splice(index, 1)
    }
  }
}
</script>
```

### Explanation:
- **Apps Management:** Added controls to manage `selectedWorkspace.apps`, including input fields for `name`, `description`, `port`, and `is_vnc`.
- **Methods:** Implemented `addApp` and `removeApp` methods for managing the apps collection.
- **Data Structure:** Initialized `apps` array within `selectedWorkspace` to store the list of apps.
- **User Interface:** Added input controls for adding and modifying apps with options to remove them as needed.