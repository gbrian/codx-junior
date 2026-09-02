<script setup>
import Chat from '@/components/chat/Chat.vue'
</script>

<template>
  <div class="flex flex-col h-full gap-2 bg-base-100 rounded-md p-3 border border-base-300">
    <!-- Info banner -->
    <div class="flex items-center justify-between gap-2 shrink-0">
      <div class="flex items-center gap-2 text-sm">
        <i class="fa-solid fa-circle-info text-info"></i>
        <span>Use task mode in chat to edit content. Last message becomes the profile content.</span>
      </div>
      <div class="flex items-center gap-2">
        <button 
          class="btn btn-xs btn-ghost gap-1" 
          @click="openChatInNewTab" 
          v-if="workingChat"
          :disabled="isSaving"
          title="Open chat in new tab">
          <i class="fa-solid fa-arrow-up-right-from-square"></i> Open
        </button>
        <button 
          class="btn btn-xs btn-ghost gap-1" 
          @click="createNewEditorChat" 
          v-if="!workingChat && !chatId"
          :disabled="isSaving">
          <i class="fa-solid fa-plus"></i> New Chat
        </button>
      </div>
    </div>

    <!-- Chat selector dropdown -->
    <div class="flex items-center gap-2 shrink-0 pb-2 border-b border-base-300" v-if="!chatId">
      <label class="text-xs font-semibold">Chat:</label>
      <select 
        v-model="selectedChatId" 
        @change="onChatChange" 
        class="select select-sm select-bordered flex-1 bg-base-200"
        :disabled="isSaving">
        <option value="">-- Create new --</option>
        <option v-for="chat in availableChats" :key="chat.id" :value="chat.id">
          {{ chat.name || 'Untitled Chat' }}
        </option>
      </select>
    </div>

    <!-- Chat component - full height -->
    <div class="flex-1 min-h-0 overflow-hidden" v-if="workingChat">
      <Chat
        :chat="workingChat"
        :showHidden="false"
        :childrenChats="[]"
        :filter="null"
        :files="chatFiles"
        @refresh-chat="reloadChat"
      />
    </div>

    <!-- Empty state -->
    <div class="flex items-center justify-center h-full text-base-content/50" v-else>
      <div class="flex flex-col items-center gap-2">
        <i class="fa-solid fa-message text-2xl opacity-50"></i>
        <span class="text-sm">Select or create a chat to edit content</span>
      </div>
    </div>

    <!-- Save indicator -->
    <div class="toast toast-bottom toast-end" v-if="isSaving">
      <div class="alert alert-info gap-2">
        <span class="loading loading-spinner"></span>
        <span>Saving chat_id...</span>
      </div>
    </div>
  </div>
</template>

<script>
import { v4 as uuidv4 } from 'uuid'

export default {
  props: {
    profile: Object,
    initialContent: String
  },
  emits: ['update:chatId', 'content-changed', 'save-chat-id'],
  data() {
    return {
      selectedChatId: null,
      workingChat: null,
      isSaving: false
    }
  },
  computed: {
    chatId() {
      return this.profile?.chat_id
    },
    availableChats() {
      return (this.$chats.allChats || [])
        .filter(c => c.mode === 'task' && c.project_id === this.$project.project_id)
        .map(c => ({ id: c.id, name: c.name }))
        .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    },
    chatFiles() {
      // ADDED: Construct markdown file reference from profile path
      if (!this.profile?.path) return null
      
      const markdownPath = this.profile.path.replace('.profile', '.md.profile')
      return [
        {
          path: markdownPath,
          name: `${this.profile.name}.md`
        }
      ]
    }
  },
  watch: {
    chatId(newVal) {
      if (newVal) {
        this.selectedChatId = newVal
        this.loadChat(newVal)
      }
    },
    'workingChat.messages': {
      handler() {
        this.updateProfileContentFromChat()
      },
      deep: true
    }
  },
  created() {
    if (this.chatId) {
      this.selectedChatId = this.chatId
      this.loadChat(this.chatId)
    }
  },
  methods: {
    async loadChat(chatId) {
      try {
        const chat = await this.$chats.loadChat({
          id: chatId,
          owner_project_id: this.$project.project_id
        })
        if (chat) {
          this.workingChat = chat
          this.$emit('update:chatId', chatId)
          this.updateProfileContentFromChat()
        }
      } catch (error) {
        console.error('Failed to load chat:', error)
      }
    },
    async onChatChange() {
      if (this.selectedChatId) {
        await this.loadChat(this.selectedChatId)
        this.$emit('update:chatId', this.selectedChatId)
        this.$emit('save-chat-id', this.selectedChatId)
      } else {
        this.workingChat = null
      }
    },
    async createNewEditorChat() {
      this.isSaving = true
      try {
        const newChat = await this.$chats.createNewChat({
          id: uuidv4(),
          name: `Profile Editor - ${this.profile.name}`,
          mode: 'task',
          board: 'Profiles',
          column: this.profile.name,
          project_id: this.$project.project_id,
          owner_project_id: this.$project.project_id,
          messages: [],
          profiles: []
        })
        if (newChat) {
          this.selectedChatId = newChat.id
          this.workingChat = newChat
          this.$emit('update:chatId', newChat.id)
          this.$emit('save-chat-id', newChat.id)
          await this.$chats.saveChat(newChat)
        }
      } finally {
        this.isSaving = false
      }
    },
    async reloadChat() {
      if (this.workingChat) {
        await this.$chats.reloadChat(this.workingChat)
        this.updateProfileContentFromChat()
      }
    },
    updateProfileContentFromChat() {
      if (this.workingChat?.messages && this.workingChat.messages.length > 0) {
        const lastMessage = this.workingChat.messages[this.workingChat.messages.length - 1]
        if (lastMessage?.content) {
          this.$emit('content-changed', lastMessage.content)
        }
      }
    },
    openChatInNewTab() {
      if (this.workingChat) {
        this.$storex.ui.openChat(this.workingChat)
      }
    }
  }
}
</script>