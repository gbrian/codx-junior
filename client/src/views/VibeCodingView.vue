<script setup>
import Chat from '@/components/chat/Chat.vue'
import AppWindow from '@/components/windowManager/AppWindow.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
import PRView from '@/components/repo/PRView.vue'
import VibeCodingHeader from '@/components/vibe/VibeCodingHeader.vue'
import KanbanContainer from '@/components/kanban/KanbanContainer.vue'
</script>

<template>
  <div class="flex flex-col h-full w-full bg-base-300 overflow-hidden">

    <!-- Status bar with git controls -->
    <VibeCodingHeader
      ref="vibeHeader"
      :chat="vibeChat"
      :project-name="$project?.project_name"
      :available-branches="branches"
      :show-chat="showChat"
      :show-changes="showChanges"
      :show-preview="showPreview"
      @toggle-view="toggleView"
      @reload="reloadWorkspace"
      @create-branch="showCreateBranchModal = true"
      @branch-changed="onCurrentBranchChanged"
      @compare-branch-changed="onCompareBranchChanged"
      @update:chat="onChatMetaUpdated"
    />

    <!-- Main content -->
    <div class="flex grow overflow-hidden min-h-0">

      <!-- LEFT: Chat panel or Kanban selector -->
      <div v-if="showChat"
        class="flex flex-col h-full border-r border-base-content/10 transition-all"
        :style="{ width: chatWidth }">

        <!-- Chat header -->
        <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
          <ChatIcon mode="vibe" class="text-sm" />
          <span class="text-sm font-bold truncate grow">{{ vibeChat?.name || 'Vibe session' }}</span>
          <button class="btn btn-xs btn-ghost" @click="showKanbanSelector = !showKanbanSelector" title="New session">
            <i class="fa-solid fa-plus"></i>
          </button>
          <button class="btn btn-xs btn-ghost" @click="showChatPicker = !showChatPicker" title="Switch session">
            <i class="fa-solid fa-chevron-down"></i>
          </button>
        </div>

        <!-- Kanban selector for new chat -->
        <div v-if="showKanbanSelector" class="flex flex-col h-full overflow-hidden bg-base-100">
          <div class="flex items-center gap-2 px-2 py-2 border-b border-base-content/10 shrink-0">
            <span class="text-xs font-semibold">Select task or create new</span>
            <button class="btn btn-xs btn-ghost ml-auto" @click="showKanbanSelector = false">
              <i class="fa-solid fa-times"></i>
            </button>
          </div>
          <div class="grow overflow-hidden">
            <KanbanContainer
              :params="kanbanParams"
              @select-board="onKanbanBoardSelected"
            />
          </div>
        </div>

        <!-- Chat session picker dropdown -->
        <div v-else-if="showChatPicker" class="bg-base-100 border-b border-base-content/10 max-h-40 overflow-y-auto z-10">
          <div v-for="c in vibeSessions" :key="c.id"
            class="flex items-center gap-2 px-2 py-1.5 text-xs cursor-pointer hover:bg-base-200"
            :class="vibeChat?.id === c.id ? 'bg-primary/10 text-primary' : ''"
            @click="selectSession(c)">
            <ChatIcon :mode="c.mode" class="opacity-60" />
            <span class="truncate grow">{{ c.name }}</span>
            <span class="text-base-content/30 shrink-0">{{ formatDate(c.updated_at) }}</span>
          </div>
          <div v-if="!vibeSessions.length" class="px-2 py-2 text-xs text-base-content-ERROR-40 text-center">
            No vibe sessions yet
          </div>
        </div>

        <!-- Chat component -->
        <div class="grow min-h-0 overflow-hidden" v-else-if="vibeChat">
          <Chat :chat="vibeChat" class="h-full" @refresh-chat="reloadVibeChat" />
        </div>
        <div v-else class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content-ERROR-40">
          <i class="fa-solid fa-wand-magic-sparkles text-4xl"></i>
          <span class="text-sm">Start a vibe coding session</span>
          <button class="btn btn-sm btn-primary" @click="newVibeChat">
            <i class="fa-solid fa-plus"></i> New session
          </button>
        </div>
      </div>

      <!-- MIDDLE: Changes/PR View panel -->
      <div v-if="showChanges"
        class="flex flex-col h-full border-r border-base-content/10 transition-all"
        :style="{ width: changesWidth }">

        <!-- Changes header -->
        <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
          <i class="fa-solid fa-code-compare text-warning text-sm"></i>
          <span class="text-sm font-bold truncate grow">Changes</span>
          <button class="btn btn-xs btn-ghost" @click="refreshChanges" title="Refresh changes">
            <i class="fa-solid fa-rotate-right"></i>
          </button>
        </div>

        <!-- PRView component -->
        <div class="grow min-h-0 overflow-hidden" v-if="vibeChat">
          <PRView
            ref="prView"
            :chat="vibeChat"
            :fromBranch="currentBranchFromMeta"
            :toBranch="compareBranchFromMeta"
            class="h-full"
            @select-branch="onPRBranchSelected"
            @comment="onPRComment"
            @change-column="onChangeColumnFromPR"
            @new-chat="onNewChatFromChanges"
            @chat-message="onPRChatMessage"
          />
        </div>
        <div v-else class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content-ERROR-40">
          <i class="fa-solid fa-inbox text-4xl"></i>
          <span class="text-sm">No active session</span>
        </div>
      </div>

      <!-- RIGHT: Preview / VNC workspace -->
      <div v-if="showPreview"
        class="flex flex-col h-full grow min-w-0 overflow-hidden">

        <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 border-b border-base-content/10 shrink-0">
          <i class="fa-solid fa-display text-success text-sm"></i>
          <span class="text-sm font-bold grow">Preview</span>

          <!-- App selector -->
          <select class="select select-xs select-bordered max-w-[180px]"
            v-model="selectedAppKey"
            @change="onAppSelected">
            <option value="">-- Select workspace app --</option>
            <option v-for="app in projectApps" :key="app.key" :value="app.key">
              {{ app.workspaceName }} / {{ app.name }}
            </option>
          </select>

          <button class="btn btn-xs btn-ghost" @click="reloadPreview" title="Reload preview">
            <i class="fa-solid fa-rotate-right"></i>
          </button>
          <button class="btn btn-xs btn-ghost" @click="openPreviewFullscreen" title="Fullscreen" v-if="selectedApp">
            <i class="fa-solid fa-expand"></i>
          </button>
        </div>

        <!-- AppWindow rendered here -->
        <div class="grow min-h-0 relative overflow-hidden bg-base-100" v-if="selectedApp" :key="previewKey">
          <AppWindow
            :workspace="selectedApp.workspace"
            :app="selectedApp.app"
            class="w-full h-full"
          />
        </div>

        <!-- Empty state -->
        <div v-else class="grow flex flex-col items-center justify-center gap-3 text-base-content/30">
          <i class="fa-solid fa-display text-5xl"></i>
          <span class="text-sm">Select a workspace app to preview</span>
          <div class="text-xs max-w-xs text-center leading-relaxed" v-if="!projectApps?.length">
            No workspace apps configured for this project.
          </div>
        </div>
      </div>
    </div>

    <!-- Create branch modal -->
    <modal v-if="showCreateBranchModal">
      <div class="flex flex-col gap-4 p-4 min-w-96">
        <h3 class="font-bold text-lg">Create New Branch</h3>
        <div class="form-control">
          <label class="label"><span class="label-text">From branch</span></label>
          <select class="select select-bordered select-sm" v-model="createBranchFrom">
            <option v-for="b in branches" :key="b" :value="b">{{ b }}</option>
          </select>
        </div>
        <input
          v-model="newBranchName"
          type="text"
          class="input input-bordered input-sm"
          placeholder="Branch name (e.g., feature/my-feature)"
          @keydown.enter="onCreateBranch"
        />
        <div class="flex gap-2 justify-end">
          <button class="btn btn-sm" @click="showCreateBranchModal = false">Cancel</button>
          <button
            class="btn btn-sm btn-primary"
            @click="onCreateBranch"
            :disabled="!newBranchName.trim()">
            Create
          </button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
