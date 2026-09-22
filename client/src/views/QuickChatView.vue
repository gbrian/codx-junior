<script setup>
import QuickChatSidebar from '@/components/quick-chat/QuickChatSidebar.vue'
import ChatMessageList from '@/components/chat/ChatMessageList.vue'
import ChatInputBox from '@/components/chat/ChatInputBox.vue'
import ChatIntelliSense from '@/components/chat/ChatIntelliSense.vue'
import ChatAttachmentPreview from '@/components/chat/ChatAttachmentPreview.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import ChatAttachment from '@/api/model/ChatAttachment.js'
import RecentChatsQuickAccess from '@/components/chats/RecentChatsQuickAccess.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
import WorkspaceAppLoader from '@/components/quick-chat/WorkspaceAppLoader.vue'
</script>

<template>
  <div
    class="flex h-full w-full bg-[#111111] overflow-hidden"
    :class="isMobile ? 'flex-col' : 'flex-row'"
  >

    <!-- ── Sidebar (desktop only — renders as bottom nav on mobile) ── -->
    <QuickChatSidebar
      :user-name="$user?.username || 'User'"
      :show-mobile-chats="showMobileChats"
      :workspace-apps="workspaceApps"
      :selected-workspace-app="selectedWorkspaceApp"
      :active-chat="activeChat"
      @new-chat="startNewChat"
      @toggle-mobile-chats="showMobileChats = !showMobileChats"
      @account-settings="openAccountSettings"
      @select-workspace-app="selectWorkspaceApp"
      @open-chat="openChat"
    />

    <!-- ── Mobile chats sidebar drawer ── -->
    <transition name="slide-left">
      <div
        v-if="isMobile && showMobileChats"
        class="fixed inset-0 z-40 flex flex-col bg-[#1a1a1a] safe-area"
      >
        <!-- Drawer header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-white/10 shrink-0">
          <span class="text-sm font-semibold text-white/80">Recent Chats</span>
          <button
            class="p-2 text-white/40 hover:text-white transition-colors"
            @click="showMobileChats = false"
          >
            <i class="fas fa-xmark"></i>
          </button>
        </div>
        <!-- Chats list -->
        <div class="flex-1 min-h-0 px-3 py-3 flex flex-col overflow-hidden">
          <RecentChatsQuickAccess 
            @select="openChat"
            :collapsed="false" />
        </div>
      </div>
    </transition>

    <!-- ── Main area with VerticalSplitter (desktop only) ── -->
    <VerticalSplitter
      v-if="!isMobile && activeChat"
      class="flex-1 min-w-0 h-full"
      :panels="splitterPanels"
    >
      <!-- Left panel: Chat content -->
      <template #left>
        <main class="flex-1 flex flex-col min-w-0 h-full relative">
          <!-- Chat header -->
          <div class="shrink-0 flex items-center gap-3 px-4 py-3 border-b border-white/5 bg-[#111111]/80 backdrop-blur-sm">
            <div class="flex-1 min-w-0">
              <h2 class="text-sm font-medium text-white/80 truncate">{{ activeChat.name || 'Chat' }}</h2>
            </div>
            <div class="flex items-center gap-1">
              <!-- Hidden messages toggle -->
              <button
                class="btn btn-ghost btn-xs rounded-lg flex items-center gap-1"
                :class="showHidden ? 'text-warning' : 'text-white/30 hover:text-white/70'"
                :title="showHidden ? 'Hide hidden messages' : 'Show hidden messages'"
                @click="showHidden = !showHidden"
              >
                <i :class="showHidden ? 'fas fa-eye' : 'fas fa-eye-slash'"></i>
                <span v-if="hiddenCount" class="text-xs tabular-nums">{{ hiddenCount }}</span>
              </button>
              <button
                class="btn btn-ghost btn-xs text-white/30 hover:text-white/70 rounded-lg"
                title="Start new chat"
                @click="startNewChat"
              >
                <i class="fas fa-pen-to-square"></i>
              </button>
            </div>
          </div>

          <!-- Message list — Notion-like centered content on wide screens -->
          <div class="flex-1 min-h-0 overflow-hidden">
            <div
              class="h-full overflow-y-auto py-4 px-4"
              ref="messagesContainer"
            >
              <div class="w-full mx-auto max-w-3xl">
                <!-- Loading skeleton -->
                <div v-if="isChatLoading" class="flex flex-col gap-6 py-6">
                  <div v-for="i in 3" :key="i" class="flex flex-col gap-2">
                    <div class="skeleton h-4 w-1/4 bg-white/8 rounded"></div>
                    <div class="skeleton h-16 w-3/4 bg-white/8 rounded-xl"></div>
                  </div>
                </div>

                <!-- Messages -->
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
                  @hide="onHideMessage"
                  @answer="onAnswerMessage"
                  @thread="onThread"
                  @sub-task="onSubTask"
                  @run-agents="onRunAgents"
                  @enhance="onEnhance"
                  @add-file-to-chat="onAddFileToChat"
                  @add-file="onAddFile"
                  @open-file="onOpenFile"
                  @save-file="onSaveFile"
                  @reload-file="onReloadFile"
                  @generate-code="onGenerateCode"
                  @image="onImage"
                  @remove-file="onRemoveFile"
                  @edit-message="onEditMessage"
                  @run-edit="onRunEdit"
                  @preview-file="onPreviewFile"
                  @search-files="onSearchFiles"
                />

                <!-- Empty chat placeholder -->
                <div v-else class="flex flex-col items-center justify-center h-full gap-3 text-white/20 py-20">
                  <i class="fas fa-comment-lines text-4xl"></i>
                  <span class="text-sm">Send a message to begin</span>
                </div>
              </div>
            </div>
          </div>

          <!-- ── Pinned input bar — Notion-like centered on wide screens ── -->
          <div class="shrink-0 pb-4 pt-2 px-4">
            <div class="w-full mx-auto max-w-3xl">
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
                  @drop="onDropImages"
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
        </main>
      </template>

      <!-- Right panel: Workspace App Loader -->
      <template #right v-if="selectedWorkspaceApp">
        <div class="h-full flex flex-col relative">
          <!-- Close button overlay (for better UX when panel is small) -->
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

    <!-- ── Main area (mobile view or desktop home) ── -->
    <main
      v-if="isMobile || !activeChat"
      class="flex-1 flex flex-col min-w-0 h-full relative"
      :class="isMobile ? 'pb-16' : ''"
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

          <!-- Floating input bar using ChatInputBox -->
          <div class="relative z-10 w-full px-4" :class="isMobile ? 'max-w-full' : 'max-w-2xl'">
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
              @drop="onHomeDropImages"
              @profiles-selected="selectedProfiles = $event"
            >
              <!-- Project selector injected above the textarea -->
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

            <!-- Attachment preview for home state -->
            <ChatAttachmentPreview
              v-if="homeAttachments.length"
              :attachments="homeAttachments"
              @remove-attachment="removeHomeAttachment"
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

      <!-- ══ ACTIVE CHAT VIEW (mobile only) ══ -->
      <transition name="fade">
        <div v-if="activeChat && isMobile" class="absolute inset-0 flex flex-col">

          <!-- Chat header with loading indicator -->
          <div class="shrink-0 flex items-center gap-3 px-4 py-3 border-b border-white/5 bg-[#111111]/80 backdrop-blur-sm">
            <!-- Mobile back button -->
            <button
              v-if="isMobile"
              class="p-1.5 text-white/40 hover:text-white transition-colors mr-1"
              @click="startNewChat"
            >
              <i class="fas fa-arrow-left text-sm"></i>
            </button>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <h2 class="text-sm font-medium text-white/80 truncate">{{ activeChat.name || 'Chat' }}</h2>
                <!-- Loading indicator -->
                <span v-if="isChatLoading" class="loading loading-spinner loading-xs text-primary"></span>
              </div>
            </div>
            <div class="flex items-center gap-1">
              <!-- Hidden messages toggle -->
              <button
                class="btn btn-ghost btn-xs rounded-lg flex items-center gap-1"
                :class="showHidden ? 'text-warning' : 'text-white/30 hover:text-white/70'"
                :title="showHidden ? 'Hide hidden messages' : 'Show hidden messages'"
                @click="showHidden = !showHidden"
              >
                <i :class="showHidden ? 'fas fa-eye' : 'fas fa-eye-slash'"></i>
                <span v-if="hiddenCount" class="text-xs tabular-nums">{{ hiddenCount }}</span>
              </button>
              <button
                class="btn btn-ghost btn-xs text-white/30 hover:text-white/70 rounded-lg"
                title="Start new chat"
                @click="startNewChat"
              >
                <i class="fas fa-pen-to-square"></i>
              </button>
            </div>
          </div>

          <!-- Message list — Notion-like centered content on wide screens -->
          <div class="flex-1 min-h-0 overflow-hidden">
            <div
              class="h-full overflow-y-auto py-4"
              :class="isMobile ? 'px-3' : 'px-4'"
              ref="messagesContainer"
            >
              <div class="w-full mx-auto" :class="isMobile ? '' : 'max-w-3xl'">
                <!-- Loading skeleton -->
                <div v-if="isChatLoading" class="flex flex-col gap-6 py-6">
                  <div v-for="i in 3" :key="i" class="flex flex-col gap-2">
                    <div class="skeleton h-4 w-1/4 bg-white/8 rounded"></div>
                    <div class="skeleton h-16 w-3/4 bg-white/8 rounded-xl"></div>
                  </div>
                </div>

                <!-- Messages -->
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
                  @hide="onHideMessage"
                  @answer="onAnswerMessage"
                  @thread="onThread"
                  @sub-task="onSubTask"
                  @run-agents="onRunAgents"
                  @enhance="onEnhance"
                  @add-file-to-chat="onAddFileToChat"
                  @add-file="onAddFile"
                  @open-file="onOpenFile"
                  @save-file="onSaveFile"
                  @reload-file="onReloadFile"
                  @generate-code="onGenerateCode"
                  @image="onImage"
                  @remove-file="onRemoveFile"
                  @edit-message="onEditMessage"
                  @run-edit="onRunEdit"
                  @preview-file="onPreviewFile"
                  @search-files="onSearchFiles"
                />

                <!-- Empty chat placeholder -->
                <div v-else class="flex flex-col items-center justify-center h-full gap-3 text-white/20 py-20">
                  <i class="fas fa-comment-lines text-4xl"></i>
                  <span class="text-sm">Send a message to begin</span>
                </div>
              </div>
            </div>
          </div>

          <!-- ── Pinned input bar — Notion-like centered on wide screens ── -->
          <div
            class="shrink-0 pb-4 pt-2"
            :class="isMobile ? 'px-3' : 'px-4'"
          >
            <div class="w-full mx-auto" :class="isMobile ? '' : 'max-w-3xl'">
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
                  @drop="onDropImages"
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
        </div>
      </transition>

    </main>
  </div>
