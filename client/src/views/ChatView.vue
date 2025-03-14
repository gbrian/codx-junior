<script setup>
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import TaskCard from '@/components/kanban/TaskCard.vue'
import Kanban from '@/components/kanban/Kanban.vue'
import moment from 'moment'
import ModelSelector from '@/components/ai_settings/ModelSelector.vue'
</script>

<template>
  <div class="flex flex-col h-full pb-2" v-if="chat">
    <div class="grow flex gap-2 h-full justify-between">
      <div class="grow flex flex-col gap-2 w-full">
        <div class="flex gap-2 items-center" v-if="!chatMode">
          <div class="flex items-start gap-2 w-full">
            <div class="flex gap-2 items-start">
              <input v-if="editName" type="text" class="input input-xs input-bordered" @keydown.enter.stop="saveChat" @keydown.esc="editName = false" v-model="chat.name" />
              <div class="font-bold flex flex-col" v-else>
                <div class="my-2 text-xs hover:underline click font-bold text-primary"
                  @click="naviageToParent"
                  v-if="parentChat || Kanban">
                  <i class="fa-solid fa-turn-up"></i> {{ parentChat?.name || kanban?.title }} ...
                </div>
                <div class="flex items-center gap-2">
                  <div class="dropdown">
                    <div tabindex="0" role="button" class="btn btn-xs btn-outline flex gap-1 items-center">
                      <i :class="chatModes[chat.mode].icon" class="fa-regular fa-comments"></i>
                    </div>
                    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                      <li v-for="info, mode in chatModes" :key="mode">
                        <details open v-if="info.profiles.length > 1">
                          <summary>
                            <i :class="info.icon" class="fa-regular fa-comments"></i>
                            {{ info.name }}
                          </summary>
                          <ul>
                            <li @click="setChatMode(mode, profile)" v-for="profile in info.profiles" :key="profile">
                              <a>{{ profile  }}</a>
                            </li>
                          </ul>
                        </details>
                        <a class="flex items-center" @click="setChatMode(mode, info.profiles[0])" v-else>
                          <i :class="info.icon" class="fa-regular fa-comments"></i>
                          {{ info.name }}
                        </a>
                      </li>
                    </ul>
                  </div>
                  <div class="click text-xs md:text-xl" @click="editName = true">
                    {{ chat.name }}
                  </div>
                </div>
              </div>
            </div>
            <div class="grow"></div>
            <div class="flex gap-1 items-center">
              <div class="flex gap-2 p-1 items-center -top-1" v-if="toggleChatOptions">
                <button class="btn btn-xs" v-if="hiddenCount" @click="showHidden = !showHidden">
                  <div class="flex items-center gap-2" v-if="!showHidden">
                    ({{ hiddenCount }})
                    <i class="fa-solid fa-eye-slash"></i>
                  </div>
                  <span class="text-warning" v-else>
                    <i class="fa-solid fa-eye"></i>
                  </span>
                </button>
                <div class="dropdown dropdown-end dropdown-bottom">
                  <div tabindex="0" class="btn btn-sm flex items-center indicator">
                    Tasks
                    <span v-if="childrenChats.length">
                      ({{ childrenChats.length }})
                    </span>
                    <i class="fa-solid fa-caret-down"></i>
                  </div>
                  <ul tabindex="0" class="dropdown-content menu bg-base-300 rounded-box z-[1] p-2 w-96 shadow">
                    <li @click="newSubChat()">
                      <a>New sub task</a>
                    </li>
                    <li @click="createSubTasks()">
                      <a>Create sub tasks <i class="fa-solid fa-wand-magic-sparkles"></i></a>
                    </li>
                    <div class="divider" v-if="childrenChats.length"></div>
                    <div class="max-h-96 w-full overflow-auto flex flex-col gap-2 p-1">
                      <TaskCard class="p-2" :task="child" @click="$projects.setActiveChat(child)"
                            v-for="child in childrenChats" :key="childrenChats.id" />
                    </div>
                  </ul>
                </div>
                <button class="btn btn-xs hover:btn-info hover:text-white" @click="saveChat">
                  <i class="fa-solid fa-floppy-disk"></i>
                </button>
                <div class="grow"></div>
                <button class="btn btn-xs btn-error btn-outline mt-1 text-white" @click="navigateToChats">
                  <i class="fa-regular fa-circle-xmark"></i>
                </button>
              </div>
              <div class="md:hidden btn btn-sm" @click="toggleChatOptions = !toggleChatOptions">
                <i class="fa-solid fa-bars"></i>
              </div>
            </div>
          </div>
        </div>
        <div class="flex justify-between">
          <div class="flex gap-2 items-center">
            <div class="text-xs">{{ formattedChatUpdatedDate }}</div>
            <div class="badge badge-sm badge-info flex gap-2" v-for="tag in chat.tags" :key="tag">
              {{ tag }}
              <button class="btn btn-xs btn-ghost" @click="removeTag(tag)">
                x
              </button>
            </div>
            <button class="btn btn-xs" @click="newTag = ''">
              + tag
            </button>
            <div class="badge text-secondary" v-for="profile in chatProfiles" :key="profile.name">
              {{ profile.name }}
              <i class="fa-solid fa-book" :class="profile.use_knowledge ? 'text-info' : 'text-error'" ></i>
            </div>
          </div>
          <div class="flex gap-2 justify-end">
            <ModelSelector class="select-xs" v-model="chat.model" />
            <select v-model="chat.project_id" class="select select-bordered select-xs w-full max-w-xs"
              @change="saveChat"
            >
              <option v-for="project in subProjects" :key="project.project_id"
                :value="project.project_id"
                :selected="project.project_id === chatProject.project_id"
              >
              {{ project.project_name }} <span>({{ $projects.aiModel }})</span>
              </option>
            </select>
          </div>
        </div>
        <div class="w-full overflow-auto" v-if="chatFiles.length">
          <div class="my-2 text-xs">
            <span>
              <i class="fa-solid fa-paperclip"></i>
            </span>
            <a v-for="file in chatFiles" :key="file" :data-tip="file" class="group text-nowrap ml-2 hover:underline hover:bg-base-300 click text-accent" @click="$ui.openFile(file)">
              <span>{{ file.split('/').reverse()[0] }}</span>
              <span class="ml-2 click" @click.stop="onRemoveFile(file)">
                <i class="fa-regular fa-circle-xmark"></i>
              </span>
            </a>
          </div>
        </div>
        <Chat :chatId="chat.id"
          :showHidden="showHidden"
          :childrenChats="childrenChats"
          @refresh-chat="loadChat(chat)"
          @add-file="onAddFile"
          @remove-file="onRemoveFile" 
          @delete-message="onRemoveMessage"
          @delete="confirmDelete = true"
          @save="saveChat" 
          v-if="chat"/>
        <modal v-if="confirmDelete">
          <div class="">
            <h3 class="font-bold text-lg">Confirm Delete</h3>
            <p class="text-error font-bold">Are you sure you want to delete this chat?</p>
            <div class="text-xl p-1">{{ chat.name }}</div>
            <div class="modal-action">
              <button class="btn btn-error" @click="confirmDeleteChat">Delete</button>
              <button class="btn" @click="resetConfirmDelete">Cancel</button>
            </div>
          </div>
        </modal>
        <modal class="modal modal-open" role="dialog" v-if="showFile || addFile !== null">
          <div class="modal-box flex flex-col gap-4 p-4">
            <h3 class="font-bold text-lg" v-if="showFile">
              This file belongs to the task context:
              <div class="font-thin">{{ showFile }}</div>
            </h3>
            <div v-else>
              <input type="text" class="input input-bordered w-full" v-model="addFile" placeholder="Add file to context, full path" />
            </div>
            <div class="flex gap-2 justify-center">
              <button class="btn btn-error" @click="removeFileFromContext" v-if="showFile">
                Remove
              </button>
              <button class="btn btn-primary" @click="addFileToContext" v-else>
                Add
              </button>
              <button class="btn" @click="addFile = showFile = null">
                Close
              </button>
            </div>
          </div>
        </modal>
        <modal v-if="newTag !== null">
          <div class="flex flex-col gap-2">
            <div class="text-xl">New tag</div>
            <select class="select select-sm select-bordered" @change="newTag = $event.target.value">
              <option value="" selected>New</option>
              <option v-for="t in $projects.allTags" :key="t" :value="t">{{t}}</option>
            </select>
            <input type="text" class="input input-sm input-bordered" v-model="newTag" />
            <div class="flex gap-2 justify-end">
              <button class="btn btn-error" @click="newTag = null">
                Cancel
              </button>
              <button class="btn" @click="addNewTag" :disabled="newTag.length === 0">
                Add
              </button>
            </div>
          </div>
        </modal>
        <modal v-if="showSubtaskModal">
          <div class="flex flex-col gap-4 p-4">
            <h3 class="font-bold text-lg">Create New Subtask</h3>
            <input v-model="subtaskName" type="text" class="input input-bordered" placeholder="Subtask Name" />
            <textarea v-model="subtaskDescription" class="textarea textarea-bordered" placeholder="Short Description (optional)" rows="3"></textarea>
            <div class="flex gap-2 justify-end">
              <button class="btn btn-error" @click="cancelSubtask">Cancel</button>
              <button class="btn btn-primary" @click="createSubtask">Create</button>
            </div>
          </div>
        </modal>
      </div>
      <add-file-dialog v-if="addNewFile" @open="onAddFile" @close="addNewFile = false" />
    </div>
  </div>
