<script setup>
import Chat from '@/components/chat/Chat.vue'
import AppWindow from '@/components/windowManager/AppWindow.vue'
import Collapsible from '@/components/Collapsible.vue'
import ChatIcon from '@/components/chat/ChatIcon.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import Markdown from '@/components/Markdown.vue'
</script>

<template>
  <div class="flex flex-col h-full w-full bg-base-300 overflow-hidden">
    <!-- Status bar -->
    <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 border-b border-base-content/10 text-xs shrink-0">
      <span class="flex items-center gap-1 text-success font-mono">
        <i class="fa-solid fa-circle text-[8px] animate-pulse"></i>
        vibe
      </span>
      <span class="text-base-content/40">|</span>
      <span class="font-mono text-base-content/60">{{ $project?.project_name }}</span>
      <span class="text-base-content/40">|</span>
      <span class="font-mono text-info">{{ currentBranch }}</span>
      <div class="grow"></div>
      <!-- Layout toggles -->
      <div class="join">
        <button class="join-item btn btn-xs" :class="showChat ? 'btn-primary' : 'btn-ghost'" @click="showChat = !showChat">
          <i class="fa-solid fa-comments"></i>
        </button>
        <button class="join-item btn btn-xs" :class="showDiff ? 'btn-warning' : 'btn-ghost'" @click="showDiff = !showDiff">
          <i class="fa-solid fa-code-compare"></i>
        </button>
        <button class="join-item btn btn-xs" :class="showPreview ? 'btn-success' : 'btn-ghost'" @click="showPreview = !showPreview">
          <i class="fa-solid fa-display"></i>
        </button>
      </div>
      <button class="btn btn-xs btn-ghost" @click="reloadWorkspace">
        <i class="fa-solid fa-rotate-right"></i>
      </button>
    </div>

    <!-- Main content -->
    <div class="flex grow overflow-hidden min-h-0">

      <!-- LEFT: Chat panel -->
      <div v-if="showChat"
        class="flex flex-col h-full border-r border-base-content/10 transition-all"
        :style="{ width: chatWidth }">

        <!-- Chat header -->
        <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
          <ChatIcon mode="vibe" class="text-sm" />
          <span class="text-sm font-bold truncate grow">{{ vibeChat?.name || 'Vibe session' }}</span>
          <button class="btn btn-xs btn-ghost" @click="newVibeChat" title="New session">
            <i class="fa-solid fa-plus"></i>
          </button>
          <button class="btn btn-xs btn-ghost" @click="showChatPicker = !showChatPicker" title="Switch session">
            <i class="fa-solid fa-chevron-down"></i>
          </button>
        </div>

        <!-- Chat session picker dropdown -->
        <div v-if="showChatPicker" class="bg-base-100 border-b border-base-content/10 max-h-40 overflow-y-auto z-10">
          <div v-for="c in vibeSessions" :key="c.id"
            class="flex items-center gap-2 px-2 py-1.5 text-xs cursor-pointer hover:bg-base-200"
            :class="vibeChat?.id === c.id ? 'bg-primary/10 text-primary' : ''"
            @click="selectSession(c)">
            <ChatIcon :mode="c.mode" class="opacity-60" />
            <span class="truncate grow">{{ c.name }}</span>
            <span class="text-base-content/30 shrink-0">{{ formatDate(c.updated_at) }}</span>
          </div>
          <div v-if="!vibeSessions.length" class="px-2 py-2 text-xs text-base-content/40 text-center">
            No vibe sessions yet
          </div>
        </div>

        <!-- Chat component -->
        <div class="grow min-h-0 overflow-hidden" v-if="vibeChat">
          <Chat :chat="vibeChat" class="h-full" @refresh-chat="reloadVibeChat" />
        </div>
        <div v-else class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
          <i class="fa-solid fa-wand-magic-sparkles text-4xl"></i>
          <span class="text-sm">Start a vibe coding session</span>
          <button class="btn btn-sm btn-primary" @click="newVibeChat">
            <i class="fa-solid fa-plus"></i> New session
          </button>
        </div>
      </div>

      <!-- CENTER: Diff / changes panel -->
      <div v-if="showDiff"
        class="flex flex-col h-full border-r border-base-content/10 transition-all overflow-hidden"
        :style="{ width: diffWidth }">

        <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 border-b border-base-content/10 shrink-0">
          <i class="fa-solid fa-code-compare text-warning text-sm"></i>
          <span class="text-sm font-bold grow">Changes</span>
          <span class="badge badge-xs badge-warning" v-if="changedFiles.length">{{ changedFiles.length }}</span>
          <button class="btn btn-xs btn-ghost" @click="refreshChanges" :class="loadingChanges ? 'loading' : ''">
            <i class="fa-solid fa-rotate-right" v-if="!loadingChanges"></i>
          </button>
        </div>

        <!-- File list -->
        <div class="overflow-y-auto grow min-h-0">
          <div v-if="loadingChanges" class="flex items-center justify-center h-20">
            <span class="loading loading-spinner loading-sm"></span>
          </div>

          <div v-else-if="!changedFiles.length"
            class="flex flex-col items-center justify-center gap-2 h-32 text-base-content/30 text-sm">
            <i class="fa-solid fa-check-circle text-2xl text-success/50"></i>
            No pending changes
          </div>

          <div v-else>
            <!-- Summary stat pills -->
            <div class="flex gap-2 px-2 py-1.5 text-xs border-b border-base-content/10">
              <span class="badge badge-xs badge-success">+{{ totalAdded }}</span>
              <span class="badge badge-xs badge-error">-{{ totalRemoved }}</span>
            </div>

            <!-- File entries -->
            <div v-for="file in changedFiles" :key="file.path"
              class="border-b border-base-content/5">
              <div
                class="flex items-center gap-2 px-2 py-1.5 cursor-pointer hover:bg-base-200 text-xs"
                :class="selectedDiffFile?.path === file.path ? 'bg-base-200' : ''"
                @click="selectDiffFile(file)">
                <i class="fa-solid fa-circle text-[7px]"
                  :class="file.status === 'added' ? 'text-success' : file.status === 'deleted' ? 'text-error' : 'text-warning'"></i>
                <span class="font-mono truncate grow" :title="file.path">{{ file.shortPath }}</span>
                <span class="text-success shrink-0">+{{ file.added }}</span>
                <span class="text-error shrink-0">-{{ file.removed }}</span>
              </div>

              <!-- Inline diff for selected file -->
              <div v-if="selectedDiffFile?.path === file.path && file.diff"
                class="bg-base-300 border-t border-base-content/10 overflow-x-auto max-h-64 overflow-y-auto">
                <pre class="text-[10px] font-mono p-2 leading-relaxed"><span
                  v-for="(line, li) in parsedDiffLines(file.diff)" :key="li"
                  :class="line.type === '+' ? 'text-success block' : line.type === '-' ? 'text-error block' : 'text-base-content/50 block'"
                >{{ line.content }}</span></pre>
              </div>
            </div>
          </div>
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
            No workspace apps configured for this project. Add a VNC app in workspace settings.
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script>
import moment from 'moment'
import { v4 as uuidv4 } from 'uuid'

