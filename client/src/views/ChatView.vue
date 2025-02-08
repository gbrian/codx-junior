<script setup>
import { API } from '../api/api'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import moment from 'moment'
import ChatIconVue from '@/components/chat/ChatIcon.vue'
</script>

<template>
  <div class="flex flex-col h-full pb-2" v-if="chat">
    <div class="grow flex gap-2 h-full justify-between">
      <div class="grow flex flex-col gap-2 w-full">
        <div class="text-xl flex gap-2 items-center" v-if="!chatMode">
          <div class="flex items-start gap-2 w-full">
            <div class="flex gap-2 items-start">
              <input v-if="editName" type="text" class="input input-xs input-bordered" @keydown.enter.stop="saveChat" @keydown.esc="editName = false" v-model="chat.name" />
              <div class="font-bold flex flex-col" v-else>
                <div class="mt-1 text-xs hover:underline click font-bold text-primary" @click="$emit('chat', parentChat)" v-if="parentChat">
                  <i class="fa-solid fa-turn-up"></i> {{ parentChat.name }}
                </div>
                <div class="flex items-center gap-2">
                  <div class="dropdown">
                    <div tabindex="0" role="button" class="btn btn-xs btn-outline flex gap-1 items-center">
                      <i :class="chatModes[chat.mode].icon" class="fa-regular fa-comments"></i>
                    </div>
                    <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                      <li @click="setChatMode(mode)" v-for="info, mode in chatModes" :key="mode">
                        <a class="flex items-center">
                          <i :class="info.icon" class="fa-regular fa-comments"></i>
                          {{ info.name }}
                        </a>
                      </li>
                    </ul>
                  </div>
                  <div class="click" @click="editName = true">
                    {{ chat.name }}
                  </div>
                </div>
              </div>
            </div>
            <div class="grow"></div>
            <div class="flex gap-2 p-1 items-center -top-1">
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
                <ul tabindex="0" class="dropdown-content menu bg-base-300 rounded-box z-[1] w-60 p-2 shadow">
                  <li @click="newSubChat()">
                    <a>New sub task</a>
                  </li>
                  <li @click="createSubTasks()">
                    <a>Create sub tasks <i class="fa-solid fa-wand-magic-sparkles"></i></a>
                  </li>
                  <div class="divider" v-if="childrenChats.length"></div>
                  <li class="overflow-hidden text-ellipsis w-full" @click="$projects.setActiveChat(child)" v-for="child in childrenChats" :key="childrenChats.id">
                    <a>
                      <div>
                        <div class="text-xs">{{ moment(child.updated_at || child.created_at).format("DDMMM HH:mm") }}</div>
                        <div>
                          <ChatIconVue :chat="child" /> {{ child.name }}
                        </div>
                      </div>
                    </a>
                  </li>
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
          </div>
        </div>
        <div class="flex justify-between">
          <div class="flex gap-2 items-center">
            <div class="text-xs">{{ moment.utc(chat.updated_at).fromNow() }}</div>
            <div class="badge badge-sm badge-info flex gap-2" v-for="tag in chat.tags" :key="tag">
              {{ tag }}
              <button class="btn btn-xs btn-ghost" @click="removeTag(tag)">
                x
              </button>
            </div>
            <button class="btn btn-xs" @click="newTag = ''">
              + tag
            </button>
            <div class="badge badge-secondary badge-outline" v-for="profile in chat.profiles" :key="profile">
              {{ profile }}
            </div>
          </div>
          <div class="flex gap-2 justify-end">
            <select v-model="chat.project_id" class="select select-bordered select-xs w-full max-w-xs"
              @change="saveChat"
            >
              <option v-for="project in subProjects" :key="project.project_id"
                :value="project.project_id"
                :selected="project.project_id === chatProject.project_id"
              >
              {{ project.project_name }}
              </option>
            </select>
            {{  }}
          </div>
        </div>
        <div class="w-full overflow-auto" v-if="chat.file_list?.length">
          <div class="my-2 text-xs">
            <span>
              <i class="fa-solid fa-paperclip"></i>
            </span>
            <a v-for="file in chat.file_list" :key="file" :data-tip="file" class="group text-nowrap ml-2 hover:underline hover:bg-base-300 click text-accent" @click="$ui.openFile(file)">
              <span>{{ file.split('/').reverse()[0] }}</span>
              <span class="ml-2 click" @click.stop="onRemoveFile(file)">
                <i class="fa-regular fa-circle-xmark"></i>
              </span>
            </a>
          </div>
        </div>
        <Chat :chatId="chat.id"
          :showHidden="showHidden"
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
            <p>Are you sure you want to delete this chat?</p>
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
      </div>
      <add-file-dialog v-if="addNewFile" @open="onAddFile" @close="addNewFile = false" />
    </div>
  </div>
</template>

<script>
export default {
  props: ['chatMode', 'openChat'],
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
      chatModes: {
        "task": { name: "Analyst", profiles: ["analyst"], icon: "fa-solid fa-user-doctor" },
        "chat": { name: "Developer", profiles: ["software_developer"], icon: "fa-solid fa-code" },
      }
    }
  },
  computed: {
    subProjects () {
      return [
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
    chatUpdatedDate() {
      const updatedAt = this.chat.updated_at
      return moment(updatedAt).isAfter(moment().subtract(7, 'days'))
        ? moment(updatedAt).fromNow()
        : moment(updatedAt).format('YYYY-MM-DD')
    },
    chats() {
      return this.$projects.allChats
    },
    chat() {
      return this.$projects.activeChat
    },
    parentChat() {
      const parentId = this.$projects.activeChat.parent_id
      return parentId ? this.chats.find(c => c.id && c.id === parentId) : null
    },
    childrenChats() {
      return this.$storex.projects.allChats.filter(c => c.parent_id === this.chat.id)
        .sort((a, b) => (a.updated_at || a.created_at) > (b.updated_at || b.created_at) ? -1 : 1)
    },
    chatProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.chat.project_id) ||
              this.$project
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
      const parentChat = this.$projects.allChats.find(c => c.id === parent_id)
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
      const ix = this.chat.messages.findIndex(m => m === message)
      if (this.chat.mode == 'task' && message.role === "assistant") {
        this.chat.messages[ix - 1].hide = false
      }
      this.chat.messages = this.chat.messages.filter((m, i) => i !== ix)
      this.saveChat()
    },
    navigateToChats() {
      this.$emit('chats')
    },
    async newSubChat() {
      this.$emit('sub-task', this.chat)
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
    setChatMode(mode) {
      this.chat.mode = mode
      this.chat.profiles = this.chatModes[mode].profiles
      this.saveChat()
    },
    async createSubTasks() {
      await this.$storex.projects.createSubTasks(this.chat)
    }
  }
}
</script>