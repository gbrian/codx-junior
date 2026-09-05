<script setup>
import ExportImportButton from './ExportImportButton.vue'
import Document from './document/Document.vue'
import ProfileChatEditor from './ProfileChatEditor.vue'
</script>

<template>
  <div class="edit-profile flex flex-col h-full gap-2 px-2">
    <!-- Header bar (full width) -->
    <div class="flex items-center gap-2 font-bold shrink-0">
      <button class="btn btn-sm btn-ghost" @click="cancelEdit">
        <i class="fa-solid fa-arrow-left"></i>
      </button>
      <div class="avatar tooltip tooltip-bottom" :data-tip="project?.project_name">
        <div class="w-6 rounded-full cursor-pointer" @click="switchProject">
          <img :src="project?.project_icon || '/only_icon.png'" />
        </div>
      </div>
      <span class="text-lg">Profile</span>
      <span class="badge badge-warning badge-sm" v-if="isInherit">Inherited</span>
      <span class="badge badge-info badge-sm" v-if="isProjectProfile">Built-in</span>
      <div class="grow"></div>
      <ExportImportButton :data="editProfile" @change="editProfile = $event" />
      <button type="button" @click="onDeleteProfile" class="btn btn-sm btn-error" :disabled="isInherit || loading">
        <i class="fa-solid fa-trash"></i>
      </button>
      <button type="button" class="btn btn-sm btn-ghost" @click="reloadProfile" :disabled="loading">
        <i class="fa-solid fa-rotate-left"></i>
      </button>
      <button type="button" class="btn btn-sm btn-primary" :class="loading && 'loading loading-spinner'" @click="onSubmit">
        <i class="fa-solid fa-floppy-disk mr-1"></i> Save
      </button>
    </div>

    <!-- Category color strip -->
    <div class="h-1 w-full rounded-full transition-all shrink-0"
      :class="{
        'bg-primary': editProfile.category === 'assistant',
        'bg-secondary': editProfile.category === 'chat',
        'bg-accent': editProfile.category === 'agent',
        'bg-info': editProfile.category === 'file',
        'bg-neutral': editProfile.category === 'project'
      }">
    </div>

    <!-- Main content: Two-column layout -->
    <div class="flex gap-3 flex-1 min-h-0">
      
      <!-- LEFT SIDEBAR: Profile metadata -->
      <div class="w-80 flex flex-col gap-3 overflow-y-auto bg-base-200 rounded-md p-3 shrink-0">
        
        <!-- Avatar preview -->
        <div class="flex flex-col items-center gap-2">
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

        <!-- Divider -->
        <div class="divider my-1"></div>

        <!-- Name + Category -->
        <div class="flex flex-col gap-2">
          <template v-if="!isProjectProfile">
            <div>
              <label class="label label-text text-xs pb-1">Name*</label>
              <input
                v-model="editProfile.name"
                type="text"
                placeholder="Profile name"
                :class="nameTaken ? 'input-error' : ''"
                class="bg-base-300 input input-sm input-bordered w-full"
              />
            </div>
            <div>
              <label class="label label-text text-xs pb-1">Category</label>
              <select v-model="editProfile.category" class="select select-sm select-bordered w-full">
                <option value="project" v-if="profile.category === 'project'">Project</option>
                <option value="assistant">Assistant</option>
                <option value="chat">Chat</option>
                <option value="file">File</option>
                <option value="agent">Agent</option>
              </select>
            </div>
          </template>
          <template v-else>
            <span class="font-bold text-base">{{ editProfile.name }}</span>
          </template>
        </div>

        <!-- Avatar URL -->
        <div>
          <label class="label label-text text-xs pb-1">Avatar URL</label>
          <input
            placeholder="Avatar URL"
            v-model="editProfile.avatar"
            type="text"
            class="bg-base-300 input input-sm input-bordered w-full"
          />
        </div>

        <!-- LLM Model -->
        <div>
          <label class="label label-text text-xs pb-1">Model</label>
          <select class="select select-bordered select-sm w-full bg-base-300" v-model="editProfile.llm_model">
            <option value="">-- default model --</option>
            <option v-for="model in aiModels" :key="model.name" :value="model.name">
              {{ model.ai_provider }} — {{ model.name }}
            </option>
          </select>
          <span v-if="editProfile.llm_model" class="badge badge-xs badge-warning font-mono mt-1">
            <i class="fa-solid fa-brain mr-1"></i>{{ editProfile.llm_model }}
          </span>
        </div>

        <!-- Description -->
        <div>
          <label class="label label-text text-xs pb-1">Description</label>
          <textarea
            v-model="editProfile.description"
            placeholder="Describe this profile's purpose..."
            class="bg-base-300 textarea textarea-bordered w-full textarea-sm resize-none"
            rows="2"
          ></textarea>
        </div>

        <!-- Divider -->
        <div class="divider my-1"></div>

        <!-- File match + linked profiles -->
        <div class="flex flex-col gap-2">
          <div>
            <label class="label label-text text-xs pb-1">
              <i class="fa-solid fa-file-code mr-1"></i> File Match (regex)
            </label>
            <input
              v-model="editProfile.file_match"
              type="text"
              placeholder="e\.g\. \.vue$"
              :class="!isValidFileMatch ? 'input-error' : ''"
              class="bg-base-300 input input-xs input-bordered font-mono w-full"
            />
          </div>
          <div>
            <label class="label label-text text-xs pb-1">
              <i class="fa-solid fa-link mr-1"></i> Linked Profiles
            </label>
            <select v-model="newProfile" @change="addProfile" class="select select-xs select-bordered w-full">
              <option value="">+ Add profile</option>
              <option v-for="p in $projects.profiles" :key="p.id" :value="p.name">{{ p.name }}</option>
            </select>
            <div class="flex flex-wrap gap-1 mt-2">
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
      </div>

      <!-- RIGHT COLUMN: Content unified tab + Settings -->
      <div class="flex-1 min-w-0 flex flex-col gap-2">
        
        <!-- Tabs -->
        <div role="tablist" class="tabs tabs-bordered shrink-0">
          <div role="tab" class="tab gap-1" :class="tab === 'content' ? 'tab-active font-semibold' : ''" @click="tab = 'content'">
            <i class="fa-solid fa-file-lines text-xs"></i> Content
          </div>
          <div role="tab" class="tab gap-1" :class="tab === 'settings' ? 'tab-active font-semibold' : ''" @click="tab = 'settings'">
            <i class="fa-solid fa-sliders text-xs"></i> Settings
          </div>
        </div>

        <!-- Tab content -->
        <div class="flex-1 min-h-0 flex flex-col rounded-md bg-base-200 p-3">
          
          <!-- Content tab: unified view/edit -->
          <div class="flex flex-col gap-2 h-full" v-if="tab === 'content'">
            <div class="flex justify-between items-center shrink-0">
              <label class="label-text font-semibold flex gap-2 items-center">
                <i class="fa-solid fa-file-lines"></i> System Prompt
              </label>
              <div class="flex gap-1">
                <button class="btn btn-xs btn-ghost gap-1" @click="copyContent" title="Copy content to clipboard">
                  <i class="fa-solid fa-copy"></i>
                  Copy
                </button>
                <button class="btn btn-xs btn-ghost gap-1" @click="toggleContentMode">
                  <i :class="contentMode === 'view' ? 'fa-solid fa-pencil-alt' : 'fa-solid fa-eye'"></i>
                  {{ contentMode === 'view' ? 'Edit' : 'View' }}
                </button>
              </div>
            </div>

            <!-- View mode: Document preview -->
            <div class="flex-1 min-h-0 overflow-auto rounded-md bg-base-100 border border-base-300 p-3" v-if="contentMode === 'view'">
              <Document
                :content="editProfile.content"
                :files="null"
                :project="project"
                :chat="null"
                :loading="false"
                :documentId="`profile-${editProfile.id}`"
                :message="null"
              />
            </div>

            <!-- Edit mode: Chat editor for content editing -->
            <div class="flex-1 min-h-0 overflow-hidden" v-else>
              <ProfileChatEditor
                :profile="editProfile"
                :initialContent="editProfile.content"
                @update:chatId="onChatIdChange"
                @content-changed="onContentChanged"
                @save-chat-id="onSaveChatId"
                class="h-full"
              />
            </div>
          </div>

          <!-- Settings tab -->
          <div class="flex flex-col gap-3 overflow-y-auto h-full" v-if="tab === 'settings'">
            
            <!-- Quick Settings -->
            <div class="flex flex-col gap-2">
              <div class="text-xs font-semibold uppercase tracking-wide text-base-content/60">Settings</div>
              <div class="flex items-center gap-2">
                <i class="fa-solid fa-book text-info text-sm"></i>
                <span class="text-xs">Use Knowledge</span>
                <input type="checkbox" v-model="editProfile.use_knowledge" class="toggle toggle-xs checked:border-info checked:bg-info ml-auto" />
              </div>
              <div class="flex items-center gap-2">
                <i class="fa-solid fa-share-nodes text-warning text-sm"></i>
                <span class="text-xs">Expose in API</span>
                <input type="checkbox" v-model="editProfile.api_settings.active" class="toggle toggle-xs checked:border-warning checked:bg-warning ml-auto" />
              </div>
            </div>

            <!-- API Settings (conditional) -->
            <div v-if="editProfile.api_settings.active" class="flex flex-col gap-2 pl-3 border-l-2 border-warning/40">
              <div>
                <label class="label label-text text-xs pb-1">API Model Name</label>
                <input
                  :placeholder="`default: ${$project.project_name}/${editProfile.name}`"
                  v-model="editProfile.api_settings.modelName"
                  type="text"
                  class="input input-sm input-bordered bg-base-300 w-full"
                />
              </div>
              <div>
                <label class="label label-text text-xs pb-1">API Model Description</label>
                <textarea v-model="editProfile.api_settings.modelDescription" class="textarea textarea-bordered bg-base-300 textarea-sm w-full" rows="2"></textarea>
              </div>
            </div>

            <!-- Tools -->
            <div v-if="tools.length" class="flex flex-col gap-2">
              <div class="text-xs font-semibold text-base-content/60 uppercase tracking-wide">
                <i class="fa-solid fa-wrench mr-1"></i> Tools
              </div>
              <div class="flex flex-col gap-1">
                <div
                  v-for="tool in tools"
                  :key="tool.name"
                  class="flex items-center gap-2 p-1.5 rounded-md bg-base-100 border border-base-300"
                >
                  <input
                    type="checkbox"
                    :checked="editProfile.tools?.includes(tool.name)"
                    @click="toggleTool(tool)"
                    class="toggle toggle-xs checked:border-info checked:bg-info"
                  />
                  <div class="flex flex-col flex-1 min-w-0">
                    <span class="text-xs font-medium truncate">{{ tool.name }}</span>
                    <span class="text-xs text-base-content/50 line-clamp-1">{{ tool.description }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete confirm modal -->
    <div class="modal modal-open" v-if="confirmDelete">
      <div class="modal-box flex flex-col gap-4">
        <h3 class="font-bold text-lg text-error">
          <i class="fa-solid fa-triangle-exclamation mr-2"></i> Delete Profile?
        </h3>
        <p class="text-sm text-base-content/70">
          This will permanently delete the profile "{{ editProfile.name }}" from this project. This action cannot be undone.
        </p>
        <div class="modal-action">
          <button type="button" @click="confirmDelete = false" class="btn btn-sm btn-ghost">Cancel</button>
          <button type="button" @click="confirmDeleteAction" :disabled="deleting" class="btn btn-sm btn-error" :class="deleting && 'loading loading-spinner'">
            <i class="fa-solid fa-trash mr-1"></i> Delete
          </button>
        </div>
      </div>
      <div class="modal-backdrop" @click="confirmDelete = false"></div>
    </div>

    <!-- Chat ID save indicator -->
    <div class="toast toast-bottom toast-end" v-if="savingChatId">
      <div class="alert alert-info gap-2">
        <span class="loading loading-spinner loading-xs"></span>
        <span>Saving profile...</span>
      </div>
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
      deleting: false,
      tab: 'content',
      contentMode: 'view',
      newProfile: '',
      tools: [],
      plugins: [],
      savingChatId: false
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
    isInherit() {
      return !this.editProfile.path?.startsWith(this.$project.abs_project_path)
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
      this.confirmDelete = true
    },
    async confirmDeleteAction() {
      this.deleting = true
      try {
        await this.$storex.profiles.deleteProfile({
          project: this.project,
          profile: this.profile
        })
        this.confirmDelete = false
        this.$ui.addNotification({
          text: `Profile "${this.profile.name}" deleted successfully`,
          type: 'success'
        })
        this.$emit('deleted')
      } catch (error) {
        console.error('Failed to delete profile:', error)
        this.$ui.addNotification({
          text: 'Failed to delete profile',
          type: 'error'
        })
      } finally {
        this.deleting = false
      }
    },
    copyContent() {
      this.$storex.ui.copyTextToClipboard(this.editProfile.content)
    },
    toggleContentMode() {
      this.contentMode = this.contentMode === 'view' ? 'edit' : 'view'
    },
    reloadProfile() {
      this.editProfile = { ...this.profile }
      this.contentMode = 'view'
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
        project && this.$projects.activeProjectChanged(project)
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
    },
    async onSaveChatId(chatId) {
      if (!chatId) return

      this.savingChatId = true
      try {
        this.editProfile.chat_id = chatId
        const fullProfile = await this.project.$api.profiles.load(this.profile.id)
        fullProfile.chat_id = chatId
        await this.project.$api.profiles.save(fullProfile)
        this.profile.chat_id = chatId
        this.$ui.addNotification({
          text: 'Chat linked to profile successfully',
          type: 'success'
        })
      } catch (error) {
        console.error('Failed to save chat_id:', error)
        this.$ui.addNotification({
          text: 'Failed to link chat',
          type: 'error'
        })
      } finally {
        this.savingChatId = false
      }
    },
    async onChatIdChange(newChatId) {
      if (!newChatId || this.editProfile.chat_id === newChatId) return

      this.savingChatId = true
      try {
        const fullProfile = await this.project.$api.profiles.load(this.profile.id)
        fullProfile.chat_id = newChatId
        await this.project.$api.profiles.save(fullProfile)
        this.editProfile.chat_id = newChatId
        this.profile.chat_id = newChatId
        this.$ui.addNotification({
          text: 'Profile chat updated successfully',
          type: 'success'
        })
      } catch (error) {
        console.error('Failed to update profile chat_id:', error)
        this.$ui.addNotification({
          text: 'Failed to save profile chat',
          type: 'error'
        })
      } finally {
        this.savingChatId = false
      }
    },
    onContentChanged(newContent) {
      if (newContent) {
        this.editProfile.content = newContent
      }
    }
  }
}
</script>