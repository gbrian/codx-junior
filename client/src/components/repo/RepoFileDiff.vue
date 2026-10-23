<script setup>
import DiffViewer from '@/components/DiffViewer.vue'
</script>

<template>
  <div class="flex flex-col h-full min-h-0 overflow-hidden bg-base-100">
    <!-- ── File header ──────────────────────────────────────────────────── -->
    <div class="flex items-center gap-1.5 px-2 py-1.5 border-b border-base-content/10 shrink-0 flex-wrap">
      <i class="fa-solid text-[11px] shrink-0" :class="[fileIcon, fileColor]"></i>
      <button
        class="font-mono text-xs font-semibold truncate max-w-[45%] hover:underline"
        :title="`${file.path} — open in editor`"
        @click="openFile"
      >{{ fileName }}</button>
      <span class="font-mono text-[10px] opacity-40 truncate hidden sm:inline" :title="file.path">{{ fileDir }}</span>
      <span class="badge badge-xs badge-ghost shrink-0">{{ fileLabel }}</span>
      <span v-if="additions || deletions" class="text-[10px] font-mono shrink-0">
        <span class="text-success">+{{ additions }}</span>
        <span class="text-error">-{{ deletions }}</span>
      </span>

      <div class="grow"></div>

      <template v-if="!selectedCommit">
        <button
          v-if="file.group === 'changes'"
          class="btn btn-xs btn-ghost gap-1"
          :disabled="busy"
          title="Stage this file"
          @click="stage"
        >
          <i class="fa-solid fa-plus text-[10px]"></i> Stage
        </button>
        <button
          v-else
          class="btn btn-xs btn-ghost gap-1"
          :disabled="busy"
          title="Remove this file from the index"
          @click="unstage"
        >
          <i class="fa-solid fa-minus text-[10px]"></i> Unstage
        </button>
        <button
          class="btn btn-xs btn-ghost gap-1 text-error"
          :disabled="busy"
          title="Roll back this file to the last commit"
          @click="rollback"
        >
          <i class="fa-solid fa-rotate-left text-[10px]"></i> Rollback
        </button>
      </template>
      <button class="btn btn-xs btn-ghost" title="Open file in editor" aria-label="Open file in editor" @click="openFile">
        <i class="fa-solid fa-up-right-from-square text-[10px]"></i>
      </button>
      <button class="btn btn-xs btn-ghost" title="Close diff" aria-label="Close diff" @click="$emit('close')">
        <i class="fa-solid fa-xmark text-[10px]"></i>
      </button>
    </div>

    <!-- ── Tabs ─────────────────────────────────────────────────────────── -->
    <div class="flex items-center gap-1 px-2 py-1 border-b border-base-content/10 shrink-0">
      <div class="join">
        <button
          class="join-item btn btn-xs"
          :class="view === 'changes' ? 'btn-primary' : 'btn-ghost'"
          @click="backToWorkingChanges"
        >
          <i class="fa-solid fa-code-compare"></i> Changes
        </button>
        <button
          class="join-item btn btn-xs"
          :class="view === 'history' ? 'btn-primary' : 'btn-ghost'"
          @click="showHistory"
        >
          <i class="fa-solid fa-clock-rotate-left"></i> History
          <span v-if="history.length" class="badge badge-xs badge-ghost ml-1">{{ history.length }}</span>
        </button>
      </div>

      <div class="grow"></div>

      <span
        v-if="selectedCommit"
        class="text-[10px] opacity-60 truncate max-w-[45%]"
        :title="selectedCommit.message"
      >
        {{ selectedCommit.short_commit }} · {{ selectedCommit.relative }}
      </span>
      <button
        v-if="selectedCommit"
        class="btn btn-xs btn-ghost"
        title="Back to the working tree diff"
        aria-label="Back to the working tree diff"
        @click="backToWorkingChanges"
      >
        <i class="fa-solid fa-arrow-left text-[10px]"></i>
      </button>
      <button
        class="btn btn-xs btn-ghost"
        :disabled="loading || historyLoading"
        title="Reload"
        aria-label="Reload"
        @click="reload"
      >
        <i
          class="fa-solid fa-rotate-right text-[10px]"
          :class="{ 'animate-spin': loading || historyLoading }"
        ></i>
      </button>
    </div>

    <!-- ── Feedback ─────────────────────────────────────────────────────── -->
    <div v-if="error" class="alert alert-error rounded-none py-1 px-2 text-[11px] flex items-start gap-2 shrink-0">
      <i class="fa-solid fa-triangle-exclamation mt-0.5"></i>
      <div class="grow min-w-0">
        <div class="break-words">{{ error }}</div>
        <div v-if="errorHint" class="opacity-80 mt-0.5 break-words">{{ errorHint }}</div>
      </div>
      <button class="btn btn-ghost btn-xs" title="Retry" aria-label="Retry" @click="reload">
        <i class="fa-solid fa-rotate-right"></i>
      </button>
    </div>

    <!-- ── History ──────────────────────────────────────────────────────── -->
    <div v-if="view === 'history'" class="grow min-h-0 overflow-auto">
      <div v-if="historyLoading" class="p-3 text-xs opacity-50 flex items-center gap-2">
        <i class="fa-solid fa-spinner animate-spin"></i> Loading history...
      </div>
      <div v-else-if="!history.length" class="p-3 text-xs opacity-40">No commits for this file</div>
      <button
        v-for="commit in history"
        :key="commit.commit"
        class="w-full flex items-center gap-2 px-2 py-1.5 text-left transition-colors"
        :class="selectedCommit?.commit === commit.commit ? 'bg-primary/15 text-primary' : 'hover:bg-base-200'"
        :title="`${commit.short_commit} · ${commit.message}`"
        @click="openCommit(commit)"
      >
        <i class="fa-solid fa-code-commit text-warning text-[11px] shrink-0"></i>
        <span class="font-mono text-[10px] opacity-60 shrink-0">{{ commit.short_commit }}</span>
        <span class="text-[11px] truncate grow">{{ commit.message }}</span>
        <span class="text-[10px] opacity-40 shrink-0 hidden sm:inline">{{ commit.author }}</span>
        <span class="badge badge-xs badge-ghost shrink-0">{{ commit.relative }}</span>
      </button>
    </div>

    <!-- ── Diff ─────────────────────────────────────────────────────────── -->
    <div v-else class="grow min-h-0 flex flex-col overflow-hidden">
      <div v-if="loading" class="p-3 text-xs opacity-50 flex items-center gap-2">
        <i class="fa-solid fa-spinner animate-spin"></i> Loading diff...
      </div>

      <div v-else-if="!hasDiff" class="p-3 flex flex-col gap-2 text-xs opacity-50">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-circle-info"></i>
          <span v-if="selectedCommit">This commit did not change this file</span>
          <span v-else>No changes to show for this file</span>
        </div>
        <pre v-if="header" class="font-mono text-[10px] whitespace-pre-wrap opacity-70">{{ header }}</pre>
        <button class="btn btn-xs btn-ghost self-start gap-1" @click="reload">
          <i class="fa-solid fa-rotate-right text-[10px]"></i> Reload
        </button>
      </div>

      <!-- Same renderer used by the Review panel (PRViewer / CodeViewer) -->
      <template v-else>
        <pre
          v-if="header"
          class="m-0 px-2 py-1 font-mono text-[10px] leading-4 opacity-50 border-b border-base-content/10 whitespace-pre-wrap shrink-0"
        >{{ header }}</pre>
        <DiffViewer
          :key="viewerKey"
          class="flex-1 min-h-0 overflow-hidden"
          :diff="diff"
          :file="fileName"
          :language="language"
        />
      </template>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RepoFileDiff',
  props: {
    // Project API instance (the diff is scoped by the project codx_path)
    api: { type: Object, required: true },
    // Working tree file: { path, group: 'staged' | 'changes', code, label, icon, color }
    file: { type: Object, required: true }
  },
  emits: ['close', 'changed'],
  data() {
    return {
      view: 'changes',
      // Unified patch only: the renderer must not receive commit metadata
      diff: '',
      header: '',
      additions: 0,
      deletions: 0,
      loading: false,
      error: null,
      errorHint: '',
      history: [],
      historyLoading: false,
      selectedCommit: null,
      busy: false,
      // Guards against an out-of-order response overwriting the current file
      requestToken: 0
    }
  },
  computed: {
    fileName() {
      return (this.file?.path || '').split('/').pop()
    },
    fileDir() {
      const parts = (this.file?.path || '').split('/')
      parts.pop()
      return parts.join('/')
    },
    fileIcon() {
      return this.file?.icon || 'fa-file'
    },
    fileColor() {
      return this.file?.color || 'text-base-content/60'
    },
    fileLabel() {
      return this.file?.label || 'Changed'
    },
    /** Mode sent to the API: the staged list diffs the index, the rest the worktree */
    mode() {
      if (this.selectedCommit) return 'commit'
      return this.file?.group === 'staged' ? 'staged' : 'worktree'
    },
    language() {
      const extension = (this.file?.path || '').split('.').pop()
      return extension && extension !== this.file?.path ? extension : ''
    },
    hasDiff() {
      return !!this.diff && this.diff.trim().length > 0
    },
    /** Remount the renderer whenever the shown content changes */
    viewerKey() {
      return `${this.file?.path || ''}:${this.mode}:${this.selectedCommit?.commit || ''}`
    }
  },
  watch: {
    'file.path'() {
      this.reset()
    },
    'file.group'() {
      this.reset()
    }
  },
  created() {
    this.reset()
  },
  methods: {
    // ── Loading ─────────────────────────────────────────────────────────
    reset() {
      this.selectedCommit = null
      this.view = 'changes'
      this.diff = ''
      this.header = ''
      this.additions = 0
      this.deletions = 0
      this.history = []
      this.error = null
      this.errorHint = ''
      this.loadDiff()
    },

    reload() {
      return this.view === 'history' ? this.loadHistory() : this.loadDiff()
    },

    /** Working tree / index / commit diff of the current file */
    async loadDiff() {
      if (!this.api || !this.file?.path) return

      const token = ++this.requestToken
      this.loading = true
      this.error = null
      this.errorHint = ''

      try {
        const query = [
          `path=${encodeURIComponent(this.file.path)}`,
          `mode=${encodeURIComponent(this.mode)}`
        ]
        if (this.selectedCommit?.commit) {
          query.push(`commit=${encodeURIComponent(this.selectedCommit.commit)}`)
        }
        const response = await this.api.get(`/api/git/repo/file/diff?${query.join('&')}`)
        if (token !== this.requestToken) return
        this.applyDiff(this.unwrap(response))
      } catch (ex) {
        if (token !== this.requestToken) return
        this.diff = ''
        this.header = ''
        this.additions = 0
        this.deletions = 0
        this.setError(ex)
      } finally {
        if (token === this.requestToken) this.loading = false
      }
    },

    async showHistory() {
      this.view = 'history'
      if (!this.history.length) await this.loadHistory()
    },

    async loadHistory() {
      if (!this.api || !this.file?.path) return
      this.historyLoading = true
      this.error = null
      this.errorHint = ''
      try {
        const result = this.unwrap(await this.api.get(
          `/api/git/repo/file/history?path=${encodeURIComponent(this.file.path)}&limit=25`
        ))
        this.history = (result?.commits || []).map(commit => ({
          ...commit,
          relative: this.relativeDate(commit.date)
        }))
      } catch (ex) {
        this.history = []
        this.setError(ex)
      } finally {
        this.historyLoading = false
      }
    },

    /** Show the changes introduced by a single commit */
    async openCommit(commit) {
      if (!this.api || !commit?.commit) return
      this.selectedCommit = commit
      this.view = 'changes'
      await this.loadDiff()
    },

    backToWorkingChanges() {
      this.view = 'changes'
      if (!this.selectedCommit) {
        return this.loadDiff()
      }
      this.selectedCommit = null
      return this.loadDiff()
    },

    // ── Response handling ───────────────────────────────────────────────
    /**
     * The API layer resolves with the payload, but some clients (and the
     * `del` helper) resolve with the raw axios response. Unwrap `data` so both
     * shapes work and the diff is never `undefined`.
     */
    unwrap(response) {
      if (!response || typeof response !== 'object') return {}
      if (!('diff' in response) && response.data && typeof response.data === 'object') {
        return response.data
      }
      return response
    },

    applyDiff(payload) {
      this.diff = payload?.diff || ''
      this.header = payload?.header || ''
      this.additions = payload?.additions || 0
      this.deletions = payload?.deletions || 0
    },

    setError(ex) {
      const detail = ex?.response?.data?.detail || ex?.message || String(ex)
      this.error = detail
      const status = ex?.response?.status
      if (status === 404 || /not found/i.test(detail)) {
        this.errorHint = 'The git diff endpoint (/api/git/repo/file/diff) is not available on the running API. Restart the codx-junior API so the repository routes are loaded, then retry.'
      } else {
        this.errorHint = ''
      }
    },

    /** Relative time without pulling a date library into this component */
    relativeDate(date) {
      if (!date) return ''
      const value = new Date(date)
      if (isNaN(value.getTime())) return date

      const minutes = Math.round((Date.now() - value.getTime()) / 60000)
      const abs = Math.abs(minutes)
      if (abs < 1) return 'just now'
      if (abs < 60) return `${minutes}m ago`
      const hours = Math.round(minutes / 60)
      if (Math.abs(hours) < 24) return `${hours}h ago`
      const days = Math.round(hours / 24)
      if (Math.abs(days) < 30) return `${days}d ago`
      return value.toISOString().slice(0, 10)
    },

    // ── Actions ─────────────────────────────────────────────────────────
    async runAction(fn) {
      if (!this.api || this.busy) return
      this.busy = true
      this.error = null
      this.errorHint = ''
      try {
        await fn()
        this.$emit('changed')
        await this.loadDiff()
      } catch (ex) {
        this.setError(ex)
      } finally {
        this.busy = false
      }
    },

    stage() {
      return this.runAction(
        () => this.api.post('/api/git/repo/stage', { paths: [this.file.path] })
      )
    },

    unstage() {
      return this.runAction(
        () => this.api.post('/api/git/repo/unstage', { paths: [this.file.path] })
      )
    },

    rollback() {
      if (!window.confirm(`Roll back "${this.file.path}" to the last commit? This cannot be undone.`)) return
      return this.runAction(() => this.api.post('/api/git/repo/discard', {
        paths: [this.file.path],
        include_staged: true
      }))
    },

    openFile() {
      if (!this.file?.path || !this.$ui?.openProjectFile) return
      this.$ui.openProjectFile(this.file.path)
    }
  }
}
</script>