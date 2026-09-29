<script setup>
import ChatView from '@/views/ChatView.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
import WorkspaceAppLoader from '@/components/quick-chat/WorkspaceAppLoader.vue'
import ChatInputBox from '@/components/chat/ChatInputBox.vue'
import ChatIntelliSense from '@/components/chat/ChatIntelliSense.vue'
import ChatAttachmentPreview from '@/components/chat/ChatAttachmentPreview.vue'
import ChatAttachment from '@/api/model/ChatAttachment.js'
</script>

<template>
  <div
    class="flex h-full w-full bg-[#111111] overflow-hidden"
    :class="isMobile ? 'flex-col' : 'flex-row'"
  >
    <!-- ── Main area with VerticalSplitter (desktop only) ── -->
    <VerticalSplitter
      v-if="!isMobile && activeChat && !isHomePage"
      class="flex-1 min-w-0 h-full"
      :panels="splitterPanels"
    >
      <!-- Left panel: ChatView (includes sidebar + header + chat) -->
      <template #left>
        <ChatView
          v-if="activeChat"
          :chat="activeChat"
          @chat="onChatChanged"
        />
      </template>

      <!-- Right panel: Workspace App Loader -->
      <template #right v-if="selectedWorkspaceApp">
        <div class="h-full flex flex-col relative">
          <div class="absolute top-2 right-2 z-10">
            <button
              class="btn btn-ghost btn-xs btn-circle text-white/50 hover:text-white"
              title="Close workspace app"
              @click="closeWorkspaceApp"
            >
              <i class="fas fa-xmark"></i>
            </button>
          </div>
          <WorkspaceAppLoader
            :app="selectedWorkspaceApp"
            @close="closeWorkspaceApp"
          />
        </div>
      </template>
    </VerticalSplitter>

    <!-- ── Home / Mobile view ── -->
    <main
      v-if="isMobile || !activeChat"
      class="flex-1 flex flex-col min-w-0 h-full relative"
      :class="[isMobile ? 'pb-20' : '']"
    >

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
          <h1
            class="text-white tracking-tight relative z-10 text-center px-4 font-semibold"
            :class="isMobile ? 'text-2xl' : 'text-4xl'"
          >
            What's next,
            <span class="text-codx-primary">{{ firstName }}</span>?
          </h1>

          <!-- Input area -->
          <div class="relative z-10 w-full px-4" :class="isMobile ? 'max-w-full' : 'max-w-2xl'">
            <!-- IntelliSense popup -->
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

            <!-- Input box with project selector and file attachment support -->
            <ChatInputBox
              ref="homeInputBox"
              :waiting="waiting"
              :cursor-word="cursorWord"
              :ai-models="aiModels"
              :profiles="profiles"
              :selected-profiles="homeMessage.profiles"
              @send="onHomeSubmit"
              @add-message="onHomeSubmit"
              @keydown="onHomeKeyDown"
              @paste="onPaste"
              @drop="onHomeDropFiles"
              @profiles-selected="homeMessage.profiles = $event"
            >
              <!-- Project selector injected above textarea -->
              <template #before-textarea>
                <div class="flex items-center gap-2">
                  <span class="text-xs text-white/30 shrink-0">Project:</span>
                  <ProjectDetailt
                    :model-value="selectedProject"
                    :options="{ showIcon: true, showFolders: false, showSelector: true }"
                    @select="onProjectSelected"
                  />
                </div>
              </template>
            </ChatInputBox>

            <!-- File list (from IntelliSense selection) -->
            <div v-if="homeMessage.files?.length" class="mt-3 space-y-2">
              <div class="text-xs text-white/50 uppercase tracking-wider">
                <i class="fa-solid fa-file text-xs mr-2"></i>Files
              </div>
              <div class="space-y-1.5">
                <div
                  v-for="(file, idx) in homeMessage.files"
                  :key="file"
                  class="flex items-center justify-between gap-2 px-3 py-2 bg-white/5 border border-white/10 rounded-lg hover:bg-white/10 transition-all"
                >
                  <span class="text-xs text-white/70 truncate">{{ file.split('/').pop() }}</span>
                  <button
                    @click.stop="removeHomeFile(idx)"
                    class="text-white/40 hover:text-white/80 transition-colors"
                  >
                    <i class="fa-solid fa-xmark text-xs"></i>
                  </button>
                </div>
              </div>
            </div>

            <!-- Attachment preview -->
            <ChatAttachmentPreview
              v-if="homeMessage.attachments?.length"
              :attachments="homeMessage.attachments"
              @remove-attachment="removeHomeAttachment"
            />
          </div>
        </div>
      </transition>

      <!-- ══ MOBILE CHAT VIEW ══ -->
      <transition name="fade">
        <ChatView
          v-if="activeChat && isMobile"
          :chat="activeChat"
          @chat="onChatChanged"
        />
      </transition>

    </main>
  </div>
</template>

<script>
import ChatAttachment from '@/api/model/ChatAttachment.js'