import moment from 'moment'
import { v4 as uuidv4 } from 'uuid'

export default {
  props: ['chat', 'kanban', 'params'],
  data() {
    return {
      showChat: true,
      showPreview: true,
      showChanges: false,
      showChatPicker: false,
      showKanbanSelector: false,
      vibeChat: null,
      selectedAppKey: '',
      selectedApp: null,
      previewKey: 0,
      branches: [],
      showCreateBranchModal: false,
      createBranchFrom: 'main',
      newBranchName: ''
    }
  },
  created() {
    this.init()
  },
  computed: {
    projectApps() {
      return this.$projects.projectApps || []
    },
    vibeSessions() {
      return this.$chats.allChats
        .filter(c => c.mode === 'vibe')
        .sort((a, b) => (a.updated_at > b.updated_at ? -1 : 1))
    },
    chatWidth() {
      if (this.showChat && this.showChanges && this.showPreview) return '33%'
      if (this.showChat && this.showChanges) return '50%'
      if (this.showChat && this.showPreview) return '50%'
      return '100%'
    },
    changesWidth() {
      if (this.showChat && this.showChanges && this.showPreview) return '33%'
      if (this.showChat && this.showChanges) return '50%'
      if (this.showChanges && this.showPreview) return '50%'
      return '100%'
    },
    currentBranchFromMeta() {
      return this.vibeChat?.meta_data?.current_branch || 'main'
    },
    compareBranchFromMeta() {
      return this.vibeChat?.meta_data?.compare_branch || 'local'
    },
    kanbanParams() {
      return this.params || {}
    }
  },
  watch: {
    '$projects.activeProject'() {
      this.init()
    },
    vibeSessions(sessions) {
      if (!this.vibeChat && sessions.length) {
        this.selectSession(sessions[0])
      }
    }
  },
  methods: {
    async init() {
      await this.loadProjectBranches()
      this.createBranchFrom = this.branches[0] || 'main'
      const firstSession = this.vibeSessions[0] || null
      if (firstSession) this.selectSession(firstSession)
      this.autoSelectApp()
    },

    async loadProjectBranches() {
      try {
        const chatProject = this.$service.chat.getChatProject(this.vibeChat)
        const projectApi = chatProject?.$api || this.$api
        this.branches = await projectApi.repo.branches()
      } catch (error) {
        console.error('Error loading branches:', error)
        this.branches = ['main']
      }
    },

    autoSelectApp() {
      const vncApp = this.projectApps.find(a =>
        a.name?.toLowerCase().includes('vnc') ||
        a.type?.toLowerCase().includes('vnc')
      ) || this.projectApps[0]
      if (vncApp) {
        this.selectedAppKey = vncApp.key
        this.onAppSelected()
      }
    },

    onAppSelected() {
      const app = this.projectApps.find(a => a.key === this.selectedAppKey)
      if (!app) { this.selectedApp = null; return }
      const workspaces = this.$storex.projects.workspaces || []
      const workspace = workspaces.find(w => w.name === app.workspaceName)
      this.selectedApp = workspace ? { workspace, app } : null
      this.previewKey++
    },

    toggleView(view) {
      if (view === 'chat') this.showChat = !this.showChat
      else if (view === 'changes') this.showChanges = !this.showChanges
      else if (view === 'preview') this.showPreview = !this.showPreview
    },

    onCurrentBranchChanged(branch) {
      // Branch state is now managed by header via meta_data
    },

    onCompareBranchChanged(branch) {
      // Branch state is now managed by header via meta_data
    },

    async onChatMetaUpdated(updatedChat) {
      if (!updatedChat?.id) return
      Object.assign(this.vibeChat, updatedChat)
      await this.$chats.saveChat(this.vibeChat)
    },

    onPRBranchSelected({ fromBranch, toBranch }) {
      this.$service.chat.updateChatBranches({
        chat: this.vibeChat,
        currentBranch: toBranch,
        compareBranch: fromBranch
      })
      this.$refs.vibeHeader?.onBranchCreated?.(toBranch)
    },

    async onCreateBranch() {
      if (!this.newBranchName.trim()) return
      try {
        const chatProject = this.$service.chat.getChatProject(this.vibeChat)
        const projectApi = chatProject?.$api || this.$api
        await projectApi.git.createBranch({
          name: this.newBranchName,
          from: this.createBranchFrom
        })
        await this.loadProjectBranches()
        this.showCreateBranchModal = false
        this.$refs.vibeHeader?.onBranchCreated(this.newBranchName)
        this.newBranchName = ''
        this.$ui.addNotification({ text: `Branch created: ${this.newBranchName}`, type: 'success' })
      } catch (error) {
        this.$ui.addNotification({ text: `Error creating branch: ${error.message}`, type: 'error' })
      }
    },

    async newVibeChat() {
      this.showChatPicker = false
      const currentBranch = this.branches[0] || 'main'
      const chat = await this.$chats.createNewChat({
        id: uuidv4(),
        name: `Vibe ${moment().format('MMM D HH:mm')}`,
        mode: 'vibe',
        board: 'codx-junior',
        project_id: this.$project.project_id,
        messages: [],
        meta_data: {
          current_branch: currentBranch,
          compare_branch: 'local'
        }
      })
      await this.$chats.saveChat(chat)
      this.vibeChat = chat
    },

    selectSession(chat) {
      this.vibeChat = chat
      this.showChatPicker = false
      this.loadProjectBranches()
    },

    // Called when user selects a task from kanban
    onKanbanBoardSelected(board) {
      this.showKanbanSelector = false
      if (board) {
        this.$chats.setActiveChat(board)
      }
    },

    reloadVibeChat() {
      if (this.vibeChat) this.$chats.reloadChat(this.vibeChat)
    },

    refreshChanges() {
      this.$refs.prView?.refreshSummary?.()
    },

    reloadPreview() {
      this.previewKey++
    },

    openPreviewFullscreen() {
      if (this.selectedApp) {
        this.$projects.openWorkspaceApp(this.selectedApp)
      }
    },

    reloadWorkspace() {
      this.reloadPreview()
      if (this.vibeChat) this.reloadVibeChat()
    },

    onPRComment({ chat, title, files, description, profiles, mode, column }) {
      this.$emit('comment', { chat, title, files, description, profiles, mode, column })
    },

    onChangeColumnFromPR({ chats, column }) {
      this.$emit('change-column', { chats, column })
    },

    onNewChatFromChanges(payload) {
      this.$emit('new-chat', payload)
    },

    onPRChatMessage({ file }) {
      if (file.chat?.messages) file.chat.messages.push({})
    },

    formatDate(date) {
      return moment(date).fromNow()
    }
  }
}
</script>