<script setup>
import PRViewer from '@/components/repo/PRViewer.vue'
import PRSearchPanel from '@/components/vibe/panels/PRSearchPanel.vue'
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
</script>

<template>
  <div class="flex flex-col h-full w-full overflow-hidden">
    <!-- Header -->
    <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
      <i class="fa-solid fa-code-pull-request text-info text-sm"></i>
      <span class="text-sm font-bold truncate grow">Pull Request Review</span>

      <!-- Search toggle -->
      <button
        class="btn btn-xs"
        :class="showSearch ? 'btn-info' : 'btn-ghost'"
        @click="toggleSearch"
        title="Search in files"
      >
        <i class="fa-solid fa-magnifying-glass"></i>
      </button>

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

      <!-- Main content area: use v-show to preserve search panel state -->
      <div v-else class="grow min-h-0 overflow-hidden">
        <!-- Split layout with search (kept mounted to preserve filter state) -->
        <SplitterGroup v-show="showSearch" direction="horizontal" class="h-full">
          <SplitterPanel :min-size="20" :defaultSize="35" class="overflow-hidden">
            <PRSearchPanel
              ref="searchPanel"
              :files="prFiles"
              :project="project"
              @close="closeSearch"
              @select-file="onSearchSelectFile"
              @jump-to-match="onJumpToMatch"
            />
          </SplitterPanel>

          <SplitterResizeHandle class="w-1 hover:bg-slate-600" />

          <SplitterPanel :min-size="30" :defaultSize="65" class="overflow-hidden">
            <PRViewer
              ref="prViewerSplit"
              :chat="chat"
              :from-branch="currentBranch"
              :to-branch="compareBranch"
              :available-branches="branches"
              :project="project"
              :repo-changes="repoChanges"
              :loading="loading"
              @refresh="loadChanges"
              @comment="onComment"
              @open-file="onOpenFile"
              @branch-changed="onBranchChanged"
              @compare-branch-changed="onCompareBranchChanged"
              @visible-files-changed="onVisibleFilesChanged"
            />
          </SplitterPanel>
        </SplitterGroup>

        <!-- PR Viewer only (no search), also kept mounted -->
        <PRViewer
          v-show="!showSearch"
          ref="prViewerFull"
          :chat="chat"
          :from-branch="currentBranch"
          :to-branch="compareBranch"
          :available-branches="branches"
          :project="project"
          :repo-changes="repoChanges"
          :loading="loading"
          @refresh="loadChanges"
          @comment="onComment"
          @open-file="onOpenFile"
          @branch-changed="onBranchChanged"
          @compare-branch-changed="onCompareBranchChanged"
          @visible-files-changed="onVisibleFilesChanged"
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
      repoChanges: null,
      showSearch: false,
      prFiles: []
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
  computed: {
    // Return the currently visible PRViewer ref
    activeViewer() {
      return this.showSearch ? this.$refs.prViewerSplit : this.$refs.prViewerFull
    }
  },
  methods: {
    async initialize() {
      this.loading = true
      try {
        const chatProject = this.$chats.chatProject(this.chat)
        this.project = chatProject

        if (this.chat?.pr_view?.from_branch) {
          this.currentBranch = this.chat.pr_view.from_branch
        }
        if (this.chat?.pr_view?.to_branch) {
          this.compareBranch = this.chat.pr_view.to_branch
        }

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

    async saveBranchSelection() {
      if (!this.chat) return
      try {
        const updatedChat = {
          ...this.chat,
          pr_view: {
            ...(this.chat.pr_view || {}),
            from_branch: this.currentBranch,
            to_branch: this.compareBranch
          }
        }
        await this.$storex.chats.saveChatInfo(updatedChat)
      } catch (error) {
        console.error('Error saving branch selection:', error)
      }
    },

    onVisibleFilesChanged(visibleFiles) {
      this.prFiles = visibleFiles || []
    },

    toggleSearch() {
      this.showSearch = !this.showSearch
      if (this.showSearch) {
        // Seed prFiles from the full viewer's visible files
        this.$nextTick(() => {
          const viewer = this.$refs.prViewerFull
          if (viewer?.visibleFiles) {
            this.prFiles = viewer.visibleFiles
          }
        })
      }
    },

    closeSearch() {
      this.showSearch = false
    },

    onSearchSelectFile(fileResult) {
      const viewer = this.activeViewer
      if (!viewer) return
      const file = viewer.files?.find(f => f.fileFullName === fileResult.fileFullName)
      if (file) viewer.selectFile(file)
    },

    onJumpToMatch({ file: fileResult, match }) {
      const viewer = this.activeViewer
      if (!viewer) return
      const file = viewer.files?.find(f => f.fileFullName === fileResult.fileFullName)
      if (!file) return

      viewer.selectFile(file)
      if (match.type === 'hunk') return

      const lineIndex = file.diffLines?.findIndex(l =>
        l.type === match.type &&
        (l.newLineNumber === match.lineNumber || l.oldLineNumber === match.lineNumber)
      )
      if (lineIndex !== undefined && lineIndex > -1) {
        viewer.visibleLineComments?.add(lineIndex)
      }
    },

    async onBranchChanged(branch) {
      this.currentBranch = branch
      await this.saveBranchSelection()
      this.loadChanges()
    },

    async onCompareBranchChanged(branch) {
      this.compareBranch = branch
      await this.saveBranchSelection()
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