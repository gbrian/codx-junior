<script>
/**
 * Git conflict resolver.
 *
 * Modal used by the git view when a merge, rebase, cherry-pick or revert stops
 * on conflicts. It detects the state from the backend (never from the local
 * working tree copy) and offers three ways out of a conflict:
 *
 * - **Manual**: edit the file in the textarea and save it, or take *ours* /
 *   *theirs* in one click.
 * - **AI**: ask the project LLM to merge the base/ours/theirs versions. The
 *   backend rejects answers that still contain conflict markers.
 * - **Abort**: drop the whole operation and go back to the previous state.
 *
 * Once every file is resolved the modal continues the merge/rebase (or, for a
 * squash merge, tells the user to commit the staged result).
 */
const CONFLICT_MARKER_PATTERN = /^(?:<{7}|={7}|>{7}|\|{7})(?: .*)?$/m

export default {
  name: 'GitConflictResolver',
  props: {
    api: { type: Object, required: true },
    project: { type: Object, default: null },
    /** Optional state already loaded by the parent (avoids a first request). */
    initialState: { type: Object, default: null },
    /** Conflict file to select when the modal opens. */
    initialPath: { type: String, default: '' }
  },
  emits: ['close', 'updated', 'finished'],
  data() {
    return {
      loading: false,
      busy: false,
      error: null,
      notice: null,
      state: this.initialState || {},
      selectedPath: '',
      // Working copy of the selected file being edited
      content: '',
      aiInstructions: '',
      showAIOptions: false,
      abortPending: false,
      preselected: false
    }
  },
  computed: {
    conflicts() {
      return this.state?.conflicts || []
    },
    unresolvedCount() {
      return this.state?.unresolved_count ?? this.conflicts.length
    },
    operation() {
      return this.state?.operation || ''
    },
    operationLabel() {
      return this.state?.operation_label || 'Conflict'
    },
    selected() {
      return this.conflicts.find(entry => entry.path === this.selectedPath) || null
    },
    allResolved() {
      return !this.loading && this.unresolvedCount === 0
    },
    /** A pending merge/rebase with zero unmerged files */
    pendingOnly() {
      return !!this.state?.in_progress && this.unresolvedCount === 0
    },
    operationHint() {
      if (!this.state?.in_progress) return 'There is no operation in progress.'
      if (this.state?.squash) {
        return 'The squashed changes are staged. Commit them from the composer to finish.'
      }
      if (this.operation === 'merge') {
        return 'The merge finished cleanly and its changes are staged. Continue it (or commit from the composer) to finish.'
      }
      if (this.operation === 'rebase') {
        return 'The rebase is waiting. Continue it to replay the remaining commits.'
      }
      if (this.operation === 'cherry-pick') {
        return 'The cherry-pick is waiting. Continue it to apply the remaining change.'
      }
      if (this.operation === 'revert') {
        return 'The revert is waiting. Continue it to finish.'
      }
      return 'Finish or abort the operation from the footer.'
    },
    canContinue() {
      return !!this.state?.can_continue && !this.busy
    },
    canCommitSquash() {
      return !!this.state?.can_commit && !this.busy
    },
    contentHasMarkers() {
      return CONFLICT_MARKER_PATTERN.test(this.content || '')
    },
    contentDirty() {
      return !!this.selected && this.content !== (this.selected.content || '')
    },
    progressLabel() {
      if (this.loading) return 'Loading conflicts...'
      if (!this.state?.in_progress) return 'No operation in progress'
      if (this.pendingOnly) return 'No conflicts'
      if (this.allResolved) return 'All conflicts resolved'
      return `${this.unresolvedCount} unresolved file(s)`
    },
    selectedIsBinary() {
      return !!this.selected?.binary
    },
    selectedOursLabel() {
      return this.selected?.ours_label || 'ours'
    },
    selectedTheirsLabel() {
      return this.selected?.theirs_label || 'theirs'
    }
  },
  watch: {
    // Keep the editor in sync when the backend refreshes the selected file
    // (after an AI resolution, a side selection or a reload).
    selected(entry) {
      if (!entry) {
        this.content = ''
        return
      }
      this.content = entry.content || ''
    },
    initialState(value) {
      if (value && Object.keys(value).length) {
        this.state = value
        this.ensureSelection()
      }
    }
  },
  created() {
    this.load()
  },
  methods: {
    /** Reload the conflict state from the backend. */
    async load({ silent = false } = {}) {
      if (!this.api) return
      if (!silent) this.loading = true
      try {
        const state = await this.api.repo.conflicts({ include_content: true })
        this.state = state || {}
        this.ensureSelection()
        this.$emit('updated', this.state)
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.loading = false
      }
    },

    /** Select a conflict, keeping the current selection when it still exists. */
    ensureSelection() {
      const paths = this.conflicts.map(entry => entry.path)
      if (!paths.length) {
        this.selectedPath = ''
        this.content = ''
        return
      }
      if (
        !this.preselected &&
        this.initialPath &&
        paths.includes(this.initialPath)
      ) {
        this.selectedPath = this.initialPath
        this.preselected = true
      }
      if (!paths.includes(this.selectedPath)) {
        this.selectedPath = paths[0]
      }
      const entry = this.conflicts.find(item => item.path === this.selectedPath)
      this.content = entry?.content || ''
    },

    select(path) {
      if (!path || path === this.selectedPath) return
      this.selectedPath = path
      this.error = null
      this.notice = null
    },

    errorMessage(ex) {
      return ex?.response?.data?.detail || ex?.message || String(ex)
    },

    /** Reset the editor to the conflict currently stored on disk. */
    resetContent() {
      this.content = this.selected?.content || ''
    },

    /** Resolve the selected file with the given API payload. */
    async runResolve(payload = {}) {
      if (!this.selected || !this.api || this.busy) return
      const path = this.selected.path
      this.busy = true
      this.error = null
      this.notice = null
      try {
        const result = await this.api.repo.resolveConflict({
          path,
          ...payload
        })
        if (result?.success === false) {
          throw new Error((result.errors || []).join('; ') || 'Could not resolve the file')
        }
        this.notice = result?.resolved
          ? `Resolved ${path}`
          : `Resolved ${path} — ${result?.remaining ?? 0} file(s) left`
        await this.load({ silent: true })
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.busy = false
      }
    },

    /** Save the edited content as the merged file. */
    saveResolution() {
      if (!this.selected) return
      if (this.contentHasMarkers) {
        this.error = 'The file still contains conflict markers: remove them before saving'
        return
      }
      return this.runResolve({
        content: this.content,
        strategy: 'manual',
        stage: true
      })
    },

    /** Keep the file edited outside the view and mark it resolved. */
    markResolved() {
      if (!this.selected) return
      if (this.contentDirty) {
        return this.saveResolution()
      }
      return this.runResolve({ strategy: 'stage', stage: true })
    },

    takeSide(side) {
      return this.runResolve({ strategy: side, stage: true })
    },

    /**
     * Resolve with AI. With no paths the backend resolves every conflict; the
     * modal then refreshes and shows the first remaining file.
     */
    async resolveWithAI(paths = null) {
      if (!this.api || this.busy) return
      this.busy = true
      this.error = null
      this.notice = null
      try {
        const result = await this.api.repo.resolveConflictsWithAI({
          paths: paths || null,
          instructions: this.aiInstructions.trim() || undefined,
          apply: true
        })
        const files = result?.files || []
        const applied = files.filter(entry => entry.applied).length
        const failed = files.filter(entry => entry.error)
        if (result?.success && applied) {
          this.notice = applied === 1
            ? `AI resolved ${files[0]?.path || 'the conflict'}`
            : `AI resolved ${applied} conflict(s)`
        } else if (applied) {
          this.notice = `AI resolved ${applied} conflict(s); review the remaining ones`
        } else {
          this.error = (result?.errors || []).join('; ') || 'The AI could not resolve the conflicts'
        }
        if (failed.length) {
          this.error = failed
            .map(entry => `${entry.path}: ${entry.error}`)
            .join('; ')
        }
        await this.load({ silent: true })
        if (result?.continued) {
          this.$emit('finished', { action: 'continue', result })
        }
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.busy = false
      }
    },

    /** Continue the merge/rebase once every conflict is resolved. */
    async continueOperation() {
      if (!this.api || this.busy) return
      this.busy = true
      this.error = null
      this.notice = null
      try {
        const result = await this.api.repo.continueOperation()
        if (result?.conflicted) {
          this.notice = null
          this.error = 'The operation stopped again on another conflict: resolve the new files'
          await this.load({ silent: true })
          return
        }
        if (result?.success === false) {
          throw new Error((result.errors || []).join('; ') || 'Could not continue the operation')
        }
        this.notice = `${this.operationLabel} continued`
        this.$emit('finished', { action: 'continue', result })
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.busy = false
      }
    },

    /** Abort the whole operation after the inline confirmation. */
    async abortOperation() {
      if (!this.api || this.busy) return
      this.busy = true
      this.error = null
      this.notice = null
      try {
        const result = await this.api.repo.abortOperation()
        if (result?.success === false) {
          throw new Error((result.errors || []).join('; ') || 'Could not abort the operation')
        }
        this.$emit('finished', { action: 'abort', result })
      } catch (ex) {
        this.error = this.errorMessage(ex)
      } finally {
        this.busy = false
        this.abortPending = false
      }
    },

    /** Run the squash merge commit from the composer (no operation to continue). */
    commitSquash() {
      this.$emit('finished', { action: 'commit-squash' })
    }
  }
}
</script>

