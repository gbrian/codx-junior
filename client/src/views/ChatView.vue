<script setup>
import { API } from '../api/api'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import moment from 'moment'
import PRView from '../views/PRView.vue'
import ChatIconVue from '@/components/chat/ChatIcon.vue'
</script>
<template>
  <div class="flex flex-col h-full pb-2" v-if="chat">
    <div class="hidden gap-2 items-center">
      <div class="dropdown">
        <div tabindex="0" role="button" class="btn btn-xs m-1"><i class="fa-solid fa-code-branch"></i></div>
        <ul tabindex="0" class="dropdown-content menu bg-base-300 rounded-box z-[1] w-68 p-2 shadow">
          <li class="mt-2">
            <a class="input input-bordered input-sm flex gap-2">
              <input class="bg-transparent active:outline-none" placeholder="New branch...">
              <i class="fa-solid fa-plus"></i>
            </a>
          </li>
          <li><a>{{ API.lastSettings.current_git_branch }}</a></li>
        </ul>
      </div>
      {{ API.lastSettings.current_git_branch }}
      <div class="grow"></div>
      <button class="btn btn-sm" @click="showPRView = false" v-if="showPRView">
        Task
      </button>
      <button class="btn btn-sm" @click="showPRView = true" v-else>
        PR
      </button>
    </div>
    <PRView v-if="showPRView"></PRView>
    <div class="grow flex gap-2 h-full justify-between" v-if="showChat">
      <div class="grow flex flex-col gap-2 w-full">
        <div class="text-xl flex gap-2 items-center" v-if="!chatMode">
          <div class="flex items-start gap-2 w-full">
            <div class="flex gap-2 items-start">
              <button class="btn btn-xs btn-circle mt-1 text-white"
                @click="navigateToChats">
                <i class="fa-solid fa-arrow-left"></i>
              </button>
              <input v-if="editName"
                type="text" class="input input-xs input-bordered"
                @keydown.enter.stop="saveChat"
                @keydown.esc="editName = false"
                v-model="chat.name" />
              <div class="font-bold flex flex-col" v-else> 
                <div class="click" @click="editName = true">
                  <ChatIconVue :chat="chat" />
                  {{ chat.name }}
                </div>
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
                  <modal v-if="newTag !== null">
                    <div class="flex flex-col gap-2">
                      <div class="text-xl">New tag</div>
                      <select class="select select-sm select-bordered"
                        @change="newTag = $event.target.value"
                      >
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
              </div>
            </div>
            <div class="grow"></div>
            <div class="group relative bg-base-100">
              <div class="bg-base-300 lg:bg-transparent p-2 rounded hidden lg:flex group-hover:flex gap-2 p-1 items-end absolute right-8 -top-1">
                <div class="dropdown -mt-1">
                  <div tabindex="0" role="button" class="select select-xs select-bordered">{{ chat.mode }}</div>
                  <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                    <li @click="chat.mode = 'chat'">
                      <a class="flex items-center">
                        <i class="fa-regular fa-comments"></i>
                        Chat
                      </a>
                    </li>
                    <li @click="chat.mode = 'task'">
                      <a class="flex items-center">
                        <i class="fa-regular fa-file-code"></i>
                        Task definition
                      </a>
                    </li>
                    <li @click="chat.mode = 'browser'">
                      <a class="flex items-center">
                        <i class="fa-brands fa-chrome"></i>
                        Browse the web
                      </a>
                    </li>
                  </ul>
                </div>
                <button class="btn btn-xs hover:btn-info hover:text-white" @click="saveChat">
                  <i class="fa-solid fa-floppy-disk"></i>
                </button>
                <button class="btn btn-xs btn-error hover:text-white" @click="deleteChat" v-if="confirmDelete">
                  Comfirm? <span class="hover:underline">YES</span> / <span class="hover:underline" @click.stop="confirmDelete = false">NO</span>
                  <i class="fa-solid fa-trash"></i>
                </button>
                <button class="btn btn-xs hover:btn-error hover:text-white" @click="deleteChat" v-else>
                  <i class="fa-solid fa-trash"></i>
                </button>
                
                <button class="btn btn-xs" v-if="hiddenCount" @click="showHidden = !showHidden">
                  <div class="flex items-center gap-2" v-if="!showHidden">
                    ({{ hiddenCount }})
                    <i class="fa-solid fa-eye-slash"></i>
                  </div>
                  <span class="text-warning" v-else>
                    <i class="fa-solid fa-eye"></i>
                  </span>
                </button>
                <div class="dropdown dropdown-end dropdown-bottom -mt-1">
                  <button tabindex="0" class="btn btn-xs">
                    <i class="fa-solid fa-plus"></i>
                  </button>
                  <ul tabindex="0" class="dropdown-content menu bg-base-300 rounded-box z-[1] w-60 p-2 shadow">
                    <li @click="newSubChat()">
                      <a>New sub task</a>
                    </li>
                  </ul>
                </div>
              </div>
              <div class="btn btn-sm btn-ghost ml-6" @click.stop="">
                <i class="fa-solid fa-ellipsis-vertical"></i>
              </div>
            </div>
          </div>
        </div>
        <Chat :chat="chat"
          :showHidden="showHidden"
          @refresh-chat="loadChat(chat)"
          @add-file="onAddFile"
          @remove-file="onRemoveFile"
          @delete-message="onRemoveMessage"
          @save="saveChat"
        v-if="chat"/>
        <div class="modal modal-open" role="dialog" v-if="showFile || addFile !== null">
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
        </div>
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
      profiles: null,
      showFile: null,
      addFile: null,
      showChatsTree: false,
      editName: false,
      showSettings: false,
      addNewFile: null,
      showHidden: false,
      showPRView: false,
      confirmDelete: false,
      newTag: null
    }
  },
  async created () {
    this.loadProfiles()
  },
  computed: {
    hiddenCount () {
      return this.chat.messages?.filter(m => m.hide).length
    },
    messages () {
      return this.chat.messages.filter(m => !m.hide || this.showHidden)
    },
    showChat () {
      return !this.showPRView
    },
    chatUpdatedDate () {
      const updatedAt = this.chat.updated_at;
      return moment(updatedAt).isAfter(moment().subtract(7, 'days'))
        ? moment(updatedAt).fromNow()
        : moment(updatedAt).format('YYYY-MM-DD');
    },
    chats () {
      return this.$projects.chats
    },
    chat () {
      return this.$projects.activeChat
    }
  },
  watch: {
  },
  methods: {
    async loadProfiles () {
      try {
        const { data } = await API.profiles.list()
        this.profiles = data
      } catch {}
    },
    async saveChat () {
      this.editName = false
      await this.$projects.saveChat(this.chat)
    },
    async deleteChat () {
      if (this.confirmDelete) {
        await this.$projects.deleteChat(this.chat)
        this.navigateToChats()
      } else {
        this.confirmDelete = true
      }
    },
    async loadChat (chat) {
      await this.$projects.setActiveChat(chat)
      this.showChatsTree = false
    },
    async removeFileFromContext () {
      this.chat.profiles = this.chat.profiles?.filter(f => f !== this.showFile) 
      this.onRemoveFile(this.showFile)
      await this.loadChat(this.chat)
      this.showFile = null
    },
    async addFileToContext () {
      this.onAddFile(this.addFile)
      await this.saveChat()
      await this.loadChat(this.chat)
      this.showFile = null
      this.addFile = null
    },
    async onAddFile (file) {
      if (this.chat.file_list?.includes(file)) {
        return
      }
      this.chat.file_list = [...(this.chat.file_list||[]), file]
      this.addNewFile = null
      await this.saveChat()
    },
    async onRemoveFile (file) {
      this.chat.file_list = (this.chat.file_list||[]).filter(f => f !== file)
      this.addNewFile = null
      await this.saveChat()
    },
    async addProfile (profile) {
      if (this.chat.profiles?.find(f => f.endsWith(profile))) {
        return
      }
      this.chat.profiles = [...this.chat.profiles||[], profile]
      await this.saveChat()
      await this.loadChat(this.chat)
    },
    onRemoveMessage (message) {
      const ix = this.chat.messages.findIndex(m => m === message)
      if (this.chat.mode == 'task' && message.role === "assistant") {
        this.chat.messages[ix-1].hide = false
      }
      this.chat.messages = this.chat.messages.filter((m, i) => i !== ix)
      this.saveChat()
    },
    navigateToChats () {
      this.$emit('chats')
    },
    async newSubChat () {
      const parent = this.chat
      await this.newChat()
      this.chat.parent_id = parent.parent_id
      this.chat.column = parent.column
      this.chat.column_ix = parent.column_ix
    },
    addNewTag () {
      this.chat.tags = [...new Set([...this.chat.tags||[], this.newTag])]
      this.newTag = null
      this.saveChat()
    },
    removeTag (tag) {
      this.chat.tags = this.chat.tags.filter(t => t !== tag)
      this.saveChat()
    }
  }
}
</script>