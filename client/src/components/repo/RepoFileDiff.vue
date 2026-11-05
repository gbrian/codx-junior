<script setup>
import CodeViewer from '@/components/CodeViewer.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
</script>

<template>
  <div class="flex flex-col h-full min-h-0 overflow-hidden bg-base-100">
    <!-- ── File header ──────────────────────────────────────────────────── -->
    <div class="flex items-center gap-1.5 px-2 py-1.5 border-b border-base-content/10 shrink-0 flex-wrap">
      <i class="fa-solid text-[11px] shrink-0" :class="[fileIcon, fileColor]"></i>
      <button
        class="font-mono text-xs font-semibold truncate max-w-[45%] hover:underline"
        :title="`${file.path} — open in FileViewer`"
        @click="openFile"
      >{{ fileName }}</button>
      <span class="font-mono text-[10px] opacity-40 truncate hidden sm:inline" :title="file.path">{{ fileDir }}</span>
      <span class="badge badge-xs badge-ghost shrink-0">{{ fileLabel }}</span>

      <div class="grow"></div>

      <template v-if="!viewingCommit">
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
      <button class="btn btn-xs btn-ghost" title="Open in FileViewer" aria-label="Open in FileViewer" @click="openFile">
        <i class="fa-solid fa-up-right-from-square text-[10px]"></i>
      </button>
      <button class="btn btn-xs btn-ghost" title="Close diff" aria-label="Close diff" @click="$emit('close')">
        <i class="fa-solid fa-xmark text-[10px]"></i>
      </button>
    </div>

    <!-- ── File load feedback ───────────────────────────────────────────── -->
    <div v-if="fileError" class="alert alert-error rounded-none py-1 px-2 text-[11px] flex items-start gap-2 shrink-0">
      <i class="fa-solid fa-triangle-exclamation mt-0.5"></i>
      <span class="grow break-words">{{ fileError }}</span>
      <button class="btn btn-ghost btn-xs" title="Retry" aria-label="Retry" @click="loadFileContent(true)">
        <i class="fa-solid fa-rotate-right"></i>
      </button>
    </div>

    <!-- Diff, code, inline edit and file history all live in CodeViewer -->
    <CodeViewer
      ref="codeViewer"
      :key="codeViewerKey"
      class="grow min-h-0"
      :code="fileContent"
      :language="language"
      :file="file.path"
      :project="project"
      :git-mode="mode"
      :read-only="!canEdit"
      :finished="true"
      :diff-option="true"
      :show-code-opened="true"
      @save-file="onSaveFile"
      @commit-view="viewingCommit = $event"
    />

    <!-- ── Rollback confirmation (replaces window.confirm) ──────────────── -->
    <ConfirmDialog
      v-if="confirmRollback"
      title="Roll back file"
      :message="`Roll back '${file.path}' to the last commit?`"
      hint="The file is restored from the last commit. Untracked and newly added files are deleted. This cannot be undone."
      icon="fa-rotate-left"
      icon-class="text-error"
      confirm-label="Roll back"
      confirm-icon="fa-rotate-left"
      confirm-class="btn-error"
      :busy="busy"
      @cancel="confirmRollback = false"
      @confirm="runRollback"
    />
  </div>
</template>