<template>
  <div class="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm px-3 py-3" @click.self="$emit('close')">
    <div class="bg-base-100 border border-base-content/10 rounded-xl w-full max-w-6xl h-[88vh] flex flex-col shadow-2xl overflow-hidden">
      <!-- Header -->
      <div class="flex items-center gap-2 px-4 py-2.5 border-b border-base-content/10 shrink-0">
        <i
          class="fa-solid"
          :class="pendingOnly ? 'fa-code-merge text-warning' : 'fa-triangle-exclamation text-error'"
        ></i>
        <h2 class="text-sm font-semibold">
          {{ pendingOnly ? `${operationLabel} in progress` : `${operationLabel} conflicts` }}
        </h2>
        <span
          class="badge badge-sm"
          :class="pendingOnly ? 'badge-warning' : unresolvedCount ? 'badge-error' : 'badge-success'"
        >{{ progressLabel }}</span>
        <span v-if="state.branch" class="badge badge-sm badge-ghost font-mono max-w-[260px] truncate" :title="state.branch">
          <i class="fa-solid fa-code-branch text-[9px]"></i> {{ state.branch }}
        </span>
        <span
          v-if="pendingOnly && state.source_branch"
          class="badge badge-sm badge-ghost font-mono max-w-[220px] truncate"
          :title="`Source: ${state.source_branch}`"
        >
          <i class="fa-solid fa-arrow-right text-[9px]"></i> {{ state.source_branch }}
        </span>
        <div class="grow"></div>
        <button class="btn btn-xs btn-ghost" :disabled="busy" title="Reload conflict state" @click="load()">
          <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': loading }"></i>
        </button>
        <button class="btn btn-xs btn-ghost" title="Close" aria-label="Close" @click="$emit('close')">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- Feedback -->
      <div v-if="error" class="alert alert-error rounded-none py-1 px-3 text-xs flex items-center gap-2 shrink-0">
        <i class="fa-solid fa-circle-exclamation"></i>
        <span class="grow">{{ error }}</span>
        <button class="btn btn-ghost btn-xs" @click="error = null"><i class="fa-solid fa-xmark"></i></button>
      </div>
      <div v-if="notice" class="alert alert-success rounded-none py-1 px-3 text-xs flex items-center gap-2 shrink-0">
        <i class="fa-solid fa-circle-check"></i>
        <span class="grow">{{ notice }}</span>
        <button class="btn btn-ghost btn-xs" @click="notice = null"><i class="fa-solid fa-xmark"></i></button>
      </div>

      <!-- Body -->
      <div class="grow flex min-h-0">
        <!-- Conflict list -->
        <aside class="w-64 shrink-0 border-r border-base-content/10 flex flex-col overflow-hidden">
          <div class="px-2 py-1.5 border-b border-base-content/10 text-[10px] font-bold uppercase tracking-wide opacity-50 shrink-0">
            Conflicted files
          </div>
          <div class="grow overflow-y-auto">
            <div v-if="loading && !conflicts.length" class="p-3 text-xs opacity-50">Loading...</div>
            <div v-else-if="!conflicts.length" class="p-3 text-xs opacity-50">
              {{ pendingOnly ? 'No conflicted files' : 'No conflicts' }}
            </div>
            <button
              v-for="entry in conflicts"
              :key="entry.path"
              class="w-full text-left px-2 py-1.5 border-b border-base-content/5 hover:bg-base-200/60 transition-colors"
              :class="entry.path === selectedPath ? 'bg-primary/15 text-primary' : ''"
              :title="entry.path"
              @click="select(entry.path)"
            >
              <div class="flex items-center gap-1.5">
                <i class="fa-solid fa-file-circle-exclamation text-error text-[10px] shrink-0"></i>
                <span class="font-mono text-[11px] truncate grow">{{ entry.path.split('/').pop() }}</span>
                <span v-if="entry.marker_count" class="badge badge-xs badge-warning shrink-0">{{ entry.marker_count }}</span>
              </div>
              <div class="text-[10px] opacity-50 truncate pl-4">{{ entry.status_label }}</div>
              <div class="text-[10px] opacity-40 truncate pl-4 font-mono">{{ entry.path }}</div>
            </button>
          </div>
        </aside>

        <!-- Selected conflict editor -->
        <section class="grow min-w-0 flex flex-col overflow-hidden">
          <template v-if="selected">
            <div class="flex items-center gap-2 px-3 py-2 border-b border-base-content/10 shrink-0 flex-wrap">
              <span class="font-mono text-xs font-semibold truncate grow min-w-0" :title="selected.path">{{ selected.path }}</span>
              <span class="badge badge-xs badge-error">{{ selected.status_label }}</span>
              <span class="badge badge-xs badge-ghost">{{ selected.code }}</span>
              <span v-if="selected.marker_count" class="badge badge-xs badge-warning">
                {{ selected.marker_count }} marker(s)
              </span>
              <span v-if="selected.truncated" class="badge badge-xs badge-warning" title="The file is large and was truncated">
                truncated
              </span>
            </div>

            <div class="flex items-center gap-1 px-3 py-1.5 border-b border-base-content/10 shrink-0 flex-wrap">
              <button class="btn btn-xs btn-ghost gap-1" :disabled="busy || !selected.stages?.ours" title="Take our version" @click="takeSide('ours')">
                <i class="fa-solid fa-arrow-left text-[10px]"></i> Ours
              </button>
              <button class="btn btn-xs btn-ghost gap-1" :disabled="busy || !selected.stages?.theirs" title="Take their version" @click="takeSide('theirs')">
                Theirs <i class="fa-solid fa-arrow-right text-[10px]"></i>
              </button>
              <div class="grow"></div>
              <button class="btn btn-xs btn-ghost gap-1" :disabled="busy || selectedIsBinary" title="Reset the editor to the conflict on disk" @click="resetContent">
                <i class="fa-solid fa-rotate-left text-[10px]"></i> Reset
              </button>
              <button class="btn btn-xs btn-ghost gap-1" :disabled="busy" title="Mark the file edited outside the view as resolved" @click="markResolved">
                <i class="fa-solid fa-check text-[10px]"></i> Mark resolved
              </button>
              <button
                class="btn btn-xs btn-primary gap-1"
                :disabled="busy || selectedIsBinary || contentHasMarkers"
                :title="contentHasMarkers ? 'Remove the conflict markers first' : 'Save the merged content and stage it'"
                @click="saveResolution"
              >
                <i class="fa-solid fa-floppy-disk text-[10px]"></i> Save &amp; resolve
              </button>
            </div>

            <div v-if="selected.binary" class="grow flex flex-col items-center justify-center gap-2 text-base-content/50 p-6 text-center">
              <i class="fa-solid fa-file-binary text-3xl"></i>
              <span class="text-xs">Binary conflict: choose <b>Ours</b> or <b>Theirs</b> to resolve it.</span>
            </div>
            <textarea
              v-else
              v-model="content"
              class="grow w-full min-h-0 resize-none border-0 bg-base-200/40 p-3 font-mono text-xs leading-relaxed focus:outline-none"
              spellcheck="false"
              aria-label="Resolved file content"
              @keydown.ctrl.s.prevent="saveResolution"
              @keydown.meta.s.prevent="saveResolution"
            ></textarea>

            <div class="flex items-center gap-2 px-3 py-1 border-t border-base-content/10 text-[10px] shrink-0">
              <span class="opacity-50">{{ (content || '').split('\n').length }} line(s)</span>
              <span v-if="contentDirty" class="badge badge-xs badge-warning">edited</span>
              <span v-if="contentHasMarkers" class="text-error">
                <i class="fa-solid fa-triangle-exclamation"></i> conflict markers still present
              </span>
              <span v-else-if="selected.has_markers" class="text-success">
                <i class="fa-solid fa-circle-check"></i> markers removed
              </span>
              <span class="grow"></span>
              <span v-if="selected.ours_label" class="opacity-50">ours: {{ selected.ours_label }}</span>
              <span v-if="selected.theirs_label" class="opacity-50">theirs: {{ selected.theirs_label }}</span>
            </div>
          </template>

          <!-- No conflicted files: either a clean pending operation or all
               conflicts already resolved. -->
          <div v-else class="grow flex flex-col items-center justify-center gap-3 text-center p-8">
            <i
              class="fa-solid text-4xl"
              :class="pendingOnly ? 'fa-code-merge text-warning' : 'fa-circle-check text-success'"
            ></i>
            <div class="text-sm font-semibold">
              {{ pendingOnly ? `${operationLabel} in progress` : 'All conflicts resolved' }}
            </div>
            <p class="text-xs opacity-60 max-w-md">
              {{ pendingOnly ? operationHint : `Continue the ${operationLabel.toLowerCase()} to finish it, or commit the staged result from the composer.` }}
            </p>
            <div v-if="pendingOnly && state.merge_message" class="text-[11px] opacity-60 max-w-md font-mono whitespace-pre-wrap break-words">
              {{ state.merge_message }}
            </div>
          </div>
        </section>
      </div>

      <!-- AI options -->
      <div v-if="conflicts.length" class="border-t border-base-content/10 px-3 py-2 shrink-0">
        <button class="btn btn-xs btn-ghost gap-1" @click="showAIOptions = !showAIOptions">
          <i class="fa-solid fa-wand-magic-sparkles text-[10px]"></i>
          Resolve with AI
          <i class="fa-solid text-[9px]" :class="showAIOptions ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
        </button>
        <div v-if="showAIOptions" class="mt-2 flex flex-col gap-2">
          <input
            v-model="aiInstructions"
            type="text"
            class="input input-xs input-bordered w-full"
            placeholder="Optional guidance (e.g. keep both logging calls, prefer the feature branch)"
          />
          <div class="flex items-center gap-2 flex-wrap">
            <button class="btn btn-xs btn-info gap-1" :disabled="busy || !selected" @click="resolveWithAI([selected?.path])">
              <i class="fa-solid fa-spinner animate-spin" v-if="busy"></i>
              <i class="fa-solid fa-wand-magic-sparkles" v-else></i>
              Resolve selected
            </button>
            <button class="btn btn-xs btn-info gap-1" :disabled="busy || !conflicts.length" @click="resolveWithAI(null)">
              <i class="fa-solid fa-spinner animate-spin" v-if="busy"></i>
              <i class="fa-solid fa-layer-group" v-else></i>
              Resolve all ({{ conflicts.length }})
            </button>
            <span class="text-[10px] opacity-50">
              The AI writes the merged file and stages it; answers with conflict markers are rejected.
            </span>
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex items-center gap-2 px-4 py-2.5 border-t border-base-content/10 shrink-0">
        <template v-if="abortPending">
          <span class="text-xs text-error grow">
            <i class="fa-solid fa-triangle-exclamation"></i>
            Abort the {{ operationLabel.toLowerCase() }} and discard the resolutions already made?
          </span>
          <button class="btn btn-xs btn-ghost" :disabled="busy" @click="abortPending = false">Cancel</button>
          <button class="btn btn-xs btn-error" :disabled="busy" @click="abortOperation">
            <i class="fa-solid fa-spinner animate-spin" v-if="busy"></i>
            <i class="fa-solid fa-xmark" v-else></i>
            Abort
          </button>
        </template>
        <template v-else>
          <button class="btn btn-xs btn-ghost gap-1 text-error" :disabled="busy" @click="abortPending = true">
            <i class="fa-solid fa-ban text-[10px]"></i> Abort {{ operationLabel.toLowerCase() }}
          </button>
          <div class="grow"></div>
          <span
            v-if="state.stash_kept"
            class="text-[10px] text-warning"
            :title="state.stash_message || 'Local changes were stashed before the operation'"
          >
            <i class="fa-solid fa-box-archive"></i> local changes in stash
          </span>
          <button
            v-if="canContinue"
            class="btn btn-xs btn-success gap-1"
            :disabled="busy"
            @click="continueOperation"
          >
            <i class="fa-solid fa-spinner animate-spin" v-if="busy"></i>
            <i class="fa-solid fa-forward" v-else></i>
            Continue {{ operationLabel.toLowerCase() }}
          </button>
          <button
            v-else-if="canCommitSquash"
            class="btn btn-xs btn-success gap-1"
            :disabled="busy"
            @click="commitSquash"
          >
            <i class="fa-solid fa-check"></i> Commit squash merge
          </button>
          <button
            v-else-if="allResolved"
            class="btn btn-xs btn-success gap-1"
            :disabled="busy"
            @click="$emit('finished', { action: 'resolved' })"
          >
            <i class="fa-solid fa-check"></i> Done
          </button>
          <span v-else-if="conflicts.length" class="text-[11px] opacity-50">
            Resolve every file to continue the {{ operationLabel.toLowerCase() }}
          </span>
          <span v-else-if="pendingOnly" class="text-[11px] opacity-50">
            {{ operationHint }}
          </span>
        </template>
      </div>
    </div>
  </div>
</template>
