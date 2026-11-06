<script>
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
import MarkdownViewer from '@/components/MarkdownViewer.vue'

/**
 * Validator: AI review of project changes.
 *
 * The section loads the change set + the profiles associated with the changed
 * files (backend `validate/context`) and sends the selection to the project LLM
 * (`validate`). Local uncommitted changes are the default; a branch comparison
 * is available too.
 *
 * The left panel keeps the review configuration (source, branches, files and
 * profiles) visible while the right panel shows the generated report. Both
 * panels live in a resizable vertical split.
 */
export default {
  name: 'GitValidator',
  components: { VerticalSplitter, MarkdownViewer },
  props: {
    project: { type: Object, default: null },
    api: { type: Object, default: null },
    branches: { type: Array, default: () => [] },
    currentBranch: { type: String, default: '' },
    // The section only loads its (expensive) working tree context when visible
    active: { type: Boolean, default: false }
  },
  data() {
    return {
      // Change source: uncommitted local changes or two refs
      source: 'local',
      fromBranch: '',
      toBranch: '',
      // Validator context
      loadingContext: false,
      contextError: null,
      files: [],
      stat: '',
      baseBranch: '',
      profiles: [],
      defaultProfiles: [],
      defaultProfilesSource: '',
      // Selection
      selectedProfiles: [],
      profileFilter: '',
      fileFilter: '',
      instructions: '',
      // Review
      reviewing: false,
      review: '',
      reviewProfiles: [],
      reviewError: null,
      reviewNotice: null,
      diffTruncated: false,
      // Resizable vertical split (left = config, right = report)
      splitterConfig: {
        left: { minSize: 22, defaultSize: 34, collapsible: true },
        right: { minSize: 35, defaultSize: 66, collapsible: true }
      }
    }
  },
  computed: {
    availableBranches() {
      return (this.branches || []).filter(branch => branch && branch !== 'local')
    },
    filteredProfiles() {
      const filter = this.profileFilter.trim().toLowerCase()
      if (!filter) return this.profiles
      return this.profiles.filter(profile =>
        (profile.name || '').toLowerCase().includes(filter) ||
        (profile.description || '').toLowerCase().includes(filter) ||
        (profile.category || '').toLowerCase().includes(filter)
      )
    },
    filteredFiles() {
      const filter = this.fileFilter.trim().toLowerCase()
      if (!filter) return this.files
      return this.files.filter(file => (file.path || '').toLowerCase().includes(filter))
    },
    fileCount() {
      return this.files.length
    },
    selectedProfileCount() {
      return this.selectedProfiles.length
    },
    defaultsLabel() {
      if (this.defaultProfilesSource === 'files') return 'matched the changed files'
      if (this.defaultProfilesSource === 'validator') return 'validator fallback'
      return 'no matching profile'
    },
    sourceLabel() {
      if (this.source === 'branch') {
        return `${this.fromBranch || 'source'} → ${this.toBranch || 'target'}`
      }
      return `local vs ${this.fromBranch || this.baseBranch || 'current branch'}`
    },
    canValidate() {
      return !!this.api && this.fileCount > 0 && !this.reviewing && !this.loadingContext
    }
  },
  watch: {
    active(active) {
      if (!active) return
      const resetSelection = !!this._pendingResetSelection
      this._pendingResetSelection = false
      this.refresh(resetSelection)
    },
    branches() {
      this.initBranchesFromProps()
    },
    currentBranch(branch) {
      if (this.source !== 'local' || !branch) return
      if (this.fromBranch && this.fromBranch !== 'HEAD' && this.fromBranch !== branch) return
      this.fromBranch = branch
    },
    fromBranch() {
      if (this._skipContextWatch) return
      this.invalidateReview()
      this.scheduleLoadContext({ resetSelection: false })
    },
    toBranch() {
      if (this._skipContextWatch) return
      this.invalidateReview()
      this.scheduleLoadContext({ resetSelection: false })
    },
    source() {
      this.invalidateReview()
      this.scheduleLoadContext({ resetSelection: true })
    }
  },
  created() {
    this._skipContextWatch = true
    this._pendingResetSelection = false
    this.initBranchesFromProps()
    // The context is loaded when the section becomes visible (`active`), so
    // mounting the git view never runs a second working tree scan for a tab
    // nobody opened.
    this.$nextTick(() => {
      this._skipContextWatch = false
    })
  },
  beforeUnmount() {
    clearTimeout(this._contextTimer)
    this._contextTimer = null
  },
  methods: {
    /** True when the profile was inferred from the changed files */
    isDefaultProfile(name) {
      return this.defaultProfiles.includes(name)
    },

    /** Initialize the branch selects once the parent projects are loaded */
    initBranchesFromProps() {
      const branches = this.availableBranches
      if (!this.fromBranch || this.fromBranch === 'HEAD' || !branches.includes(this.fromBranch)) {
        this.fromBranch = this.currentBranch && branches.includes(this.currentBranch)
          ? this.currentBranch
          : (branches[0] || 'HEAD')
      }
      if (!this.toBranch || !branches.includes(this.toBranch) || this.toBranch === this.fromBranch) {
        this.toBranch = branches.find(branch => branch !== this.fromBranch) || ''
      }
    },

    /** Debounce the watcher-driven context loads (source + branch changes) */
    scheduleLoadContext({ resetSelection = false } = {}) {
      if (!this.active) {
        this._pendingResetSelection = this._pendingResetSelection || resetSelection
        return
      }
      clearTimeout(this._contextTimer)
      this._contextTimer = setTimeout(() => {
        this._contextTimer = null
        this.loadContext({ resetSelection })
      }, 80)
    },

    /** Load the files and profiles for the selected source */
    async loadContext({ resetSelection = false } = {}) {
      if (!this.api) return
      const token = (this._contextToken || 0) + 1
      this._contextToken = token
      this.loadingContext = true
      this.contextError = null
      try {
        const context = await this.api.repo.validateContext({
          source: this.source,
          from_branch: this.fromBranch,
          to_branch: this.source === 'branch' ? this.toBranch : 'local'
        })
        // Ignore a response for a branch/source the user already changed
        if (token !== this._contextToken) return
        this.files = context.files || []
        this.stat = context.stat || ''
        this.baseBranch = context.base_branch || ''
        this.profiles = context.profiles || []
        this.defaultProfiles = context.default_profiles || []
        this.defaultProfilesSource = context.default_profiles_source || ''

        const known = new Set(this.profiles.map(profile => profile.name))
        let selection = (this.selectedProfiles || []).filter(name => known.has(name))
        if (resetSelection || !selection.length) {
          selection = this.defaultProfiles.filter(name => known.has(name))
        }
        this.selectedProfiles = selection
      } catch (ex) {
        if (token !== this._contextToken) return
        this.files = []
        this.profiles = []
        this.defaultProfiles = []
        this.contextError = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        if (token === this._contextToken) this.loadingContext = false
      }
    },

    /** Public refresh used by GitView when files change on disk / tab opens */
    refresh(resetSelection = false) {
      clearTimeout(this._contextTimer)
      this._contextTimer = null
      this._pendingResetSelection = false
      return this.loadContext({ resetSelection })
    },

    /** Clear the report when the reviewed change set changes */
    invalidateReview() {
      if (this.review || this.reviewError) {
        this.review = ''
        this.reviewError = null
        this.reviewNotice = null
        this.reviewProfiles = []
        this.diffTruncated = false
      }
    },

    setSource(source) {
      if (this.source === source) return
      if (source === 'branch') {
        const list = this.availableBranches
        if (!list.includes(this.fromBranch)) {
          this.fromBranch = this.currentBranch && list.includes(this.currentBranch)
            ? this.currentBranch
            : (list[0] || '')
        }
        if (!list.includes(this.toBranch) || this.toBranch === this.fromBranch) {
          this.toBranch = list.find(branch => branch !== this.fromBranch) || this.fromBranch
        }
      }
      // Set the source last: its watcher resets the profile selection.
      this.source = source
    },

    selectDefaults() {
      const known = new Set(this.profiles.map(profile => profile.name))
      this.selectedProfiles = this.defaultProfiles.filter(name => known.has(name))
    },

    selectAllProfiles() {
      this.selectedProfiles = this.profiles.map(profile => profile.name)
    },

    clearProfiles() {
      this.selectedProfiles = []
    },

    clearFileFilter() {
      this.fileFilter = ''
    },

    /** Ask the backend to review the selected changes with the AI */
    async runValidation() {
      if (!this.api || this.reviewing) return
      this.reviewing = true
      this.reviewError = null
      this.reviewNotice = null
      this.review = ''
      try {
        const result = await this.api.repo.validate({
          profiles: this.selectedProfiles,
          source: this.source,
          from_branch: this.fromBranch,
          to_branch: this.source === 'branch' ? this.toBranch : 'local',
          instructions: this.instructions.trim() || undefined
        })
        this.review = result.review || ''
        this.reviewProfiles = result.profiles || []
        this.diffTruncated = !!result.diff_truncated
        const warnings = (result.errors || []).filter(Boolean)
        this.reviewNotice = `Reviewed ${result.file_count || this.fileCount} file(s) with ${this.reviewProfiles.length} profile(s)`
        if (warnings.length) this.reviewNotice += ` · ${warnings.join('; ')}`
      } catch (ex) {
        this.reviewError = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.reviewing = false
      }
    },

    statusClass(file) {
      if (file.code === '?' || file.code === 'A') return 'badge-success'
      if (file.code === 'D') return 'badge-error'
      if (file.code === 'R') return 'badge-info'
      return 'badge-warning'
    }
  }
}
</script>

