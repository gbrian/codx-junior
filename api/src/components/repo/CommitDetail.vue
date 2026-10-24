<script setup>
import moment from 'moment'
import DiffViewer from '@/components/DiffViewer.vue'
</script>

<template>
  <div class="flex flex-col h-full min-h-0 overflow-hidden bg-base-100">
    <!-- ── Commit header ────────────────────────────────────────────────── -->
    <div class="flex items-start gap-2 px-2 py-1.5 border-b border-base-content/10 shrink-0">
      <i class="fa-solid fa-code-commit text-warning text-xs mt-1"></i>
      <div class="grow min-w-0">
        <div class="text-xs font-semibold truncate" :title="commit.subject">{{ commit.subject }}</div>
        <div class="flex items-center gap-2 text-[10px] opacity-60 mt-0.5 flex-wrap">
          <span class="font-mono">{{ commit.short }}</span>
          <span class="truncate">{{ commit.author.name }}</span>
          <span>{{ formatDate(commit.date) }}</span>
          <span v-if="commit.isMerge" class="badge badge-xs badge-ghost">merge</span>
        </div>
      </div>
      <button
        class="btn btn-xs btn-ghost shrink-0"
        title="Close commit details"
        aria-label="Close commit details"
        @click="$emit('close')"
      >
        <i class="fa-solid fa-xmark text-[10px]"></i>
      </button>
    </div>

    <!-- ── Feedback ─────────────────────────────────────────────────────── -->
    <div v-if="error" class="alert alert-error rounded-none py-1 px-2 text-[11px] flex items-center gap-2 shrink-0">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <span class="grow break-words">{{ error }}</span>
      <button class="btn btn-ghost btn-xs" aria-label="Dismiss error" @click="error = null">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- ── Changed files ────────────────────────────────────────────────── -->
    <div class="shrink-0 max-h-[42%] overflow-auto border-b border-base-content/10">
      <div v-if="loading" class="p-3 text-xs opacity-50 flex items-center gap-2">
        <i class="fa-solid fa-spinner animate-spin"></i> Loading commit...
      </div>
      <div v-else-if="!files.length" class="p-3 text-xs opacity-40 flex items-center gap-2">
        <i class="fa-solid fa-circle-info"></i> No files in this commit
      </div>

      <template v-else>
        <div class="flex items-center gap-2 px-2 py-1 bg-base-200/40 text-[10px] uppercase tracking-wide opacity-60">
          <span class="grow">{{ files.length }} file(s)</span>
          <span class="text-success normal-case">+{{ totalAdditions }}</span>
          <span class="text-error normal-case">-{{ totalDeletions }}</span>
        </div>
        <button
          v-for="file in files"
          :key="file.path"
          type="button"
          class="w-full flex items-center gap-1.5 px-2 py-1 text-left transition-colors"
          :class="selectedPath === file.path ? 'bg-primary/15' : 'hover:bg-base-200/60'"
          :title="file.path"
          @click="openFile(file)"
        >
          <i class="fa-solid text-[11px] shrink-0" :class="[statusIcon(file.status), statusColor(file.status)]"></i>
          <span class="font-mono text-[11px] truncate shrink-0 max-w-[55%]">{{ fileName(file.path) }}</span>
          <span class="font-mono text-[10px] opacity-40 truncate grow">{{ fileDir(file.path) }}</span>
          <span v-if="file.additions" class="text-[10px] font-mono text-success shrink-0">+{{ file.additions }}</span>
          <span v-if="file.deletions" class="text-[10px] font-mono text-error shrink-0">-{{ file.deletions }}</span>
        </button>
      </template>
    </div>

    <!-- ── File diff ────────────────────────────────────────────────────── -->
    <div class="grow min-h-0 flex flex-col overflow-hidden">
      <div v-if="diffLoading" class="p-3 text-xs opacity-50 flex items-center gap-2">
        <i class="fa-solid fa-spinner animate-spin"></i> Loading diff...
      </div>
      <div v-else-if="diffError" class="p-3 text-[11px] flex flex-col gap-2">
        <div class="flex items-center gap-2 text-error">
          <i class="fa-solid fa-triangle-exclamation"></i>
          <span class="break-words">{{ diffError }}</span>
        </div>
        <button class="btn btn-xs btn-ghost self-start gap-1" @click="reloadDiff">
          <i class="fa-solid fa-rotate-right text-[10px]"></i> Retry
        </button>
      </div>
      <DiffViewer
        v-else-if="diff"
        :key="diffKey"
        class="flex-1 min-h-0 overflow-hidden"
        :diff="diff"
        :file="selectedPath"
        :language="language"
      />
      <div v-else class="p-3 text-xs opacity-40 flex items-center gap-2">
        <i class="fa-solid fa-code-compare"></i> Select a file to see its diff
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CommitDetail',
  props: {
    // Project API instance
    api: { type: Object, required: true },
    // Commit selected in the graph ({ hash, short, subject, author, date, parents })
    commit: { type: Object, required: true }
  },
  emits: ['close'],
  data() {
    return {
      loading: false,
      error: null,
      stat: '',
      files: [],
      selectedPath: '',
      diff: '',
      diffLoading: false,
      diffError: null
    }
  },
  computed: {
    language() {
      const extension = (this.selectedPath || '').split('.').pop()
      return extension && extension !== this.selectedPath ? extension : ''
    },
    totalAdditions() {
      return this.files.reduce((total, file) => total + (file.additions || 0), 0)
    },
    totalDeletions() {
      return this.files.reduce((total, file) => total + (file.deletions || 0), 0)
    },
    /** Remount the renderer whenever the shown file changes */
    diffKey() {
      return `${this.commit?.hash || ''}:${this.selectedPath}`
    }
  },
  watch: {
    'commit.hash'() {
      this.load()
    }
  },
  created() {
    this.load()
  },
  methods: {
    // ── Loading ─────────────────────────────────────────────────────────
    async load() {
      if (!this.api?.repo?.commitDetail) {
        this.error = 'Repository API not available'
        return
      }
      this.loading = true
      this.error = null
      this.stat = ''
      this.files = []
      this.selectedPath = ''
      this.diff = ''
      this.diffError = null
      try {
        const detail = await this.api.repo.commitDetail({ hash: this.commit?.hash })
        this.stat = detail?.stat || ''
        this.files = detail?.files || []
        if (this.files.length) {
          await this.openFile(this.files[0])
        }
      } catch (ex) {
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.loading = false
      }
    },

    async openFile(file) {
      if (!file?.path) return
      this.selectedPath = file.path
      this.diffError = null
      // The commit detail endpoint already ships the patch: nothing to fetch
      if (file.diff) {
        this.diff = file.diff
        return
      }
      this.diff = ''
      await this.reloadDiff()
    },

    async reloadDiff() {
      if (!this.selectedPath || !this.api?.repo?.fileDiff) return
      this.diffLoading = true
      this.diffError = null
      try {
        const payload = await this.api.repo.fileDiff({
          path: this.selectedPath,
          mode: 'commit',
          commit: this.commit?.hash
        })
        this.diff = payload?.diff || ''
      } catch (ex) {
        this.diff = ''
        this.diffError = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.diffLoading = false
      }
    },

    // ── Helpers ─────────────────────────────────────────────────────────
    fileName(path) {
      return (path || '').split('/').pop()
    },

    fileDir(path) {
      const parts = (path || '').split('/')
      parts.pop()
      return parts.join('/')
    },

    statusIcon(status) {
      const icons = {
        added: 'fa-circle-plus',
        new: 'fa-circle-plus',
        deleted: 'fa-trash-can',
        renamed: 'fa-arrow-right-arrow-left',
        copied: 'fa-copy',
        modified: 'fa-pen'
      }
      return icons[status] || icons.modified
    },

    statusColor(status) {
      const colors = {
        added: 'text-success',
        new: 'text-success',
        deleted: 'text-error',
        renamed: 'text-info',
        copied: 'text-info',
        modified: 'text-warning'
      }
      return colors[status] || colors.modified
    },

    formatDate(date) {
      const value = moment(date)
      return value.isValid() ? value.format('DD MMM YYYY HH:mm') : (date || '')
    }
  }
}
</script>