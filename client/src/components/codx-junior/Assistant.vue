<script setup>
import moment from 'moment'
import ChatEntry from '../ChatEntry.vue';
import UserSelector from '../chat/UserSelector.vue'

</script>
<template>
  <div class="absolute md:relative top-0 left-0 right-0 p-4 flex gap-2 justify-center w-full bg-base-300" @mouseenter="onOpen" @mouseleave="onClose">
    <div class="absolute transition-all w-full md:w-[600px] z-[100] right-0 -mt-3 p-2 " :class="!showAssistant && 'hidden'">
      
      <div class="input input-bordered w-full flex gap-2 items-center">
        <UserSelector
          :mini="true"
          :selectedUser="selectedUser"
          @user-changed="selectedUser = $event"
        />
        <input type="text" class="grow" v-model="query" placeholder="How can I help you?"
          @keydown.enter="sendMessage" />
      </div>
      <div class="p-2 flex flex-col gap-2 bg-base-300" v-if="chat">
        <div class="max-h-96 overflow-auto flex flex-col">
          <ChatEntry 
            class="border-t-2 border-base-100"
            :chat="chat"
            :message="message"
            v-for="message in chat.messages" :key="message.id"
          />
        </div>
        <div class="text-xs text-info" v-if="$session.lastEvent?.chat.id === chat.id">{{ $session.lastEvent?.text }}</div>
        <div class="flex justify-end gap-2">
          <button class="btn btn-xs btn-outline" @click="resetChat">
            <i class="fa-solid fa-plus"></i> New
          </button>
          <button class="btn btn-xs btn-outline" @click="closeAssitant">
            Close
          </button>
        </div>
      </div>
    </div>
    <div class="avatar">
      <div class="w-8 rounded-full">
        <img src="/only_icon.png" />
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: [],
  data() {
    return {
      isOpen: false,
      query: '',
      chatId: null,
      tout: null,
      keepOpen: false,
      selectedUser: null
    }
  },
  created() {
    this.selectedUser = this.$user
  },
  computed: {
    chat() {
      return this.$projects.chats[this.chatId]
    },
    showAssistant() {
      return this.isOpen || this.keepOpen
    },
    lastAiMessage() {
      if (!this.chat) {
        return null
      }
      return [...this.$projects.chats[this.chat.id]?.messages || []].reverse().find(m => m.role === 'assistant')
    }
  },
  watch: {},
  methods: {
    async newChat(query) {
      const column = moment().format("YYYY-MM-DD")
      const name = `${query.replace(/[^a-zA-Z0-9 ]/g, '-').slice(0, 20)} - ${moment().format("hhmmss")}` 
      const chat = await this.$projects.createNewChat({
        board: 'codx-junior',
        column,
        description: query,
        users: [this.$user.username],
        name
      })
      this.chatId = chat.id
    },
    async sendMessage() {
      if (!this.chat) {
        await this.newChat(this.query)
      }
      const tabContext = this.getCurrentTabContext()
      if (tabContext && !this.chat.messages.length) {
        const msg = {
          role: 'user',
          content: tabContext,
          user: this.$user.username
        }
        this.chat.messages.push(msg)  
      }
      const profiles = this.selectedUser.name ? [this.selectedUser.name] : []
      let content = this.query
      this.query = ""
      if (!profiles.length) {
        content += ` @${this.$project.project_name}`
      }
      const msg = {
        role: 'user',
        content,
        user: this.$user.username
      }
      this.chat.messages.push(msg)
      this.keepOpen = true
      await this.$storex.projects.chatWihProject(this.chat)
      this.$storex.projects.saveChat(this.chat)
    },
    onOpen() {
      clearTimeout(this.tout)
      this.tout = null
      this.isOpen = true 
    },
    onClose() {
      if (this.isOpen) {
        this.tout = setTimeout(() => {
          this.isOpen = false
          this.tout = null
        }, 800)
      }
    },
    closeAssitant() {
      this.keepOpen = false
      this.isOpen = false
      clearTimeout(this.tout)
    },
    resetChat() {
      this.chat = null
    },
    getCurrentTabContext() {
      if (this.$ui.activeTab === 'prview') {
        if (this.$projects.project_branches) {
          return ["User is reviewing project file changes:",
            "```diff",
            this.$projects.project_branches.git_diff,
            "```"
          ].join("\n")
        }
      }
    }
  }
}
</script>