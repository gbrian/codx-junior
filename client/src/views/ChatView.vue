<script setup>
import { API } from '../api/api'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import moment from 'moment'
import PRView from '../views/PRView.vue'
</script>
<template>
  <div class="flex flex-col h-full" v-if="chat">
    <div class="flex gap-2 items-center hidden">
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
      <div class="flex flex-col  bg-base-300 p-2 overflow-auto" v-if="showChatsTree">
        <ul tabindex="0" class=" p-2 w-52">
          <li class="p-2 click hover:underline flex flex-col"
            v-for="openChat in chats" :key="openChat"
            @click="loadChat(openChat.name)" >
            <div class="text-xs">{{ chatUpdatedDate }}</div>
            <a>{{ openChat.name }}</a>
          </li>
        </ul>
      <div class="grow"></div>
        <div class="px-2">
        </div>
      </div>
      <div class="grow flex flex-col gap-2 w-full">
        <div class="text-xl flex gap-2 items-center" v-if="!chatMode">
          <div class="flex flex-col sm:flex-row gap-2 w-full">
            <div class="flex gap-2">
              <button :class="['btn btn-xs hover:btn-info hover:text-white', showChatsTree && 'btn-info text-white']"
                @click="onShowChats">
                <i class="fa-solid fa-folder-tree"></i>
              </button>
              <input v-if="editName"
                type="text" class="input input-xs input-bordered"
                @keydown.enter.stop="saveChat"
                @keydown.esc="editName = false"
                v-model="chat.name" />
              <div class="font-bold flex flex-col" v-else> 
                <div class="click" @click="editName = true">{{ chat.name }}</div>
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
            <div class="flex gap-2 items-center">
              <button :class="['btn btn-xs flex items-center', livePreview && 'btn-info']"
                @click="livePreview = !livePreview"
              >
                <i class="fa-brands fa-chromecast"></i>
                Live session
              </button>
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
          </div>
        </div>
        <div v-if="false">
          <span class="cursor-pointer mr-2 hover:underline group text-primary"
            v-for="file in chat.profiles" :key="file" :title="file"
            @click="showFile = file"
          >
            <i class="fa-solid fa-user-doctor"></i>
            {{ file.split("/").reverse()[0] }}
          </span>
          <span class="cursor-pointer mr-2 hover:underline group text-secondary"
            v-for="file in chat.file_list" :key="file" :title="file"
            @click="showFile = file"
          >
            <i class="fa-solid fa-file"></i>
            {{ file.split("/").reverse()[0] }}
          </span>
          <button class="btn btn-circle btn-xs" @click="addNewFile = true">
            <i class="fa-solid fa-plus"></i>
          </button>
        </div>
        <Chat :chat="chat"
          :showHidden="showHidden"
          :livePreview="livePreview"
          @refresh-chat="loadChat(chat.name)"
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
      chat: null,
      chats: [],
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
      livePreview: false,
      newTag: null
    }
  },
  async created () {
    if (this.openChat) {
      this.chat = this.openChat
    } else {
      this.chats = await API.chats.list()
      if (this.chats.length) {
        this.chat = await API.chats.loadChat(this.chats[0].name)
      } else {
        this.chat = await API.chats.newChat()
        this.chats.push(this.chat.name)
      }
    }
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
    }
  },
  watch: {
    async showChatsTree(newVal) {
      if (newVal) {
        this.chats = await API.chats.list()
      }
    }
  },
  methods: {
    async loadProfiles () {
      try {
        const { data } = await API.profiles.list()
        this.profiles = data
      } catch {}
    },
    async newChat () {
      this.chat = await API.chatManager.newChat()
      this.chat.mode = this.chat.mode || 'task'
    },
    async saveChat () {
      this.editName = false
      API.chats.save(this.chat)
      this.chats = await API.chats.list()
    },
    async deleteChat () {
      if (this.confirmDelete) {
        await API.chats.delete(this.chat.name)
        this.onShowChats()
      } else {
        this.confirmDelete = true
      }
    },
    async loadChat (newChat) {
      this.chat = await API.chats.loadChat(newChat)
      this.showChatsTree = false
    },
    async removeFileFromContext () {
      this.chat.profiles = this.chat.profiles?.filter(f => f !== this.showFile) 
      this.onRemoveFile(this.showFile)
      await this.loadChat(this.chat.name)
      this.showFile = null
    },
    async addFileToContext () {
      this.onAddFile(this.addFile)
      await this.saveChat()
      await this.loadChat(this.chat.name)
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
      await this.loadChat(this.chat.name)
    },
    onRemoveMessage (ix) {
      this.chat.messages = this.chat.messages.filter((m, i) => i !== ix)
      this.saveChat()
    },
    onShowChats () {
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
    removeNewTag (tag) {
      this.chat.tags = this.chat.tags.filter(t => t !== tag)
      this.saveChat()
    }
  }
}
</script>