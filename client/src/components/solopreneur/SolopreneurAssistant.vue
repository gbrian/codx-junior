<template>
  <section class="flex flex-col min-h-0 bg-base-200/40" aria-label="AI co-founder">
    <!-- Header -->
    <header class="shrink-0 flex items-center gap-2 px-3 py-2 border-b border-base-content/10">
      <div class="w-7 h-7 rounded-lg grid place-items-center bg-primary/15 text-primary shrink-0">
        <i class="fa-solid fa-wand-magic-sparkles text-xs" aria-hidden="true"></i>
      </div>
      <div class="min-w-0 mr-auto">
        <h2 class="text-sm font-semibold leading-tight truncate">AI co-founder</h2>
        <p class="text-[11px] text-base-content/50 truncate">{{ venture.name }}</p>
      </div>

      <!-- Previous assistant conversations (reuses $projects.lastAssistantChats) -->
      <div v-if="previousChats.length" class="dropdown dropdown-end">
        <button
          type="button"
          tabindex="0"
          class="btn btn-ghost btn-xs btn-square"
          title="Previous conversations"
          aria-label="Previous conversations"
        >
          <i class="fa-solid fa-clock-rotate-left" aria-hidden="true"></i>
        </button>
        <ul tabindex="0" class="dropdown-content z-50 menu p-2 shadow bg-base-100 rounded-box w-64">
          <li v-for="previous in previousChats" :key="previous.id">
            <a class="truncate" @click="openPrevious(previous)">{{ previous.name }}</a>
          </li>
        </ul>
      </div>

      <button
        type="button"
        class="btn btn-ghost btn-xs btn-square"
        title="New conversation"
        aria-label="New conversation"
        @click="reset"
      >
        <i class="fa-solid fa-plus" aria-hidden="true"></i>
      </button>
    </header>

    <!-- Messages -->
    <div ref="messages" class="flex-1 min-h-0 overflow-auto px-3 py-3 flex flex-col gap-2" role="log" aria-live="polite">
      <div v-if="!messages.length" class="flex flex-col gap-2">
        <p class="text-xs text-base-content/50">
          Ask your co-founder anything about {{ venture.name || 'your venture' }}.
        </p>
        <button
          v-for="suggestion in suggestions"
          :key="suggestion"
          type="button"
          class="text-left text-xs rounded-lg border border-base-content/10 bg-base-100 px-3 py-2 hover:border-primary/40 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50"
          @click="sendPreset(suggestion)"
        >
          <i class="fa-solid fa-arrow-right text-[10px] text-primary mr-1" aria-hidden="true"></i>
          {{ suggestion }}
        </button>
      </div>

      <div
        v-for="(message, index) in messages"
        :key="message.doc_id || message.id || index"
        class="flex"
        :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div
          class="max-w-[85%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap break-words border"
          :class="message.role === 'user'
            ? 'bg-primary/15 border-primary/30'
            : 'bg-base-100 border-base-content/10 text-base-content/80'"
        >{{ message.content }}</div>
      </div>

      <div v-if="busy" class="flex items-center gap-2 text-[11px] text-base-content/50">
        <span class="loading loading-spinner loading-xs"></span>
        <span>{{ progressText || 'Thinking…' }}</span>
      </div>
    </div>

    <!-- Input -->
    <div class="shrink-0 p-2 border-t border-base-content/10">
      <div class="relative">
        <input
          v-model="query"
          type="text"
          class="input input-sm input-bordered w-full pr-10"
          placeholder="Ask anything…"
          aria-label="Ask your AI co-founder"
          :disabled="busy"
          @keydown.enter="sendMessage"
        />
        <button
          type="button"
          class="absolute right-1 top-1/2 -translate-y-1/2 btn btn-ghost btn-xs btn-square"
          :disabled="busy || !query.trim()"
          aria-label="Send message"
          @click="sendMessage"
        >
          <i class="fa-solid fa-paper-plane text-xs" aria-hidden="true"></i>
        </button>
      </div>
    </div>
  </section>
</template>

<script>
import moment from 'moment'

// Board used by every assistant conversation. It is the same bucket the
// `$projects.lastAssistantChats` getter reads from (board === 'codx-junior'),
// so the "previous conversations" menu works without new storage.
const ASSISTANT_BOARD = 'codx-junior'

export default {
  name: 'SolopreneurAssistant',
  props: {
    // { id, name, tagline, icon }
    venture: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      query: '',
      chatId: null,
      sending: false,
      suggestions: [
        'What should I focus on today?',
        'Summarize what changed this week',
        'Draft a plan for the next milestone'
      ]
    }
  },
  computed: {
    chat() {
      return this.chatId ? (this.$chats.chats[this.chatId] || null) : null
    },
    // Only the tail of the thread is shown: this is a side panel, not the chat view.
    messages() {
      return (this.chat?.messages || []).slice(-20)
    },
    busy() {
      if (!this.chatId) return this.sending
      return this.sending || this.$chats.isChatUpdating(this.chatId)
    },
    previousChats() {
      return (this.$projects.lastAssistantChats || [])
        .filter(chat => chat.id !== this.chatId)
        .slice(0, 5)
    },
    progressText() {
      const event = this.$session.lastEvent
      return event?.chat?.id === this.chatId ? (event.text || null) : null
    }
  },
  watch: {
    messages() {
      this.scrollToBottom()
    }
  },
  methods: {
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.messages
        if (container) container.scrollTop = container.scrollHeight
      })
    },

    // Create the conversation on the existing chats pipeline (no new endpoint).
    async newChat(query) {
      const name = `${query.replace(/[^a-zA-Z0-9 ]/g, '-').slice(0, 20)} - ${moment().format('HHmmss')}`
      const chat = await this.$chats.createNewChat({
        board: ASSISTANT_BOARD,
        column: moment().format('YYYY-MM-DD'),
        description: query,
        users: this.$user?.username ? [this.$user.username] : [],
        mode: 'task',
        name
      })
      this.chatId = chat.id
      return this.$chats.chats[chat.id] || chat
    },

    async sendMessage() {
      const content = (this.query || '').trim()
      if (!content || this.busy) return
      await this.ask(content)
    },

    async sendPreset(suggestion) {
      if (this.busy) return
      await this.ask(suggestion)
    },

    // The message is persisted through the chats store and the run is triggered
    // by `chatWihProject`. Server updates arrive over the socket, where
    // `chats.onChatEvent` reloads the chat in place — the panel stays in sync.
    async ask(content) {
      if (!this.$project?.$api) {
        this.$ui.addNotification({ text: 'Select a project first', type: 'warning' })
        return
      }
      this.sending = true
      try {
        const chat = this.chat || await this.newChat(content)
        this.query = ''
        await this.$chats.addMessage({
          chat,
          message: { role: 'user', content, user: this.$user?.username }
        })
        await this.$storex.projects.chatWihProject(chat)
        this.scrollToBottom()
      } catch (e) {
        console.error('[Solopreneur] assistant request failed', e)
        this.$ui.addNotification({ text: 'The assistant could not be reached', type: 'error' })
      } finally {
        this.sending = false
      }
    },

    async openPrevious(chat) {
      try {
        await this.$chats.loadChat(chat)
        this.chatId = chat.id
      } catch (e) {
        console.error('[Solopreneur] could not load the conversation', e)
      }
    },

    reset() {
      this.chatId = null
      this.query = ''
    }
  }
}
</script>