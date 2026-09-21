<script setup>
import QuickChatSidebar from '@/components/quick-chat/QuickChatSidebar.vue'
import ChatMessageList from '@/components/chat/ChatMessageList.vue'
import ChatInputBox from '@/components/chat/ChatInputBox.vue'
import ChatIntelliSense from '@/components/chat/ChatIntelliSense.vue'
import ChatAttachmentPreview from '@/components/chat/ChatAttachmentPreview.vue'
import ChatAttachment from '@/api/model/ChatAttachment.js'
</script>

<template>
  <div class="flex h-full w-full bg-[#111111] overflow-hidden" data-theme="dark">

    <!-- ── Sidebar ── -->
    <QuickChatSidebar
      :user-name="$user?.username || 'User'"
      @new-chat="startNewChat"
      @project-selected="onProjectSelected"
    />

    <!-- ── Main area ── -->
    <main class="flex-1 flex flex-col min-w-0 h-full relative">

      <!-- ══ HOME / EMPTY STATE ══ -->
      <transition name="fade">
        <div
          v-if="!activeChat"
          class="absolute inset-0 flex flex-col items-center justify-center gap-8 z-10"
        >
          <!-- Radial gradient glow -->
          <div
            class="absolute inset-0 pointer-events-none"
            style="background: radial-gradient(ellipse 70% 50% at 50% 60%, rgba(99,102,241,0.13) 0%, transparent 70%)"
          ></div>

          <!-- Greeting -->
          <h1 class="text-4xl font-semibold text-white tracking-tight relative z-10 text-center px-4">
            What's next,
            <span class="text-primary">{{ firstName }}</span>?
          </h1>

          <!-- Floating input bar using ChatInputBox -->
          <div class="relative z-10 w-full max-w-2xl px-4">
            <!-- IntelliSense popup for home input -->
            <ChatIntelliSense
              v-if="intelliSenseSuggestions.length"
              ref="homeIntelliSense"
              :suggestions="intelliSenseSuggestions"
              :active-index="intelliSenseIndex"
              :query="intelliSenseQuery"
              :search-controller="searchController"
              :progress="intelliSenseProgress"
              @select="onIntelliSenseSelect"
              @hover="intelliSenseIndex = $event"
              @accept-multi="onIntelliSenseAcceptMulti"
              @cancel="cancelIntelliSense"
            />

            <ChatInputBox
              ref="homeInputBox"
              :waiting="waiting"
              :cursor-word="cursorWord"
              :ai-models="aiModels"
              :profiles="profiles"
              :selected-profiles="selectedProfiles"
              @send="onHomeSubmit"
              @add-message="onHomeSubmit"
              @keydown="onHomeKeyDown"
              @paste="onPaste"
              @profiles-selected="selectedProfiles = $event"
            />

            <!-- Suggestion chips -->
            <div class="flex flex-wrap gap-2 mt-3 justify-center">
              <button
                v-for="chip in suggestionChips"
                :key="chip"
                class="px-3 py-1.5 rounded-full bg-white/5 border border-white/8 text-white/50 text-xs hover:bg-white/10 hover:text-white/80 transition-colors"
                @click="setHomeChip(chip)"
              >
                {{ chip }}
              </button>
            </div>
          </div>
        </div>
      </transition>

      <!-- ══ ACTIVE CHAT VIEW ══ -->
      <transition name="fade">
        <div v-if="activeChat" class="absolute inset-0 flex flex-col">

          <!-- Chat header -->
          <div class="shrink-0 flex items-center gap-3 px-6 py-3 border-b border-white/5 bg-[#111111]/80 backdrop-blur-sm">
            <div class="flex-1 min-w-0">
              <h2 class="text-sm font-medium text-white/80 truncate">{{ activeChat.name || 'Chat' }}</h2>
            </div>
            <div class="flex items-center gap-1">
              <button
                class="btn btn-ghost btn-xs text-white/30 hover:text-white/70 rounded-lg"
                title="Start new chat"
                @click="startNewChat"
              >
                <i class="fa-regular fa-pen-to-square"></i>
              </button>
            </div>
          </div>

          <!-- Message list -->
          <div class="flex-1 min-h-0 overflow-hidden">
            <div class="h-full overflow-y-auto px-4 md:px-8 lg:px-16 xl:px-32 py-4" ref="messagesContainer">
              <!-- Loading skeleton -->
              <div v-if="isChatLoading" class="flex flex-col gap-6 py-6">
                <div v-for="i in 3" :key="i" class="flex flex-col gap-2">
                  <div class="skeleton h-4 w-1/4 bg-white/8 rounded"></div>
                  <div class="skeleton h-16 w-3/4 bg-white/8 rounded-xl"></div>
                </div>
              </div>

              <!-- Messages rendered via ChatMessageList (wraps ChatEntry) -->
              <ChatMessageList
                v-else-if="messages.length"
                ref="messageList"
                class="w-full"
                :chat="activeChat"
                :messages="messages"
                :read-only="false"
                :users-list="usersList"
                @remove="removeMessage"
                @copy="onCopy"
                @message-changed="onMessageChanged"
                @edited="onMessageEdited"
              />

              <!-- Empty chat placeholder -->
              <div v-else class="flex flex-col items-center justify-center h-full gap-3 text-white/20 py-20">
                <i class="fa-regular fa-comment-lines text-4xl"></i>
                <span class="text-sm">Send a message to begin</span>
              </div>
            </div>
          </div>

          <!-- ── Pinned input bar ── -->
          <div class="shrink-0 px-4 md:px-8 lg:px-16 xl:px-32 pb-4 pt-2">
            <div class="relative">
              <!-- IntelliSense popup -->
              <ChatIntelliSense
                v-if="intelliSenseSuggestions.length"
                ref="intelliSense"
                :suggestions="intelliSenseSuggestions"
                :active-index="intelliSenseIndex"
                :query="intelliSenseQuery"
                :search-controller="searchController"
                :progress="intelliSenseProgress"
                @select="onIntelliSenseSelect"
                @hover="intelliSenseIndex = $event"
                @accept-multi="onIntelliSenseAcceptMulti"
                @cancel="cancelIntelliSense"
              />

              <!-- Input box -->
              <ChatInputBox
                ref="inputBox"
                :waiting="waiting"
                :selected-model="activeChat.llm_model"
                :ai-models="aiModels"
                :cursor-word="cursorWord"
                :profiles="profiles"
                :selected-profiles="selectedProfiles"
                @send="sendMessage"
                @add-message="sendMessage"
                @keydown="onKeyDown"
                @paste="onPaste"
                @profiles-selected="selectedProfiles = $event"
              />

              <!-- Attachment preview -->
              <ChatAttachmentPreview
                v-if="attachments.length"
                :attachments="attachments"
                @remove-attachment="removeAttachment"
              />
            </div>

            <!-- Disclaimer -->
            <p class="text-center text-xs text-white/15 mt-2 select-none">
              codx-junior can make mistakes. Consider checking important info.
            </p>
          </div>
        </div>
      </transition>

    </main>
  </div>
