<script setup>
import PRViewer from '@/components/repo/PRViewer.vue'
import PRSearchPanel from '@/components/vibe/panels/PRSearchPanel.vue'
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
</script>

<template>
  <!-- Rendered only for PR-view chats. Chat.vue keeps this panel mounted for
       every chat (`v-show`), so the root is gated here: a non-PR chat builds
       nothing at all — no header, no viewers, no branch/change requests. -->
  <div v-if="isActive" class="flex flex-col h-full w-full overflow-hidden">
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

    <!-- Loading state: only replaces the content while there is nothing to show
         yet. Reloading (branch change, refresh) keeps the viewers mounted, so the
         diff is not re-parsed and the PR↔chat correlation is not restarted. -->
    <div v-if="loading && !repoChanges" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/50">
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
              :repo-changes="splitRepoChanges"
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
          :repo-changes="fullRepoChanges"
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
      prFiles: [],
      // (chatId::projectId) this panel's data was initialised for. The chats
      // store rewrites the chat record on every save, socket event or list
      // refresh; re-initialising on each of those refetched the branches, the
      // changes and (through PRViewer) the whole PR↔chat correlation.
      initKey: null
    }
  },
  async created() {
    // Only a PR-view chat may load anything. Everything else stays inert.
    if (this.chat && this.isActive) {
      await this.initialize()
    }
  },
  watch: {
    chat() {
      this.onChatChanged()
    },
    // The store mutates `mode` in place, so the `chat` watcher may not fire when
    // a chat becomes a PR view. Track the visibility flag itself.
    isActive(active) {
      if (active) this.initialize()
      else this.release()
    }
  },
  computed: {
    // Mirrors Chat.vue's `isPRView`: the panel is only visible for prview chats.
    isActive() {
      return this.chat?.mode === 'prview'
    },
    // Identity of the (chat, working project) pair this panel belongs to.
    // Stable across store refreshes, which is exactly what the `chat` watcher
    // needs to tell a real navigation apart from a mere record update.
    chatKey() {
      const projectId = this.chat?.project_id || this.chat?.owner_project_id || ''
      return `${this.chat?.id || ''}::${projectId}`
    },
    // Hand the changes payload to the viewer currently on screen ONLY.
    // PRViewer starts parsing the diff (and may start its chat correlation) as
    // soon as `repoChanges` arrives, so giving it to both the split and the full
    // instance (both are mounted) did the whole work twice.
    splitRepoChanges() {
      return this.showSearch ? this.repoChanges : null
    },
    fullRepoChanges() {
      return this.showSearch ? null : this.repoChanges
    },
    // Return the currently visible PRViewer ref
    activeViewer() {
      return this.showSearch ? this.$refs.prViewerSplit : this.$refs.prViewerFull
    }
  },
  methods: {
    async initialize() {
      this.initKey = this.chatKey
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

    /**
     * The chat record changed. Only a real navigation (another chat / another
     * working project) rebuilds the panel; a record rewrite from the store
     * (save, socket event, list refresh) must not refetch the branches nor the
     * whole PR comparison.
     */
    onChatChanged() {
      if (!this.isActive) return

      if (this.chatKey !== this.initKey) {
        this.initialize()
        return
      }

      // Same chat and project: only reload when the branch pair really changed.
      // Our own branch selections already match, so this does not double the
      // request made by onBranchChanged/onCompareBranchChanged.
      const from = this.chat?.pr_view?.from_branch
      const to = this.chat?.pr_view?.to_branch
      if ((from && from !== this.currentBranch) || (to && to !== this.compareBranch)) {
        if (from) this.currentBranch = from
        if (to) this.compareBranch = to
        this.loadChanges()
      }
    },

    /** The chat is not a PR view anymore: drop the payload, keep it inert. */
    release() {
      this.repoChanges = null
      this.prFiles = []
      this.initKey = null
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
      // Seed prFiles from the full viewer BEFORE hiding it: once search opens,
      // the full viewer stops receiving `repoChanges` and clears its files.
      if (!this.showSearch) {
        const viewer = this.$refs.prViewerFull
        if (viewer?.visibleFiles?.length) {
          this.prFiles = viewer.visibleFiles
        }
      }
      this.showSearch = !this.showSearch
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