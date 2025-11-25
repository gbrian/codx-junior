
<script setup>
import ExportImportButton from './ExportImportButton.vue';
import Markdown from './Markdown.vue';
</script>

<template>
  <div class="edit-profile px-4 mx-auto flex flex-col gap-2">
    <div class="text-xl flex items-center gap-2 font-bold">
      <button class="btn btn-sm" @click="cancelEdit">
        <i class="fa-solid fa-arrow-left"></i>
      </button>
      <div class="avatar tooltip tooltip-bottom" :data-tip="project?.project_name">
        <div class="w-6 rounded-full click" @click="switchProject">
            <img :src="project?.project_icon || '/only_icon.png'" />
        </div>  
      </div>
       Profile
      <div class="grow"></div>
      <button type="button" class="btn btn-sm btn-primary" :class="loading && 'loading loading-spinner'" @click="onSubmit">Update</button>
      <button type="button" @click="onDeleteProfile" class="btn btn-sm btn-error" :disabled="!isOverriden || loading">Delete</button>
      <ExportImportButton :data="editProfile" @change="editProfile = $event" />
    </div>
    <div class="flex justify-center">
      <div class="flex flex-col gpa-2 items-center w-full">
        <div class="avatar">
          <div class="w-24 rounded">
            <img :src="userAvatar" />
          </div>
        </div>
      </div>
    </div>
    <div class="flex justify-between items-end gap-4">
      <div class="flex flex-col grow gap-1">
        <div class="flex gap-2 items-center">
          Name* 
          <input v-model="editProfile.name" type="text" placeholder="Name" :class="nameTaken && 'text-error'" class="bg-base-300 input input-sm input-bordered w-full" />
        <div class="flex gap-2 items-center">
          <label for="category">Category*</label>
            <select v-model="editProfile.category" :disabled="profile.category === 'project'" class="select select-sm select-bordered">
              <option value="project" v-if="profile.category === 'project'">Project</option>
              <option value="assistant">Assistant</option>
              <option value="chat">Chat</option>
              <option value="file">File</option>
              <option value="agent">Agent</option>
            </select>
          </div>        
        </div>
        <div class="flex gap-2 items-center">Avatar <input placeholder="Avatar" v-model="editProfile.avatar" type="text" class="bg-base-300 input input-sm input-bordered w-full" /></div>
      </div>
    </div>
    <div class="form-group">
      <label for="description">Description</label>
      <textarea id="description" v-model="editProfile.description" class="bg-base-300 textarea textarea-bordered w-full"></textarea>
    </div>
    <div class="form-group flex space-x-4 text-xs">
      <div class="w-1/2 flex flex-col gap-2">
        <label for="fileMatch">File Match</label>
        <input id="fileMatch" v-model="editProfile.file_match" type="text" 
          :class="!isValidFileMatch && 'text-error'"
          class="bg-base-300 input input-xs input-bordered w-full" />
      </div>
    </div>
    <div class="form-group">
      <label for="description">Parent profiles</label>
      <div class="flex flex-wrap gap-2">
        <select v-model="newProfile" @change="addProfile" class="select select-xs select-bordered">
          <option value="">Add a profile</option>
          <option v-for="profile in $projects.profiles" :key="profile.id" :value="profile.name">{{ profile.name }}</option>
        </select>
        <div v-for="profile in editProfile.profiles" :key="profile.id" class="badge badge-secondary">
          {{ profile }} <button @click="removeProfile(profile)" class="fa fa-times"></button>
        </div>
      </div>
    </div>
    <div class="form-group">
      <label for="description">Description</label>
      <textarea id="description" v-model="editProfile.description" class="bg-base-300 textarea textarea-bordered w-full"></textarea>
    </div>

    <div role="tablist" class="tabs tabs-boxed">
      <div role="tab" class="tab" :class="{ 'tab-active': tab === 'content' }" @click="tab = 'content'">
        Content
      </div>
      <div role="tab" class="tab" :class="{ 'tab-active': tab === 'settings' }" @click="tab = 'settings'">
        Settings
      </div>
    </div>

    <div class="form-group flex flex-col gap-4" v-if="tab === 'settings'">
      <div class="flex gap-2 items-center">
        Expose in API
        <input type="checkbox" v-model="editProfile.api_settings.active" class="toggle checked:border-info checked:bg-info" />
      </div>
      <div class="pl-4 flex flex-col gap-2" v-if="editProfile.api_settings.active">
        <label for="modelName">API Model Name</label>
        <input :placeholder="`default: ${$project.project_name}/${editProfile.name}`" v-model="editProfile.api_settings.modelName" type="text" class="input input-sm input-bordered bg-base-300" />
        <label for="modelDescription">API Model Description</label>
        <textarea v-model="editProfile.api_settings.modelDescription" class="textarea textarea-bordered bg-base-300"></textarea>
      </div>
      <select class="select select-bordered select-sm" v-model="editProfile.llm_model">
        <option value="">-- default model --</option>
        <option v-for="model in aiModels" :key="model.name" :value="model.name">
          {{ model.ai_provider }} - {{ model.name }}
        </option>
      </select>
      <div class="flex gap-2 items-center">
        Use knowledge
        <input type="checkbox" v-model="editProfile.use_knowledge" class="toggle checked:border-info checked:bg-info" />
      </div>
      <div class="flex gap-2 items-center">
        Chat mode
        <select v-model="editProfile.chat_mode" class="select select-sm select-bordered">
          <option value="task">Task</option>
          <option value="chat">Chat</option>
          <option value="code">Coding</option>
          <option value="browser">Browser</option>
        </select>
      </div>
    </div>
    <div class="flex flex-col gap-2" v-if="tab === 'content'">
      <div class="flex justify-between">
        <label for="content" class="flex gap-2">Content
          <button class="btn btn-xs" @click="toggleContentPreview">
            <i :class="contentPreview ? 'fa-solid fa-pencil-alt' : 'fa-solid fa-eye'"></i>
          </button>
        </label>
      </div>
      <Markdown class="p-2 rounded-md" :class="contentPreview ? 'bg-base-100 border border-slate-700' : 'bg-base-300'" :text="editProfile.content" v-if="contentPreview" />
      <textarea id="content" v-model="editProfile.content" class="textarea textarea-bordered w-full h-96 bg-base-300 overflow-auto" v-else></textarea>
    </div>
    <modal v-if="confirmDelete">
      <div class="text-2xl">Confirm delete?</div>
      <div class="flex gap-2">
        <button type="button" @click="confirmDelete = false" class="btn btn-sm">Cancel</button>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  props: ['profile', 'project', 'allProfiles', 'loading'],
  data() {
    return {
      editProfile: { ...this.profile },
      confirmDelete: false,
      contentPreview: true,
      tab: 'content',
      newProfile: ''
    }
  },
  computed: {
    userAvatar() {
      return this.editProfile.avatar ||
        'https://img.daisyui.com/images/stock/photo-1534528741775-53994a69daeb.webp'
    },
    aiModels() {
      return this.$storex.api.globalSettings?.ai_models
                ?.filter(m => m.model_type === 'llm')
                ?.sort((a, b) => a.ai_provider > b.ai_provider ? 1 : -1)
    },
    isOverriden() {
      return !this.profile.path || this.profile.path?.startsWith(this.$project.project_path)
    },
    nameTaken() {
      const { name } = this.editProfile
      const { name: orgName } = this.profile
      return name !== orgName && this.allProfiles.find(p => p.name.toLowerCase() === name?.toLowerCase())
    },
    isValidFileMatch() {
      if (this.editProfile.category !== "file") {
        return true
      }
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
    deleteProfile() {
      this.confirmDelete = true
    },
    onDeleteProfile() {
      this.confirmDelete = false
      this.$emit('delete')
    },
    async toggleContentPreview() {
      /*
      if (!this.editProfile.chat_id) {
        const chat = await this.$projects.createNewChat({
          name: `Profile ${this.editProfile.name}`,
          mode: 'task',
          board: "Profiles",
          column: "Profile"
        })
        this.editProfile.chat_id = chat.id
        this.onSubmit()
      }
      */
      this.contentPreview = !this.contentPreview
    },
    downloadProfileContent() {
      console.log('Download initiated for:', this.editProfile.url)
    },
    addProfile() {
      if (this.newProfile && !this.editProfile.profiles.includes(this.newProfile)) {
        this.editProfile.profiles.push(this.newProfile)
        this.newProfile = ''
      }
    },
    removeProfile(profile) {
      this.editProfile.profiles = this.editProfile.profiles.filter(p => p !== profile)
    },
    switchProject() {
      if (this.$project.project_id !== this.project.project_id) {
        const project = this.$projects.allProjects.find(p => p.project_id === this.project.project_id)
        project && this.$projects.setActiveProject(project)
      }
    }
  }
}
</script>