</template>

<script>
import ChatAttachment from '@/api/model/ChatAttachment.js'
import RecentChatsQuickAccess from '@/components/chats/RecentChatsQuickAccess.vue'

export default {
  components: {
    RecentChatsQuickAccess
  },
  data() {
    return {
      activeChatId: null,
      waiting: false,
      attachments: [],
      homeAttachments: [],
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
      selectedProject: null,
      showMobileChats: false,
      selectedWorkspaceApp: null,
      showHidden: false,
      MAX_IMAGE_SIZE_MB: 50,
      suggestionChips: [
        'Explain this code',
        'Write a unit test',
        'Refactor for readability',
        'Find bugs in my code'
      ],
      isChatLoading: false
    }
  },
  async created() {
    this.loadProfiles()
    // Open chat from query param if present — loadChat is called inside openChat
    const chatId = this.$route?.query?.chatId
    if (chatId) {
      await this.openChat({ id: chatId })
    }
  },
  mounted() {
    this.syncInterval = setInterval(() => this.syncEditorText(), 100)
  },
  unmounted() {
    clearInterval(this.syncInterval)
    this.cancelIntelliSense()
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    },
    activeChat() {
      if (!this.activeChatId) return null
      return this.$storex.chats.chats[this.activeChatId] || null
    },
    hiddenCount() {
      return this.activeChat?.messages?.filter(m => m.hide)?.length || 0
    },
    messages() {
      if (!this.activeChat?.messages) return []
      return this.showHidden
        ? this.activeChat.messages
        : this.activeChat.messages.filter(m => !m.hide)
    },
    chatProject() {
      return this.$projects.allProjectsById[this.activeChat?.project_id || this.activeChat?.owner_project_id]
        || this.selectedProject
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
    },
    workspaceApps() {
      return this.$storex.projects.projectApps
    },
    // Build the panels config for VerticalSplitter based on whether a workspace app is open
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
      this.updateCursorWord()
      this.scheduleIntelliSense()
    },
    '$project'() {
      this.loadProfiles()
    },
    // Reset showHidden when switching chats
    activeChatId() {
      this.showHidden = false
    }
  },
  methods: {
    // ── Account / Settings ─────────────────────────────────
    openAccountSettings() {
      this.$emit('settings')
    },

    // ── Workspace Apps ────────────────────────────────────
    selectWorkspaceApp(app) {
      this.selectedWorkspaceApp = app
    },
    closeWorkspaceApp() {
      this.selectedWorkspaceApp = null
    },

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

    async loadProfilesForChat() {
      try {
        const project = this.chatProject
        if (project?.$api) {
          const list = await project.$api.profiles.list()
          this.profiles = (list || []).sort((a, b) => a.name > b.name ? 1 : -1)
        }
      } catch (err) {
        console.error('[QuickChat] loadProfilesForChat error', err)
      }
    },

    // ── Project selection (from input box slot) ────────────
    async onProjectSelected(project) {
      this.selectedProject = project
      await this.$storex.projects.setActiveProject(project)
      await this.loadProfiles()
    },

    // ── Chat management ────────────────────────────────────
    async startNewChat() {
      this.activeChatId = null
      this.attachments = []
      this.homeAttachments = []
      this.showMobileChats = false
      this.selectedWorkspaceApp = null
    },

    async createChat(initialMessage) {
      const shortTitle = initialMessage.slice(0, 50) + (initialMessage.length > 50 ? '…' : '')
      const ownerProject = this.selectedProject || this.$project
      const chat = await this.$chats.createNewChat({
        name: shortTitle,
        mode: 'chat',
        board: 'quick-chat',
        messages: [],
        owner_project_id: ownerProject?.project_id
      })
      return chat
    },

    async openChat(chat) {
      if (!chat) return
      try {
        this.isChatLoading = true
        // loadChat fetches full chat data including messages from the server
        const loaded = await this.$chats.loadChat(chat)
        this.activeChatId = loaded?.id || chat.id
        this.showMobileChats = false
        this.selectedWorkspaceApp = null
        this.loadProfilesForChat()
        this.$nextTick(() => this.scrollToBottom())
      } catch (err) {
        console.error('[QuickChat] openChat error', err)
      } finally {
        this.isChatLoading = false
      }
    },

    // ── Home state submit ──────────────────────────────────
    async onHomeSubmit() {
      const text = this.$refs.homeInputBox?.getEditorText()?.trim()
      if (!text || this.waiting) return
      this.$refs.homeInputBox?.setEditorText('')
      const chat = await this.createChat(text)
      if (!chat) return
      this.activeChatId = chat.id
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

    // ── Image handling ─────────────────────────────────────
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
    async processMultipleImages(imageFiles, isHomeState) {
      const validImageFiles = imageFiles.filter(f => this.validateImageSize(f))
      if (validImageFiles.length === 0) return false
      for (const imageFile of validImageFiles) {
        const attachment = await this.prepareAttachmentFromFile(imageFile)
        if (attachment) {
          if (isHomeState) {
            this.homeAttachments.push(attachment)
          } else {
            this.attachments.push(attachment)
          }
        }
      }
      return validImageFiles.length > 0
    },
    removeAttachment(idx) {
      this.attachments = this.attachments.filter((_, i) => i !== idx)
    },
    removeHomeAttachment(idx) {
      this.homeAttachments = this.homeAttachments.filter((_, i) => i !== idx)
    },
    onHomeDropImages(event) {
      this.onDropImages(event, true)
    },
    async onDropImages(event, isHomeState = false) {
      if (event.dataTransfer.files?.length) {
        const imageFiles = [...event.dataTransfer.files].filter(f => f.type.startsWith('image/'))
        if (imageFiles.length > 0) {
          await this.processMultipleImages(imageFiles, isHomeState)
        }
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
      const chat = this.activeChat
      if (!chat) return

      const message = this.$service.chat.getUserMessage({
        message: text,
        files: [],
        profiles: this.selectedProfiles.map(p => p.name || p),
        attachments: this.attachments.map(a => a.toJSON?.() || a),
        user: this.$user?.username
      })
      this.attachments = []

      this.$storex.chats.addMessageToChat({ chatId: chat.id, message })

      this.scrollToBottom()
      this.waiting = true
      try {
        await this.$storex.projects.chatWihProject(chat)
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
    onHideMessage(message) {
      this.$service.chat.toggleHide({ chat: this.activeChat, doc_id: message.doc_id })
    },
    onAnswerMessage(message) {
      this.$service.chat.toggleAnswer({ chat: this.activeChat, doc_id: message.doc_id })
    },
    onThread(message) {
      const threadChat = this.$projects.allChats.find(c => c.message_id === message.doc_id)
      if (threadChat) {
        this.$chats.setActiveChat(threadChat)
      }
    },
    onSubTask({ content, title, file }) {
      const name = title || (file ? file.split('/').reverse()[0] : 'Sub-task')
      this.$chats.createNewChat({
        name,
        mode: 'task',
        board: 'quick-chat',
        messages: [{ role: 'user', content: content || '', done: true, user: this.$user?.username }],
        owner_project_id: this.chatProject?.project_id
      })
    },
    onRunAgents(message) {
      this.$storex.projects.runAgents({ chat: this.activeChat, message })
    },
    onEnhance(message) {
      console.info('[QuickChat] enhance not fully implemented in quick-chat context', message)
    },
    onAddFileToChat(file) {
      if (!this.activeChat) return
      this.$service.chat.addFileToChat({ chat: this.activeChat, file })
    },
    onAddFile(file) {
      if (!this.activeChat) return
      this.$service.chat.addFileToChat({ chat: this.activeChat, file })
    },
    onOpenFile(file) {
      this.chatProject?.$api?.coder?.openFile(file)
    },
    async onSaveFile({ file, content }) {
      try {
        await this.$storex.chats.writeFile({ chat: this.activeChat, file, content })
      } catch (err) {
        console.error('[QuickChat] onSaveFile error', err)
      }
    },
    async onReloadFile({ file, message }) {
      console.info('[QuickChat] onReloadFile', file, message)
    },
    onGenerateCode(codeBlockInfo) {
      this.$projects.generateCode({ chat: this.activeChat, codeBlockInfo })
    },
    onImage(imageData) {
      console.info('[QuickChat] onImage', imageData)
    },
    onRemoveFile({ message, file }) {
      if (!message || !file) return
      this.$service.chat.removeFileFromMessage({ message, file })
    },
    onEditMessage(message) {
      console.info('[QuickChat] onEditMessage', message)
    },
    onRunEdit(codeSnippet) {
      console.info('[QuickChat] onRunEdit', codeSnippet)
    },
    onPreviewFile(filePath) {
      this.chatProject?.$api?.coder?.openFile(filePath)
    },
    onSearchFiles({ query }) {
      console.info('[QuickChat] onSearchFiles', query)
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
          if (attachment) {
            if (this.activeChat) {
              this.attachments.push(attachment)
            } else {
              this.homeAttachments.push(attachment)
            }
          }
        } catch (err) {
          console.error('[QuickChat] paste image error', err)
        }
      }
    },

    // ── Scroll ─────────────────────────────────────────────
    scrollToBottom() {
      this.$refs.messageList?.scrollToBottom?.()
      const el = this.$refs.messagesContainer
      if (el) el.scrollTop = el.scrollHeight
    },

    // ── Editor sync ────────────────────────────────────────
    syncEditorText() {
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
.slide-left-enter-active, .slide-left-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.slide-left-enter-from, .slide-left-leave-to {
  transform: translateX(-100%);
  opacity: 0;
}
</style>