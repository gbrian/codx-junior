<script setup>
import moment from 'moment'
</script>

<template>
  <div class="flex flex-col h-full min-h-0 overflow-hidden">
    <!-- ── File header ──────────────────────────────────────────────────── -->
    <div class="flex items-center gap-1.5 px-2 py-1.5 border-b border-base-content/10 shrink-0 flex-wrap">
      <i class="fa-solid text-[11px] shrink-0" :class="[file.icon, file.color]"></i>
      <span class="font-mono text-xs font-semibold truncate" :title="file.path">{{ fileName }}</span>
      <span class="font-mono text-[10px] opacity-40 truncate hidden sm:inline">{{ fileDir }}</span>
      <span class="badge badge-xs badge-ghost shrink-0">{{ file.label }}</span>
      <span v-if="additions || deletions" class="text-[10px] font-mono shrink-0">
        <span class="text-success">+{{ additions }}</span>
        <span class="text-error">-{{ deletions }}</span>
      </span>

      <div class="grow"></div>

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
          @click="view = 'changes'"
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
    <div v-if="error" class="alert alert-error rounded-none py-1 px-2 text-[11px] flex items-center gap-2 shrink-0">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <span class="grow truncate" :title="error">{{ error }}</span>
      <button class="btn btn-ghost btn-xs" aria-label="Dismiss error" @click="error = null">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- ── History ──────────────────────────────────────────────────────── -->
    <div v-if="view === 'history'" class="grow overflow-auto">
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
    <div v-else class="grow overflow-auto font-mono text-[11px] leading-5">
      <div v-if="loading" class="p-3 text-xs opacity-50 font-sans flex items-center gap-2">
        <i class="fa-solid fa-spinner animate-spin"></i> Loading diff...
      </div>
      <div v-else-if="!diffLines.length" class="p-3 text-xs opacity-40 font-sans">No changes</div>
      <table v-else class="w-full border-collapse">
        <tbody>
          <tr v-for="(line, index) in diffLines" :key="index" :class="lineClass(line)">
            <td class="w-9 pr-2 text-right opacity-30 select-none align-top">{{ line.oldNo }}</td>
            <td class="w-9 pr-2 text-right opacity-30 select-none align-top">{{ line.newNo }}</td>
            <td class="pr-2 align-top whitespace-pre-wrap break-all">{{ line.text }}</td>
          </tr>
        </tbody>
      </table>
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
      diff: '',
      additions: 0,
      deletions: 0,
      loading: false,
      history: [],
      historyLoading: false,
      selectedCommit: null,
      error: null,
      busy: false
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
    diffLines() {
      return this.parseDiff(this.diff)
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
      this.additions = 0
      this.deletions = 0
      this.history = []
      this.error = null
      this.loadDiff()
    },

    reload() {
      return this.view === 'history' ? this.loadHistory() : this.loadDiff()
    },

    /** Working tree (or index) diff of the current file group */
    async loadDiff() {
      if (!this.api || !this.file?.path) return
      this.loading = true
      this.error = null
      this.selectedCommit = null
      try {
        const staged = this.file.group === 'staged'
        const result = await this.api.get(
          `/api/git/repo/file/diff?path=${encodeURIComponent(this.file.path)}&staged=${staged ? 'true' : 'false'}`
        )
        this.applyDiff(result)
      } catch (ex) {
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
        this.diff = ''
        this.additions = 0
        this.deletions = 0
      } finally {
        this.loading = false
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
      try {
        const result = await this.api.get(
          `/api/git/repo/file/history?path=${encodeURIComponent(this.file.path)}&limit=25`
        )
        this.history = (result?.commits || []).map(commit => ({
          ...commit,
          relative: commit.date ? this.relativeDate(commit.date) : ''
        }))
      } catch (ex) {
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
        this.history = []
      } finally {
        this.historyLoading = false
      }
    },

    /** Show the changes introduced by a single commit */
    async openCommit(commit) {
      if (!this.api || !commit?.commit) return
      this.view = 'changes'
      this.loading = true
      this.error = null
      try {
        const result = await this.api.get(
          `/api/git/repo/file/diff?path=${encodeURIComponent(this.file.path)}&commit=${encodeURIComponent(commit.commit)}`
        )
        this.selectedCommit = commit
        this.applyDiff(result)
      } catch (ex) {
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.loading = false
      }
    },

    backToWorkingChanges() {
      this.loadDiff()
    },

    applyDiff(result) {
      this.diff = result?.diff || ''
      this.additions = result?.additions || 0
      this.deletions = result?.deletions || 0
    },

    relativeDate(date) {
      const value = moment(date)
      return value.isValid() ? value.fromNow() : date
    },

    // ── Actions ─────────────────────────────────────────────────────────
    async runAction(fn) {
      if (!this.api || this.busy) return
      this.busy = true
      this.error = null
      try {
        await fn()
        this.$emit('changed')
        await this.loadDiff()
      } catch (ex) {
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.busy = false
      }
    },

    stage() {
      this.runAction(() => this.api.post('/api/git/repo/stage', { paths: [this.file.path] }))
    },

    unstage() {
      this.runAction(() => this.api.post('/api/git/repo/unstage', { paths: [this.file.path] }))
    },

    rollback() {
      if (!window.confirm(`Roll back "${this.file.path}" to the last commit? This cannot be undone.`)) return
      this.runAction(() => this.api.post('/api/git/repo/discard', {
        paths: [this.file.path],
        include_staged: true
      }))
    },

    openFile() {
      if (!this.file?.path || !this.$ui?.openProjectFile) return
      this.$ui.openProjectFile(this.file.path)
    },

    // ── Rendering ───────────────────────────────────────────────────────
    /**
     * Split a unified diff into renderable lines with old/new line numbers.
     * Everything before the first diff/hunk line is a header block (e.g. the
     * commit metadata printed by `git show`).
     */
    parseDiff(diff) {
      const lines = []
      let oldNo = 0
      let newNo = 0
      let inDiff = false

      const push = (text, type, oldNumber = '', newNumber = '') => {
        lines.push({ text, type, oldNo: oldNumber, newNo: newNumber })
      }

      ;(diff || '').split('\n').forEach(text => {
        if (!inDiff && /^(diff --git |--- |\+\+\+ |@@ )/.test(text)) inDiff = true

        if (!inDiff) {
          push(text, 'meta')
          return
        }

        if (/^(diff --git |index |new file mode|deleted file mode|old mode|new mode|similarity index|rename |Binary files )/.test(text)) {
          push(text, 'meta')
          return
        }

        const hunk = text.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/)
        if (hunk) {
          oldNo = Number(hunk[1])
          newNo = Number(hunk[2])
          push(text, 'hunk')
          return
        }

        if (/^(--- |\+\+\+ )/.test(text)) {
          push(text, 'file')
          return
        }

        if (text.startsWith('+')) {
          push(text, 'add', '', newNo)
          newNo += 1
          return
        }

        if (text.startsWith('-')) {
          push(text, 'del', oldNo, '')
          oldNo += 1
          return
        }

        push(text, 'context', oldNo, newNo)
        oldNo += 1
        newNo += 1
      })

      return lines
    },

    lineClass(line) {
      if (line.type === 'add') return 'bg-success/15 text-success'
      if (line.type === 'del') return 'bg-error/15 text-error'
      if (line.type === 'hunk') return 'bg-info/10 text-info font-semibold'
      if (line.type === 'file') return 'text-base-content/50'
      if (line.type === 'meta') return 'text-base-content/40'
      return ''
    }
  }
}
</script>