</template>

<script>
import ChatAttachment from '@/api/model/ChatAttachment.js'
import { ENTITY_STATUS } from '@/store/entityStatuses'

export default {
  data() {
    return {
      waiting: false,
      attachments: [],
      cursorWord: {},
      intelliSenseSuggestions: [],
      intelliSenseIndex: 0,
      intelliSenseQuery: '',
      intelliSenseProgress: '',
      intelliSenseDebounce: null,
      intelliSenseDismissed: false,
      searchController: null,
      previousQuery: null,
      syncInterval: null,
      editorText: '',
      profiles: [],
      selectedProfiles: [],
      suggestionChips: [
        'Explain this code',
        'Write a unit test',
        'Refactor for readability',
        'Find bugs in my code'
      ]
    }
  },
  created() {
    this.$storex.chats.loadChats()
    this.loadProfiles()
  },
  mounted() {
    this.syncInterval = setInterval(() => this.syncEditorText(), 100)
  },
  unmounted() {
    clearInterval(this.syncInterval)
    this.cancelIntelliSense()
  },
  computed: {
    activeChat() {
      return this.$chats.activeChat
    },
    isChatLoading() {
      return this.activeChat?.status === ENTITY_STATUS.LOADING
    },
    messages() {
      return this.activeChat?.messages?.filter(m => !m.hide) || []
    },
    chatProject() {
      return this.$projects.allProjectsById[this.activeChat?.project_id || this.activeChat?.owner_project_id]
        || this.$project
    },
    aiModels() {
      return this.$projects.ai?.models || []
    },
    usersList() {
      return [this.$user]
    },
    firstName() {
      const name = this.$user?.username || 'there'
      return name.split(' ')[0]
    }
  },
  watch: {
    editorText(val) {
      this.updateCursorWord()
      this.scheduleIntelliSense()
    },
    activeChat(chat) {
      if (chat) {
        this.$nextTick(() => this.scrollToBottom())
      }
    },
    '$project'() {
      this.loadProfiles()
    }
  },
  methods: {
    // ── Profiles ───────────────────────────────────────────
    async loadProfiles() {
      try {
        if (this.$project?.$api) {
          const list = await this.$project.$api.profiles.list()
          this.profiles = (list || []).sort((a, b) => a.name > b.name ? 1 : -1)
        }
      } catch (err) {
        console.error('[QuickChat] loadProfiles error', err)
        this.profiles = []
      }
    },

    // ── Project selection ──────────────────────────────────
    async onProjectSelected(project) {
      await this.$storex.projects.setActiveProject(project)
      await this.$storex.chats.loadChats()
      await this.loadProfiles()
    },

    // ── Chat management ────────────────────────────────────
    async startNewChat() {
      this.$chats.clearActiveChat()
      this.attachments = []
    },
    async createChat(initialMessage) {
      const shortTitle = initialMessage.slice(0, 50) + (initialMessage.length > 50 ? '…' : '')
      const chat = await this.$chats.createNewChat({
        name: shortTitle,
        mode: 'chat',
        board: 'quick-chat',
        messages: [],
        owner_project_id: this.$project?.project_id
      })
      return chat
    },

    // ── Home state submit ──────────────────────────────────
    async onHomeSubmit() {
      const text = this.$refs.homeInputBox?.getEditorText()?.trim()
      if (!text || this.waiting) return
      this.$refs.homeInputBox?.setEditorText('')
      const chat = await this.createChat(text)
      if (!chat) return
      await this.$chats.setActiveChat(chat)
      await this.postAndSend(text)
    },
    setHomeChip(chip) {
      this.$refs.homeInputBox?.setEditorText(chip)
      this.$nextTick(() => this.$refs.homeInputBox?.focusEditor())
    },

    // ── Home keyboard handler ──────────────────────────────
    onHomeKeyDown(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        this.onHomeSubmit()
      }
    },

    // ── Active chat message sending ────────────────────────
    async sendMessage() {
      const text = this.$refs.inputBox?.getEditorText()?.trim()
      if (!text || this.waiting) return
      this.$refs.inputBox?.setEditorText('')
      await this.postAndSend(text)
    },
    async postAndSend(text) {
      if (!this.activeChat) return
      const message = this.$service.chat.getUserMessage({
        message: text,
        files: [],
        profiles: this.selectedProfiles.map(p => p.name || p),
        attachments: this.attachments.map(a => a.toJSON?.() || a),
        user: this.$user?.username
      })
      this.attachments = []
      await this.$service.chat.addMessage({ chat: this.activeChat, message })
      this.scrollToBottom()
      this.waiting = true
      try {
        await this.$storex.projects.chatWihProject(this.activeChat)
      } finally {
        this.waiting = false
        this.$nextTick(() => this.scrollToBottom())
      }
    },

    // ── Message events ─────────────────────────────────────
    removeMessage(message) {
      this.$service.chat.removeMessage({ chat: this.activeChat, message })
    },
    onMessageEdited({ doc_id, content }) {
      this.$service.chat.updateExistingMessage({ chat: this.activeChat, doc_id, update: { content } })
    },
    onMessageChanged({ doc_id, content }) {
      this.$service.chat.updateExistingMessage({ chat: this.activeChat, doc_id, update: { content } })
    },
    onCopy(message) {
      navigator.clipboard.writeText(message.content).catch(console.error)
    },

    // ── Keyboard ───────────────────────────────────────────
    onKeyDown(event) {
      if (this.intelliSenseSuggestions.length) {
        if (event.key === 'Tab') {
          event.preventDefault()
          this.onIntelliSenseSelect(this.intelliSenseSuggestions[this.intelliSenseIndex])
          return
        }
        if (event.key === 'Escape') { this.dismissIntelliSense(); return }
        if (event.key === 'ArrowUp') {
          event.preventDefault()
          this.intelliSenseIndex = Math.max(0, this.intelliSenseIndex - 1)
          return
        }
        if (event.key === 'ArrowDown') {
          event.preventDefault()
          this.intelliSenseIndex = Math.min(this.intelliSenseSuggestions.length - 1, this.intelliSenseIndex + 1)
          return
        }
      }
      if (event.key === 'Enter' && event.ctrlKey) {
        event.preventDefault()
        this.sendMessage()
      }
    },

    // ── Paste ──────────────────────────────────────────────
    async onPaste(e) {
      const imageFile = await this.$service.chat.parseImageFromPaste(e)
      if (imageFile) {
        e.preventDefault()
        try {
          const attachment = await ChatAttachment.fromFile(imageFile)
          if (attachment) this.attachments.push(attachment)
        } catch (err) {
          console.error('[QuickChat] paste image error', err)
        }
      }
    },
    removeAttachment(idx) {
      this.attachments = this.attachments.filter((_, i) => i !== idx)
    },

    // ── Scroll ─────────────────────────────────────────────
    scrollToBottom() {
      this.$refs.messageList?.scrollToBottom?.()
      const el = this.$refs.messagesContainer
      if (el) el.scrollTop = el.scrollHeight
    },

    // ── Editor sync ────────────────────────────────────────
    syncEditorText() {
      // Sync from whichever input is currently visible
      const activeRef = this.activeChat ? this.$refs.inputBox : this.$refs.homeInputBox
      const text = activeRef?.getEditorText() ?? ''
      if (text !== this.editorText) this.editorText = text
    },
    updateCursorWord() {
      const activeRef = this.activeChat ? this.$refs.inputBox : this.$refs.homeInputBox
      this.cursorWord = activeRef?.getCaretWordInfo() ?? {}
    },

    // ── IntelliSense ───────────────────────────────────────
    scheduleIntelliSense() {
      if (this.intelliSenseDismissed) {
        if (this.cursorWord.word !== this.intelliSenseQuery) this.intelliSenseDismissed = false
      }
      clearTimeout(this.intelliSenseDebounce)
      this.intelliSenseDebounce = setTimeout(() => this.runIntelliSense(), 220)
    },
    async runIntelliSense() {
      if (this.intelliSenseDismissed) return
      const word = this.cursorWord.word
      if (!word?.startsWith('@')) { this.cancelIntelliSense(); return }
      const rawQuery = word.slice(1)
      if (!rawQuery || rawQuery.trim().length < 3) { this.cancelIntelliSense(); return }
      if (this.previousQuery !== rawQuery && this.searchController) this.cancelIntelliSense()
      this.previousQuery = rawQuery
      this.intelliSenseQuery = rawQuery
      this.intelliSenseIndex = 0
      this.searchController = await this.$storex.projects.createSearchController()
      this.searchController.onProgress = ({ stage, project }) => {
        this.intelliSenseProgress = `${stage}: ${project}`
      }
      try {
        await this.chatProject?.$state?.searchMentions?.({
          query: rawQuery,
          limit: 10,
          controller: this.searchController,
          onResults: (results) => {
            if (!this.searchController?.isCancelled) {
              this.intelliSenseSuggestions = results
              this.intelliSenseIndex = 0
            }
          }
        })
      } catch (err) {
        if (err.message !== 'Search cancelled') console.error('[QuickChat IntelliSense]', err)
      }
      this.intelliSenseProgress = ''
    },
    cancelIntelliSense() {
      if (this.searchController) { this.searchController.cancel(); this.searchController = null }
      this.intelliSenseSuggestions = []
      this.intelliSenseQuery = ''
      this.previousQuery = null
    },
    dismissIntelliSense() {
      this.intelliSenseDismissed = true
    },
    onIntelliSenseSelect(suggestion) {
      const { file, name } = suggestion
      const { caretIndex, word } = this.cursorWord
      const activeRef = this.activeChat ? this.$refs.inputBox : this.$refs.homeInputBox
      const text = activeRef?.getEditorText() || ''
      const left = text.slice(0, caretIndex - word.length)
      const right = text.slice(caretIndex)
      const insert = file ? '' : '@' + name
      activeRef?.setEditorText(left + insert + ' ' + right)
      this.dismissIntelliSense()
      this.$nextTick(() => activeRef?.focusEditor())
    },
    onIntelliSenseAcceptMulti(items) {
      const { caretIndex, word } = this.cursorWord
      const activeRef = this.activeChat ? this.$refs.inputBox : this.$refs.homeInputBox
      const text = activeRef?.getEditorText() || ''
      const left = text.slice(0, caretIndex - word.length)
      const right = text.slice(caretIndex)
      const inserts = items.filter(i => !i.file).map(i => '@' + i.name).join(' ')
      activeRef?.setEditorText(left + inserts + (inserts ? ' ' : '') + right)
      this.dismissIntelliSense()
      this.$nextTick(() => activeRef?.focusEditor())
    }
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>