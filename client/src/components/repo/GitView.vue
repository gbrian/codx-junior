<script>
import ChangesPanel from '@/components/vibe/panels/ChangesPanel.vue'
import RepoFileDiff from '@/components/repo/RepoFileDiff.vue'
import RepoBranchList from '@/components/repo/RepoBranchList.vue'
import GitGraph from '@/components/repo/GitGraph.vue'
import CommitDetail from '@/components/repo/CommitDetail.vue'
import GitValidator from '@/components/repo/GitValidator.vue'
import GitConflictResolver from '@/components/repo/GitConflictResolver.vue'
import GitContextMenu from '@/components/repo/GitContextMenu.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
import { contextMenuMixin } from '@/mixins/contextMenu'
import { onFileEvent } from '@/utils/fileEvents'

// 50/72 rule: maximum subject length and maximum body line width
const COMMIT_SUBJECT_LIMIT = 50
const COMMIT_BODY_LIMIT = 72
// File events are coalesced: a burst of writes reloads the view only once
const FILE_EVENT_REFRESH_DELAY = 600

export default {
  name: 'GitView',
  components: { ChangesPanel, RepoFileDiff, RepoBranchList, GitGraph, CommitDetail, GitValidator, GitConflictResolver, GitContextMenu, ConfirmDialog, VerticalSplitter },
  mixins: [contextMenuMixin],
  props: {
    params: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      activeTab: 'repository',
      loading: false,
      busy: false,
      error: null,
      notice: null,
      // repository state
      info: {},
      branches: [],
      repoTree: [],
      // Registered worktrees with the changes inside each checkout
      worktrees: [],
      // Worktree expansion, keyed by worktree path (undefined = expanded)
      expandedWorktrees: {},
      // .gitignore editor
      showGitignore: false,
      gitignoreLoading: false,
      gitignoreSaving: false,
      gitignorePath: '',
      gitignoreContent: '',
      gitignoreExists: false,
      gitignoreError: null,
      gitignoreNotice: null,
      selectedBranch: null,
      branchFilter: '',
      collapsedSections: {},
      // graph
      selectedCommit: null,
      // Bumped after every git operation so the graph reloads its commits
      graphRefreshToken: 0,
      // Unsubscribe function of the file event bus (refreshes on disk activity)
      fileEventsOff: null,
      // Pending debounced refresh triggered by a file event
      fileEventRefreshTimer: null,
      // working tree
      selection: {},
      // Anchor for shift+click range selection: { group, path }
      selectionAnchor: null,
      selectedFile: null,
      // Working tree presentation: flat list or folder tree, plus a filter
      treeView: true,
      fileFilter: '',
      // Folder expansion in the tree view, keyed by `group:folderPath`.
      // Undefined means expanded: the tree opens fully by default.
      expandedFolders: {},
      // create branch (modal, shared by the sidebar and the headers)
      showNewBranch: false,
      newBranchName: '',
      newBranchFrom: '',
      newBranchCheckout: false,
      // commit
      commitMessage: '',
      committing: false,
      generatingMessage: false,
      // merge
      showMerge: false,
      mergeFrom: '',
      mergeTo: '',
      mergeMessage: '',
      // Merge modes: collapse the source commits into one and/or leave the
      // result staged so it can be reviewed and committed from the composer.
      mergeSquash: false,
      mergeNoCommit: false,
      // Remove the source branch worktree once the merge succeeded
      mergeDeleteWorktree: false,
      mergePreview: null,
      mergePreviewLoading: false,
      merging: false,
      // Conflicts: pending merge/rebase state and the resolver modal
      conflictState: null,
      showConflicts: false,
      // File to preselect when the resolver opens (from a conflict file row)
      conflictPreselect: '',
      // Pending confirmation: { title, message, details, hint, icon, iconClass,
      // confirmLabel, confirmIcon, confirmClass, resolve }
      confirmRequest: null,
      // Working tree / diff split. The diff is the right panel so the file list
      // stays visible (and usable) while a file is being reviewed or edited.
      splitterConfig: {
        left: { minSize: 20, defaultSize: 28, collapsible: true },
        right: { minSize: 30, defaultSize: 72, collapsible: true }
      },
      // Graph / commit detail split. Resizable like the working tree split.
      graphSplitterConfig: {
        left: { minSize: 35, defaultSize: 58, collapsible: true },
        right: { minSize: 25, defaultSize: 42, collapsible: true }
      },
      // Branch sidebar + working tree split
      branchesSplitterConfig: {
        left: { minSize: 10, defaultSize: 15, collapsible: true },
        right: { minSize: 40, defaultSize: 85, collapsible: true }
      }
    }
  },
  computed: {
    /** Project the git view works with: explicit panel param, else active project */
    project() {
      return this.params?.project || this.$storex.projects.activeProject || null
    },
    projectName() {
      return this.project?.project_name || 'No project'
    },
    projectPath() {
      return this.project?.abs_project_path || this.project?.codx_path || ''
    },
    /** Absolute on-disk path of the project, used to match file events */
    projectRoot() {
      return this.project?.abs_project_path || ''
    },
    /**
     * The active project is a git worktree (not the main checkout).
     *
     * Worktrees are registered as separate projects with the same display name,
     * so the header must say which checkout the branch belongs to.
     */
    isWorktreeCheckout() {
      const projectPath = this.info?.project_path || this.projectPath
      const repoPath = this.info?.repo_path || ''
      return !!projectPath && !!repoPath && projectPath !== repoPath
    },
    api() {
      return this.project?.$api || null
    },
    isGit() {
      return !!(this.info?.active_branch || this.branches.length)
    },
    currentBranch() {
      return this.info?.active_branch || this.branches[0] || null
    },
    /** Repository is locked by a stale .git/index.lock */
    locked() {
      return !!this.info?.locked
    },
    lockPath() {
      return this.info?.lock_path || ''
    },
    /** Conflict state reported by the backend (info and resolver share it) */
    conflicts() {
      return this.conflictState || this.info?.conflict_state || null
    },
    /** The repository has real unmerged files (not just a pending operation) */
    hasConflicts() {
      if (this.conflicts?.has_conflicts || this.info?.has_conflicts) return true
      if (this.conflictCount > 0) return true
      return this.statusFiles.staged.some(file => file.code === 'U')
        || this.statusFiles.unstaged.some(file => file.code === 'U')
    },
    /** A merge/rebase/cherry-pick/revert is in progress, conflicts or not */
    hasPendingOperation() {
      return !!this.conflicts?.in_progress || !!this.info?.operation_in_progress
    },
    conflictCount() {
      return this.conflicts?.unresolved_count ?? this.conflicts?.conflict_count ?? 0
    },
    conflictOperationLabel() {
      return this.conflicts?.operation_label || 'Git'
    },
    conflictOperation() {
      return this.conflicts?.operation || ''
    },
    /** Whether the pending merge/rebase can be finished from the composer */
    pendingOperationCanCommit() {
      return this.hasPendingOperation && this.conflictOperation === 'merge'
    },
    filteredBranches() {
      const filter = this.branchFilter.trim().toLowerCase()
      if (!filter) return this.branches
      return this.branches.filter(b => b.toLowerCase().includes(filter))
    },
    /** Commit counts shown next to each branch in the shared branch list */
    branchCounts() {
      return Object.fromEntries(
        this.branches.map(branch => [branch, this.branchCommitCount(branch)])
      )
    },
    /** Working tree files split into staged / not staged */
    statusFiles() {
      const info = this.info || {}

      // Preferred source: structured lists from the API
      if (Array.isArray(info.staged) || Array.isArray(info.unstaged)) {
        return {
          staged: (info.staged || [])
            .map(file => this.buildStatusFile(this.codeFor(file), file.path || file.file_name))
            .filter(Boolean),
          unstaged: (info.unstaged || [])
            .map(file => this.buildStatusFile(this.codeFor(file), file.path || file.file_name))
            .filter(Boolean)
        }
      }

      // Fallback: derive both lists from `git status --porcelain` lines
      const staged = []
      const unstaged = []
      const lines = info.changed_files || []
      lines.forEach(line => {
        const parsed = this.parsePorcelainLine(line)
        if (!parsed) return
        if (parsed.index === '?' && parsed.worktree === '?') {
          const file = this.buildStatusFile('?', parsed.path)
          if (file) unstaged.push(file)
          return
        }
        if (parsed.index !== ' ') {
          const file = this.buildStatusFile(parsed.index, parsed.path)
          if (file) staged.push(file)
        }
        if (parsed.worktree !== ' ' && parsed.worktree !== '?') {
          const file = this.buildStatusFile(parsed.worktree, parsed.path)
          if (file) unstaged.push(file)
        }
      })
      return { staged, unstaged }
    },
    stagedFiles() {
      return this.statusFiles.staged
    },
    unstagedFiles() {
      return this.statusFiles.unstaged
    },
    workingTreeCount() {
      return this.stagedFiles.length + this.unstagedFiles.length
    },
    /** Whether the working tree filter has any term */
    hasFileFilter() {
      return !!this.fileFilter.trim()
    },
    filteredStagedFiles() {
      return this.stagedFiles.filter(file => this.matchesFileFilter(file))
    },
    filteredUnstagedFiles() {
      return this.unstagedFiles.filter(file => this.matchesFileFilter(file))
    },
    filteredWorkingTreeCount() {
      return this.filteredStagedFiles.length + this.filteredUnstagedFiles.length
    },
    workingTreeGroups() {
      return [
        {
          key: 'staged',
          label: 'Staged',
          empty: 'No staged changes',
          files: this.filteredStagedFiles,
          total: this.stagedFiles.length
        },
        {
          key: 'changes',
          label: 'Changes',
          empty: 'No unstaged changes',
          files: this.filteredUnstagedFiles,
          total: this.unstagedFiles.length
        }
      ]
    },
    /** With a filter active, empty groups are hidden */
    visibleWorkingTreeGroups() {
      if (!this.hasFileFilter) return this.workingTreeGroups
      return this.workingTreeGroups.filter(group => group.files.length > 0)
    },
    /**
     * Worktrees with their changed files in one list.
     *
     * The backend reads `git status` inside every worktree, so each entry knows
     * exactly which files changed in that checkout. Staged and unstaged entries
     * of the same path are merged into one row (with both flags).
     */
    worktreeList() {
      // The main checkout is the working tree shown above: list only the
      // additional worktrees so its files are not rendered twice. `repo_path`
      // is the real git root, so the main checkout is also filtered when the
      // API could not flag it (`is_main`) or the project points at a subfolder.
      const repoPath = this.info?.repo_path || ''
      return (this.worktrees || [])
        .filter(worktree => {
          if (worktree.is_main) return false
          return !(repoPath && this.samePath(worktree.path, repoPath))
        })
        .map(worktree => {
          const changes = worktree.changes || {}
          const byPath = new Map()

          const add = (entry, staged) => {
            const file = this.buildStatusFile(
              this.codeFor(entry),
              entry.path || entry.file_name
            )
            if (!file) return
            const current = byPath.get(file.path)
            if (current) {
              current.staged = current.staged || staged
              current.unstaged = current.unstaged || !staged
              return
            }
            byPath.set(file.path, {
              ...file,
              staged,
              unstaged: !staged
            })
          }

          ;(changes.staged || []).forEach(entry => add(entry, true))
          ;(changes.unstaged || []).forEach(entry => add(entry, false))

          const files = Array.from(byPath.values())
          return {
            ...worktree,
            files,
            changeCount: files.length,
            label: worktree.branch || (worktree.detached ? 'detached HEAD' : 'worktree')
          }
        })
    },
    noFilterMatches() {
      return this.hasFileFilter && this.filteredWorkingTreeCount === 0
    },
    stagedSelection() {
      return this.selectedPaths('staged')
    },
    changesSelection() {
      return this.selectedPaths('changes')
    },
    selectionCount() {
      return this.stagedSelection.length + this.changesSelection.length
    },
    commitHint() {
      if (this.hasConflicts) {
        return `Resolve ${this.conflictCount || 'the'} conflict(s) before committing`
      }
      if (this.hasPendingOperation) {
        if (this.pendingOperationCanCommit) {
          return `${this.conflictOperationLabel} in progress: commit to finish it`
        }
        return `${this.conflictOperationLabel} in progress: continue it from the operation panel`
      }
      if (this.stagedFiles.length) {
        return `${this.stagedFiles.length} staged file(s) will be committed`
      }
      if (this.unstagedFiles.length) {
        return 'Nothing staged: every change will be staged and committed'
      }
      return 'No changes to commit'
    },
    canCommit() {
      if (!this.commitMessage.trim() || this.workingTreeCount <= 0) return false
      if (this.hasConflicts) return false
      if (this.hasPendingOperation && !this.pendingOperationCanCommit) return false
      return true
    },
    /** Length of the commit subject (first line of the message) */
    subjectLength() {
      return (this.commitMessage.split('\n')[0] || '').trim().length
    },
    /** Subject exceeds the 50 characters of the 50/72 rule */
    subjectTooLong() {
      return this.subjectLength > COMMIT_SUBJECT_LIMIT
    },
    /**
     * Feedback for the message being written: the 50/72 counters once there is
     * a subject, otherwise the working tree hint.
     */
    messageHint() {
      const lines = this.commitMessage.split('\n')
      const subject = (lines[0] || '').trim()
      if (!subject) return this.commitHint

      const body = lines.slice(1).map(line => line.trim()).filter(Boolean)
      const longest = body.length ? Math.max(...body.map(line => line.length)) : 0
      const parts = [`Subject ${subject.length}/${COMMIT_SUBJECT_LIMIT}`]
      if (body.length) parts.push(`body ${longest}/${COMMIT_BODY_LIMIT}`)
      return parts.join(' · ')
    },
    /** Only the staged changes can be described: the generator reads the index */
    canGenerateMessage() {
      return !!this.api && !this.busy && !this.generatingMessage && this.stagedFiles.length > 0
    },
    /** Tooltip explaining why the generate button is disabled */
    generateTitle() {
      if (this.generatingMessage) return 'Generating the commit message...'
      if (!this.api) return 'No project API available'
      if (!this.stagedFiles.length) {
        return 'Stage the files to commit first: the message is built from the staged changes'
      }
      return 'Generate a commit message from the staged changes (50/72 rule)'
    },
    /** Worktree registered for the merge source branch, if any */
    mergeSourceWorktree() {
      if (!this.mergeFrom) return null
      return (this.worktrees || []).find(
        worktree => !worktree.is_main && this.sameBranch(worktree.branch, this.mergeFrom)
      ) || null
    },
    /** Uncommitted files inside the source worktree (discarded when removed) */
    mergeSourceWorktreeChangeCount() {
      const changes = this.mergeSourceWorktree?.changes || {}
      return changes.file_count ?? (changes.staged?.length || 0) + (changes.unstaged?.length || 0)
    },
    /** Merge message label: squashing produces a regular (squashed) commit */
    mergeMessageLabel() {
      return this.mergeSquash
        ? 'Squash commit message (optional)'
        : 'Merge commit message (optional)'
    },
    /** Label of the action button in the merge modal */
    mergeActionLabel() {
      return this.mergeSquash ? 'Squash' : 'Merge'
    },
    /** Identity of the open diff: remounts the pane for every file / group */
    diffKey() {
      if (!this.selectedFile) return null
      return `${this.selectedFile.group}:${this.selectedFile.path}`
    }
  },
  watch: {
    // Hidden files must not stay selected: a staging action would otherwise
    // affect files the filter is not showing.
    fileFilter() {
      this.clearSelection()
    },
    // A worktree removal only applies to the branch it was chosen for
    mergeFrom() {
      this.mergeDeleteWorktree = false
    }
  },
  created() {
    this.loadRepo()
  },
  mounted() {
    // Backend file activity (a chat, the terminal or an editor touching a file)
    // changes the working tree behind our back: keep the view in sync.
    this.fileEventsOff = onFileEvent(this.onProjectFileEvent)
  },
  beforeUnmount() {
    if (this.fileEventsOff) this.fileEventsOff()
    this.fileEventsOff = null
    clearTimeout(this.fileEventRefreshTimer)
    this.fileEventRefreshTimer = null
    // Never leave a pending confirmation promise unresolved
    this.resolveConfirmation(false)
  },
  methods: {
    sameBranch(a, b) {
      const clean = value => (value || '').replace(/^[*+\s]+/, '').trim()
      return !!a && !!b && clean(a) === clean(b)
    },

    /** Compare two filesystem paths ignoring trailing separators */
    samePath(a, b) {
      const clean = value => (value || '').replace(/[\\/]+$/, '')
      return !!a && !!b && clean(a) === clean(b)
    },

    branchCommitCount(branch) {
      const tree = this.repoTree.find(b => this.sameBranch(b.branch_name, branch))
      return tree?.commits?.length || 0
    },

    // ── Confirmations ───────────────────────────────────────────────────
    /**
     * Ask the user to confirm an operation with the app modal.
     *
     * Resolves `true` when the user accepts and `false` when the dialog is
     * cancelled or dismissed. A new request settles the pending one first, so
     * an awaited confirmation is never left hanging.
     *
     * @param {Object} options - Modal content (title, message, details, hint)
     * and confirm button style (confirmLabel, confirmIcon, confirmClass).
     * @returns {Promise<boolean>} User decision.
     *
     * @example
     * const accepted = await this.confirmAction({
     *   title: 'Delete branch',
     *   message: `Delete branch "${branch}"?`,
     *   confirmLabel: 'Delete',
     *   confirmClass: 'btn-error'
     * })
     */
    confirmAction(options = {}) {
      this.resolveConfirmation(false)
      return new Promise(resolve => {
        this.confirmRequest = { ...options, resolve }
      })
    },

    /** Settle the pending confirmation (no-op when there is none) */
    resolveConfirmation(accepted) {
      const request = this.confirmRequest
      this.confirmRequest = null
      if (request?.resolve) request.resolve(accepted)
    },

    // ── File events ─────────────────────────────────────────────────────
    /**
     * True when a published file event belongs to the project on screen.
     *
     * The payload carries the project (`project_id`) and/or its `codx_path`;
     * when neither is available the absolute project path is used, so file
     * activity from other projects never reloads this view.
     *
     * @param {Object} fileEvent - Normalized event from `@/utils/fileEvents`.
     * @returns {boolean}
     */
    isOwnProjectFileEvent(fileEvent) {
      if (!fileEvent) return false

      const projectId = this.project?.project_id
      if (projectId && fileEvent.projectId) return fileEvent.projectId === projectId

      const codxPath = this.project?.codx_path
      if (codxPath && fileEvent.codxPath) return fileEvent.codxPath === codxPath

      const root = this.projectRoot
      const path = fileEvent.filePath || fileEvent.newPath || fileEvent.previousPath
      return !!root && !!path && path.startsWith(root)
    },

    /**
     * A file was read / written / created / deleted on disk: the working tree,
     * the branches and the graph may be stale. Bursts of events (a chat writing
     * several files) are coalesced into a single reload.
     *
     * @param {Object} fileEvent - Normalized event from `@/utils/fileEvents`.
     */
    onProjectFileEvent(fileEvent) {
      if (!this.api || !this.isOwnProjectFileEvent(fileEvent)) return
      clearTimeout(this.fileEventRefreshTimer)
      this.fileEventRefreshTimer = setTimeout(this.refreshFromFileEvent, FILE_EVENT_REFRESH_DELAY)
    },

    /** Debounced reload triggered by the last file event */
    refreshFromFileEvent() {
      this.fileEventRefreshTimer = null
      // An in-flight git operation reloads the view when it finishes
      if (!this.api || this.busy || this.committing || this.merging) return
      this.loadRepo()
      // Branches, hashes and lanes changed: reload the graph too
      this.graphRefreshToken += 1
      // The validator may be showing the files that just changed on disk
      if (this.activeTab === 'validator') {
        this.$refs.gitValidator?.refresh()
      }
    },

    // ── Local changes review ────────────────────────────────────────────
    /**
     * Open the Review tab directly on the uncommitted changes against the
     * current branch (the ChangesPanel local mode).
     */
    reviewLocalChanges() {
      this.activeTab = 'review'
      this.$nextTick(() => this.$refs.changesPanel?.enableLocalReview())
    },

    /** Open the Validator tab (AI review of the project changes). */
    openValidator() {
      if (this.activeTab === 'validator') {
        this.$refs.gitValidator?.refresh()
        return
      }
      // The GitValidator `active` prop loads its context when it becomes visible
      this.activeTab = 'validator'
    },

    // ── Worktrees ───────────────────────────────────────────────────────
    isWorktreeExpanded(path) {
      return this.expandedWorktrees[path] !== false
    },

    toggleWorktree(path) {
      this.expandedWorktrees = {
        ...this.expandedWorktrees,
        [path]: !this.isWorktreeExpanded(path)
      }
    },

    /** Absolute path of a file inside a worktree checkout */
    worktreeFilePath(worktree, file) {
      if (!worktree?.path || !file?.path) return ''
      const relative = file.path.replace(/^[/\\]+/, '')
      return `${worktree.path.replace(/[/\\]+$/, '')}/${relative}`
    },

    /** Open a worktree file in the editor (absolute path from its checkout) */
    openWorktreeFile(worktree, file) {
      const absolute = this.worktreeFilePath(worktree, file)
      if (!absolute) return
      this.$ui.openFile(absolute)
    },

    /** Remove a worktree after the user confirms (its branch is kept) */
    async removeWorktree(worktree) {
      if ((!worktree?.path && !worktree?.branch) || !this.api) return
      const changeCount = worktree.changeCount || worktree.changes?.file_count || 0
      const label = worktree.branch ? `"${worktree.branch}"` : worktree.path
      const accepted = await this.confirmAction({
        title: 'Delete worktree',
        message: `Remove the worktree ${label}?`,
        details: [worktree.path],
        hint: changeCount
          ? `${changeCount} uncommitted change(s) in this worktree will be discarded. The branch is kept.`
          : 'The checkout is removed from disk. Its branch is kept.',
        icon: 'fa-folder-minus',
        iconClass: 'text-error',
        confirmLabel: 'Delete worktree',
        confirmIcon: 'fa-folder-minus',
        confirmClass: 'btn-error'
      })
      if (!accepted) return

      await this.runOperation(
        () => this.api.repo.removeWorktree({
          branch: worktree.branch || undefined,
          path: worktree.path
        }),
        'Worktree removed'
      )
    },

    /** Worktree registered for a branch, if any */
    worktreeForBranch(branch) {
      if (!branch) return null
      return (this.worktrees || []).find(
        worktree => !worktree.is_main && this.sameBranch(worktree.branch, branch)
      ) || null
    },

    // ── .gitignore editor ───────────────────────────────────────────────
    /** Open the editor and load the current `.gitignore` */
    async openGitignoreEditor() {
      this.showGitignore = true
      await this.loadGitignore()
    },

    async loadGitignore() {
      if (!this.api) return
      this.gitignoreLoading = true
      this.gitignoreError = null
      this.gitignoreNotice = null
      try {
        const result = await this.api.repo.gitignore()
        this.gitignorePath = result?.path || ''
        this.gitignoreContent = result?.content || ''
        this.gitignoreExists = !!result?.exists
      } catch (ex) {
        this.gitignoreError = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.gitignoreLoading = false
      }
    },

    closeGitignoreEditor() {
      if (this.gitignoreSaving) return
      this.showGitignore = false
      this.gitignoreError = null
      this.gitignoreNotice = null
    },

    async saveGitignore() {
      if (!this.api || this.gitignoreSaving) return
      this.gitignoreSaving = true
      this.gitignoreError = null
      this.gitignoreNotice = null
      try {
        const result = await this.api.repo.saveGitignore(this.gitignoreContent)
        this.gitignorePath = result?.path || this.gitignorePath
        this.gitignoreContent = result?.content ?? this.gitignoreContent
        this.gitignoreExists = !!result?.exists
        this.gitignoreNotice = 'Saved .gitignore'
        await this.loadRepo()
      } catch (ex) {
        this.gitignoreError = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.gitignoreSaving = false
      }
    },

    /**
     * Add files/folders to `.gitignore` and refresh the working tree.
     *
     * @param {Array<string|Object>} entries - Paths or `{ path, is_dir }`.
     */
    async addToGitignore(entries) {
      const list = (entries || []).filter(entry => (
        typeof entry === 'string' ? entry : entry?.path
      ))
      if (!list.length || !this.api) return
      this.gitignoreError = null
      this.gitignoreNotice = null
      const result = await this.runOperation(
        () => this.api.repo.addToGitignore(list),
        null
      )
      if (!result) return
      const added = result.added || []
      const skipped = result.skipped || []
      if (added.length) {
        this.notice = `Added to .gitignore: ${added.join(', ')}`
      } else if (skipped.length) {
        this.notice = 'Already ignored (no duplicate added)'
      }
      const warnings = (result.errors || []).filter(Boolean)
      if (warnings.length) this.error = warnings.join('; ')
      if (this.showGitignore) {
        this.gitignoreContent = result.content || this.gitignoreContent
        this.gitignorePath = result.path || this.gitignorePath
        this.gitignoreExists = !!result.exists
      }
    },

    // ── Context menus ───────────────────────────────────────────────────
    /** Branch sidebar entry */
    openBranchContextMenu(event, branch) {
      if (!branch) return
      const current = this.currentBranch
      const isCurrent = this.sameBranch(branch, current)
      const worktree = this.worktreeForBranch(branch)
      this.openContextMenu(event, `Branch ${branch}`, [
        this.contextMenuItem('checkout', 'Checkout', 'fa-arrow-right-to-bracket', () => this.onCheckout(branch), {
          disabled: isCurrent || !!worktree,
          title: worktree ? 'The branch is checked out in a worktree' : undefined
        }),
        this.contextMenuItem('merge', 'Merge into current…', 'fa-code-merge', () => this.openMerge(branch, current), { disabled: isCurrent || !current }),
        this.contextMenuItem('rebase', 'Rebase current onto this…', 'fa-arrows-rotate', () => this.onRebase(branch), { disabled: isCurrent || !current }),
        this.contextMenuItem('new-branch', 'New branch from…', 'fa-code-branch', () => this.openNewBranch(branch)),
        this.contextMenuDivider('branch-delete'),
        this.contextMenuItem('delete', 'Delete branch', 'fa-trash', () => this.deleteBranch(branch), {
          danger: true,
          disabled: isCurrent,
          title: worktree ? `Deletes the branch and its worktree at ${worktree.path}` : undefined
        }),
        ...(worktree
          ? [
              this.contextMenuItem('remove-worktree', 'Delete worktree', 'fa-folder-minus', () => this.removeWorktree(worktree), {
                danger: true,
                title: `Remove ${worktree.path} and keep the branch`
              })
            ]
          : []),
        this.contextMenuDivider('branch-copy'),
        this.contextMenuItem('copy', 'Copy branch name', 'fa-copy', () => this.copyText(branch, 'Branch name copied'))
      ])
    },

    /** Empty area of the branches sidebar: section-level actions */
    openBranchesContextMenu(event) {
      this.openContextMenu(event, 'Branches', [
        this.contextMenuItem('new-branch', 'New branch…', 'fa-plus', () => this.openNewBranch(this.selectedBranch || this.currentBranch)),
        this.contextMenuItem('refresh', 'Refresh branches', 'fa-rotate-right', () => this.loadRepo()),
        this.contextMenuDivider('branches-copy'),
        this.contextMenuItem('copy', 'Copy branch list', 'fa-list', () => this.copyText(this.filteredBranches.join('\n'), 'Branch list copied'), { disabled: !this.filteredBranches.length })
      ])
    },

    /** Staged / Changes group header: bulk actions over the visible files */
    openGroupContextMenu(event, group) {
      const files = group?.files || []
      const paths = files.map(file => file.path)
      const staged = group?.key === 'staged'
      this.openContextMenu(event, `${group?.label || 'Changes'} (${files.length})`, [
        this.contextMenuItem('select-all', 'Select all', 'fa-check-double', () => this.setGroupSelection(group.key, true), { disabled: !files.length }),
        this.contextMenuItem('clear', 'Clear selection', 'fa-xmark', () => this.setGroupSelection(group.key, false), { disabled: !this.selectionCount }),
        this.contextMenuDivider('group-actions'),
        this.contextMenuItem('stage', staged ? 'Unstage all' : 'Stage all', staged ? 'fa-minus' : 'fa-plus', () => staged ? this.unstagePaths(paths) : this.stagePaths(paths), { disabled: !files.length }),
        this.contextMenuItem('discard', 'Roll back all', 'fa-rotate-left', () => this.discardPaths(paths), { danger: true, disabled: !files.length }),
        this.contextMenuDivider('group-ignore'),
        this.contextMenuItem('gitignore', `Add ${files.length} changed file(s) to .gitignore`, 'fa-ban', () => this.addToGitignore(paths), { disabled: !files.length }),
        this.contextMenuItem('edit-gitignore', 'Edit .gitignore…', 'fa-pen', () => this.openGitignoreEditor()),
        this.contextMenuDivider('group-copy'),
        this.contextMenuItem('copy', 'Copy paths', 'fa-list', () => this.copyText(paths.join('\n'), 'Paths copied'), { disabled: !files.length })
      ])
    },

    /** Working tree folder row: same actions as a file, applied to the folder */
    openFolderContextMenu(event, group, row) {
      if (!row?.path) return
      const files = this.folderFiles(group, row.path)
      const paths = files.map(file => file.path)
      const staged = group === 'staged'
      const suffix = paths.length ? ` (${paths.length})` : ''
      this.openContextMenu(event, `Folder ${row.path}`, [
        this.contextMenuItem('select-all', `Select all files${suffix}`, 'fa-check-double', () => this.selectFolder(group, row.path), { disabled: !paths.length }),
        this.contextMenuDivider('folder-actions'),
        this.contextMenuItem('stage', `${staged ? 'Unstage' : 'Stage'} folder${suffix}`, staged ? 'fa-minus' : 'fa-plus', () => this.stageFolder(group, row.path), { disabled: !paths.length }),
        this.contextMenuItem('discard', `Roll back folder${suffix}`, 'fa-rotate-left', () => this.discardFolder(group, row.path), {
          danger: true,
          disabled: !paths.length,
          title: `Restore ${paths.length} file(s) from the last commit (you will see the affected files before confirming)`
        }),
        this.contextMenuDivider('folder-ignore'),
        this.contextMenuItem('gitignore', 'Add folder to .gitignore', 'fa-ban', () => this.addToGitignore([{ path: row.path, is_dir: true }])),
        this.contextMenuItem('edit-gitignore', 'Edit .gitignore…', 'fa-pen', () => this.openGitignoreEditor()),
        this.contextMenuDivider('folder-copy'),
        this.contextMenuItem('copy-path', 'Copy folder path', 'fa-copy', () => this.copyText(row.path, 'Folder path copied'))
      ])
    },

    /** Working tree file row */
    openWorkingTreeContextMenu(event, group, file) {
      if (!file?.path) return
      const wasSelected = this.isSelected(group, file.path)
      if (!wasSelected) {
        this.setSelection([this.fileKey(group, file.path)])
        this.selectionAnchor = { group, path: file.path }
      }
      const selected = this.selectedPaths(group)
      const paths = wasSelected && selected.length > 1 ? selected : [file.path]
      const count = paths.length
      const suffix = count > 1 ? ` (${count})` : ''
      const staged = group === 'staged'
      this.openContextMenu(event, count > 1 ? `${count} selected files` : file.path, [
        this.contextMenuItem('diff', 'Open diff', 'fa-code-compare', () => this.openDiff(group, file)),
        ...(file.code === 'U'
          ? [this.contextMenuItem('resolve-conflict', 'Resolve conflict…', 'fa-triangle-exclamation', () => this.openConflictResolver(file.path))]
          : []),
        this.contextMenuItem('editor', 'Open in editor', 'fa-up-right-from-square', () => this.$ui.openProjectFile(file.path)),
        this.contextMenuDivider('file-actions'),
        this.contextMenuItem('stage', staged ? `Unstage${suffix}` : `Stage${suffix}`, staged ? 'fa-minus' : 'fa-plus', () => staged ? this.unstagePaths(paths) : this.stagePaths(paths)),
        this.contextMenuItem('discard', `Roll back${suffix}`, 'fa-rotate-left', () => this.discardPaths(paths), { danger: true }),
        this.contextMenuDivider('file-ignore'),
        this.contextMenuItem('gitignore', `Add to .gitignore${suffix}`, 'fa-ban', () => this.addToGitignore(paths)),
        this.contextMenuItem('edit-gitignore', 'Edit .gitignore…', 'fa-pen', () => this.openGitignoreEditor()),
        this.contextMenuDivider('file-copy'),
        this.contextMenuItem('copy-path', 'Copy path', 'fa-copy', () => this.copyText(file.path, 'File path copied')),
        this.contextMenuItem('copy-paths', `Copy paths${suffix}`, 'fa-list', () => this.copyText(paths.join('\n'), 'Paths copied'), { disabled: count < 2 })
      ])
    },

    /** Worktree entry (header row): branch + checkout actions */
    openWorktreeContextMenu(event, worktree) {
      if (!worktree?.path) return
      const branch = worktree.branch || ''
      const current = this.currentBranch
      const isCurrent = !!branch && this.sameBranch(branch, current)
      const isActiveCheckout = this.samePath(worktree.path, this.projectRoot)
      const changeCount = worktree.changeCount || worktree.changes?.file_count || 0
      const title = branch
        ? `Worktree ${branch}${changeCount ? ` · ${changeCount} change(s)` : ''}`
        : `Worktree ${worktree.path}`
      this.openContextMenu(event, title, [
        this.contextMenuItem('merge', 'Merge into current…', 'fa-code-merge', () => this.openMerge(branch, current), { disabled: !branch || isCurrent || !current }),
        this.contextMenuItem('new-branch', 'New branch from…', 'fa-code-branch', () => this.openNewBranch(branch), { disabled: !branch }),
        this.contextMenuItem('refresh', 'Refresh changes', 'fa-rotate-right', () => this.loadRepo()),
        this.contextMenuDivider('worktree-remove'),
        this.contextMenuItem('remove-worktree', 'Delete worktree', 'fa-folder-minus', () => this.removeWorktree(worktree), {
          danger: true,
          disabled: isActiveCheckout,
          title: isActiveCheckout ? 'The checkout in use cannot be removed' : 'Remove the checkout and keep the branch'
        }),
        this.contextMenuItem('delete-branch', 'Delete branch', 'fa-trash', () => this.deleteBranch(branch), {
          danger: true,
          disabled: !branch || isCurrent,
          title: 'Deletes the branch and its worktree (if any), discarding uncommitted changes there'
        }),
        this.contextMenuDivider('worktree-copy'),
        this.contextMenuItem('copy-path', 'Copy worktree path', 'fa-copy', () => this.copyText(worktree.path, 'Worktree path copied')),
        this.contextMenuItem('copy-branch', 'Copy branch name', 'fa-code-branch', () => this.copyText(branch, 'Branch name copied'), { disabled: !branch })
      ])
    },

    /** Worktree file row */
    openWorktreeFileContextMenu(event, worktree, file) {
      if (!file?.path) return
      const absolute = this.worktreeFilePath(worktree, file)
      this.openContextMenu(event, `${file.label}: ${file.path}`, [
        this.contextMenuItem('open', 'Open in editor', 'fa-up-right-from-square', () => this.openWorktreeFile(worktree, file)),
        this.contextMenuDivider('worktree-file-ignore'),
        this.contextMenuItem('gitignore', 'Add to .gitignore', 'fa-ban', () => this.addToGitignore([{ path: file.path, is_dir: false }])),
        this.contextMenuItem('edit-gitignore', 'Edit .gitignore…', 'fa-pen', () => this.openGitignoreEditor()),
        this.contextMenuDivider('worktree-file-copy'),
        this.contextMenuItem('copy-path', 'Copy path', 'fa-copy', () => this.copyText(file.path, 'File path copied')),
        this.contextMenuItem('copy-absolute', 'Copy absolute path', 'fa-link', () => this.copyText(absolute, 'Absolute path copied')),
        this.contextMenuItem('copy-branch', 'Copy branch name', 'fa-code-branch', () => this.copyText(worktree.branch || '', 'Branch name copied'), { disabled: !worktree.branch })
      ])
    },

    /** Action emitted by the graph / commit detail context menus */
    onBranchContextAction({ action, branch: branchName, ref } = {}) {
      const branch = branchName || ref?.name
      if (!branch) return
      if (action === 'checkout') return this.onCheckout(branch)
      if (action === 'merge') return this.openMerge(branch, this.currentBranch)
      if (action === 'rebase') return this.onRebase(branch)
      if (action === 'delete') return this.deleteBranch(branch)
      if (action === 'new-branch') return this.openNewBranch(branch)
    },

    // ── Working tree ────────────────────────────────────────────────────
    /** Split a porcelain line (`XY <path>`) into index/worktree codes and path */
    parsePorcelainLine(line) {
      if (!line || !line.trim()) return null
      let index = ' '
      let worktree = ' '
      let path = ''
      if (line.length >= 3 && line[2] === ' ') {
        index = line[0]
        worktree = line[1]
        path = line.slice(3)
      } else if (line.length >= 2) {
        // Leading space trimmed by the transport: only the worktree code is left
        worktree = line[0]
        path = line.slice(2)
      } else {
        return null
      }
      path = this.cleanStatusPath(path)
      return path ? { index, worktree, path } : null
    },

    cleanStatusPath(path) {
      let value = (path || '').trim()
      if (value.includes(' -> ')) value = value.split(' -> ').pop()
      return value.replace(/^"|"$/g, '').trim()
    },

    statusMeta(code) {
      const meta = {
        A: { label: 'Added', icon: 'fa-circle-plus', color: 'text-success' },
        M: { label: 'Modified', icon: 'fa-pen', color: 'text-warning' },
        D: { label: 'Deleted', icon: 'fa-trash-can', color: 'text-error' },
        R: { label: 'Renamed', icon: 'fa-arrow-right-arrow-left', color: 'text-info' },
        C: { label: 'Copied', icon: 'fa-copy', color: 'text-info' },
        T: { label: 'Type changed', icon: 'fa-shuffle', color: 'text-warning' },
        U: { label: 'Conflict', icon: 'fa-triangle-exclamation', color: 'text-error' },
        '?': { label: 'Untracked', icon: 'fa-file-circle-plus', color: 'text-success' }
      }
      return meta[(code || '').trim()] || meta.M
    },

    /** Status code for an API entry, which can expose a code or a status name */
    codeFor(file) {
      if (file?.code) return file.code
      const codes = {
        added: 'A',
        modified: 'M',
        deleted: 'D',
        renamed: 'R',
        copied: 'C',
        typechange: 'T',
        conflict: 'U',
        untracked: '?'
      }
      return codes[(file?.status || '').toLowerCase()] || 'M'
    },

    buildStatusFile(code, path) {
      const clean = this.cleanStatusPath(path)
      if (!clean) return null
      const normalized = (code || '').trim() || 'M'
      const meta = this.statusMeta(normalized)
      return {
        path: clean,
        code: normalized,
        icon: meta.icon,
        color: meta.color,
        label: meta.label
      }
    },

    fileName(path) {
      return (path || '').split('/').pop()
    },

    fileDir(path) {
      const parts = (path || '').split('/')
      parts.pop()
      return parts.join('/')
    },

    isSectionCollapsed(key) {
      return !!this.collapsedSections[key]
    },

    toggleSection(key) {
      this.collapsedSections = {
        ...this.collapsedSections,
        [key]: !this.collapsedSections[key]
      }
    },

    // ── Multi selection ─────────────────────────────────────────────────
    fileKey(group, path) {
      return `${group}:${path}`
    },

    isSelected(group, path) {
      return !!this.selection[this.fileKey(group, path)]
    },

    /** Files currently rendered as rows (respects tree folder collapse) */
    visibleRowFiles(group) {
      return this.rowsForGroup(group)
        .filter(row => row.type === 'file')
        .map(row => row.file)
    },

    /** Index of a visible file row inside its group, -1 when it is not shown */
    fileIndex(group, path) {
      return this.visibleRowFiles(group).findIndex(file => file.path === path)
    },

    /** Replace the whole selection with the given keys */
    setSelection(keys) {
      const next = {}
      ;(keys || []).forEach(key => { next[key] = true })
      this.selection = next
    },

    toggleSelect(group, path) {
      const key = this.fileKey(group, path)
      const next = { ...this.selection }
      if (next[key]) {
        delete next[key]
      } else {
        next[key] = true
      }
      this.selection = next
    },

    /**
     * Shift+click: select every file between the anchor and the clicked file.
     * Without a valid anchor in the same group it falls back to a single
     * selection.
     */
    selectRange(group, path) {
      const targetIndex = this.fileIndex(group, path)
      if (targetIndex < 0) return

      const anchor = this.selectionAnchor
      const anchorIndex = anchor && anchor.group === group
        ? this.fileIndex(group, anchor.path)
        : -1

      if (anchorIndex < 0) {
        this.setSelection([this.fileKey(group, path)])
        this.selectionAnchor = { group, path }
        return
      }

      const [start, end] = anchorIndex <= targetIndex
        ? [anchorIndex, targetIndex]
        : [targetIndex, anchorIndex]

      const files = this.visibleRowFiles(group).slice(start, end + 1)
      this.setSelection(files.map(file => this.fileKey(group, file.path)))
    },

    /**
     * Plain click selects the file and opens its diff. Ctrl/Cmd and Shift only
     * manage the selection so multi-file actions stay possible without
     * replacing the right panel for every click.
     */
    onRowClick(event, group, file) {
      if (!file?.path) return

      if (event?.shiftKey) {
        this.selectRange(group, file.path)
        return
      }

      if (event?.ctrlKey || event?.metaKey) {
        this.toggleSelect(group, file.path)
        this.selectionAnchor = { group, path: file.path }
        return
      }

      this.setSelection([this.fileKey(group, file.path)])
      this.selectionAnchor = { group, path: file.path }
      this.openDiff(group, file)
    },

    /** Row highlight: open diff first, then selection, then hover */
    rowClass(group, file) {
      if (!file?.path) return ''
      if (this.isFileOpen(group, file.path)) {
        return 'bg-primary/20 ring-1 ring-inset ring-primary/40'
      }
      if (this.isSelected(group, file.path)) {
        return 'bg-primary/15 text-primary'
      }
      return 'hover:bg-base-200'
    },

    // ── Filtering / tree view ───────────────────────────────────────────
    /** Files of a group that pass the current filter */
    visibleGroupFiles(group) {
      return group === 'staged' ? this.filteredStagedFiles : this.filteredUnstagedFiles
    },

    /**
     * Match a change against the filter.
     *
     * Supported terms (space separated, all must match):
     * - plain text: path or file name contains it, or the extension matches
     * - `ext:js` / `.js`: exact extension
     * - `name:controller`: file name contains it
     * - `folder:components`: folder path contains it
     *
     * @param {Object} file - Change entry with a `path`.
     * @returns {boolean}
     */
    matchesFileFilter(file) {
      const terms = this.fileFilter.trim().toLowerCase().split(/\s+/).filter(Boolean)
      if (!terms.length) return true
      return terms.every(term => this.matchesFilterTerm(file, term))
    },

    /** Match one filter term against a file path */
    matchesFilterTerm(file, term) {
      const path = (file?.path || '').toLowerCase()
      const name = path.split('/').pop() || ''
      const slashIndex = path.lastIndexOf('/')
      const folder = slashIndex >= 0 ? path.slice(0, slashIndex) : ''
      const ext = name.includes('.') ? name.split('.').pop() : ''
      const value = (term || '').toLowerCase()

      if (value.startsWith('ext:')) {
        const wanted = value.slice(4).replace(/^\./, '')
        return !!wanted && ext === wanted
      }
      if (value.startsWith('folder:')) {
        const wanted = value.slice(7)
        return !!wanted && folder.includes(wanted)
      }
      if (value.startsWith('name:')) {
        const wanted = value.slice(5)
        return !!wanted && name.includes(wanted)
      }
      if (value.startsWith('.')) {
        return !!ext && ext === value.slice(1)
      }

      return path.includes(value) || name.includes(value) || (!!ext && ext === value)
    },

    /** Folder expansion state; filtering always shows the matching tree */
    isFolderExpanded(group, path) {
      if (this.hasFileFilter) return true
      return this.expandedFolders[`${group}:${path}`] !== false
    },

    /** Collapse / expand a folder in the tree view */
    toggleFolder(group, path) {
      // While filtering, all matching folders stay open so results are visible.
      if (this.hasFileFilter) return
      const key = `${group}:${path}`
      this.expandedFolders = {
        ...this.expandedFolders,
        [key]: !this.isFolderExpanded(group, path)
      }
    },

    /**
     * Rows rendered for a group: flat files in list mode, folder/file rows in
     * tree mode. Both shapes drive the same file-row markup.
     */
    rowsForGroup(group) {
      const files = this.visibleGroupFiles(group)
      if (!this.treeView) {
        return files.map(file => ({
          type: 'file',
          depth: 0,
          file,
          path: file.path,
          name: this.fileName(file.path)
        }))
      }
      return this.buildTreeRows(group, files)
    },

    /** Build and flatten a folder tree of the given files */
    buildTreeRows(group, files) {
      const root = { children: [], folders: new Map(), fileCount: 0 }

      files.forEach(file => {
        const parts = (file.path || '').split('/').filter(Boolean)
        if (!parts.length) return
        root.fileCount++
        let node = root

        parts.forEach((part, index) => {
          const isFile = index === parts.length - 1
          if (isFile) {
            node.children.push({ type: 'file', name: part, path: file.path, file })
            return
          }

          let folder = node.folders.get(part)
          if (!folder) {
            folder = {
              type: 'folder',
              name: part,
              path: parts.slice(0, index + 1).join('/'),
              children: [],
              folders: new Map(),
              fileCount: 0
            }
            node.folders.set(part, folder)
            node.children.push(folder)
          }
          folder.fileCount++
          node = folder
        })
      })

      const sortNodes = nodes => {
        nodes.sort((a, b) => {
          if (a.type !== b.type) return a.type === 'folder' ? -1 : 1
          return a.name.localeCompare(b.name)
        })
        nodes.forEach(node => {
          if (node.type === 'folder') sortNodes(node.children)
        })
      }
      sortNodes(root.children)

      const rows = []
      const walk = (nodes, depth) => {
        nodes.forEach(node => {
          if (node.type === 'folder') {
            rows.push({
              type: 'folder',
              depth,
              name: node.name,
              path: node.path,
              count: node.fileCount
            })
            if (this.isFolderExpanded(group, node.path)) {
              walk(node.children, depth + 1)
            }
          } else {
            rows.push({
              type: 'file',
              depth,
              name: node.name,
              path: node.path,
              file: node.file
            })
          }
        })
      }
      walk(root.children, 0)
      return rows
    },

    /** Paths of the current selection belonging to a group */
    selectedPaths(group) {
      const prefix = `${group}:`
      return Object.keys(this.selection)
        .filter(key => this.selection[key] && key.startsWith(prefix))
        .map(key => key.slice(prefix.length))
    },

    groupFiles(group) {
      return group === 'staged' ? this.stagedFiles : this.unstagedFiles
    },

    /** Files of a group that live under a folder (the folder itself too) */
    folderFiles(group, folderPath) {
      const prefix = String(folderPath || '').replace(/\/+$/, '')
      if (!prefix) return []
      return this.groupFiles(group).filter(file => (
        file.path === prefix || file.path.startsWith(`${prefix}/`)
      ))
    },

    folderPaths(group, folderPath) {
      return this.folderFiles(group, folderPath).map(file => file.path)
    },

    /** Select every file under a tree folder */
    selectFolder(group, folderPath) {
      const files = this.folderFiles(group, folderPath)
      if (!files.length) return
      this.setSelection(files.map(file => this.fileKey(group, file.path)))
      this.selectionAnchor = null
    },

    /** Stage (or unstage) every file under a tree folder */
    async stageFolder(group, folderPath) {
      const paths = this.folderPaths(group, folderPath)
      if (!paths.length) return
      if (group === 'staged') {
        await this.unstagePaths(paths)
      } else {
        await this.stagePaths(paths)
      }
    },

    /** Roll back every file under a tree folder, warning about each file */
    async discardFolder(group, folderPath) {
      const paths = this.folderPaths(group, folderPath)
      if (!paths.length) return
      await this.discardPaths(paths, {
        title: 'Roll back folder changes',
        message: `Roll back ${paths.length} file(s) under "${folderPath}" to the last commit?`,
        hint: 'Every file listed below is affected: tracked files are restored from the last commit, untracked/new files are deleted. This cannot be undone.'
      })
    },

    groupAllSelected(group) {
      const files = this.visibleGroupFiles(group)
      return files.length > 0 && files.every(file => this.isSelected(group, file.path))
    },

    /** Select / clear every file of a group from the header button state */
    setGroupSelection(group, checked) {
      const next = { ...this.selection }
      this.visibleGroupFiles(group).forEach(file => {
        const key = this.fileKey(group, file.path)
        if (checked) {
          next[key] = true
        } else {
          delete next[key]
        }
      })
      this.selection = next
    },

    clearSelection() {
      this.selection = {}
      this.selectionAnchor = null
    },

    /** Drop selections (and the anchor) whose file left its group */
    pruneSelection() {
      const valid = new Set()
      this.stagedFiles.forEach(file => valid.add(this.fileKey('staged', file.path)))
      this.unstagedFiles.forEach(file => valid.add(this.fileKey('changes', file.path)))
      const next = {}
      Object.keys(this.selection).forEach(key => {
        if (this.selection[key] && valid.has(key)) next[key] = true
      })
      this.selection = next

      if (this.selectionAnchor) {
        const anchorKey = this.fileKey(this.selectionAnchor.group, this.selectionAnchor.path)
        if (!valid.has(anchorKey)) this.selectionAnchor = null
      }
    },

    isFileOpen(group, path) {
      return this.selectedFile?.group === group && this.selectedFile?.path === path
    },

    openDiff(group, file) {
      if (!file?.path) return
      // Same file/group already open: keep it (no remount, no extra request)
      if (this.isFileOpen(group, file.path)) return
      this.selectedFile = {
        path: file.path,
        group,
        code: file.code,
        icon: file.icon,
        color: file.color,
        label: file.label
      }
    },

    closeDiff() {
      this.selectedFile = null
    },

    /** Keep the diff pane in sync with the reloaded working tree */
    syncSelectedFile() {
      if (!this.selectedFile) return

      const { path, group } = this.selectedFile
      const order = group === 'staged'
        ? ['staged', 'changes']
        : ['changes', 'staged']

      for (const key of order) {
        const match = this.groupFiles(key).find(file => file.path === path)
        if (match) {
          this.selectedFile = {
            path: match.path,
            group: key,
            code: match.code,
            icon: match.icon,
            color: match.color,
            label: match.label
          }
          return
        }
      }

      // The file is no longer part of the working tree (committed or rolled back)
      this.selectedFile = null
    },

    onFileChanged() {
      return this.loadRepo()
    },

    // ── Conflicts ───────────────────────────────────────────────────────
    /** True when the path is one of the unmerged files */
    isConflictFile(path) {
      if (!path) return false
      if ((this.conflicts?.conflicts || []).some(entry => entry.path === path)) {
        return true
      }
      return this.stagedFiles.some(file => file.path === path && file.code === 'U')
        || this.unstagedFiles.some(file => file.path === path && file.code === 'U')
    },

    /** Open the conflict resolver, optionally preselecting a file */
    openConflictResolver(path = '') {
      this.conflictPreselect = path || ''
      this.showConflicts = true
      this.error = null
    },

    /** The resolver refreshed the conflict state: keep the banner in sync */
    onConflictsUpdated(state) {
      this.conflictState = state || null
    },

    /**
     * The resolver finished (continued, aborted or asked to commit a squash).
     * Reload the repository and the graph so the view leaves the conflict UI.
     */
    async onConflictFinished({ action, result } = {}) {
      const label = this.conflictOperationLabel.toLowerCase()
      this.showConflicts = false
      this.conflictPreselect = ''
      await this.loadRepo()
      this.graphRefreshToken += 1
      if (result?.stash_error) {
        this.error = `The local changes could not be restored from the stash: ${result.stash_error}`
      }
      if (action === 'abort') {
        this.notice = 'Operation aborted'
      } else if (action === 'commit-squash') {
        this.notice = 'Squash merge resolved: review the staged changes and commit them'
        this.$nextTick(() => this.$refs.commitBox?.focus())
      } else if (action === 'resolved') {
        this.notice = 'Conflicts resolved: review the staged changes and commit them'
        this.$nextTick(() => this.$refs.commitBox?.focus())
      } else {
        this.notice = `Operation continued (${label})`
      }
    },

    // ── Graph ───────────────────────────────────────────────────────────
    onSelectCommit(commit) {
      this.selectedCommit = commit
    },

    closeCommit() {
      this.selectedCommit = null
    },

    /**
     * Branch action requested from the commit panel (which only lists the refs
     * pointing to the selected commit): checkout, merge into the current
     * branch, rebase the current branch onto it, or delete the branch.
     */
    async onCommitBranchAction({ action, branch } = {}) {
      if (!branch || !this.api) return

      if (action === 'checkout') {
        return this.onCheckout(branch)
      }

      if (action === 'delete') {
        await this.deleteBranch(branch)
        this.selectedCommit = null
        return
      }

      if (action === 'new-branch') {
        this.openNewBranch(branch)
        return
      }

      const target = this.currentBranch
      if (!target) {
        this.error = 'No branch is checked out'
        return
      }
      if (this.sameBranch(branch, target)) {
        this.error = `"${branch}" is already the current branch`
        return
      }

      if (action === 'merge') {
        // Open the merge modal prefilled: it offers the merge modes (squash,
        // no commit, worktree removal) and the compare preview.
        this.openMerge(branch, target)
        return
      }

      if (action === 'rebase') {
        await this.onRebase(branch)
        this.selectedCommit = null
      }
    },

    // ── Working tree operations ─────────────────────────────────────────
    async stagePaths(paths) {
      const list = paths || []
      if (!list.length || !this.api) return
      // Staging an unmerged file marks it resolved: never do that silently,
      // send the user to the resolver so the markers are removed first.
      const conflictPaths = list.filter(path => this.isConflictFile(path))
      const stageable = list.filter(path => !this.isConflictFile(path))
      if (stageable.length) {
        await this.runOperation(
          () => this.api.repo.stage(stageable),
          `${stageable.length} file(s) staged`
        )
      }
      this.clearSelection()
      if (conflictPaths.length) {
        this.openConflictResolver(conflictPaths[0])
      }
    },

    async unstagePaths(paths) {
      const list = paths || []
      if (!list.length || !this.api) return
      await this.runOperation(
        () => this.api.repo.unstage(list),
        `${list.length} file(s) unstaged`
      )
      this.clearSelection()
    },

    async discardPaths(paths, options = {}) {
      const list = paths || []
      if (!list.length || !this.api) return

      const accepted = await this.confirmAction({
        title: options.title || 'Roll back changes',
        message: options.message || (list.length === 1
          ? `Roll back "${list[0]}" to the last commit?`
          : `Roll back ${list.length} files to the last commit?`),
        details: list,
        hint: options.hint || 'Tracked files are restored from the last commit. Untracked and newly added files are deleted. This cannot be undone.',
        icon: options.icon || 'fa-rotate-left',
        iconClass: options.iconClass || 'text-error',
        confirmLabel: options.confirmLabel || 'Roll back',
        confirmIcon: options.confirmIcon || 'fa-rotate-left',
        confirmClass: options.confirmClass || 'btn-error'
      })
      if (!accepted) return

      await this.runOperation(
        () => this.api.repo.discard(list, true),
        `${list.length} file(s) rolled back`
      )
      this.clearSelection()
    },

    // ── Repository lock ─────────────────────────────────────────────────
    /**
     * Remove the stale `.git/index.lock` after the user confirms it.
     *
     * The lock is only safe to release when no git process is running, so the
     * confirmation warns about it before deleting the file.
     */
    async releaseLock() {
      if (!this.api) return
      const accepted = await this.confirmAction({
        title: 'Release repository lock',
        message: 'Remove the git lock file and unlock the repository?',
        details: this.lockPath ? [this.lockPath] : [],
        hint: 'Only do this if no git process is running. Removing index.lock while git is writing can corrupt the repository.',
        icon: 'fa-lock-open',
        iconClass: 'text-warning',
        confirmLabel: 'Release lock',
        confirmIcon: 'fa-lock-open',
        confirmClass: 'btn-warning'
      })
      if (!accepted) return

      await this.runOperation(
        () => this.api.repo.releaseLock(),
        'Repository lock released'
      )
    },

    // ── Loading ─────────────────────────────────────────────────────────
    async loadRepo() {
      if (!this.api) return
      this.loading = true
      this.error = null
      const errors = []

      // Fetch independently: when one request fails the other still provides
      // useful data. In particular, `/branches` carries `active_branch`, so the
      // header can keep informing the checked out branch even if `/info` fails.
      let info = {}
      let branchesRes = {}
      try {
        info = await this.api.repo.info()
      } catch (ex) {
        errors.push(`repository info: ${ex?.response?.data?.detail || ex?.message || ex}`)
      }
      try {
        branchesRes = await this.api.repo.branches()
      } catch (ex) {
        errors.push(`branches: ${ex?.response?.data?.detail || ex?.message || ex}`)
      }

      this.info = info || {}
      if (!this.info.active_branch && branchesRes?.active_branch) {
        this.info = {
          ...this.info,
          active_branch: branchesRes.active_branch,
          default_branch: this.info.default_branch || branchesRes.default_branch || ''
        }
      }
      this.branches = Array.isArray(branchesRes) ? branchesRes : (branchesRes?.branches || [])
      this.repoTree = branchesRes?.repo_tree || []
      // Repository info carries every worktree with the files changed inside it
      this.worktrees = Array.isArray(this.info.worktrees) ? this.info.worktrees : []
      // Conflict state: the backend detects a pending merge/rebase while
      // loading the info, so the banner appears without another request.
      this.conflictState = this.info.conflict_state || null
      if (this.hasConflicts && !this.showConflicts && !this.notice && this.conflictCount) {
        this.notice = `${this.conflictOperationLabel}: ${this.conflictCount} unresolved conflict(s)`
      }

      if (errors.length) {
        this.error = `Unable to load repository: ${errors.join('; ')}`
      }

      if (!this.selectedBranch || !this.branches.includes(this.selectedBranch)) {
        this.selectedBranch = this.currentBranch || this.branches[0] || null
      }
      this.pruneSelection()
      this.syncSelectedFile()
      this.loading = false
    },

    selectBranch(branch) {
      if (!branch) return
      this.selectedBranch = branch
    },

    // ── Shared operation runner ─────────────────────────────────────────
    async runOperation(fn, successMessage) {
      if (!this.api) return
      this.error = null
      this.notice = null
      this.busy = true
      try {
        const result = await fn()
        const errors = (result && Array.isArray(result.errors) ? result.errors : []).filter(Boolean)
        // Some endpoints answer 200 with success:false (e.g. stage): never
        // report them as succeeded. A merge/rebase stopped on conflicts is the
        // exception: the pending state is what the resolver needs.
        if (result && result.success === false && !result.conflicted) {
          throw new Error(errors.join('; ') || 'Git operation failed')
        }
        if (result?.conflicted) {
          this.conflictState = result.conflict_state || this.conflictState
          this.notice = null
          this.showConflicts = true
        } else if (successMessage) {
          this.notice = successMessage
        }
        await this.loadRepo()
        // Branches, hashes and lanes changed: reload the graph too
        this.graphRefreshToken += 1
        return result
      } catch (ex) {
        const message = ex?.response?.data?.detail || ex?.message || String(ex)
        // Reflect whatever could be applied (e.g. a partial staging)
        await this.loadRepo()
        // loadRepo clears `error` on entry: restore the operation failure so a
        // refused/failed write (e.g. deleting a worktree) is never silent.
        this.error = message
        this.graphRefreshToken += 1
      } finally {
        this.busy = false
      }
    },

    // ── Remote operations ───────────────────────────────────────────────
    onFetch() {
      this.runOperation(() => this.api.repo.fetch(), 'Fetched from remote')
    },
    onPull() {
      this.runOperation(() => this.api.repo.pull(), 'Pulled from remote')
    },
    onPush() {
      this.runOperation(() => this.api.repo.push(), 'Pushed to remote')
    },

    // ── Branch operations ───────────────────────────────────────────────
    onCheckout(branch) {
      if (!branch || this.sameBranch(branch, this.currentBranch)) return
      this.runOperation(
        () => this.api.repo.checkoutBranch(branch),
        `Checked out ${branch}`
      )
    },

    /** Open the create-branch modal, pre-filling the base branch */
    openNewBranch(from = '') {
      this.newBranchName = ''
      this.newBranchCheckout = false
      this.newBranchFrom = from || this.selectedBranch || this.currentBranch || ''
      this.showNewBranch = true
    },

    closeNewBranch() {
      this.showNewBranch = false
      this.newBranchName = ''
      this.newBranchCheckout = false
    },

    async createBranch() {
      const name = this.newBranchName.trim()
      if (!name || !this.api) return
      const from = this.newBranchFrom || this.currentBranch || ''
      await this.runOperation(
        () => this.api.repo.createBranch({
          branch: name,
          from_branch: from,
          checkout: this.newBranchCheckout
        }),
        `Branch ${name} created from ${from}`
      )
      if (!this.error) {
        this.closeNewBranch()
        this.selectedBranch = name
      }
    },

    async deleteBranch(branch) {
      if (!branch || !this.api) return

      // Deleting a branch removes its worktree first: tell the user exactly
      // which checkout disappears and how many uncommitted changes are lost.
      const worktree = this.worktreeForBranch(branch)
      const changeCount = worktree
        ? worktree.changeCount || worktree.changes?.file_count || 0
        : 0
      const hint = [
        worktree
          ? `Its worktree at ${worktree.path} is removed too${changeCount ? `, discarding ${changeCount} uncommitted change(s)` : ''}.`
          : '',
        'The branch is removed locally. Commits that are not reachable from another branch are lost.'
      ].filter(Boolean).join(' ')

      const accepted = await this.confirmAction({
        title: worktree ? 'Delete branch and worktree' : 'Delete branch',
        message: worktree
          ? `Delete branch "${branch}" and its worktree?`
          : `Delete branch "${branch}"?`,
        details: worktree ? [worktree.path] : [],
        hint,
        icon: 'fa-trash',
        iconClass: 'text-error',
        confirmLabel: 'Delete branch',
        confirmIcon: 'fa-trash',
        confirmClass: 'btn-error'
      })
      if (!accepted) return

      const result = await this.runOperation(
        () => this.api.repo.deleteBranch(branch),
        null
      )
      if (result) {
        this.notice = result.worktree_removed
          ? `Branch ${branch} deleted · worktree removed`
          : `Branch ${branch} deleted`
      }
    },

    /** Rebase the current branch onto the given branch (destructive, confirmed) */
    async onRebase(branch) {
      const target = this.currentBranch
      if (!branch || !this.api || !target || this.sameBranch(branch, target)) return

      const accepted = await this.confirmAction({
        title: 'Rebase branch',
        message: `Rebase "${target}" onto "${branch}"?`,
        hint: 'Rebasing rewrites the commits of the current branch: their hashes change. Nothing is pushed.',
        icon: 'fa-arrows-rotate',
        iconClass: 'text-warning',
        confirmLabel: 'Rebase',
        confirmIcon: 'fa-arrows-rotate',
        confirmClass: 'btn-warning'
      })
      if (!accepted) return

      await this.runOperation(
        () => this.api.repo.rebase({ onto_branch: branch, branch: target, keep_conflicts: true }),
        `Rebased ${target} onto ${branch}`
      )
    },

    // ── Commit message ──────────────────────────────────────────────────
    /**
     * Ask the backend to write a commit message for the staged changes.
     *
     * The message is generated from the index (what the next commit will
     * contain) and normalized to the 50/72 rule: subject of at most 50
     * characters and body lines of at most 72. Whatever is already written in
     * the box is sent as `hint`, so a user draft steers the result instead of
     * being discarded.
     *
     * When the AI is unavailable the backend answers a message built from the
     * staged file names with `fallback = true`: it is still inserted, and the
     * user is told it must be reviewed. Nothing staged answers 400.
     *
     * @returns {Promise<void>}
     *
     * @example
     * // Commit box contains "fix login timeout" -> sent as hint
     * await this.generateCommitMessage()
     */
    async generateCommitMessage() {
      if (!this.canGenerateMessage) return
      this.generatingMessage = true
      this.error = null
      this.notice = null
      try {
        const result = await this.api.repo.commitMessage({
          hint: this.commitMessage.trim() || undefined,
          include_body: true
        })
        const message = (result?.message || '').trim()
        if (!message) throw new Error('The AI returned an empty commit message')
        this.commitMessage = message
        const files = result.file_count || this.stagedFiles.length
        this.notice = result.fallback
          ? `AI unavailable: inserted a message built from the ${files} staged file(s), review it before committing`
          : `Commit message generated from ${files} staged file(s)`
      } catch (ex) {
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.generatingMessage = false
      }
    },

    // ── Commit ──────────────────────────────────────────────────────────
    async doCommit() {
      const message = this.commitMessage.trim()
      if (!message || !this.api || this.committing || !this.workingTreeCount) return
      if (this.hasConflicts) {
        this.error = 'Resolve the conflicts before committing'
        this.openConflictResolver()
        return
      }
      if (this.hasPendingOperation && !this.pendingOperationCanCommit) {
        this.error = `${this.conflictOperationLabel} in progress: continue it from the operation panel`
        this.openConflictResolver()
        return
      }
      const finishingOperation = this.pendingOperationCanCommit
      // Commit what is staged; stage everything only when nothing is staged
      const stageAll = this.stagedFiles.length === 0
      this.committing = true
      this.error = null
      this.notice = null
      try {
        await this.api.repo.commit({ message, stage_all: stageAll })
        this.notice = finishingOperation
          ? `${this.conflictOperationLabel} committed`
          : 'Changes committed'
        this.commitMessage = ''
        this.clearSelection()
        await this.loadRepo()
        this.graphRefreshToken += 1
      } catch (ex) {
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.committing = false
      }
    },

    // ── Merge ───────────────────────────────────────────────────────────
    /**
     * Open the merge modal, optionally prefilled with the branch pair.
     *
     * The modal is the single merge entry point (repository toolbar and the
     * graph commit panel) so every merge can choose the squash / no-commit /
     * worktree-removal options.
     *
     * @param {string} [from] - Source branch. Defaults to the selected branch.
     * @param {string} [to] - Target branch. Defaults to the current branch.
     */
    openMerge(from = '', to = '') {
      this.mergeFrom = from || this.selectedBranch || this.currentBranch || ''
      this.mergeTo = to || this.currentBranch || this.branches[0] || ''
      this.mergeMessage = ''
      this.mergeSquash = false
      this.mergeNoCommit = false
      this.mergeDeleteWorktree = false
      this.mergePreview = null
      this.showMerge = true
      this.loadMergePreview()
    },

    async loadMergePreview() {
      if (!this.api || !this.mergeFrom || !this.mergeTo) return
      this.mergePreviewLoading = true
      this.mergePreview = null
      try {
        const changes = await this.api.repo.changes({
          from_branch: this.mergeFrom,
          to_branch: this.mergeTo
        })
        const files = Object.keys(changes?.branch_file_and_commits || {})
        this.mergePreview = {
          fileCount: files.length,
          files: files.slice(0, 25),
          stat: changes?.stat || ''
        }
      } catch {
        this.mergePreview = null
      } finally {
        this.mergePreviewLoading = false
      }
    },

    /** Notice describing what the merge actually did (and left pending) */
    mergeNotice(result = {}) {
      const from = result.from_branch || this.mergeFrom
      const to = result.to_branch || this.mergeTo
      if (result.up_to_date) {
        return `${to} is already up to date with ${from}`
      }

      let message
      if (result.no_commit) {
        message = result.squashed
          ? `Squashed ${from} into ${to}: changes staged, commit them when ready`
          : `Merged ${from} into ${to}: changes staged, commit them when ready`
      } else if (result.squashed) {
        message = `Squashed ${from} into ${to} in one commit`
      } else {
        message = `Merged ${from} into ${to}`
      }

      if (result.worktree_removed) message += ' · source worktree removed'
      return message
    },

    async doMerge() {
      if (!this.mergeFrom || !this.mergeTo || !this.api) return
      if (this.sameBranch(this.mergeFrom, this.mergeTo)) {
        this.error = 'Source and target branches must be different'
        return
      }
      this.merging = true
      this.error = null
      try {
        const result = await this.api.repo.merge({
          from_branch: this.mergeFrom,
          to_branch: this.mergeTo,
          message: this.mergeMessage.trim() || undefined,
          no_commit: this.mergeNoCommit,
          squash: this.mergeSquash,
          delete_worktree: this.mergeDeleteWorktree,
          keep_conflicts: true
        })
        this.showMerge = false
        this.selectedCommit = null
        if (result?.conflicted) {
          // The merge is left in progress: open the resolver on the new state.
          this.conflictState = result.conflict_state || null
          this.notice = null
          this.showConflicts = true
          this.conflictPreselect = result.conflicts?.[0] || ''
          await this.loadRepo()
          this.graphRefreshToken += 1
          return
        }
        this.notice = this.mergeNotice(result || {})
        await this.loadRepo()
        this.graphRefreshToken += 1
      } catch (ex) {
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.merging = false
      }
    }
  }
}
</script>

