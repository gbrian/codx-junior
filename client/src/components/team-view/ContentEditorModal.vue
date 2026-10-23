<script setup>
import ChatView from '@/views/ChatView.vue'
import { avatarUrl } from './config'
</script>

<template>
  <div class="fixed inset-0 z-[60] flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="$emit('close')"></div>

    <div
      class="relative w-full max-w-3xl h-[82vh] bg-base-100 border border-base-content/10 rounded-xl shadow-2xl flex flex-col overflow-hidden"
      role="dialog"
      aria-modal="true"
      :aria-label="`Edit ${profile.name} with chat`"
    >
      <!-- Header -->
      <header class="flex items-center gap-3 px-4 py-3 border-b border-base-content/10 shrink-0">
        <div class="avatar">
          <div class="w-8 rounded-full">
            <img :src="avatar" :alt="profile.name" />
          </div>
        </div>
        <div class="min-w-0">
          <div class="font-semibold text-sm truncate">Edit “{{ profile.name }}” with chat</div>
          <div class="text-[11px] text-base-content/50">Ask the assistant to rewrite this persona, then close this dialog.</div>
        </div>
        <button
          type="button"
          class="btn btn-ghost btn-sm btn-square ml-auto"
          aria-label="Close editor"
          @click="$emit('close')"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </header>

      <!-- Chat body -->
      <div class="flex-1 min-h-0 overflow-hidden">
        <ChatView
          v-if="editorChat"
          class="h-full"
          :chat="editorChat"
          @chat="onChatUpdated"
        />
        <div v-else class="flex flex-col items-center justify-center gap-2 h-full text-base-content/50">
          <span class="loading loading-spinner loading-sm"></span>
          <span class="text-sm">Preparing editor chat…</span>
        </div>
      </div>

      <!-- Footer -->
      <footer class="flex items-center gap-2 px-4 py-3 border-t border-base-content/10 shrink-0">
        <span class="text-xs text-base-content/40 mr-auto">The last assistant message becomes the persona content.</span>
        <button type="button" class="btn btn-sm btn-primary" @click="$emit('close')">
          <i class="fa-solid fa-check"></i>
          Done
        </button>
      </footer>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ContentEditorModal',
  props: {
    /** The persona draft being edited (carries `chat_id` + `content`). */
    profile: { type: Object, required: true }
  },
  emits: ['update', 'close'],
  data() {
    return {
      editorChat: null
    }
  },
  computed: {
    avatar() {
      return avatarUrl(this.profile)
    }
  },
  created() {
    window.addEventListener('keydown', this.onKeydown)
    this.initializeEditorChat()
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    onKeydown(event) {
      if (event.key === 'Escape') this.$emit('close')
    },

    async initializeEditorChat() {
      if (this.profile?.chat_id) {
        await this.loadEditorChat(this.profile.chat_id)
      } else {
        await this.createEditorChat()
      }
    },

    async loadEditorChat(chatId) {
      try {
        const chat = await this.$chats.loadChat({
          id: chatId,
          owner_project_id: this.$project.project_id
        })
        if (chat) this.editorChat = chat
      } catch (error) {
        console.error('[ContentEditorModal] Failed to load profile chat:', error)
        await this.createEditorChat()
      }
    },

    async createEditorChat() {
      try {
        const { v4: uuidv4 } = await import('uuid')
        const newChat = await this.$chats.createNewChat({
          id: uuidv4(),
          name: `Profile Editor - ${this.profile.name}`,
          mode: 'task',
          board: 'Profiles',
          column: this.profile.name,
          project_id: this.$project.project_id,
          owner_project_id: this.$project.project_id,
          messages: this.profile.content ? [{ role: 'assistant', content: this.profile.content }] : [],
          profiles: []
        })
        if (newChat) {
          this.editorChat = newChat
          await this.$chats.saveChat(newChat)
          // Keep the draft in sync with the freshly created editor chat.
          this.$emit('update', { content: this.profile.content || '', chatId: newChat.id })
        }
      } catch (error) {
        console.error('[ContentEditorModal] Failed to create profile chat:', error)
        this.$ui.addNotification({ text: 'Failed to open the chat editor', type: 'error' })
      }
    },

    async onChatUpdated(chat) {
      if (!chat) return
      this.editorChat = chat
      let content = this.profile.content || ''
      if (chat.messages?.length) {
        const last = chat.messages[chat.messages.length - 1]
        if (last?.content) content = last.content
      }
      this.$emit('update', { content, chatId: chat.id })
    }
  }
}
</script>