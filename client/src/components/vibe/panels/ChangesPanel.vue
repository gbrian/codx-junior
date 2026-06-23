<script setup>
import PRView from '@/components/repo/PRView.vue'
import BranchSelector from '@/components/vibe/panels/BranchSelector.vue'
</script>

<template>
  <div class="changes-panel flex flex-col h-full w-full">
    <!-- Header with title and refresh -->
    <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
      <i class="fa-solid fa-code-compare text-warning text-sm"></i>
      <span class="text-sm font-bold truncate grow">Changes</span>
      <button class="btn btn-xs btn-ghost" @click="refreshBranches" :disabled="loadingBranches" title="Load branches from project">
        <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': loadingBranches }"></i>
      </button>
      <button class="btn btn-xs btn-ghost" @click="$emit('refresh')" title="Refresh changes">
        <i class="fa-solid fa-arrows-rotate"></i>
      </button>
    </div>

    <!-- Projects tabs with change counts -->
    <div v-if="projectsWithGit.length > 0" class="shrink-0 border-b border-base-content/10 bg-base-200/30 overflow-x-auto scrollbar-none">
      <div class="flex gap-1 px-2 py-1 min-w-max">
        <button
          v-for="proj in projectsWithGit"
          :key="chatId(proj)"
          @click="selectedProjectId = chatId(proj)"
          :class="selectedProjectId === chatId(proj) ? 'tab-active' : ''"
          class="tab tab-sm tab-bordered text-xs gap-1 whitespace-nowrap"
        >
          <span class="font-mono truncate max-w-[100px]">{{ proj.project_name }}</span>
          <span 
            class="badge badge-xs"
            :class="getChangeCountClass(chatId(proj))"
            v-if="changeCountByProject[chatId(proj)]"
          >
            {{ changeCountByProject[chatId(proj)] }}
          </span>
        </button>
      </div>
    </div>

    <!-- Branch selector for current project -->
    <BranchSelector
      v-if="selectedProject && branchesLoaded"
      :project="selectedProject"
      :current-branch="currentBranch"
      :compare-branch="compareBranch"
      :available-branches="availableBranches"
      :loading="loadingBranches"
      @branch-changed="onBranchChanged"
      @compare-branch-changed="onCompareBranchChanged"
    />

    <!-- PR View content -->
    <div v-if="chat && selectedProject && branchesLoaded" class="grow min-h-0 overflow-hidden p-2">
      <PRView
        ref="prView"
        :chat="activeChat"
        :from-branch="compareBranch"
        :to-branch="currentBranch"
        :project="selectedProject"
        class="h-full"
        @select-branch="onBranchSelected"
        @comment="$emit('comment', $event)"
        @change-column="$emit('change-column', $event)"
        @new-chat="$emit('new-chat', $event)"
        @chat-message="$emit('chat-message', $event)"
      />
    </div>

    <!-- Empty state -->
    <div v-else-if="!chat" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
      <i class="fa-solid fa-inbox text-4xl"></i>
      <span class="text-sm">No active session</span>
    </div>

    <!-- No projects with git -->
    <div v-else-if="projectsWithGit.length === 0" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
      <i class="fa-solid fa-exclamation-triangle text-4xl text-warning"></i>
      <span class="text-sm">No projects with git initialized</span>
    </div>

    <!-- Loading state -->
    <div v-else class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
      <i class="fa-solid fa-spinner text-4xl animate-spin"></i>
      <span class="text-sm">Loading branches...</span>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, default: null }
  },
  emits: ['refresh', 'select-branch', 'comment', 'change-column', 'new-chat', 'chat-message'],
  data() {
    return {
      selectedProjectId: null,
      currentBranch: 'main',
      compareBranch: 'local',
      availableBranches: [],
      loadingBranches: false,
      branchesLoaded: false,
      projectBranchCache: {},
      projectsGitStatus: {},
      changeCountByProject: {}
    }
  },
  computed: {
    activeChat() {
      return this.chat
    },
    projectsList() {
      if (!this.chat) return []

      const projects = new Map()
      const chatsToProcess = [this.chat]

      const allChats = this.$storex.chats.allChats || []
      const subtasks = allChats.filter(c => c.parent_id === this.chat.id)
      chatsToProcess.push(...subtasks)

      chatsToProcess.forEach(c => {
        const chatId = this.chatId(c)
        if (chatId) {
          const proj = this.$storex.projects.allProjectsById?.[chatId]
          if (proj) {
            projects.set(chatId, proj)
          }
        }
      })

      return Array.from(projects.values())
    },

    projectsWithGit() {
      // Filter projects that have branches (git initialized)
      return this.projectsList.filter(proj => {
        const projId = this.chatId(proj)
        return this.projectsGitStatus[projId]?.hasGit === true
      })
    },

    selectedProject() {
      if (!this.selectedProjectId) return null
      return this.$storex.projects.allProjectsById?.[this.selectedProjectId] || null
    }
  },

  watch: {
    chat(newChat) {
      if (newChat?.id) {
        this.initializeProjectSelection()
      }
    },

    selectedProjectId(newProjectId) {
      if (newProjectId) {
        this.loadProjectBranches(newProjectId)
        this.loadBranchConfigForProject(newProjectId)
        this.loadChangeCount(newProjectId)
      }
    }
  },

  mounted() {
    this.initializeProjectSelection()
  },

  methods: {
    chatId({ project_id, owner_project_id }) {
      return project_id || owner_project_id
    },

    initializeProjectSelection() {
      if (!this.chat) {
        this.branchesLoaded = false
        this.selectedProjectId = null
        return
      }

      // Check git status for all projects first
      this.checkAllProjectsGitStatus()

      this.selectedProjectId = this.chatId(this.chat)

      if (this.selectedProjectId) {
        this.loadProjectBranches(this.selectedProjectId)
        this.loadBranchConfigForProject(this.selectedProjectId)
        this.loadChangeCount(this.selectedProjectId)
      } else {
        this.branchesLoaded = false
      }
    },

    async checkAllProjectsGitStatus() {
      // Check which projects have git initialized
      for (const proj of this.projectsList) {
        const projId = this.chatId(proj)
        if (!projId) continue

        if (this.projectsGitStatus[projId] !== undefined) {
          continue // Already checked
        }

        try {
          const branches = await proj.$api.repo.branches()
          this.projectsGitStatus[projId] = {
            hasGit: Array.isArray(branches) && branches.length > 0
          }
        } catch (error) {
          this.projectsGitStatus[projId] = { hasGit: false }
        }
      }
    },

    async loadProjectBranches(projectId) {
      if (!projectId) {
        this.branchesLoaded = false
        return
      }

      if (this.projectBranchCache[projectId]) {
        this.availableBranches = this.projectBranchCache[projectId]
        this.branchesLoaded = true
        return
      }

      this.loadingBranches = true
      this.branchesLoaded = false

      try {
        const project = this.$storex.projects.allProjectsById[projectId]
        const branches = await project.$api.repo.branches()
        this.projectBranchCache[projectId] = branches || []
        this.availableBranches = this.projectBranchCache[projectId]
        this.branchesLoaded = true
      } catch (error) {
        console.error('Failed to load branches:', error)
        this.availableBranches = []
        this.branchesLoaded = true
      } finally {
        this.loadingBranches = false
      }
    },

    async loadChangeCount(projectId) {
      if (!projectId) return

      try {
        const project = this.$storex.projects.allProjectsById[projectId]
        if (!project) return

        const changes = await project.$api.repo.changes({
          from_branch: this.currentBranch,
          to_branch: this.compareBranch
        })

        const fileCount = Object.keys(changes?.branch_file_and_commits || {}).length
        this.changeCountByProject[projectId] = fileCount
      } catch (error) {
        console.error('Failed to load change count:', error)
        this.changeCountByProject[projectId] = 0
      }
    },

    async refreshBranches() {
      if (!this.selectedProjectId || this.loadingBranches) return

      this.loadingBranches = true

      try {
        const project = this.selectedProject
        if (!project) return

        const branches = await project.$api.repo.branches()

        this.projectBranchCache[this.selectedProjectId] = branches || []
        this.availableBranches = this.projectBranchCache[this.selectedProjectId]

        if (!this.availableBranches.includes(this.currentBranch)) {
          this.currentBranch = this.availableBranches[0] || 'main'
        }

        // Refresh change counts for all projects
        for (const proj of this.projectsWithGit) {
          const projId = this.chatId(proj)
          this.loadChangeCount(projId)
        }
      } catch (error) {
        console.error('Failed to refresh branches:', error)
        this.$toast.error('Failed to load branches from project')
      } finally {
        this.loadingBranches = false
      }
    },

    loadBranchConfigForProject(projectId) {
      if (!this.chat?.pr_view) {
        this.currentBranch = 'main'
        this.compareBranch = 'local'
        return
      }

      const prConfig = this.chat.pr_view.pull_requests?.[projectId]
      if (prConfig) {
        this.currentBranch = prConfig.fromBranch || 'main'
        this.compareBranch = prConfig.toBranch || 'local'
      } else {
        this.currentBranch = 'main'
        this.compareBranch = 'local'
      }
    },

    onBranchChanged(branch) {
      this.currentBranch = branch
      this.loadChangeCount(this.selectedProjectId)
      this.saveBranchConfig()
    },

    onCompareBranchChanged(branch) {
      this.compareBranch = branch
      this.loadChangeCount(this.selectedProjectId)
      this.saveBranchConfig()
    },

    onBranchSelected({ fromBranch, toBranch }) {
      this.currentBranch = fromBranch
      this.compareBranch = toBranch
      this.loadChangeCount(this.selectedProjectId)
      this.saveBranchConfig()
      this.$emit('select-branch', { fromBranch, toBranch })
    },

    saveBranchConfig() {
      if (!this.chat || !this.selectedProjectId) return

      const updatedChat = {
        ...this.chat,
        pr_view: {
          ...(this.chat.pr_view || {}),
          pull_requests: {
            ...(this.chat.pr_view?.pull_requests || {}),
            [this.selectedProjectId]: {
              url: '',
              fromBranch: this.currentBranch,
              toBranch: this.compareBranch
            }
          }
        }
      }

      this.$storex.chats.saveChat(updatedChat)
    },

    getChangeCountClass(projectId) {
      const count = this.changeCountByProject[projectId] || 0
      if (count === 0) return 'badge-ghost'
      if (count < 5) return 'badge-info'
      if (count < 10) return 'badge-warning'
      return 'badge-error'
    }
  }
}
</script>