<template>
  <div class="git-view h-full w-full flex flex-col bg-base-100 overflow-hidden">
    <!-- ── Toolbar ──────────────────────────────────────────────────────── -->
    <header class="flex items-center gap-2 px-3 py-1.5 bg-base-200 border-b border-base-content/10 shrink-0 flex-wrap">
      <i class="fa-solid fa-folder-tree text-warning"></i>
      <span class="font-mono text-sm font-semibold truncate min-w-0" :title="projectPath">{{ projectName }}</span>
      <span
        v-if="isWorktreeCheckout"
        class="badge badge-xs badge-info badge-outline gap-1"
        :title="`Git worktree: ${projectPath}`"
      >
        <i class="fa-solid fa-code-fork text-[9px] shrink-0"></i>
        <span>worktree</span>
      </span>
      <span
        v-if="currentBranch"
        class="badge badge-sm badge-primary badge-outline gap-1 max-w-[220px]"
        :title="isWorktreeCheckout
          ? `Active branch: ${currentBranch} (worktree ${projectPath})`
          : `Active branch: ${currentBranch}`"
      >
        <i class="fa-solid fa-check text-[9px] shrink-0"></i>
        <span class="truncate">{{ currentBranch }}</span>
      </span>

      <div class="grow"></div>

      <div v-if="isGit" class="join">
        <button class="join-item btn btn-xs btn-ghost" @click="onFetch" :disabled="busy" title="Fetch from remote">
          <i class="fa-solid fa-cloud-arrow-down"></i>
        </button>
        <button class="join-item btn btn-xs btn-ghost" @click="onPull" :disabled="busy" title="Pull from remote">
          <i class="fa-solid fa-arrow-down"></i>
        </button>
        <button class="join-item btn btn-xs btn-ghost" @click="onPush" :disabled="busy" title="Push to remote">
          <i class="fa-solid fa-arrow-up"></i>
        </button>
      </div>

      <button
        class="btn btn-xs btn-ghost"
        @click="openGitignoreEditor"
        :disabled="!api || !isGit"
        title="Edit .gitignore"
        aria-label="Edit .gitignore"
      >
        <i class="fa-solid fa-ban"></i>
      </button>

      <button class="btn btn-xs btn-ghost" @click="loadRepo" :disabled="loading" title="Reload repository">
        <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': loading }"></i>
      </button>

      <div class="join">
        <button
          class="join-item btn btn-xs"
          :class="activeTab === 'repository' ? 'btn-primary' : 'btn-ghost'"
          @click="activeTab = 'repository'"
          title="Working tree, branches and diffs"
        >
          <i class="fa-solid fa-code-branch"></i> Repository
        </button>
        <button
          class="join-item btn btn-xs"
          :class="activeTab === 'graph' ? 'btn-primary' : 'btn-ghost'"
          @click="activeTab = 'graph'"
          title="Commit graph of every branch"
        >
          <i class="fa-solid fa-diagram-project"></i> Graph
        </button>
        <button
          class="join-item btn btn-xs"
          :class="activeTab === 'review' ? 'btn-primary' : 'btn-ghost'"
          @click="activeTab = 'review'"
          title="Compare branches and review diffs"
        >
          <i class="fa-solid fa-code-compare"></i> Review
        </button>
        <button
          class="join-item btn btn-xs"
          :class="activeTab === 'validator' ? 'btn-primary' : 'btn-ghost'"
          @click="openValidator"
          title="AI review of the project changes"
        >
          <i class="fa-solid fa-shield-halved"></i> Validator
        </button>
      </div>
    </header>

    <!-- ── Feedback ─────────────────────────────────────────────────────── -->
    <div v-if="error" class="alert alert-error rounded-none py-1 px-3 text-xs flex items-center gap-2 shrink-0">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <span class="grow">{{ error }}</span>
      <button class="btn btn-ghost btn-xs" @click="error = null" aria-label="Dismiss error">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>
    <div v-if="notice" class="alert alert-success rounded-none py-1 px-3 text-xs flex items-center gap-2 shrink-0">
      <i class="fa-solid fa-circle-check"></i>
      <span class="grow">{{ notice }}</span>
      <button class="btn btn-ghost btn-xs" @click="notice = null" aria-label="Dismiss notice">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- ── Repository locked (stale .git/index.lock) ─────────────────────── -->
    <div v-if="locked" class="alert alert-warning rounded-none py-1 px-3 text-xs flex items-center gap-2 shrink-0">
      <i class="fa-solid fa-lock"></i>
      <span class="grow truncate" :title="lockPath ? `Locked by ${lockPath}` : 'Repository locked'">
        Repository is locked<span v-if="lockPath" class="font-mono opacity-70"> — {{ lockPath }}</span>
      </span>
      <button class="btn btn-xs btn-warning gap-1 shrink-0" :disabled="busy" @click="releaseLock">
        <i class="fa-solid fa-lock-open"></i> Release lock
      </button>
    </div>

    <!-- ── Conflicts (unmerged files) ────────────────────────────────────── -->
    <div v-if="hasConflicts" class="alert alert-error rounded-none py-1 px-3 text-xs flex items-center gap-2 shrink-0">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <span class="grow truncate">
        <b>{{ conflictOperationLabel }} in progress</b>
        <span class="opacity-80"> — {{ conflictCount || 'some' }} unresolved conflict(s)</span>
        <span
          v-if="conflicts?.stash_kept"
          class="text-warning"
          :title="conflicts.stash_message || 'Local changes were stashed before the operation'"
        > · local changes kept in stash</span>
      </span>
      <button class="btn btn-xs btn-error gap-1 shrink-0" :disabled="busy" @click="openConflictResolver()">
        <i class="fa-solid fa-code-merge"></i> Resolve conflicts
      </button>
    </div>

    <!-- ── Operation in progress without unmerged files (clean --no-commit
         merge, resolved merge waiting commit, paused rebase...) ─────────── -->
    <div v-else-if="hasPendingOperation" class="alert alert-warning rounded-none py-1 px-3 text-xs flex items-center gap-2 shrink-0">
      <i class="fa-solid fa-code-merge"></i>
      <span class="grow truncate">
        <b>{{ conflictOperationLabel }} in progress</b>
        <span class="opacity-80"> — no unresolved conflicts</span>
        <span v-if="conflicts?.squash" class="opacity-80"> · squashed changes are staged, commit them to finish</span>
        <span v-else-if="pendingOperationCanCommit" class="opacity-80"> · commit to finish the merge</span>
        <span v-else class="opacity-80"> · continue the operation from the panel</span>
        <span v-if="conflicts?.source_branch" class="font-mono"> · from {{ conflicts.source_branch }}</span>
      </span>
      <button class="btn btn-xs btn-warning gap-1 shrink-0" :disabled="busy" @click="openConflictResolver()">
        <i class="fa-solid fa-forward"></i> Finish {{ conflictOperationLabel.toLowerCase() }}
      </button>
    </div>

    <!-- ── No project ───────────────────────────────────────────────────── -->
    <div v-if="!project" class="grow flex flex-col items-center justify-center gap-3 text-base-content/40">
      <i class="fa-solid fa-code-branch text-4xl"></i>
      <span class="text-sm">No project selected</span>
    </div>

    <template v-else>
      <!-- ── Review: ChangesPanel (pick two branches, review diffs) ──────── -->
      <!-- v-show keeps the panel mounted so the branch selection survives tab switching -->
      <ChangesPanel
        v-show="activeTab === 'review'"
        ref="changesPanel"
        :project="project"
        class="grow min-h-0 overflow-hidden"
        @refresh="onFileChanged"
        @context-menu-notice="notice = $event"
        @context-menu-error="error = $event"
      />

      <!-- ── Validator: AI review of local changes / a branch comparison ─── -->
      <GitValidator
        v-show="activeTab === 'validator'"
        ref="gitValidator"
        :project="project"
        :api="api"
        :branches="branches"
        :current-branch="currentBranch || ''"
        :active="activeTab === 'validator'"
        class="grow min-h-0 overflow-hidden"
      />

      <!-- ── Graph: commit graph + commit details ────────────────────────── -->
      <!-- Resizable vertical split so the commit panel can be widened when
           reading a diff and the graph can take the full width when closed. -->
      <div v-show="activeTab === 'graph'" class="grow flex overflow-hidden min-h-0">
        <VerticalSplitter
          class="grow min-w-0 min-h-0"
          :panels="graphSplitterConfig"
          persist-key="git-view-graph"
          show-handle
          :show-right="!!selectedCommit"
        >
          <template #left>
            <GitGraph
              v-if="api"
              :api="api"
              :branches="branches"
              :current-branch="currentBranch || ''"
              :default-branch="info.default_branch || ''"
              :refresh-token="graphRefreshToken"
              class="h-full w-full"
              @select-commit="onSelectCommit"
              @context-action="onBranchContextAction"
              @context-menu-notice="notice = $event"
              @context-menu-error="error = $event"
            />
            <div v-else class="h-full flex items-center justify-center text-sm text-base-content/40">
              No project API available
            </div>
          </template>

          <template #right>
            <CommitDetail
              v-if="selectedCommit && api"
              :key="selectedCommit.hash"
              :api="api"
              :commit="selectedCommit"
              :current-branch="currentBranch || ''"
              :busy="busy"
              class="h-full w-full"
              @close="closeCommit"
              @branch-action="onCommitBranchAction"
              @context-menu-notice="notice = $event"
              @context-menu-error="error = $event"
            />
          </template>
        </VerticalSplitter>
      </div>

      <!-- ── Repository: branches + working tree + on-demand diff panel ─── -->
      <div v-show="activeTab === 'repository'" class="grow flex overflow-hidden">
        <!-- Branches sidebar + working tree, in a resizable vertical split -->
        <VerticalSplitter
          class="grow min-w-0 min-h-0"
          :panels="branchesSplitterConfig"
          persist-key="git-view-branches"
          show-handle
          :show-left="!$ui.isMobile"
        >
          <template #left>
            <aside class="h-full w-full flex flex-col overflow-hidden border-r border-base-content/10">
          <div class="flex items-center gap-1 px-2 py-1.5 border-b border-base-content/10 shrink-0">
            <span class="text-xs font-bold uppercase tracking-wide opacity-50 grow">Branches</span>
            <button class="btn btn-xs btn-ghost" @click="openNewBranch(selectedBranch || currentBranch)" title="New branch" aria-label="New branch">
              <i class="fa-solid fa-plus text-[10px]"></i>
            </button>
          </div>

          <div class="grow min-h-0" @contextmenu.prevent="openBranchesContextMenu($event)">
            <RepoBranchList
              v-model:filter="branchFilter"
              :branches="branches"
              :current-branch="currentBranch"
              :selected-branch="selectedBranch"
              :loading="loading"
              :counts="branchCounts"
              @select="selectBranch"
              @contextmenu="openBranchContextMenu"
            />
          </div>
        </aside>
          </template>

          <template #right>
        <!-- Working tree (left) + on-demand diff (right).
             The right panel only exists while a file is open for diff; the
             branch header lives on the left so the diff panel can stay hidden. -->
        <VerticalSplitter
          class="h-full w-full min-w-0 min-h-0"
          :panels="splitterConfig"
          persist-key="git-view-repository"
          show-handle
          :show-right="!!selectedFile"
        >
          <template #left>
            <div class="h-full w-full flex flex-col overflow-hidden">
            <!-- Branch header (moved here so the right panel can stay hidden
                 until a file diff is opened) -->
            <div class="flex items-center gap-2 px-2 py-1.5 border-b border-base-content/10 shrink-0 flex-wrap">
              <i class="fa-solid fa-code-commit text-warning text-xs"></i>
              <span
                class="font-mono text-sm font-semibold truncate min-w-0"
                :title="selectedBranch ? `${selectedBranch} — right-click for branch actions` : selectedBranch"
                @contextmenu.prevent.stop="openBranchContextMenu($event, selectedBranch)"
              >{{ selectedBranch || 'Select a branch' }}</span>
              <span v-if="sameBranch(selectedBranch, currentBranch)" class="badge badge-xs badge-success">current</span>
              <div class="grow"></div>

              <button
                class="btn btn-xs btn-ghost gap-1"
                @click="openNewBranch(selectedBranch)"
                :disabled="busy || !selectedBranch"
                title="Create a branch from the selected branch"
              >
                <i class="fa-solid fa-code-branch"></i> New branch
              </button>
              <button class="btn btn-xs btn-ghost gap-1" @click="openMerge()" :disabled="!branches.length || busy" title="Merge a branch into another">
                <i class="fa-solid fa-code-merge"></i> Merge
              </button>
              <button
                class="btn btn-xs btn-ghost gap-1"
                @click="reviewLocalChanges"
                :disabled="!workingTreeCount"
                title="Review the uncommitted changes against the current branch"
              >
                <i class="fa-solid fa-laptop-file"></i> Local changes
              </button>
              <button
                class="btn btn-xs btn-ghost gap-1"
                @click="onCheckout(selectedBranch)"
                :disabled="busy || !selectedBranch || sameBranch(selectedBranch, currentBranch)"
                title="Checkout branch"
              >
                <i class="fa-solid fa-arrow-right-to-bracket"></i> Checkout
              </button>
              <button
                class="btn btn-xs btn-ghost text-error gap-1"
                @click="deleteBranch(selectedBranch)"
                :disabled="busy || !selectedBranch || sameBranch(selectedBranch, currentBranch)"
                title="Delete the selected branch"
              >
                <i class="fa-solid fa-trash"></i> Delete branch
              </button>
            </div>

            <!-- Working tree -->
            <section class="grow w-full flex flex-col overflow-hidden min-h-0">
          <div class="flex items-center gap-1 px-2 py-1.5 border-b border-base-content/10 shrink-0">
            <i class="fa-solid fa-file-pen text-warning text-xs"></i>
            <span class="text-xs font-bold uppercase tracking-wide opacity-50 grow">Working tree</span>
            <span
              class="badge badge-xs"
              :class="filteredWorkingTreeCount ? 'badge-warning badge-outline' : 'badge-ghost'"
              :title="hasFileFilter
                ? `${filteredWorkingTreeCount} of ${workingTreeCount} changed file(s) match the filter`
                : `${workingTreeCount} changed file(s)`"
            >{{ hasFileFilter ? `${filteredWorkingTreeCount}/${workingTreeCount}` : workingTreeCount }}</span>
            <div class="join">
              <button
                class="join-item btn btn-xs"
                :class="!treeView ? 'btn-primary' : 'btn-ghost'"
                title="List view"
                aria-label="List view"
                :aria-pressed="!treeView"
                @click="treeView = false"
              >
                <i class="fa-solid fa-list text-[10px]"></i>
              </button>
              <button
                class="join-item btn btn-xs"
                :class="treeView ? 'btn-primary' : 'btn-ghost'"
                title="Tree view"
                aria-label="Tree view"
                :aria-pressed="treeView"
                @click="treeView = true"
              >
                <i class="fa-solid fa-folder-tree text-[10px]"></i>
              </button>
            </div>
            <button
              class="btn btn-xs btn-ghost"
              @click="openNewBranch(currentBranch)"
              :disabled="busy || !currentBranch"
              title="Create a branch from the current changes"
              aria-label="Create a branch from the current changes"
            >
              <i class="fa-solid fa-code-branch text-[10px]"></i>
            </button>
            <button
              class="btn btn-xs btn-ghost"
              @click="loadRepo"
              :disabled="loading"
              title="Reload working tree"
              aria-label="Reload working tree"
            >
              <i class="fa-solid fa-rotate-right text-[10px]" :class="{ 'animate-spin': loading }"></i>
            </button>
          </div>

          <!-- File filter: plain text, ext:, folder: and name: terms -->
          <div class="px-2 py-1.5 border-b border-base-content/10 shrink-0">
            <div class="relative">
              <i class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-[10px] opacity-40 pointer-events-none"></i>
              <input
                v-model="fileFilter"
                type="text"
                class="input input-xs input-bordered w-full pl-6 pr-7"
                placeholder="Filter files (ext:js, folder:src, name:foo)"
                aria-label="Filter changed files"
                @keydown.esc.prevent="fileFilter = ''"
              />
              <button
                v-if="hasFileFilter"
                class="btn btn-xs btn-ghost btn-square absolute right-0.5 top-1/2 -translate-y-1/2"
                title="Clear filter"
                aria-label="Clear filter"
                @click="fileFilter = ''"
              >
                <i class="fa-solid fa-xmark text-[10px]"></i>
              </button>
            </div>
          </div>

          <!-- Commit composer -->
          <div class="p-2 border-b border-base-content/10 flex flex-col gap-1.5 shrink-0">
            <textarea
              ref="commitBox"
              v-model="commitMessage"
              rows="2"
              class="textarea textarea-xs textarea-bordered w-full resize-y font-mono leading-tight"
              :placeholder="`Message (Ctrl+Enter to commit on '${currentBranch || 'HEAD'}')`"
              aria-label="Commit message"
              @keydown.ctrl.enter.prevent="doCommit"
              @keydown.meta.enter.prevent="doCommit"
            ></textarea>
            <div class="flex items-start gap-1">
              <p
                class="text-[10px] leading-tight grow"
                :class="subjectTooLong ? 'text-error' : 'opacity-50'"
              >{{ messageHint }}</p>
              <button
                class="btn btn-xs btn-ghost btn-square shrink-0"
                :disabled="!canGenerateMessage"
                :title="generateTitle"
                aria-label="Generate commit message"
                @click="generateCommitMessage"
              >
                <i class="fa-solid fa-spinner animate-spin text-[10px]" v-if="generatingMessage"></i>
                <i class="fa-solid fa-wand-magic-sparkles text-[10px]" v-else></i>
              </button>
            </div>
            <button
              class="btn btn-xs btn-primary w-full gap-1"
              :disabled="committing || !canCommit"
              @click="doCommit"
            >
              <i class="fa-solid fa-spinner animate-spin" v-if="committing"></i>
              <i class="fa-solid fa-check" v-else></i>
              Commit<span v-if="stagedFiles.length" class="opacity-70">{{ stagedFiles.length }}</span>
            </button>
          </div>

          <!-- Selection toolbar -->
          <div
            v-if="selectionCount"
            class="flex items-center gap-1 px-2 py-1 bg-primary/10 border-b border-base-content/10 shrink-0"
          >
            <span class="text-[11px] font-semibold grow">{{ selectionCount }} selected</span>
            <button
              v-if="changesSelection.length"
              class="btn btn-xs btn-ghost gap-1"
              :disabled="busy"
              title="Stage selected files"
              @click="stagePaths(changesSelection)"
            >
              <i class="fa-solid fa-plus text-[10px]"></i> Stage
            </button>
            <button
              v-if="stagedSelection.length"
              class="btn btn-xs btn-ghost gap-1"
              :disabled="busy"
              title="Unstage selected files"
              @click="unstagePaths(stagedSelection)"
            >
              <i class="fa-solid fa-minus text-[10px]"></i> Unstage
            </button>
            <button
              class="btn btn-xs btn-ghost text-error"
              :disabled="busy"
              title="Roll back selected files"
              aria-label="Roll back selected files"
              @click="discardPaths([...stagedSelection, ...changesSelection])"
            >
              <i class="fa-solid fa-rotate-left text-[10px]"></i>
            </button>
            <button
              class="btn btn-xs btn-ghost"
              title="Clear selection"
              aria-label="Clear selection"
              @click="clearSelection"
            >
              <i class="fa-solid fa-xmark text-[10px]"></i>
            </button>
          </div>

          <!-- Staged / Changes -->
          <div class="grow overflow-y-auto">
            <div
              v-if="noFilterMatches"
              class="flex flex-col items-center justify-center gap-2 p-6 text-center text-base-content/40"
            >
              <i class="fa-solid fa-filter text-2xl"></i>
              <span class="text-xs">No changed files match "<span class="font-mono">{{ fileFilter }}</span>"</span>
              <button class="btn btn-xs btn-ghost" @click="fileFilter = ''">Clear filter</button>
            </div>

            <div
              v-for="group in visibleWorkingTreeGroups"
              :key="group.key"
              class="border-b border-base-content/5 last:border-b-0"
            >
              <div
                class="flex items-center gap-1.5 px-2 py-1.5 hover:bg-base-200/60"
                :title="`${group.label} — right-click for group actions`"
                @contextmenu.prevent.stop="openGroupContextMenu($event, group)"
              >
                <button
                  class="flex items-center gap-1.5 grow min-w-0 text-left"
                  :aria-expanded="!isSectionCollapsed(group.key)"
                  @click="toggleSection(group.key)"
                >
                  <i
                    class="fa-solid text-[9px] opacity-50"
                    :class="isSectionCollapsed(group.key) ? 'fa-chevron-right' : 'fa-chevron-down'"
                  ></i>
                  <span class="text-[11px] font-bold uppercase tracking-wide truncate">{{ group.label }}</span>
                  <span
                    class="badge badge-xs"
                    :class="group.files.length ? 'badge-primary badge-outline' : 'badge-ghost'"
                  >{{ hasFileFilter ? `${group.files.length}/${group.total}` : group.files.length }}</span>
                </button>
                <button
                  v-if="group.files.length"
                  class="btn btn-xs btn-ghost btn-square shrink-0"
                  :class="groupAllSelected(group.key) ? 'text-primary' : ''"
                  :title="groupAllSelected(group.key)
                    ? `Clear ${group.label} selection`
                    : `Select ${hasFileFilter ? 'visible ' : 'all '}${group.label}`"
                  :aria-label="groupAllSelected(group.key)
                    ? `Clear ${group.label} selection`
                    : `Select ${hasFileFilter ? 'visible ' : 'all '}${group.label}`"
                  @click="setGroupSelection(group.key, !groupAllSelected(group.key))"
                >
                  <i class="fa-solid fa-check-double text-[10px]"></i>
                </button>
                <button
                  v-if="group.files.length"
                  class="btn btn-xs btn-ghost btn-square shrink-0"
                  :disabled="busy"
                  :title="`${group.key === 'staged' ? 'Unstage' : 'Stage'} ${hasFileFilter ? 'visible ' : 'all '}files`"
                  :aria-label="`${group.key === 'staged' ? 'Unstage' : 'Stage'} ${hasFileFilter ? 'visible ' : 'all '}files`"
                  @click="group.key === 'staged'
                    ? unstagePaths(group.files.map(file => file.path))
                    : stagePaths(group.files.map(file => file.path))"
                >
                  <i class="fa-solid text-[10px]" :class="group.key === 'staged' ? 'fa-minus' : 'fa-plus'"></i>
                </button>
              </div>

              <template v-if="!isSectionCollapsed(group.key)">
                <p v-if="!group.files.length" class="px-4 pb-2 text-[11px] opacity-40">{{ group.empty }}</p>
                <template
                  v-for="row in rowsForGroup(group.key)"
                  :key="`${group.key}-${row.type}-${row.path}`"
                >
                  <!-- Folder row (tree mode only) -->
                  <div
                    v-if="row.type === 'folder'"
                    class="group flex items-center gap-1.5 pr-1 py-0.5 cursor-pointer text-[11px] hover:bg-base-200/60 transition-colors"
                    :style="{ paddingLeft: `${8 + row.depth * 14}px` }"
                    :title="`${row.path} — click to expand, right-click for folder actions`"
                    @click="toggleFolder(group.key, row.path)"
                    @contextmenu.prevent.stop="openFolderContextMenu($event, group.key, row)"
                  >
                    <i
                      class="fa-solid text-[9px] opacity-50 shrink-0"
                      :class="isFolderExpanded(group.key, row.path) ? 'fa-chevron-down' : 'fa-chevron-right'"
                    ></i>
                    <i class="fa-solid fa-folder text-warning/70 text-[11px] shrink-0"></i>
                    <span class="font-mono truncate grow">{{ row.name }}</span>
                    <span class="badge badge-xs badge-ghost shrink-0">{{ row.count }}</span>
                    <div class="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                      <button
                        class="btn btn-xs btn-ghost btn-square"
                        :disabled="busy"
                        :title="group.key === 'staged' ? 'Unstage all changes in this folder' : 'Stage all changes in this folder'"
                        :aria-label="group.key === 'staged' ? 'Unstage all changes in this folder' : 'Stage all changes in this folder'"
                        @click.stop="stageFolder(group.key, row.path)"
                      >
                        <i class="fa-solid text-[10px]" :class="group.key === 'staged' ? 'fa-minus' : 'fa-plus'"></i>
                      </button>
                      <button
                        class="btn btn-xs btn-ghost btn-square text-error"
                        :disabled="busy"
                        title="Roll back all changes in this folder"
                        aria-label="Roll back all changes in this folder"
                        @click.stop="discardFolder(group.key, row.path)"
                      >
                        <i class="fa-solid fa-rotate-left text-[10px]"></i>
                      </button>
                    </div>
                  </div>

                  <!-- File row (list and tree mode) -->
                  <div
                    v-else
                    class="group flex items-center gap-1.5 pr-1 py-0.5 cursor-pointer transition-colors"
                    :class="rowClass(group.key, row.file)"
                    :style="{ paddingLeft: `${8 + row.depth * 14}px` }"
                    :title="`${row.file.label}: ${row.file.path} — click to open the diff, Ctrl/Shift+click to select multiple, right-click for actions.`"
                    @click="onRowClick($event, group.key, row.file)"
                    @contextmenu.prevent.stop="openWorkingTreeContextMenu($event, group.key, row.file)"
                  >
                    <span
                      class="w-0.5 self-stretch rounded-full shrink-0"
                      :class="isSelected(group.key, row.file.path) ? 'bg-primary' : 'bg-transparent'"
                    ></span>
                    <i class="fa-solid text-[11px] shrink-0" :class="[row.file.icon, row.file.color]"></i>
                    <span class="font-mono text-[11px] truncate shrink-0 max-w-[55%]">{{ fileName(row.file.path) }}</span>
                    <span
                      v-if="!treeView"
                      class="font-mono text-[10px] opacity-40 truncate grow text-right"
                    >{{ fileDir(row.file.path) }}</span>
                    <span v-else class="grow"></span>
                    <div class="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                      <button
                        class="btn btn-xs btn-ghost btn-square"
                        :disabled="busy"
                        :title="group.key === 'staged' ? 'Unstage file' : 'Stage file'"
                        :aria-label="group.key === 'staged' ? 'Unstage file' : 'Stage file'"
                        @click.stop="group.key === 'staged' ? unstagePaths([row.file.path]) : stagePaths([row.file.path])"
                      >
                        <i class="fa-solid text-[10px]" :class="group.key === 'staged' ? 'fa-minus' : 'fa-plus'"></i>
                      </button>
                      <button
                        class="btn btn-xs btn-ghost btn-square text-error"
                        :disabled="busy"
                        title="Roll back file"
                        aria-label="Roll back file"
                        @click.stop="discardPaths([row.file.path])"
                      >
                        <i class="fa-solid fa-rotate-left text-[10px]"></i>
                      </button>
                    </div>
                  </div>
                </template>
              </template>
            </div>

            <!-- Worktrees: every checkout with the files changed inside it -->
            <div v-if="worktreeList.length" class="border-t border-base-content/10">
              <div class="flex items-center gap-1.5 px-2 py-1.5 bg-base-200/40">
                <i class="fa-solid fa-folder-tree text-info text-[10px]"></i>
                <span class="text-[11px] font-bold uppercase tracking-wide opacity-60 grow">Worktrees</span>
                <span class="badge badge-xs badge-ghost">{{ worktreeList.length }}</span>
              </div>

              <div
                v-for="worktree in worktreeList"
                :key="`worktree-${worktree.path}`"
                class="border-t border-base-content/5 first:border-t-0"
              >
                <div
                  class="flex items-center gap-1.5 px-2 py-1.5 hover:bg-base-200/50"
                  :title="`${worktree.branch || worktree.path} — right-click for worktree actions`"
                  @contextmenu.prevent.stop="openWorktreeContextMenu($event, worktree)"
                >
                  <button
                    class="flex items-center gap-1.5 grow min-w-0 text-left"
                    :aria-expanded="isWorktreeExpanded(worktree.path)"
                    :title="worktree.path"
                    @click="toggleWorktree(worktree.path)"
                  >
                    <i
                      class="fa-solid text-[9px] opacity-50 shrink-0"
                      :class="isWorktreeExpanded(worktree.path) ? 'fa-chevron-down' : 'fa-chevron-right'"
                    ></i>
                    <i class="fa-solid fa-code-branch text-info text-[10px] shrink-0"></i>
                    <span class="font-mono text-[11px] truncate">{{ worktree.label }}</span>
                    <span v-if="worktree.is_main" class="badge badge-xs badge-ghost shrink-0">main</span>
                    <span
                      class="badge badge-xs shrink-0"
                      :class="worktree.changeCount ? 'badge-warning badge-outline' : 'badge-ghost'"
                    >{{ worktree.changeCount }}</span>
                  </button>
                  <span class="text-[9px] opacity-40 truncate max-w-[42%]" :title="worktree.path">{{ worktree.path }}</span>
                  <button
                    class="btn btn-xs btn-ghost btn-square shrink-0"
                    :disabled="busy || samePath(worktree.path, projectRoot)"
                    :title="samePath(worktree.path, projectRoot)
                      ? 'The checkout in use cannot be removed'
                      : 'Delete this worktree (the branch is kept)'"
                    aria-label="Delete worktree"
                    @click.stop="removeWorktree(worktree)"
                    @contextmenu.prevent.stop="openWorktreeContextMenu($event, worktree)"
                  >
                    <i class="fa-solid fa-folder-minus text-error text-[10px]"></i>
                  </button>
                </div>

                <div v-if="isWorktreeExpanded(worktree.path)">
                  <p v-if="!worktree.files.length" class="pl-8 pr-2 pb-1.5 text-[10px] opacity-40">No changes</p>
                  <div
                    v-for="file in worktree.files"
                    :key="`worktree-file-${worktree.path}-${file.path}`"
                    class="flex items-center gap-1.5 pl-8 pr-2 py-0.5 cursor-pointer hover:bg-base-200/60 transition-colors"
                    :title="`${file.label}: ${file.path} — open in the editor (right-click for actions)`"
                    @click="openWorktreeFile(worktree, file)"
                    @contextmenu.prevent.stop="openWorktreeFileContextMenu($event, worktree, file)"
                  >
                    <i class="fa-solid text-[10px] shrink-0" :class="[file.icon, file.color]"></i>
                    <span class="font-mono text-[10px] truncate grow">{{ file.path }}</span>
                    <span v-if="file.staged" class="badge badge-xs badge-ghost shrink-0">staged</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
            </section>
            </div>
          </template>

          <template #right>
            <div class="h-full flex flex-col overflow-hidden min-w-0">
              <!-- The right panel only exists while a file is selected for diff.
                   RepoFileDiff wraps the shared CodeViewer (patch, edit, history). -->
              <RepoFileDiff
                v-if="selectedFile && api"
                :key="diffKey"
                :api="api"
                :project="project"
                :file="selectedFile"
                class="flex-1 min-h-0"
                @close="closeDiff"
                @changed="onFileChanged"
              />
              <div v-else class="grow flex items-center justify-center text-xs text-base-content/40">
                No project API available
              </div>
            </div>
          </template>
        </VerticalSplitter>
          </template>
        </VerticalSplitter>
      </div>
    </template>

    <!-- ── Create branch modal ───────────────────────────────────────────── -->
    <div v-if="showNewBranch" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4" @click.self="closeNewBranch">
      <div class="bg-base-100 border border-base-content/10 rounded-xl w-full max-w-md shadow-xl">
        <div class="flex items-center justify-between px-4 py-3 border-b border-base-content/10">
          <h2 class="text-sm font-semibold flex items-center gap-2">
            <i class="fa-solid fa-code-branch text-warning"></i> New branch
          </h2>
          <button class="btn btn-xs btn-ghost" @click="closeNewBranch" aria-label="Close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="px-4 py-3 flex flex-col gap-3">
          <div class="flex flex-col gap-1">
            <label class="text-xs opacity-60" for="new-branch-name">Branch name</label>
            <input
              id="new-branch-name"
              v-model="newBranchName"
              type="text"
              placeholder="new-branch-name"
              class="input input-sm input-bordered w-full"
              @keyup.enter="createBranch"
              @keyup.esc="closeNewBranch"
            />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-xs opacity-60" for="new-branch-from">Create from</label>
            <select id="new-branch-from" v-model="newBranchFrom" class="select select-sm select-bordered w-full">
              <option v-for="b in branches" :key="`new-from-${b}`" :value="b">{{ b }}</option>
            </select>
          </div>
          <label class="flex items-center gap-2 text-xs cursor-pointer select-none">
            <input v-model="newBranchCheckout" type="checkbox" class="checkbox checkbox-xs" />
            Checkout the new branch (keeps the current changes)
          </label>
        </div>

        <div class="flex gap-2 px-4 py-3 border-t border-base-content/10">
          <button class="btn btn-sm btn-ghost grow" @click="closeNewBranch">Cancel</button>
          <button class="btn btn-sm btn-primary grow" :disabled="!newBranchName.trim() || busy" @click="createBranch">
            <i class="fa-solid fa-spinner animate-spin" v-if="busy"></i>
            <i class="fa-solid fa-code-branch" v-else></i>
            Create branch
          </button>
        </div>
      </div>
    </div>

    <!-- ── Merge modal ───────────────────────────────────────────────────── -->
    <div v-if="showMerge" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4" @click.self="showMerge = false">
      <div class="bg-base-100 border border-base-content/10 rounded-xl w-full max-w-lg max-h-[90vh] flex flex-col shadow-xl">
        <div class="flex items-center justify-between px-4 py-3 border-b border-base-content/10 shrink-0">
          <h2 class="text-sm font-semibold flex items-center gap-2">
            <i class="fa-solid fa-code-merge text-warning"></i> Merge branches
          </h2>
          <button class="btn btn-xs btn-ghost" @click="showMerge = false" aria-label="Close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="px-4 py-3 flex flex-col gap-3 overflow-y-auto">
          <div class="grid grid-cols-2 gap-2">
            <div class="flex flex-col gap-1">
              <label class="text-xs opacity-60">Merge from (source)</label>
              <select v-model="mergeFrom" class="select select-sm select-bordered w-full" @change="loadMergePreview">
                <option v-for="b in branches" :key="`mfrom-${b}`" :value="b">{{ b }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-xs opacity-60">Merge into (target)</label>
              <select v-model="mergeTo" class="select select-sm select-bordered w-full" @change="loadMergePreview">
                <option v-for="b in branches" :key="`mto-${b}`" :value="b">{{ b }}</option>
              </select>
            </div>
          </div>

          <!-- Two-branch compare preview -->
          <div class="bg-base-200 rounded-lg p-3 text-xs min-h-[64px]">
            <div v-if="mergePreviewLoading" class="flex items-center gap-2 opacity-60">
              <i class="fa-solid fa-spinner animate-spin"></i> Comparing branches...
            </div>
            <div v-else-if="mergePreview">
              <div class="flex items-center gap-2 mb-1">
                <span class="badge badge-sm badge-ghost">
                  <i class="fa-solid fa-file-pen text-warning"></i> {{ mergePreview.fileCount }} file(s)
                </span>
                <span v-if="mergePreview.stat" class="opacity-60">{{ mergePreview.stat }}</span>
              </div>
              <div class="h-32 overflow-auto flex flex-col gap-0.5 opacity-70">
                <div v-for="file in mergePreview.files" :key="file"
                  class="truncate font-mono shrink-0">{{ file }}</div>
              </div>
            </div>
            <div v-else class="opacity-50">
              <i class="fa-solid fa-circle-info"></i> Select two different branches to compare.
            </div>
          </div>

          <!-- Merge modes: squash and/or leave the result uncommitted; the
               source worktree can be removed once the merge succeeded. -->
          <div class="rounded-lg border border-base-content/10 p-3 flex flex-col gap-2">
            <span class="text-[11px] font-bold uppercase tracking-wide opacity-50">Options</span>

            <label class="flex items-start gap-2 text-xs cursor-pointer select-none">
              <input v-model="mergeSquash" type="checkbox" class="checkbox checkbox-xs mt-0.5" />
              <span class="min-w-0">
                <span class="font-semibold">Squash commits</span>
                <span class="block opacity-60 leading-tight">Collapse every commit from the source branch into a single commit.</span>
              </span>
            </label>

            <label class="flex items-start gap-2 text-xs cursor-pointer select-none">
              <input v-model="mergeNoCommit" type="checkbox" class="checkbox checkbox-xs mt-0.5" />
              <span class="min-w-0">
                <span class="font-semibold">Do not commit</span>
                <span class="block opacity-60 leading-tight">Leave the merge result staged so you can review and commit it yourself.</span>
              </span>
            </label>

            <label
              v-if="mergeSourceWorktree"
              class="flex items-start gap-2 text-xs cursor-pointer select-none"
            >
              <input v-model="mergeDeleteWorktree" type="checkbox" class="checkbox checkbox-xs mt-0.5" />
              <span class="min-w-0">
                <span class="font-semibold">Delete worktree after merging</span>
                <span class="block font-mono text-[10px] opacity-60 break-all">Source: {{ mergeSourceWorktree.path }}</span>
                <span
                  v-if="mergeSourceWorktreeChangeCount"
                  class="block text-warning leading-tight"
                >{{ mergeSourceWorktreeChangeCount }} uncommitted change(s) in this worktree will be discarded.</span>
              </span>
            </label>

            <p class="text-[10px] leading-tight opacity-50">
              Nothing is pushed: the merge stays local to this repository.
            </p>
          </div>

          <div class="flex flex-col gap-1">
            <label class="text-xs opacity-60" for="merge-message">{{ mergeMessageLabel }}</label>
            <input
              id="merge-message"
              v-model="mergeMessage"
              type="text"
              class="input input-sm input-bordered w-full"
              :disabled="mergeNoCommit"
              :placeholder="mergeNoCommit ? 'Not used: the changes stay uncommitted' : 'Merge message'"
            />
            <p v-if="mergeNoCommit" class="text-[10px] leading-tight opacity-50">
              The changes will be staged on <span class="font-mono">{{ mergeTo }}</span>. Commit them from the composer when ready.
            </p>
          </div>
        </div>

        <div class="flex gap-2 px-4 py-3 border-t border-base-content/10 shrink-0">
          <button class="btn btn-sm btn-ghost grow" @click="showMerge = false">Cancel</button>
          <button
            class="btn btn-sm btn-warning grow"
            :disabled="merging || !mergeFrom || !mergeTo || sameBranch(mergeFrom, mergeTo)"
            @click="doMerge"
          >
            <i class="fa-solid fa-spinner animate-spin" v-if="merging"></i>
            <i class="fa-solid fa-code-merge" v-else></i>
            {{ mergeActionLabel }} {{ mergeFrom }} → {{ mergeTo }}
          </button>
        </div>
      </div>
    </div>

    <!-- ── .gitignore editor ─────────────────────────────────────────────── -->
    <div v-if="showGitignore" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4" @click.self="closeGitignoreEditor">
      <div class="bg-base-100 border border-base-content/10 rounded-xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-xl">
        <div class="flex items-center justify-between gap-2 px-4 py-3 border-b border-base-content/10 shrink-0">
          <div class="min-w-0">
            <h2 class="text-sm font-semibold flex items-center gap-2">
              <i class="fa-solid fa-ban text-warning"></i>
              {{ gitignoreExists ? 'Edit .gitignore' : 'Create .gitignore' }}
            </h2>
            <p class="text-[10px] font-mono opacity-50 truncate" :title="gitignorePath">{{ gitignorePath }}</p>
          </div>
          <button class="btn btn-xs btn-ghost" @click="closeGitignoreEditor" :disabled="gitignoreSaving" aria-label="Close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="px-4 py-3 flex flex-col gap-2 overflow-y-auto grow min-h-0">
          <div v-if="gitignoreError" class="alert alert-error py-1 px-2 text-xs rounded">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span class="break-words">{{ gitignoreError }}</span>
          </div>
          <div v-if="gitignoreNotice" class="alert alert-success py-1 px-2 text-xs rounded">
            <i class="fa-solid fa-circle-check"></i>
            <span>{{ gitignoreNotice }}</span>
          </div>

          <p class="text-[10px] leading-tight opacity-60">
            One pattern per line. A leading <code>/</code> anchors it at the checkout root;
            a trailing <code>/</code> ignores a folder. Right-click a file or folder in the
            working tree to append a pattern automatically.
          </p>

          <div v-if="gitignoreLoading" class="grow min-h-[240px] flex items-center justify-center gap-2 text-xs opacity-60">
            <i class="fa-solid fa-spinner animate-spin"></i> Loading .gitignore...
          </div>
          <textarea
            v-else
            v-model="gitignoreContent"
            rows="16"
            spellcheck="false"
            class="textarea textarea-bordered w-full font-mono text-xs leading-tight resize-y min-h-[240px]"
            placeholder="# Ignore build output&#10;/dist/&#10;/node_modules/"
            aria-label=".gitignore content"
            @keydown.ctrl.s.prevent="saveGitignore"
            @keydown.meta.s.prevent="saveGitignore"
          ></textarea>
        </div>

        <div class="flex items-center gap-2 px-4 py-3 border-t border-base-content/10 shrink-0">
          <span class="text-[10px] opacity-50 grow">Ctrl+S saves; nothing is committed.</span>
          <button class="btn btn-sm btn-ghost" @click="closeGitignoreEditor" :disabled="gitignoreSaving">Cancel</button>
          <button class="btn btn-sm btn-primary" :disabled="gitignoreLoading || gitignoreSaving" @click="saveGitignore">
            <i class="fa-solid fa-spinner animate-spin" v-if="gitignoreSaving"></i>
            <i class="fa-solid fa-floppy-disk" v-else></i>
            Save
          </button>
        </div>
      </div>
    </div>

    <!-- ── Conflict resolver (manual / AI / abort) ───────────────────────── -->
    <GitConflictResolver
      v-if="showConflicts && api"
      :api="api"
      :project="project"
      :initial-state="conflicts"
      :initial-path="conflictPreselect"
      @close="showConflicts = false"
      @updated="onConflictsUpdated"
      @finished="onConflictFinished"
    />

    <!-- ── Repository sections context menu ─────────────────────────────── -->
    <GitContextMenu
      :visible="contextMenuState.visible"
      :position="contextMenuState.position"
      :title="contextMenuState.title"
      :items="contextMenuState.items"
      @select="onContextMenuSelect"
      @close="closeContextMenu"
    />

    <!-- ── Confirmation dialog (replaces window.confirm) ─────────────────── -->
    <ConfirmDialog
      v-if="confirmRequest"
      :title="confirmRequest.title"
      :message="confirmRequest.message"
      :details="confirmRequest.details"
      :hint="confirmRequest.hint"
      :icon="confirmRequest.icon"
      :icon-class="confirmRequest.iconClass"
      :confirm-label="confirmRequest.confirmLabel"
      :confirm-icon="confirmRequest.confirmIcon"
      :confirm-class="confirmRequest.confirmClass"
      :busy="busy"
      @confirm="resolveConfirmation(true)"
      @cancel="resolveConfirmation(false)"
    />
  </div>
</template>