export default {
  data() {
    return {
      activeChatId: null,
      chatLoading: false,
      waiting: false,
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
      selectedProject: null,
      rightSidebarCollapsed: false,
      MAX_IMAGE_SIZE_MB: 50,
      loadingTimeout: null,
      homeMessage: {
        content: '',
        attachments: [],
        files: [],
        profiles: [],
        model: null
      }
    }
  },
  async created() {
    await this.loadProfiles()
    await this.openChat()
  },
  mounted() {
    this.syncInterval = setInterval(() => this.syncEditorText(), 100)
  },
  unmounted() {
    clearInterval(this.syncInterval)
    clearTimeout(this.loadingTimeout)
    clearTimeout(this.intelliSenseDebounce)
    this.cancelIntelliSense()
  },
  computed: {
    chatId() {
      return this.$route.params.chatId
    },
    workspaceId() {
      return this.$router.$navigation.getWorkspaceId()
    },
    selectedWorkspaceApp() {
      return this.$projects.projectApps.find(app => app.key === this.workspaceId)
    },
    isMobile() {
      return this.$ui.isMobile
    },
    isHomePage() {
      return this.$route.path === '/'
    },
    activeChat() {
      if (!this.activeChatId) return null
      return this.$chats.chats[this.activeChatId] || null
    },
    chatProject() {
      return this.$projects.allProjectsById[this.activeChat?.project_id || this.activeChat?.owner_project_id]
        || this.selectedProject
        || this.$project
    },
    aiModels() {
      return this.$projects.ai?.models || []
    },
    childrenChats() {
      if (!this.activeChat?.id) return []
      return this.$chats.allChats.filter(c => c.parent_id === this.activeChat.id)
    },
    firstName() {
      const name = this.$user?.username || 'there'
      return name.split(' ')[0]
    },
    splitterPanels() {
      return {
        left: {
          defaultSize: this.selectedWorkspaceApp ? 60 : 100,
          minSize: 30,
          collapsible: false
        },
        right: {
          defaultSize: this.selectedWorkspaceApp ? 40 : 0,
          minSize: 0,
          collapsible: true
        }
      }
    }
  },
  watch: {
    editorText() {
      this.homeMessage.content = this.editorText
      this.updateCursorWord()
      this.scheduleIntelliSense()
    },
    '$project'() {
      this.loadProfiles()
    },
    chatId() {
      this.openChat()
    },
    activeChatId() {
      this.onActiveChatIdChange()
    }
  },
  methods: {
    onActiveChatIdChange() {
      clearTimeout(this.loadingTimeout)
      this.chatLoading = true
      this.loadingTimeout = setTimeout(() => {
        this.chatLoading = false
      }, 600)
    },
    onChatChanged(chat) {
      if (chat && chat.id) {
        this.activeChatId = chat.id
      }
    },
    closeWorkspaceApp() {
      if (this.activeChat) {
        this.$storex.$router.$navigation.chats.open(
          this.activeChat.id,
          this.activeChat.name
        )
      }
    },
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
    async onProjectSelected(project) {
      this.selectedProject = project
      await this.$storex.projects.setActiveProject(project)
      await this.loadProfiles()
    },
    async createChat(initialMessage) {
      try {
        const shortTitle = initialMessage.slice(0, 50) + (initialMessage.length > 50 ? '…' : '')
        const ownerProject = this.selectedProject || this.$project

        if (!ownerProject?.project_id) {
          throw new Error('No active project selected')
        }

        const userMessage = this.$service.chat.getUserMessage({
          message: this.homeMessage.content,
          files: this.homeMessage.files,
          profiles: this.homeMessage.profiles.map(p => p.name || p),
          attachments: this.homeMessage.attachments.map(a => a.toJSON?.() || a),
          user: this.$user?.username
        })

        const chat = await this.$chats.createNewChat({
          name: shortTitle,
          mode: 'chat',
          board: 'quick-chat',
          messages: [userMessage],
          owner_project_id: ownerProject.project_id,
          project_id: ownerProject.project_id
        })

        if (!chat || !chat.id) {
          throw new Error('Failed to create chat - no ID returned')
        }

        await this.$chats.saveChatInfo(chat)
        return chat
      } catch (err) {
        console.error('[QuickChat] createChat error:', err)
        this.$ui?.addNotification?.({
          text: `Failed to create chat: ${err.message}`,
          type: 'error'
        })
        return null
      }
    },
    async openChat() {
      try {
        this.activeChatId = this.chatId  
        if (this.chatId) {
          const chat = { id: this.chatId }
          await this.$chats.loadChat(chat)
        }
      } catch (err) {
        console.error('[QuickChat] openChat error', err)
        this.activeChatId = null
      } finally {
        this.chatLoading = false
      }
    },
    async onHomeSubmit() {
      const text = this.$refs.homeInputBox?.getEditorText()?.trim()
      if (!text || this.waiting) return

      this.waiting = true
      try {
        const chat = await this.createChat(text)
        if (!chat) return

        this.$ui.openChat(chat)
        await this.$nextTick()
        await this.postAndSend(chat)
        this.clearHomeMessage()
        this.$refs.homeInputBox?.setEditorText('')
      } finally {
        this.waiting = false
      }
    },
    onHomeKeyDown(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        this.onHomeSubmit()
      }
    },
    validateImageSize(file) {
      const maxSizeBytes = this.MAX_IMAGE_SIZE_MB * 1024 * 1024
      if (file.size > maxSizeBytes) {
        const errorMsg = `Image exceeds maximum size of ${this.MAX_IMAGE_SIZE_MB}MB`
        this.$ui?.addNotification?.({ text: errorMsg, type: 'error' })
        return false
      }
      return true
    },
    async prepareAttachmentFromFile(file) {
      if (!this.validateImageSize(file)) return null
      try {
        const attachment = await ChatAttachment.fromFile(file)
        return attachment
      } catch (error) {
        console.error('[QuickChat] Error preparing attachment:', error)
        this.$ui?.addNotification?.({ text: 'Failed to process image', type: 'error' })
        return null
      }
    },
    async processMultipleImages(imageFiles) {
      const validImageFiles = imageFiles.filter(f => this.validateImageSize(f))
      if (validImageFiles.length === 0) return false
      for (const imageFile of validImageFiles) {
        const attachment = await this.prepareAttachmentFromFile(imageFile)
        if (attachment) {
          this.homeMessage.attachments.push(attachment)
        }
      }
      return validImageFiles.length > 0
    },
    removeHomeAttachment(idx) {
      this.homeMessage.attachments = this.homeMessage.attachments.filter((_, i) => i !== idx)
    },
    removeHomeFile(idx) {
      this.homeMessage.files = this.homeMessage.files.filter((_, i) => i !== idx)
    },
    onHomeDropFiles(event) {
      this.onDropFiles(event)
    },
    async onDropFiles(event) {
      if (event.dataTransfer.files?.length) {
        const imageFiles = [...event.dataTransfer.files].filter(f => f.type.startsWith('image/'))
        if (imageFiles.length > 0) {
          await this.processMultipleImages(imageFiles)
        }
      }
    },
    async postAndSend(chat) {
      if (!chat) return

      this.waiting = true
      try {
        await this.$storex.projects.chatWihProject(chat)
      } catch (err) {
        console.error('[QuickChat] postAndSend error:', err)
        this.$ui?.addNotification?.({
          text: 'Failed to send message',
          type: 'error'
        })
      } finally {
        this.waiting = false
      }
    },
    clearHomeMessage() {
      this.homeMessage = {
        content: '',
        attachments: [],
        files: [],
        profiles: [],
        model: null
      }
    },
    onChatSendMessage(message) {
      console.debug('[QuickChat] Message sent:', message)
    },
    syncEditorText() {
      const activeRef = this.$refs.homeInputBox
      const text = activeRef?.getEditorText() ?? ''
      if (text !== this.editorText) this.editorText = text
    },
    updateCursorWord() {
      const activeRef = this.$refs.homeInputBox
      this.cursorWord = activeRef?.getCaretWordInfo() ?? {}
    },
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
      const activeRef = this.$refs.homeInputBox
      const text = activeRef?.getEditorText() || ''
      const left = text.slice(0, caretIndex - word.length)
      const right = text.slice(caretIndex)

      if (file) {
        if (!this.homeMessage.files.includes(file)) {
          this.homeMessage.files.push(file)
        }
        activeRef?.setEditorText(left + right)
      } else {
        const insert = '@' + name
        activeRef?.setEditorText(left + insert + ' ' + right)
      }

      this.dismissIntelliSense()
      this.$nextTick(() => activeRef?.focusEditor())
    },
    onIntelliSenseAcceptMulti(items) {
      const { caretIndex, word } = this.cursorWord
      const activeRef = this.$refs.homeInputBox
      const text = activeRef?.getEditorText() || ''
      const left = text.slice(0, caretIndex - word.length)
      const right = text.slice(caretIndex)

      const mentionInserts = []
      items.forEach(({ file, name }) => {
        if (file) {
          if (!this.homeMessage.files.includes(file)) {
            this.homeMessage.files.push(file)
          }
        } else {
          mentionInserts.push('@' + name)
        }
      })

      const insert = mentionInserts.join(' ')
      activeRef?.setEditorText(left + insert + (insert ? ' ' : '') + right)
      this.dismissIntelliSense()
      this.$nextTick(() => activeRef?.focusEditor())
    },
    async onPaste(e) {
      const imageFile = await this.$service.chat.parseImageFromPaste(e)
      if (imageFile) {
        e.preventDefault()
        try {
          const attachment = await ChatAttachment.fromFile(imageFile)
          if (attachment) {
            this.homeMessage.attachments.push(attachment)
          }
        } catch (err) {
          console.error('[QuickChat] paste image error', err)
        }
      }
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