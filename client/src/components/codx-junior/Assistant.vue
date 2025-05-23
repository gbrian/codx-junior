<script setup>
import moment from 'moment'
import ChatEntry from '../ChatEntry.vue';
</script>
<template>
  <div class="flex gap-2 justify-center w-full" @mouseenter="onOpen" @mouseleave="onClose">
    <div class="absolute transition-all w-[600px] z-[100] right-0 -mt-3 p-2 " :class="!showAssistant && 'hidden'">
      <input type="text" v-model="query" placeholder="How can I help you?"
        class="input input-bordered w-full" @keydown.enter="sendMessage" />
      <div class="p-2 flex flex-col gap-2 bg-base-300" v-if="chat">
        <ChatEntry class="max-h-96 overflow-auto" :chat="chat" :message="lastAiMessage" v-if="lastAiMessage"  />
        <div class="flex justify-end gap-2">
          <button class="btn btn-sm btn-outline" @click="resetChat">
            <i class="fa-solid fa-plus"></i> New
          </button>
          <button class="btn btn-sm btn-outline" @click="closeAssitant">
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
      chat: null,
      tout: null,
      keepOpen: false
    }
  },
  created() {
  },
  computed: {
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
      this.chat = await this.$projects.createNewChat({
        board: 'codx-junior',
        column,
        profiles: ['project'],
        users: [this.$user.username],
        name
      })
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
      const msg = {
        role: 'user',
        content: this.query,
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