<template>
  <div class="validator-view h-full w-full flex flex-col bg-base-100 overflow-hidden">
    <!-- ── Toolbar ──────────────────────────────────────────────────────── -->
    <header class="flex items-center gap-2 px-3 py-1.5 bg-base-200 border-b border-base-content/10 shrink-0 flex-wrap">
      <i class="fa-solid fa-shield-halved text-warning"></i>
      <span class="text-sm font-bold">Validator</span>
      <span class="badge badge-xs badge-ghost">{{ sourceLabel }}</span>
      <span class="badge badge-xs" :class="fileCount ? 'badge-info badge-outline' : 'badge-ghost'">
        {{ fileCount }} file(s)
      </span>

      <div class="grow"></div>

      <div class="join">
        <button
          class="join-item btn btn-xs"
          :class="source === 'local' ? 'btn-primary' : 'btn-ghost'"
          title="Review uncommitted local changes"
          @click="setSource('local')"
        >
          <i class="fa-solid fa-laptop-file"></i> Local changes
        </button>
        <button
          class="join-item btn btn-xs"
          :class="source === 'branch' ? 'btn-primary' : 'btn-ghost'"
          title="Review two branches or refs"
          @click="setSource('branch')"
        >
          <i class="fa-solid fa-code-compare"></i> Branch compare
        </button>
      </div>

      <button class="btn btn-xs btn-ghost" :disabled="loadingContext" @click="refresh" title="Reload changes and profiles">
        <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': loadingContext }"></i>
      </button>
    </header>

    <!-- ── Split: configuration (left) + AI report (right) ─────────────── -->
    <VerticalSplitter
      class="grow min-h-0"
      :panels="splitterConfig"
      persist-key="git-view-validator"
      show-handle
    >
      <template #left>
        <div class="h-full flex flex-col overflow-hidden">
          <div class="grow overflow-y-auto p-2 flex flex-col gap-3">
            <!-- Branch pair -->
            <section class="flex flex-col gap-1">
              <label class="text-[10px] uppercase tracking-wide font-bold opacity-50">
                {{ source === 'local' ? 'Compare local changes against' : 'Source branch' }}
              </label>
              <select v-model="fromBranch" class="select select-xs select-bordered w-full font-mono">
                <option v-for="branch in availableBranches" :key="`v-from-${branch}`" :value="branch">{{ branch }}</option>
                <option v-if="!availableBranches.length" value="HEAD">HEAD</option>
              </select>

              <template v-if="source === 'branch'">
                <label class="text-[10px] uppercase tracking-wide font-bold opacity-50 mt-1">Target branch</label>
                <select v-model="toBranch" class="select select-xs select-bordered w-full font-mono">
                  <option v-for="branch in availableBranches" :key="`v-to-${branch}`" :value="branch">{{ branch }}</option>
                </select>
              </template>
            </section>

            <!-- Context error -->
            <div v-if="contextError" class="alert alert-error py-1 px-2 text-[11px] rounded">
              <i class="fa-solid fa-triangle-exclamation"></i>
              <span class="break-words">{{ contextError }}</span>
            </div>

            <!-- Changed files -->
            <section class="flex flex-col gap-1">
              <div class="flex items-center gap-1">
                <span class="text-[10px] uppercase tracking-wide font-bold opacity-50 grow">
                  Files to validate
                </span>
                <span class="badge badge-xs badge-ghost">{{ fileCount }}</span>
              </div>

              <div class="relative">
                <i class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-[10px] opacity-40"></i>
                <input
                  v-model="fileFilter"
                  type="text"
                  class="input input-xs input-bordered w-full pl-6 pr-6"
                  placeholder="Filter files..."
                  aria-label="Filter files to validate"
                />
                <button
                  v-if="fileFilter"
                  class="btn btn-xs btn-ghost btn-square absolute right-0 top-1/2 -translate-y-1/2"
                  @click="clearFileFilter"
                  aria-label="Clear file filter"
                >
                  <i class="fa-solid fa-xmark text-[10px]"></i>
                </button>
              </div>

              <div class="max-h-52 overflow-y-auto rounded border border-base-content/10">
                <div v-if="loadingContext" class="p-3 text-xs opacity-50 flex items-center gap-2">
                  <i class="fa-solid fa-spinner animate-spin"></i> Loading changes...
                </div>
                <div v-else-if="!filteredFiles.length" class="p-3 text-xs opacity-50">
                  {{ fileCount ? 'No file matches the filter' : 'No changes to validate' }}
                </div>
                <div
                  v-for="file in filteredFiles"
                  :key="`validator-${file.path}`"
                  class="flex items-center gap-1.5 px-2 py-1 text-[11px] border-b border-base-content/5 last:border-b-0"
                  :title="file.path"
                >
                  <span class="badge badge-xs shrink-0" :class="statusClass(file)">{{ file.code }}</span>
                  <span class="font-mono truncate grow">{{ file.path }}</span>
                  <span class="text-success shrink-0" v-if="file.additions">+{{ file.additions }}</span>
                  <span class="text-error shrink-0" v-if="file.deletions">-{{ file.deletions }}</span>
                  <span v-if="file.staged" class="badge badge-xs badge-ghost shrink-0">staged</span>
                </div>
              </div>
              <p v-if="stat" class="text-[10px] opacity-50">{{ stat }}</p>
            </section>

            <!-- Profiles -->
            <section class="flex flex-col gap-1">
              <div class="flex items-center gap-1">
                <span class="text-[10px] uppercase tracking-wide font-bold opacity-50 grow">
                  Review profiles
                </span>
                <span class="badge badge-xs badge-ghost">{{ selectedProfileCount }}/{{ profiles.length }}</span>
              </div>
              <p class="text-[10px] opacity-50">
                Defaults {{ defaultsLabel }}.
                <span v-if="defaultProfiles.length" class="font-mono">{{ defaultProfiles.join(', ') }}</span>
              </p>

              <input
                v-if="profiles.length > 6"
                v-model="profileFilter"
                type="text"
                class="input input-xs input-bordered w-full"
                placeholder="Filter profiles..."
                aria-label="Filter profiles"
              />

              <div class="max-h-56 overflow-y-auto rounded border border-base-content/10">
                <div v-if="!profiles.length" class="p-3 text-xs opacity-50">No profiles available</div>
                <label
                  v-for="profile in filteredProfiles"
                  :key="`validator-profile-${profile.name}`"
                  class="flex items-start gap-1.5 px-2 py-1 cursor-pointer hover:bg-base-200/60 border-b border-base-content/5 last:border-b-0"
                >
                  <input
                    v-model="selectedProfiles"
                    type="checkbox"
                    :value="profile.name"
                    class="checkbox checkbox-xs mt-0.5 shrink-0"
                  />
                  <div class="grow min-w-0">
                    <div class="flex items-center gap-1">
                      <span class="text-[11px] font-semibold truncate">{{ profile.name }}</span>
                      <span v-if="isDefaultProfile(profile.name)" class="badge badge-xs badge-primary badge-outline">default</span>
                      <span v-if="profile.category" class="badge badge-xs badge-ghost">{{ profile.category }}</span>
                    </div>
                    <p v-if="profile.description" class="text-[10px] opacity-50 truncate" :title="profile.description">
                      {{ profile.description }}
                    </p>
                  </div>
                </label>
              </div>

              <div class="flex items-center gap-1">
                <button class="btn btn-xs btn-ghost" :disabled="!defaultProfiles.length" @click="selectDefaults" title="Select the profiles matched from the changed files">
                  Defaults
                </button>
                <button class="btn btn-xs btn-ghost" @click="selectAllProfiles">All</button>
                <button class="btn btn-xs btn-ghost" @click="clearProfiles">None</button>
              </div>
            </section>

            <!-- Extra instructions -->
            <section class="flex flex-col gap-1">
              <label class="text-[10px] uppercase tracking-wide font-bold opacity-50" for="validator-instructions">
                Extra instructions (optional)
              </label>
              <textarea
                id="validator-instructions"
                v-model="instructions"
                rows="2"
                class="textarea textarea-xs textarea-bordered w-full resize-y"
                placeholder="Focus on security, missing tests..."
              ></textarea>
            </section>
          </div>

          <div class="p-2 border-t border-base-content/10 shrink-0">
            <button
              class="btn btn-sm btn-primary w-full gap-1"
              :disabled="!canValidate"
              @click="runValidation"
            >
              <i class="fa-solid fa-spinner animate-spin" v-if="reviewing"></i>
              <i class="fa-solid fa-shield-halved" v-else></i>
              Validate changes
            </button>
          </div>
        </div>
      </template>

      <template #right>
        <div class="h-full flex flex-col overflow-hidden min-w-0">
          <div class="flex items-center gap-2 px-3 py-1.5 border-b border-base-content/10 shrink-0 flex-wrap">
            <i class="fa-solid fa-wand-magic-sparkles text-warning"></i>
            <span class="text-xs font-bold uppercase tracking-wide opacity-60">AI review</span>
            <span v-if="reviewProfiles.length" class="badge badge-xs badge-primary badge-outline">
              {{ reviewProfiles.join(', ') }}
            </span>
            <span v-if="diffTruncated" class="badge badge-xs badge-warning badge-outline" title="The patch was truncated before sending it to the AI">
              diff truncated
            </span>
            <div class="grow"></div>
            <span v-if="reviewNotice" class="text-[10px] opacity-50">{{ reviewNotice }}</span>
          </div>

          <div v-if="reviewError" class="alert alert-error m-2 py-1 px-2 text-xs">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span class="break-words">{{ reviewError }}</span>
          </div>

          <div v-if="reviewing" class="grow flex flex-col items-center justify-center gap-2 text-base-content/50">
            <i class="fa-solid fa-spinner animate-spin text-2xl"></i>
            <span class="text-xs">The AI is reviewing the changes...</span>
          </div>

          <MarkdownViewer
            v-else-if="review"
            :text="review"
            class="grow min-h-0 overflow-y-auto p-3"
          />

          <div v-else class="grow flex flex-col items-center justify-center gap-2 p-6 text-center text-base-content/40">
            <i class="fa-solid fa-shield-halved text-4xl"></i>
            <span class="text-sm">Select the profiles and validate the changes</span>
            <span class="text-[11px] opacity-70">
              The AI reviews the diff and reports findings per file. Nothing is committed.
            </span>
          </div>
        </div>
      </template>
    </VerticalSplitter>
  </div>
</template>
