<script setup>
import ExportImportButton from './ExportImportButton.vue'
import Markdown from './Markdown.vue'
</script>

<template>
  <div class="edit-profile px-4 mx-auto flex flex-col gap-3">
    <!-- Header bar -->
    <div class="flex items-center gap-2 font-bold">
      <button class="btn btn-sm btn-ghost" @click="cancelEdit">
        <i class="fa-solid fa-arrow-left"></i>
      </button>
      <div class="avatar tooltip tooltip-bottom" :data-tip="project?.project_name">
        <div class="w-6 rounded-full cursor-pointer" @click="switchProject">
          <img :src="project?.project_icon || '/only_icon.png'" />
        </div>
      </div>
      <span class="text-lg">Profile</span>
      <span class="badge badge-warning badge-sm" v-if="isOverriden">Overridden</span>
      <span class="badge badge-info badge-sm" v-if="isProjectProfile">Built-in</span>
      <div class="grow"></div>
      <ExportImportButton :data="editProfile" @change="editProfile = $event" />
      <button type="button" @click="onDeleteProfile" class="btn btn-sm btn-error" :disabled="!isOverriden || loading">
        <i class="fa-solid fa-trash"></i>
      </button>
      <button type="button" class="btn btn-sm btn-primary" :class="loading && 'loading loading-spinner'" @click="onSubmit">
        <i class="fa-solid fa-floppy-disk mr-1"></i> Save
      </button>
    </div>

    <!-- Category color strip -->
    <div class="h-1 w-full rounded-full transition-all"
      :class="{
        'bg-primary': editProfile.category === 'assistant',
        'bg-secondary': editProfile.category === 'chat',
        'bg-accent': editProfile.category === 'agent',
        'bg-info': editProfile.category === 'file',
        'bg-neutral': editProfile.category === 'project'
      }">
    </div>

    <!-- Identity row -->
    <div class="flex gap-4 items-start">
      <!-- Avatar preview -->
      <div class="flex flex-col items-center gap-1 flex-shrink-0">
        <div class="indicator">
          <span class="indicator-item badge badge-xs"
            :class="{
              'badge-primary': editProfile.category === 'assistant',
              'badge-secondary': editProfile.category === 'chat',
              'badge-accent': editProfile.category === 'agent',
              'badge-info': editProfile.category === 'file',
              'badge-neutral': editProfile.category === 'project'
            }">
            {{ editProfile.category }}
          </span>
          <div class="avatar">
            <div class="w-20 rounded-full ring ring-primary ring-offset-base-100 ring-offset-2">
              <img :src="userAvatar" />
            </div>
          </div>
        </div>
        <span class="text-xs text-base-content/50 max-w-[80px] truncate text-center">{{ editProfile.name }}</span>
      </div>

      <!-- Fields -->
      <div class="grow flex flex-col gap-2">
        <!-- Name + Category row -->
        <div class="flex gap-2 items-center flex-wrap">
          <template v-if="!isProjectProfile">
            <label class="text-xs text-base-content/60 w-12">Name*</label>
            <input
              v-model="editProfile.name"
              type="text"
              placeholder="Profile name"
              :class="nameTaken ? 'input-error' : ''"
              class="bg-base-300 input input-sm input-bordered flex-1 min-w-0"
            />
            <label class="text-xs text-base-content/60">Category</label>
            <select v-model="editProfile.category" class="select select-sm select-bordered">
              <option value="project" v-if="profile.category === 'project'">Project</option>
              <option value="assistant">Assistant</option>
              <option value="chat">Chat</option>
              <option value="file">File</option>
              <option value="agent">Agent</option>
            </select>
          </template>
          <template v-else>
            <span class="font-bold text-base">{{ editProfile.name }}</span>
          </template>
        </div>

        <!-- Avatar URL -->
        <div class="flex gap-2 items-center">
          <label class="text-xs text-base-content/60 w-12">Avatar</label>
          <input
            placeholder="Avatar URL"
            v-model="editProfile.avatar"
            type="text"
            class="bg-base-300 input input-sm input-bordered flex-1 min-w-0"
          />
        </div>

        <!-- LLM Model -->
        <div class="flex gap-2 items-center">
          <label class="text-xs text-base-content/60 w-12">Model</label>
          <select class="select select-bordered select-sm flex-1 bg-base-300" v-model="editProfile.llm_model">
            <option value="">-- default model --</option>
            <option v-for="model in aiModels" :key="model.name" :value="model.name">
              {{ model.ai_provider }} — {{ model.name }}
            </option>
          </select>
          <span v-if="editProfile.llm_model" class="badge badge-xs badge-warning font-mono">
            <i class="fa-solid fa-brain mr-1"></i>{{ editProfile.llm_model }}
          </span>
        </div>

        <!-- Description -->
        <div class="flex gap-2 items-start">
          <label class="text-xs text-base-content/60 w-12 pt-1">Desc</label>
          <textarea
            v-model="editProfile.description"
            placeholder="Describe this profile's purpose..."
            class="bg-base-300 textarea textarea-bordered w-full textarea-sm resize-none"
            rows="2"
          ></textarea>
        </div>
      </div>
    </div>

    <!-- File match + linked profiles -->
    <div class="flex gap-3 flex-wrap">
      <div class="form-control flex-1 min-w-[160px]">
        <label class="label label-text text-xs pb-1">
          <i class="fa-solid fa-file-code mr-1"></i> File Match (regex)
        </label>
        <input
          v-model="editProfile.file_match"
          type="text"
          placeholder="e\.g\. \.vue$"
          :class="!isValidFileMatch ? 'input-error' : ''"
          class="bg-base-300 input input-xs input-bordered font-mono"
        />
      </div>
      <div class="form-control flex-1 min-w-[220px]">
        <label class="label label-text text-xs pb-1">
          <i class="fa-solid fa-link mr-1"></i> Linked Profiles
        </label>
        <div class="flex flex-wrap gap-1 items-center">
          <select v-model="newProfile" @change="addProfile" class="select select-xs select-bordered">
            <option value="">+ Add profile</option>
            <option v-for="p in $projects.profiles" :key="p.id" :value="p.name">{{ p.name }}</option>
          </select>
          <span
            v-for="p in editProfile.profiles"
            :key="p"
            class="badge badge-sm badge-secondary gap-1"
          >
            {{ p }}
            <button @click="removeProfile(p)" class="hover:text-error">
              <i class="fa fa-times text-xs"></i>
            </button>
          </span>
        </div>
      </div>
    </div>

    <!-- Tabs -->
    <div role="tablist" class="tabs tabs-bordered mt-2">
      <div role="tab" class="tab gap-1" :class="tab === 'content' ? 'tab-active font-semibold' : ''" @click="tab = 'content'">
        <i class="fa-solid fa-file-lines text-xs"></i> Content
      </div>
      <div role="tab" class="tab gap-1" :class="tab === 'settings' ? 'tab-active font-semibold' : ''" @click="tab = 'settings'">
        <i class="fa-solid fa-sliders text-xs"></i> Settings
      </div>
    </div>

    <!-- Tab panels -->
    <div class="rounded-md bg-base-200 p-3 min-h-[200px]">

      <!-- Settings tab -->
      <div class="flex flex-col gap-4" v-if="tab === 'settings'">
        <!-- Quick toggles -->
        <div class="flex flex-wrap gap-4">
          <div class="flex items-center gap-2">
            <i class="fa-solid fa-book text-info"></i>
            <span class="text-sm">Use Knowledge</span>
            <input type="checkbox" v-model="editProfile.use_knowledge" class="toggle toggle-sm checked:border-info checked:bg-info" />
          </div>
          <div class="flex items-center gap-2">
            <i class="fa-solid fa-share-nodes text-warning"></i>
            <span class="text-sm">Expose in API</span>
            <input type="checkbox" v-model="editProfile.api_settings.active" class="toggle toggle-sm checked:border-warning checked:bg-warning" />
          </div>
        </div>

        <!-- API settings -->
        <div class="pl-4 flex flex-col gap-2 border-l-2 border-warning/40" v-if="editProfile.api_settings.active">
          <div class="form-control">
            <label class="label label-text text-xs">API Model Name</label>
            <input
              :placeholder="`default: ${$project.project_name}/${editProfile.name}`"
              v-model="editProfile.api_settings.modelName"
              type="text"
              class="input input-sm input-bordered bg-base-300"
            />
          </div>
          <div class="form-control">
            <label class="label label-text text-xs">API Model Description</label>
            <textarea v-model="editProfile.api_settings.modelDescription" class="textarea textarea-bordered bg-base-300 textarea-sm" rows="2"></textarea>
          </div>
        </div>

        <!-- Tools -->
        <div v-if="tools.length" class="flex flex-col gap-2">
          <div class="text-xs font-semibold text-base-content/60 uppercase tracking-wide">
            <i class="fa-solid fa-wrench mr-1"></i> Tools & Plugins
          </div>
          <div class="grid grid-cols-1 gap-2">
            <div
              v-for="tool in tools"
              :key="tool.name"
              class="flex items-center gap-3 p-2 rounded-lg bg-base-100 border border-base-300"
            >
              <input
                type="checkbox"
                :checked="editProfile.tools?.includes(tool.name)"
                @click="toggleTool(tool)"
                class="toggle toggle-sm checked:border-info checked:bg-info"
              />
              <div class="flex flex-col flex-1 min-w-0">
                <span class="text-sm font-medium">{{ tool.name }}</span>
                <span class="text-xs text-base-content/50 truncate">{{ tool.description }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Content tab -->
      <div class="flex flex-col gap-2" v-if="tab === 'content'">
        <div class="flex justify-between items-center">
          <label class="label-text font-semibold flex gap-2 items-center">
            <i class="fa-solid fa-file-lines"></i> System Prompt
          </label>
          <button class="btn btn-xs btn-ghost gap-1" @click="toggleContentPreview">
            <i :class="contentPreview ? 'fa-solid fa-pencil-alt' : 'fa-solid fa-eye'"></i>
            {{ contentPreview ? 'Edit' : 'Preview' }}
          </button>
        </div>
        <Markdown
          class="p-3 rounded-md bg-base-100 border border-base-300 min-h-[300px]"
          :text="editProfile.parsed_content"
          v-if="contentPreview"
        />
        <textarea
          v-else
          id="content"
          v-model="editProfile.content"
          class="textarea textarea-bordered w-full bg-base-300 font-mono text-sm"
          style="min-height: 380px;"
          placeholder="Write the system prompt for this profile..."
        ></textarea>
      </div>
    </div>

    <!-- Delete confirm modal -->
    <div class="modal modal-open" v-if="confirmDelete">
      <div class="modal-box flex flex-col gap-4">
        <h3 class="font-bold text-lg text-error">
          <i class="fa-solid fa-triangle-exclamation mr-2"></i> Delete Profile?
        </h3>
        <p class="text-sm text-base-content/70">This action cannot be undone. The profile will be removed from this project.</p>
        <div class="modal-action">
          <button type="button" @click="confirmDelete = false" class="btn btn-sm btn-ghost">Cancel</button>
          <button type="button" @click="onDeleteProfile" class="btn btn-sm btn-error">
            <i class="fa-solid fa-trash mr-1"></i> Delete
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="confirmDelete = false"></div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['profile', 'allProfiles', 'loading'],
  data() {
    return {
      editProfile: { ...this.profile },
      confirmDelete: false,
      contentPreview: true,
      tab: 'content',
      newProfile: '',
      tools: [],
      plugins: []
    }
  },
  created() {
    this.loadTools()
  },
  computed: {
    isProjectProfile() {
      return this.profile.category === 'project'
    },
    project() {
      return this.$projects.allProjectsById[this.editProfile.project_id] || this.$project
    },
    userAvatar() {
      return this.editProfile.avatar ||
        `https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=400&d=robohash&r=${this.editProfile.name}`
    },
    aiModels() {
      return this.$storex.api.globalSettings?.ai_models
        ?.filter(m => m.model_type === 'llm')
        ?.sort((a, b) => a.ai_provider > b.ai_provider ? 1 : -1)
    },
    isOverriden() {
      return this.editProfile.path?.startsWith(this.$project.abs_project_path)
    },
    nameTaken() {
      const { name } = this.editProfile
      const { name: orgName } = this.profile
      return name !== orgName && this.allProfiles.find(p => p.name.toLowerCase() === name?.toLowerCase())
    },
    isValidFileMatch() {
      if (this.editProfile.category !== 'file') return true
      try {
        new RegExp(this.editProfile.file_match)
        return true
      } catch (e) {
        return false
      }
    }
  },
  methods: {
    onSubmit() {
      this.$emit('save', this.editProfile)
    },
    cancelEdit() {
      this.$emit('cancel')
    },
    onDeleteProfile() {
      if (!this.confirmDelete) {
        this.confirmDelete = true
        return
      }
      this.confirmDelete = false
      this.$emit('delete')
    },
    toggleContentPreview() {
      this.contentPreview = !this.contentPreview
    },
    addProfile() {
      if (this.newProfile && !this.editProfile.profiles.includes(this.newProfile)) {
        this.editProfile.profiles.push(this.newProfile)
      }
      this.newProfile = ''
    },
    removeProfile(profile) {
      this.editProfile.profiles = this.editProfile.profiles.filter(p => p !== profile)
    },
    switchProject() {
      if (this.$project.project_id !== this.project.project_id) {
        const project = this.$projects.allProjects.find(p => p.project_id === this.project.project_id)
        project && this.$projects.setActiveProject(project)
      }
    },
    toggleTool(tool) {
      const has = this.editProfile.tools?.includes(tool.name)
      this.editProfile.tools = has
        ? this.editProfile.tools.filter(tn => tn !== tool.name)
        : [...(this.editProfile.tools || []), tool.name]
    },
    async loadTools() {
      const tools = await this.project.$api.profiles.tools()
      const plugins = await this.$storex.api.settings.global.plugins.list()
      this.tools = [...tools, ...plugins.filter(p => p.extends?.includes('profile'))]
    }
  }
}
</script>