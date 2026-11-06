<script setup>
import moment from 'moment'
import DiffViewer from '@/components/DiffViewer.vue'
</script>

<template>
  <div class="flex flex-col h-full min-h-0 overflow-hidden bg-base-100">
    <!-- ── Commit header ────────────────────────────────────────────────── -->
    <div
      class="flex items-start gap-2 px-2 py-1.5 border-b border-base-content/10 shrink-0"
      :title="`${commit.subject} — right-click for commit actions`"
      @contextmenu.prevent.stop="openCommitContextMenu($event)"
    >
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

    <!-- ── Branch refs pointing to this commit ──────────────────────────── -->
    <div v-if="branchRefs.length" class="shrink-0 border-b border-base-content/10 bg-base-200/40">
      <div class="flex items-center gap-1.5 px-2 py-1 text-[10px] font-bold uppercase tracking-wide opacity-60">
        <i class="fa-solid fa-code-branch text-[9px]"></i>
        <span class="grow">Branch{{ branchRefs.length > 1 ? 'es' : '' }} at this commit</span>
      </div>
      <div
        v-for="ref in branchRefs"
        :key="`ref-${ref.name}`"
        class="flex items-center gap-1 px-2 py-1 border-t border-base-content/5 flex-wrap"
        :title="`${ref.name} — right-click for branch actions`"
        @contextmenu.prevent.stop="openRefContextMenu($event, ref)"
      >
        <span
          class="badge badge-xs gap-1 font-mono shrink-0 max-w-[180px]"
          :class="refClass(ref)"
          :title="ref.name"
        >
          <i class="fa-solid text-[8px] shrink-0" :class="refIcon(ref)"></i>
          <span class="truncate min-w-0">{{ ref.name }}</span>
        </span>
        <span v-if="isCurrentBranch(ref)" class="badge badge-xs badge-success shrink-0">HEAD</span>

        <div class="grow"></div>

        <button
          class="btn btn-xs btn-ghost gap-1"
          :disabled="busy || isCurrentBranch(ref)"
          :title="isCurrentBranch(ref) ? 'Already checked out' : `Checkout ${ref.name}`"
          @click="emitAction('checkout', ref)"
        >
          <i class="fa-solid fa-arrow-right-to-bracket text-[10px]"></i> Checkout
        </button>
        <button
          class="btn btn-xs btn-ghost gap-1"
          :disabled="busy || !currentBranch || isCurrentBranch(ref)"
          :title="`Merge ${ref.name} into ${currentBranch || 'the current branch'}`"
          @click="emitAction('merge', ref)"
        >
          <i class="fa-solid fa-code-merge text-[10px]"></i> Merge into current
        </button>
        <button
          class="btn btn-xs btn-ghost gap-1"
          :disabled="busy || !currentBranch || isCurrentBranch(ref)"
          :title="`Rebase ${currentBranch || 'the current branch'} onto ${ref.name}`"
          @click="emitAction('rebase', ref)"
        >
          <i class="fa-solid fa-arrows-rotate text-[10px]"></i> Rebase current onto this
        </button>
        <button
          v-if="ref.type === 'local'"
          class="btn btn-xs btn-ghost gap-1 text-error"
          :disabled="busy || isCurrentBranch(ref)"
          :title="isCurrentBranch(ref)
            ? 'A checked out branch cannot be deleted: check out another branch first'
            : `Delete branch ${ref.name}`"
          @click="emitAction('delete', ref)"
        >
          <i class="fa-solid fa-trash text-[10px]"></i> Delete
        </button>
      </div>
    </div>

    <!-- ── Changed files ────────────────────────────────────────────────── -->
    <div class="shrink-0 max-h-[40%] overflow-auto border-b border-base-content/10">
      <div v-if="loading" class="p-3 text-xs opacity-50 flex items-center gap-2">
        <i class="fa-solid fa-spinner animate-spin"></i> Loading commit...
      </div>
      <div v-else-if="!files.length" class="p-3 text-xs opacity-40 flex items-center gap-2">
        <i class="fa-solid fa-circle-info"></i> No files in this commit
      </div>

      <template v-else>
        <div class="flex items-center gap-2 px-2 py-1 bg-base-200/40 text-[10px] uppercase tracking-wide opacity-60">
          <span class="grow">{{ files.length }} file(s) changed</span>
          <span class="text-success normal-case">+{{ totalAdditions }}</span>
          <span class="text-error normal-case">-{{ totalDeletions }}</span>
        </div>
        <button
          v-for="file in files"
          :key="file.path"
          type="button"
          class="w-full flex items-center gap-1.5 px-2 py-1 text-left transition-colors"
          :class="selectedPath === file.path ? 'bg-primary/15' : 'hover:bg-base-200/60'"
          :title="`${file.path} — diff against the previous version (right-click for actions)`"
          @click="openFile(file)"
          @contextmenu.prevent.stop="openFileContextMenu($event, file)"
        >
          <i class="fa-solid text-[11px] shrink-0" :class="[statusIcon(file.status), statusColor(file.status)]"></i>
          <span class="font-mono text-[11px] truncate shrink-0 max-w-[55%]">{{ fileName(file.path) }}</span>
          <span class="font-mono text-[10px] opacity-40 truncate grow">{{ fileDir(file.path) }}</span>
          <span v-if="file.additions" class="text-[10px] font-mono text-success shrink-0">+{{ file.additions }}</span>
          <span v-if="file.deletions" class="text-[10px] font-mono text-error shrink-0">-{{ file.deletions }}</span>
        </button>
      </template>
    </div>

    <!-- ── File diff (against the previous version) ─────────────────────── -->
    <div class="grow min-h-0 flex flex-col overflow-hidden">
      <div
        v-if="selectedPath && parentShort"
        class="px-2 py-0.5 text-[10px] opacity-50 border-b border-base-content/10 shrink-0 truncate"
        :title="`Diff of ${selectedPath} against ${parentShort}`"
      >
        <i class="fa-solid fa-code-compare text-[9px]"></i>
        {{ fileName(selectedPath) }} vs {{ parentShort }}
      </div>

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

    <!-- Commit / ref / file context menu -->
    <GitContextMenu
      :visible="contextMenuState.visible"
      :position="contextMenuState.position"
      :title="contextMenuState.title"
      :items="contextMenuState.items"
      @select="onContextMenuSelect"
      @close="closeContextMenu"
    />
  </div>