export default {
  props: ['chatMode', 'chat', 'kanban', 'params'],
  data() {
    return {
      showChat: true,
      showDiff: true,
      showPreview: true,
      showChatPicker: false,
      vibeChat: null,
      changedFiles: [],
      selectedDiffFile: null,
      loadingChanges: false,
      selectedAppKey: '',
      selectedApp: null,
      previewKey: 0,
    }
  },
  created() {
    this.init()
  },
  computed: {
    currentBranch() {
      return this.$projects.currentBranch || 'main'
    },
    projectApps() {
      return this.$projects.projectApps || []
    },
    vibeSessions() {
      return this.$chats.allChats
        .filter(c => c.mode === 'vibe')
        .sort((a, b) => (a.updated_at > b.updated_at ? -1 : 1))
    },
    totalAdded() {
      return this.changedFiles.reduce((s, f) => s + (f.added || 0), 0)
    },
    totalRemoved() {
      return this.changedFiles.reduce((s, f) => s + (f.removed || 0), 0)
    },
    // Dynamic widths based on visible panels
    chatWidth() {
      if (this.showDiff && this.showPreview) return '30%'
      if (this.showDiff || this.showPreview) return '50%'
      return '100%'
    },
    diffWidth() {
      if (this.showChat && this.showPreview) return '25%'
      if (this.showChat || this.showPreview) return '40%'
      return '100%'
    },
  },
  watch: {
    '$projects.activeProject'() {
      this.init()
    },
    vibeSessions(sessions) {
      // Auto-select first session if none selected
      if (!this.vibeChat && sessions.length) {
        this.vibeChat = sessions[0]
      }
    }
  },
  methods: {
    async init() {
      await this.$projects.loadBranches()
      // Pick last vibe session or set null
      this.vibeChat = this.vibeSessions[0] || null
      // Auto-select first VNC app
      this.autoSelectApp()
      await this.refreshChanges()
    },

    autoSelectApp() {
      // Prefer VNC apps
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
      // Split back workspace/app from the flat app list
      const workspaces = this.$storex.projects.workspaces || []
      const workspace = workspaces.find(w => w.name === app.workspaceName)
      this.selectedApp = workspace ? { workspace, app } : null
      this.previewKey++
    },

    async newVibeChat() {
      this.showChatPicker = false
      const chat = await this.$chats.createNewChat({
        id: uuidv4(),
        name: `Vibe ${moment().format('MMM D HH:mm')}`,
        mode: 'vibe',
        board: 'codx-junior',
        project_id: this.$project.project_id,
        messages: [],
      })
      await this.$chats.saveChat(chat)
      this.vibeChat = chat
    },

    selectSession(chat) {
      this.vibeChat = chat
      this.showChatPicker = false
    },

    reloadVibeChat() {
      if (this.vibeChat) this.$chats.reloadChat(this.vibeChat)
    },

    async refreshChanges() {
      if (!this.$project) return
      this.loadingChanges = true
      try {
        const summary = await this.$storex.api.run.changesSummary({ branch: this.currentBranch })
        this.changedFiles = this.parseChangesSummary(summary)
      } catch (ex) {
        console.error('Error loading changes', ex)
      } finally {
        this.loadingChanges = false
      }
    },

    parseChangesSummary(summary) {
      if (!summary?.files) return []
      return summary.files.map(f => ({
        ...f,
        shortPath: f.path?.split('/').slice(-2).join('/'),
        added: f.insertions || 0,
        removed: f.deletions || 0,
        status: f.insertions > 0 && f.deletions === 0 ? 'added'
              : f.deletions > 0 && f.insertions === 0 ? 'deleted'
              : 'modified'
      }))
    },

    selectDiffFile(file) {
      this.selectedDiffFile = this.selectedDiffFile?.path === file.path ? null : file
    },

    parsedDiffLines(diff) {
      if (!diff) return []
      return diff.split('\n').map(line => ({
        content: line,
        type: line.startsWith('+') ? '+' : line.startsWith('-') ? '-' : ' '
      }))
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
      this.refreshChanges()
      this.reloadPreview()
    },

    formatDate(date) {
      return moment(date).fromNow()
    },
  }
}
</script>