</template>

<script>
export default {
  props: ['chatMode', 'openChat', 'kanban'],
  data() {
    return {
      showFile: null,
      addFile: null,
      showChatsTree: false,
      editName: false,
      showSettings: false,
      addNewFile: null,
      showHidden: false,
      confirmDelete: false,
      newTag: null,
      toggleChatOptions: false,
      showSubtaskModal: false,
      subtaskName: '',
      subtaskDescription: ''
    }
  },
  mounted () {
    this.toggleChatOptions = !this.$ui.isMobile
  },
  computed: {
    chatProfiles () {
      const { profiles } = this.$projects
      return this.chat.profiles?.map(name => profiles.find(p => p.name === name ))
    },
    chatModes () {
      return this.$projects.chatModes
    },
    subProjects () {
      return [
        this.$project,
        ...this.$projects.childProjects || [],
        ...this.$projects.projectDependencies || []
      ]
    },
    hiddenCount() {
      return this.chat.messages?.filter(m => m.hide).length
    },
    messages() {
      return this.chat.messages.filter(m => !m.hide || this.showHidden)
    },
    formattedChatUpdatedDate() {
      const updatedAt = this.chat.updated_at
      return moment(updatedAt).isAfter(moment().subtract(7, 'days'))
        ? moment(updatedAt).fromNow()
        : moment(updatedAt).format('YYYY-MM-DD')
    },
    chats() {
      return this.$projects.allChats
    },
    chat() {
      return this.$projects.chats[this.openChat?.id || this.$projects.activeChat.id]
    },
    childrenChats() {
      return this.$storex.projects.allChats.filter(c => c.parent_id === this.chat.id)
        .sort((a, b) => (a.updated_at || a.created_at) > (b.updated_at || b.created_at) ? -1 : 1)
    },
    chatProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.chat.project_id) ||
              this.$project
    },
    parentChat () {
      return this.$projects.allChats.find(c => c.id === this.chat.parent_id)
    },
    chatFiles() {
      return [...this.chat.file_list||[], ...this.parentChat?.file_list||[]]
    }
  },
  methods: {
    async saveChat() {
      this.editName = false
      await this.$projects.saveChat(this.chat)
    },
    async confirmDeleteChat() {
      this.confirmDelete = false
      const parent_id = this.chat.parent_id
      await this.$projects.deleteChat(this.chat)
      const parentChat = this.parentChat
      if (parentChat) {
        this.$projects.setActiveChat(parentChat)
      } else {
        this.navigateToChats()
      }
    },
    resetConfirmDelete() {
      this.confirmDelete = false
    },
    async loadChat(chat) {
      await this.$projects.setActiveChat(chat)
      this.showChatsTree = false
    },
    async removeFileFromContext() {
      this.chat.profiles = this.chat.profiles?.filter(f => f !== this.showFile)
      this.onRemoveFile(this.showFile)
      await this.loadChat(this.chat)
      this.showFile = null
    },
    async addFileToContext() {
      this.onAddFile(this.addFile)
      await this.saveChat()
      await this.loadChat(this.chat)
      this.showFile = null
      this.addFile = null
    },
    async onAddFile(file) {
      if (this.chat.file_list?.includes(file)) {
        return
      }
      this.chat.file_list = [...(this.chat.file_list || []), file]
      this.addNewFile = null
      await this.saveChat()
    },
    async onRemoveFile(file) {
      this.chat.file_list = (this.chat.file_list || []).filter(f => f !== file)
      this.addNewFile = null
      await this.saveChat()
    },
    async addProfile(profile) {
      if (this.chat.profiles?.includes(profile)) {
        return
      }
      this.chat.profiles = [...this.chat.profiles || [], profile]
      await this.saveChat()
    },
    removeProfile(profile) {
      if (this.chat.profiles?.includes(profile)) {
        this.chat.profiles = this.chat.profiles.filter(p => p !== profile)
        this.saveChat()
      }
    },
    onRemoveMessage(message) {
      const ix = this.chat.messages.findIndex(m => m.doc_id === message.doc_id)
      if (this.chat.mode == 'task' && message.role === "assistant" && ix > 1) {
        this.chat.messages[ix - 1].hide = false
      }
      this.chat.messages = this.chat.messages.filter((_, i) => i !== ix)
      this.saveChat()
    },
    navigateToChats() {
      this.$emit('chats')
    },
    async newSubChat() {
      this.showSubtaskModal = true
    },
    createSubtask() {
      if (this.subtaskName.trim()) {
        this.$emit('sub-task', {
          parent: this.chat,
          name: this.subtaskName,
          description: this.subtaskDescription
        })
        this.resetSubtaskModal()
      }
    },
    cancelSubtask() {
      this.resetSubtaskModal()
    },
    resetSubtaskModal() {
      this.showSubtaskModal = false
      this.subtaskName = ''
      this.subtaskDescription = ''
    },
    addNewTag() {
      this.chat.tags = [...new Set([...this.chat.tags || [], this.newTag])]
      this.newTag = null
      this.saveChat()
    },
    removeTag(tag) {
      this.chat.tags = this.chat.tags.filter(t => t !== tag)
      this.saveChat()
    },
    setChatMode(mode, profile) {
      this.chat.mode = mode
      this.chat.profiles = [profile]
      this.saveChat()
    },
    async createSubTasks() {
      await this.$storex.projects.createSubTasks(this.chat)
    },
    naviageToParent() {
      if (this.parentChat) {
        this.$emit('chat', this.parentChat)
      } else {
        this.navigateToChats()
      }
    }
  }
}
</script>