<script setup>
import PRViewer from '@/components/repo/PRViewer.vue'
import BranchSelector from '@/components/vibe/panels/BranchSelector.vue'
</script>

<template>
  <div class="flex flex-col h-full w-full overflow-auto">
    <!-- Header -->
    <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
      <i class="fa-solid fa-code-pull-request text-info text-sm"></i>
      <span class="text-sm font-bold truncate grow">Pull Request Review</span>
      <button class="btn btn-xs btn-ghost" @click="loadChanges" :disabled="loading" title="Reload">
        <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': loading }"></i>
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/50">
      <i class="fa-solid fa-spinner text-3xl animate-spin"></i>
      <span class="text-sm font-medium">Loading changes...</span>
    </div>

    <template v-else>
      <!-- No active session -->
      <div v-if="!chat" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
        <i class="fa-solid fa-inbox text-4xl"></i>
        <span class="text-sm">No active session</span>
      </div>

      <!-- Branch selector row -->
      <div class="shrink-0 border-b border-base-content/10 bg-base-200/30 px-2 py-2">
        <BranchSelector
          v-if="project"
          :project="project"
          :current-branch="currentBranch"
          :compare-branch="compareBranch"
          :available-branches="branches"
          :loading="loading"
          @branch-changed="onBranchChanged"
          @compare-branch-changed="onCompareBranchChanged"
        />
      </div>

      <!-- PR View -->
      <div class="grow min-h-0 overflow-hidden">
        <PRViewer
          :chat="chat"
          :from-branch="compareBranch"
          :to-branch="currentBranch"
          :project="project"
          :repo-changes="repoChanges"
          :loading="loading"
          @refresh="loadChanges"
          @comment="onComment"
          @open-file="onOpenFile"
        />
      </div>
    </template>
  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, default: null }
  },
  emits: ['comment'],
  data() {
    return {
      loading: false,
      project: null,
      branches: [],
      currentBranch: 'main',
      compareBranch: 'local',
      repoChanges: null
    }
  },
  async created() {
    if (this.chat) {
      await this.initialize()
    }
  },
  watch: {
    chat(newChat) {
      if (newChat?.id) this.initialize()
    }
  },
  methods: {
    async initialize() {
      this.loading = true
      try {
        const chatProject = this.$chats.chatProject(this.chat)
        this.project = chatProject

        if (this.project?.$api) {
          const { branches } = await this.project.$api.repo.branches()
          this.branches = branches || []
          await this.loadChanges()
        }
      } catch (error) {
        console.error('Error initializing PR view:', error)
      } finally {
        this.loading = false
      }
    },

    async loadChanges() {
      if (!this.project?.$api) return
      this.loading = true
      try {
        this.repoChanges = await this.project.$api.repo.changes({
          from_branch: this.currentBranch,
          to_branch: this.compareBranch
        })
      } catch (error) {
        console.error('Error loading changes:', error)
        this.repoChanges = null
      } finally {
        this.loading = false
      }
    },

    onBranchChanged(branch) {
      this.currentBranch = branch
      this.loadChanges()
    },

    onCompareBranchChanged(branch) {
      this.compareBranch = branch
      this.loadChanges()
    },

    onComment({ file, line, comment, lineNumber }) {
      this.$emit('comment', {
        file: file.fileFullName,
        lineNumber,
        comment,
        diff: line?.content
      })
    },

    onOpenFile(filePath) {
      this.$ui.openProjectFile(filePath)
    }
  }
}
</script>