</template>

<script>
import GitContextMenu from '@/components/repo/GitContextMenu.vue'
import { contextMenuMixin } from '@/mixins/contextMenu'

export default {
  name: 'CommitDetail',
  components: { GitContextMenu },
  mixins: [contextMenuMixin],
  props: {
    // Project API instance
    api: { type: Object, required: true },
    // Commit selected in the graph ({ hash, short, subject, author, date, parents, refs })
    commit: { type: Object, required: true },
    // Branch checked out in the repository: used by the branch actions
    currentBranch: { type: String, default: '' },
    // Whether a git operation is running (branch actions are disabled meanwhile)
    busy: { type: Boolean, default: false }
  },
  emits: ['close', 'branch-action', 'context-menu-notice', 'context-menu-error'],
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
    /** Local and remote branches pointing to the selected commit */
    branchRefs() {
      return (this.commit?.refs || []).filter(ref => ref.type === 'local' || ref.type === 'remote')
    },
    parentShort() {
      const parent = this.commit?.parents?.[0]
      return parent ? parent.slice(0, 8) : ''
    },
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

    /** Diff of the selected file against the previous version (first parent) */
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

    // ── Branch actions ──────────────────────────────────────────────────
    isCurrentBranch(ref) {
      return !!ref?.name && ref.name === this.currentBranch
    },

    /** Forward the action to the parent view, which owns the operations */
    emitAction(action, ref) {
      if (!ref?.name) return
      this.$emit('branch-action', { action, branch: ref.name, type: ref.type })
    },

    // ── Context menus ───────────────────────────────────────────────────
    /** Commit header: copy the hash / subject */
    openCommitContextMenu(event) {
      const commit = this.commit
      if (!commit) return
      this.openContextMenu(event, commit.short, [
        this.contextMenuItem('copy-hash', 'Copy commit hash', 'fa-hashtag', () => this.copyText(commit.hash, 'Commit hash copied')),
        this.contextMenuItem('copy-message', 'Copy commit message', 'fa-quote-left', () => this.copyText(commit.subject, 'Commit message copied')),
        this.contextMenuItem('copy-reference', 'Copy hash and message', 'fa-copy', () => this.copyText(`${commit.short} ${commit.subject}`, 'Commit reference copied')),
        this.contextMenuDivider('commit-close'),
        this.contextMenuItem('close', 'Close commit details', 'fa-xmark', () => this.$emit('close'))
      ])
    },

    /** Branch ref at this commit: same actions as the inline buttons */
    openRefContextMenu(event, ref) {
      if (!ref?.name) return
      const current = this.isCurrentBranch(ref)
      const local = ref.type === 'local'
      const items = [
        this.contextMenuItem('checkout', 'Checkout', 'fa-arrow-right-to-bracket', () => this.emitAction('checkout', ref), { disabled: current }),
        this.contextMenuItem('merge', 'Merge into current…', 'fa-code-merge', () => this.emitAction('merge', ref), { disabled: current || !this.currentBranch }),
        this.contextMenuItem('rebase', 'Rebase current onto this…', 'fa-arrows-rotate', () => this.emitAction('rebase', ref), { disabled: current || !this.currentBranch }),
        this.contextMenuItem('new-branch', 'New branch from…', 'fa-code-branch', () => this.emitAction('new-branch', ref)),
        this.contextMenuDivider('ref-copy')
      ]
      if (local) {
        items.push(
          this.contextMenuItem('delete', 'Delete branch', 'fa-trash', () => this.emitAction('delete', ref), { danger: true, disabled: current }),
          this.contextMenuDivider('ref-delete-separator')
        )
      }
      items.push(
        this.contextMenuItem('copy', 'Copy branch name', 'fa-copy', () => this.copyText(ref.name, 'Branch name copied'))
      )
      this.openContextMenu(event, ref.name, items)
    },

    /** File changed by the commit: diff, copy and editor actions */
    openFileContextMenu(event, file) {
      if (!file?.path) return
      this.openContextMenu(event, file.path, [
        this.contextMenuItem('diff', 'Open diff', 'fa-code-compare', () => this.openFile(file)),
        this.contextMenuItem('editor', 'Open in editor', 'fa-up-right-from-square', () => this.$ui?.openProjectFile(file.path)),
        this.contextMenuDivider('file-copy'),
        this.contextMenuItem('copy-path', 'Copy path', 'fa-copy', () => this.copyText(file.path, 'File path copied')),
        this.contextMenuItem('copy-name', 'Copy file name', 'fa-file', () => this.copyText(this.fileName(file.path), 'File name copied')),
        this.contextMenuItem('copy-diff', 'Copy diff', 'fa-file-code', () => this.copyText(file.diff || '', 'Diff copied'), { disabled: !file.diff })
      ])
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

    refClass(ref) {
      const styles = {
        local: 'badge-success',
        remote: 'badge-info badge-outline',
        tag: 'badge-warning badge-outline'
      }
      return styles[ref.type] || 'badge-ghost'
    },

    refIcon(ref) {
      const icons = {
        local: 'fa-code-branch',
        remote: 'fa-cloud',
        tag: 'fa-tag'
      }
      return icons[ref.type] || 'fa-code-branch'
    },

    formatDate(date) {
      const value = moment(date)
      return value.isValid() ? value.format('DD MMM YYYY HH:mm') : (date || '')
    }
  }
}
</script>