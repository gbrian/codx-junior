<script setup>
import { API } from '../api/api'
import AddFileDialog from '../components/chat/AddFileDialog.vue'
import Chat from '@/components/chat/Chat.vue'
import moment from 'moment'
import PRView from '../views/PRView.vue'
</script>
<template>
  <div class="flex flex-col gap-1 h-full" v-if="chat">
    <div class="flex gap-2 items-center">
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
    <div class="grow flex gap-2 h-full justify-between" v-else>
      <div class="flex flex-col  bg-base-300 p-2 overflow-auto" v-if="showChatsTree">
        <ul tabindex="0" class=" p-2 w-52">
          <li class="p-2 click hover:underline flex flex-col"
            v-for="openChat in chats" :key="openChat"
            @click="loadChat(openChat.name)" >
            <div class="text-xs">{{ moment.utc(openChat.updated_at).fromNow() }}</div>
            <a>{{ openChat.name }}</a>
          </li>
        </ul>
      <div class="grow"></div>
        <div class="px-2">
        </div>
      </div>
      <div class="grow flex flex-col gap-2">
        <div class="text-xl flex gap-2 items-center" v-if="!chatMode">
          <div class="flex flex-col sm:flex-row gap-2 w-full">
            <div class="flex gap-2">
              <button :class="['btn btn-xs hover:btn-info hover:text-white', showChatsTree && 'btn-info text-white']" @click="showChatsTree = !showChatsTree">
                <i class="fa-solid fa-folder-tree"></i>
              </button>
              <input v-if="editName"
                type="text" class="input input-xs input-bordered"
                @keydown.enter.stop="saveChat"
                @keydown.esc="editName = false"
                v-model="chat.name" />
              <div class="font-bold flex flex-col" v-else> 
                <div class="click" @click="editName = true">{{ chat.name }}</div>
                <div class="flex gap-2">
                  <div class="text-xs">{{ moment.utc(chat.updated_at).fromNow() }}</div>
                  <div class="badge badge-sm">
                    {{  chat.id }}
                  </div>
                </div>
              </div>
            </div>
            <div class="grow"></div>
            <div class="flex gap-2">
              <select v-model="chat.mode" class="select select-xs select-bordered">
                <option selected value="chat">chat</option>
                <option selected value="task">task</option>
              </select>
              <button class="btn btn-xs hover:btn-info hover:text-white" @click="saveChat">
                <i class="fa-solid fa-floppy-disk"></i>
              </button>
              <button class="btn btn-xs hover:btn-error hover:text-white" @click="deleteChat">
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
              <button class="btn btn-primary btn-xs" @click="newChat">
                <i class="fa-solid fa-plus"></i>
              </button>
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
          @refresh-chat="loadChat(chat.name)"
          @add-file="onAddFile"
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
  props: ['chatMode'],
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
      showPRView: false
    }
  },
  async created () {
    this.chats = await API.chats.list()
    if (this.chats.length) {
      this.chat = await API.chats.loadChat(this.chats[0].name)
    } else {
      this.chat = await API.chats.newChat()
      this.chats.push(this.chat.name)
    }
    this.loadProfiles()
  },
  computed: {
    hiddenCount () {
      return this.chat.messages?.filter(m => m.hide).length
    },
    messages () {
      return this.chat.messages.filter(m => !m.hide || this.showHidden)
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
    newChat () {
      this.chat = API.chatManager.newChat()
      this.chat.mode = this.chat.mode || 'task'
    },
    async saveChat () {
      this.editName = false
      API.chats.save(this.chat)
      this.chats = await API.chats.list()
    },
    async deleteChat () {
      API.chatManager.deleteChat(this.chat)
      this.chats = await API.chats.list()
      this.newChat()
    },
    async loadChat (newChat) {
      this.chat = await API.chats.loadChat(newChat)
      this.showChatsTree = false
    },
    async removeFileFromContext () {
      this.chat.profiles = this.chat.profiles?.filter(f => f !== this.showFile) 
      this.chat.file_list = this.chat.file_list?.filter(f => f !== this.showFile)
      await this.saveChat()
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
    onAddFile (file) {
      this.chat.file_list = [...(this.chat.file_list||[]), file]
      this.addNewFile = null
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
    }
  }
}
</script>