<script>
export default {
  name: 'RepoFileDiff',
  props: {
    // Project API instance (the diff is scoped by the project codx_path)
    api: { type: Object, required: true },
    // Project owning the file: CodeViewer resolves its API/project from it
    project: { type: Object, default: null },
    // Working tree file: { path, group: 'staged' | 'changes', code, label, icon, color }
    file: { type: Object, required: true }
  },
  emits: ['close', 'changed'],
  data() {
    return {
      // Working tree content passed to CodeViewer (its code view / editor)
      fileContent: '',
      fileError: null,
      busy: false,
      // Commit currently inspected from CodeViewer's history (read-only)
      viewingCommit: null,
      // Rollback confirmation dialog visibility
      confirmRollback: false,
      // Guards against an out-of-order read overwriting a newer selection
      fileRequestToken: 0,
      // Remounts CodeViewer after a write so its git diff is reloaded
      contentRevision: 0
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
    language() {
      const extension = (this.file?.path || '').split('.').pop()
      return extension && extension !== this.file?.path ? extension : ''
    },
    /** Diff source for CodeViewer: index for staged files, worktree otherwise */
    mode() {
      return this.file?.group === 'staged' ? 'staged' : 'worktree'
    },
    /** A deleted file has no content to edit (its patch is still shown) */
    canEdit() {
      return (this.file?.code || '').toUpperCase() !== 'D'
    },
    /** Remount the viewer whenever the file or its content is refreshed */
    codeViewerKey() {
      return `${this.file?.path || ''}:${this.file?.group || ''}:${this.contentRevision}`
    }
  },
  watch: {
    // The parent creates a new `file` object after every repository reload, so
    // this refreshes both the content and the git diff of an open file.
    file() {
      this.loadFileContent(true)
    }
  },
  created() {
    this.loadFileContent()
  },
  methods: {
    // ── Loading ─────────────────────────────────────────────────────────
    /**
     * Read the working tree version of the file for CodeViewer.
     *
     * @param {boolean} [force] - Bypass the short-lived files cache.
     * @returns {Promise<void>}
     */
    async loadFileContent(force = false) {
      if (!this.api || !this.file?.path) return
      if (force) this.viewingCommit = null
      if (!this.canEdit) {
        this.fileContent = ''
        this.fileError = null
        return
      }

      const token = ++this.fileRequestToken
      this.fileError = null
      try {
        const result = await this.api.files.read(this.file.path, { force })
        if (token !== this.fileRequestToken) return
        this.fileContent = result?.content ?? ''
        // A forced read follows a write/git action: remount CodeViewer so both
        // the code and the git diff are reloaded from scratch.
        if (force) this.contentRevision += 1
      } catch (ex) {
        if (token !== this.fileRequestToken) return
        this.fileError = ex?.response?.data?.detail || ex?.message || String(ex)
      }
    },

    // ── Actions ─────────────────────────────────────────────────────────
    async runAction(fn) {
      if (!this.api || this.busy) return
      this.busy = true
      this.fileError = null
      try {
        await fn()
        this.$emit('changed')
        await this.loadFileContent(true)
      } catch (ex) {
        this.fileError = ex?.response?.data?.detail || ex?.message || String(ex)
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

    /** Ask for confirmation with the app modal instead of `window.confirm` */
    rollback() {
      if (!this.file?.path) return
      this.confirmRollback = true
    },

    /** Rollback accepted in the confirmation dialog */
    async runRollback() {
      this.confirmRollback = false
      if (!this.file?.path) return
      await this.runAction(() => this.api.post('/api/git/repo/discard', {
        paths: [this.file.path],
        include_staged: true
      }))
    },

    /**
     * Persist the content edited in CodeViewer.
     *
     * @param {Object} payload - CodeViewer `save-file` event.
     * @param {string} payload.file - File path.
     * @param {string} payload.content - New file content.
     * @returns {Promise<void>}
     */
    async onSaveFile({ file, content } = {}) {
      const path = file || this.file?.path
      if (!this.api || !path || content == null || this.busy) return

      this.busy = true
      this.fileError = null
      try {
        await this.api.files.write(path, content)
        this.fileContent = content
        this.contentRevision += 1
        this.$ui?.addNotification?.({ text: `${this.fileName} saved`, type: 'success' })
        this.$emit('changed')
      } catch (ex) {
        this.fileError = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.busy = false
      }
    },

    /**
     * Open the file in the in-app FileViewer tab (not the external code editor).
     * `openFileInViewer` routes through the unified app opener, so it lands as a
     * dockview panel on desktop and as a route in single/mobile mode.
     */
    openFile() {
      if (!this.file?.path || !this.$ui?.openFileInViewer) return
      this.$ui.openFileInViewer(this.file.path)
    }
  }
}
</script>
