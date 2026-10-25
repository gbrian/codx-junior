<script>
import ChangesPanel from '@/components/vibe/panels/ChangesPanel.vue'
import RepoFileDiff from '@/components/repo/RepoFileDiff.vue'
import GitGraph from '@/components/repo/GitGraph.vue'
import CommitDetail from '@/components/repo/CommitDetail.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import moment from 'moment'

// 50/72 rule: maximum subject length and maximum body line width
const COMMIT_SUBJECT_LIMIT = 50
const COMMIT_BODY_LIMIT = 72

export default {
  name: 'GitView',
  components: { ChangesPanel, RepoFileDiff, GitGraph, CommitDetail, ConfirmDialog },
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
      selectedBranch: null,
      branchFilter: '',
      rawCommits: [],
      commitsLoading: false,
      collapsedSections: {},
      // graph
      selectedCommit: null,
      // Bumped after every git operation so the graph reloads its commits
      graphRefreshToken: 0,
      // working tree
      selection: {},
      // Anchor for shift+click range selection: { group, path }
      selectionAnchor: null,
      selectedFile: null,
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
      mergePreview: null,
      mergePreviewLoading: false,
      merging: false,
      // Pending confirmation: { title, message, details, hint, icon, iconClass,
      // confirmLabel, confirmIcon, confirmClass, resolve }
      confirmRequest: null
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
    filteredBranches() {
      const filter = this.branchFilter.trim().toLowerCase()
      if (!filter) return this.branches
      return this.branches.filter(b => b.toLowerCase().includes(filter))
    },
    selectedTree() {
      return this.repoTree.find(b => this.sameBranch(b.branch_name, this.selectedBranch)) || null
    },
    commits() {
      if (this.selectedTree?.commits?.length) {
        return this.selectedTree.commits.map(c => this.normalizeCommit({
          commit: c.commit_id,
          author: c.author,
          date: c.date,
          message: c.comment
        }))
      }
      return this.rawCommits
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
    workingTreeGroups() {
      return [
        { key: 'staged', label: 'Staged', empty: 'No staged changes', files: this.stagedFiles },
        { key: 'changes', label: 'Changes', empty: 'No unstaged changes', files: this.unstagedFiles }
      ]
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
      if (this.stagedFiles.length) {
        return `${this.stagedFiles.length} staged file(s) will be committed`
      }
      if (this.unstagedFiles.length) {
        return 'Nothing staged: every change will be staged and committed'
      }
      return 'No changes to commit'
    },
    canCommit() {
      return !!this.commitMessage.trim() && this.workingTreeCount > 0
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
    /** Identity of the open diff: remounts the pane for every file / group */
    diffKey() {
      if (!this.selectedFile) return null
      return `${this.selectedFile.group}:${this.selectedFile.path}`
    }
  },
  created() {
    this.loadRepo()
  },
  beforeUnmount() {
    // Never leave a pending confirmation promise unresolved
    this.resolveConfirmation(false)
  },
  methods: {
    sameBranch(a, b) {
      const clean = value => (value || '').replace(/^[*+\s]+/, '').trim()
      return !!a && !!b && clean(a) === clean(b)
    },

    normalizeCommit(commit) {
      const id = commit.commit || commit.commit_id || commit.hash || ''
      const author = typeof commit.author === 'object'
        ? (commit.author?.name || '')
        : (commit.author || '')
      return {
        id,
        short: commit.short_commit || (id || '').slice(0, 8),
        author,
        date: commit.date || '',
        message: commit.message || commit.comment || '',
        relative: commit.date ? this.relativeDate(commit.date) : ''
      }
    },

    relativeDate(date) {
      const m = moment(date)
      return m.isValid() ? m.fromNow() : date
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

    /** Index of a file inside its group, -1 when it is not there anymore */
    fileIndex(group, path) {
      return this.groupFiles(group).findIndex(file => file.path === path)
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

      const files = this.groupFiles(group).slice(start, end + 1)
      this.setSelection(files.map(file => this.fileKey(group, file.path)))
    },

    /** Row click: plain = single selection + diff, ctrl = toggle, shift = range */
    onRowClick(event, group, file) {
      if (!file?.path) return

      if (event?.shiftKey) {
        this.selectRange(group, file.path)
        return
      }

      if (event?.ctrlKey || event?.metaKey) {
        this.toggleSelect(group, file.path)
      } else {
        this.setSelection([this.fileKey(group, file.path)])
      }

      this.selectionAnchor = { group, path: file.path }
      this.openDiff(group, file)
    },

    /** Checkbox click: plain = toggle, shift = select the range */
    onCheckboxClick(event, group, file) {
      if (!file?.path) return

      if (event?.shiftKey) {
        this.selectRange(group, file.path)
        return
      }

      this.toggleSelect(group, file.path)
      this.selectionAnchor = { group, path: file.path }
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

    groupAllSelected(group) {
      const files = this.groupFiles(group)
      return files.length > 0 && files.every(file => this.isSelected(group, file.path))
    },

    toggleGroupSelection(group) {
      const files = this.groupFiles(group)
      const allSelected = this.groupAllSelected(group)
      const next = { ...this.selection }
      files.forEach(file => {
        const key = this.fileKey(group, file.path)
        if (allSelected) {
          delete next[key]
        } else {
          next[key] = true
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
        const accepted = await this.confirmAction({
          title: 'Merge branch',
          message: `Merge "${branch}" into "${target}"?`,
          hint: 'A merge commit is created on the current branch. Nothing is pushed.',
          icon: 'fa-code-merge',
          iconClass: 'text-warning',
          confirmLabel: 'Merge',
          confirmIcon: 'fa-code-merge',
          confirmClass: 'btn-warning'
        })
        if (!accepted) return

        await this.runOperation(
          () => this.api.repo.merge({ from_branch: branch, to_branch: target }),
          `Merged ${branch} into ${target}`
        )
        this.selectedCommit = null
        return
      }

      if (action === 'rebase') {
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
          () => this.api.repo.rebase({ onto_branch: branch, branch: target }),
          `Rebased ${target} onto ${branch}`
        )
        this.selectedCommit = null
      }
    },

    // ── Working tree operations ─────────────────────────────────────────
    async stagePaths(paths) {
      const list = paths || []
      if (!list.length || !this.api) return
      await this.runOperation(
        () => this.api.repo.stage(list),
        `${list.length} file(s) staged`
      )
      this.clearSelection()
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

    async discardPaths(paths) {
      const list = paths || []
      if (!list.length || !this.api) return

      const accepted = await this.confirmAction({
        title: 'Roll back changes',
        message: list.length === 1
          ? `Roll back "${list[0]}" to the last commit?`
          : `Roll back ${list.length} files to the last commit?`,
        details: list,
        hint: 'Tracked files are restored from the last commit. Untracked and newly added files are deleted. This cannot be undone.',
        icon: 'fa-rotate-left',
        iconClass: 'text-error',
        confirmLabel: 'Roll back',
        confirmIcon: 'fa-rotate-left',
        confirmClass: 'btn-error'
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
      try {
        const [info, branchesRes] = await Promise.all([
          this.api.repo.info().catch(() => ({})),
          this.api.repo.branches()
        ])
        this.info = info || {}
        this.branches = Array.isArray(branchesRes) ? branchesRes : (branchesRes?.branches || [])
        this.repoTree = branchesRes?.repo_tree || []

        if (!this.selectedBranch || !this.branches.includes(this.selectedBranch)) {
          this.selectedBranch = this.currentBranch || this.branches[0] || null
        }
        this.pruneSelection()
        this.syncSelectedFile()
        await this.loadCommitsForBranch(this.selectedBranch)
      } catch (ex) {
        this.error = `Unable to load repository: ${ex?.message || ex}`
      } finally {
        this.loading = false
      }
    },

    selectBranch(branch) {
      if (!branch) return
      this.selectedBranch = branch
      this.rawCommits = []
      this.loadCommitsForBranch(branch)
    },

    async loadCommitsForBranch(branch) {
      if (!this.api || !branch) return
      const tree = this.repoTree.find(b => this.sameBranch(b.branch_name, branch))
      if (tree?.commits?.length) {
        this.rawCommits = []
        return
      }
      this.commitsLoading = true
      try {
        const res = await this.api.repo.commits(branch)
        this.rawCommits = this.parseRawCommits(res)
      } catch {
        this.rawCommits = []
      } finally {
        this.commitsLoading = false
      }
    },

    /** Fallback parser for `git log` output when repo_tree is not available */
    parseRawCommits(res) {
      const raw = res?.commits ?? res
      if (Array.isArray(raw)) return raw.map(c => this.normalizeCommit(c))
      if (typeof raw !== 'string' || !raw.trim()) return []
      return raw.split(/^commit /m).filter(Boolean).map(block => {
        const lines = block.split('\n')
        const id = lines[0].trim().split(' ')[0]
        const authorLine = lines.find(l => l.startsWith('Author:')) || ''
        const dateLine = lines.find(l => l.startsWith('Date:')) || ''
        const blankIndex = lines.findIndex(l => l.trim() === '')
        const message = (blankIndex > -1 ? lines.slice(blankIndex + 1).join(' ') : '').trim()
        return this.normalizeCommit({
          commit: id,
          author: authorLine.replace('Author:', '').trim(),
          date: dateLine.replace('Date:', '').trim(),
          message
        })
      })
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
        // report them as succeeded
        if (result && result.success === false) {
          throw new Error(errors.join('; ') || 'Git operation failed')
        }
        if (successMessage) this.notice = successMessage
        await this.loadRepo()
        // Branches, hashes and lanes changed: reload the graph too
        this.graphRefreshToken += 1
        return result
      } catch (ex) {
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
        // Reflect whatever could be applied (e.g. a partial staging)
        await this.loadRepo()
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
        this.loadCommitsForBranch(name)
      }
    },

    async deleteBranch(branch) {
      if (!branch || !this.api) return

      const accepted = await this.confirmAction({
        title: 'Delete branch',
        message: `Delete branch "${branch}"?`,
        hint: 'The branch is removed locally. Commits that are not reachable from another branch are lost.',
        icon: 'fa-trash',
        iconClass: 'text-error',
        confirmLabel: 'Delete branch',
        confirmIcon: 'fa-trash',
        confirmClass: 'btn-error'
      })
      if (!accepted) return

      await this.runOperation(
        () => this.api.repo.deleteBranch(branch),
        `Branch ${branch} deleted`
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
      // Commit what is staged; stage everything only when nothing is staged
      const stageAll = this.stagedFiles.length === 0
      this.committing = true
      this.error = null
      this.notice = null
      try {
        await this.api.repo.commit({ message, stage_all: stageAll })
        this.notice = 'Changes committed'
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
    openMerge() {
      this.mergeFrom = this.selectedBranch || this.currentBranch || ''
      this.mergeTo = this.currentBranch || this.branches[0] || ''
      this.mergeMessage = ''
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

    async doMerge() {
      if (!this.mergeFrom || !this.mergeTo || !this.api) return
      if (this.sameBranch(this.mergeFrom, this.mergeTo)) {
        this.error = 'Source and target branches must be different'
        return
      }
      this.merging = true
      this.error = null
      try {
        await this.api.repo.merge({
          from_branch: this.mergeFrom,
          to_branch: this.mergeTo,
          message: this.mergeMessage.trim() || undefined
        })
        this.notice = `Merged ${this.mergeFrom} into ${this.mergeTo}`
        this.showMerge = false
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
        v-if="currentBranch"
        class="badge badge-sm badge-primary badge-outline gap-1 max-w-[220px]"
        :title="`Current branch: ${currentBranch}`"
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

      <button class="btn btn-xs btn-ghost" @click="loadRepo" :disabled="loading" title="Reload repository">
        <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': loading }"></i>
      </button>

      <div class="join">
        <button
          class="join-item btn btn-xs"
          :class="activeTab === 'repository' ? 'btn-primary' : 'btn-ghost'"
          @click="activeTab = 'repository'"
          title="Working tree, branches and commits"
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
        :project="project"
        class="grow min-h-0 overflow-hidden"
      />

      <!-- ── Graph: commit graph + commit details ────────────────────────── -->
      <div v-show="activeTab === 'graph'" class="grow flex overflow-hidden">
        <GitGraph
          v-if="api"
          :api="api"
          :branches="branches"
          :current-branch="currentBranch || ''"
          :default-branch="info.default_branch || ''"
          :refresh-token="graphRefreshToken"
          class="grow min-w-0"
          @select-commit="onSelectCommit"
        />
        <div v-else class="grow flex items-center justify-center text-sm text-base-content/40">
          No project API available
        </div>

        <CommitDetail
          v-if="selectedCommit && api"
          :key="selectedCommit.hash"
          :api="api"
          :commit="selectedCommit"
          :current-branch="currentBranch || ''"
          :busy="busy"
          class="w-full md:w-[46%] md:max-w-[720px] shrink-0 border-l border-base-content/10"
          @close="closeCommit"
          @branch-action="onCommitBranchAction"
        />
      </div>

      <!-- ── Repository: working tree + branches + diff/commits ─────────── -->
      <div v-show="activeTab === 'repository'" class="grow flex overflow-hidden">
        <!-- Branches sidebar -->
        <aside class="hidden lg:flex lg:w-52 shrink-0 border-r border-base-content/10 flex-col overflow-hidden">
          <div class="flex items-center gap-1 px-2 py-1.5 border-b border-base-content/10 shrink-0">
            <span class="text-xs font-bold uppercase tracking-wide opacity-50 grow">Branches</span>
            <button class="btn btn-xs btn-ghost" @click="openNewBranch(selectedBranch || currentBranch)" title="New branch" aria-label="New branch">
              <i class="fa-solid fa-plus text-[10px]"></i>
            </button>
          </div>

          <div class="px-2 py-1.5 border-b border-base-content/10 shrink-0">
            <input v-model="branchFilter" type="text" placeholder="Filter branches..." class="input input-xs input-bordered w-full" />
          </div>

          <div class="grow overflow-y-auto">
            <div v-if="loading && !branches.length" class="p-3 text-xs opacity-50">Loading branches...</div>
            <div v-else-if="!filteredBranches.length" class="p-3 text-xs opacity-50">No branches</div>
            <button
              v-for="branch in filteredBranches"
              :key="branch"
              class="w-full flex items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors"
              :class="[
                selectedBranch === branch ? 'bg-primary/15 text-primary' : 'hover:bg-base-200',
                sameBranch(branch, currentBranch) ? 'font-semibold' : ''
              ]"
              :title="branch"
              @click="selectBranch(branch)"
            >
              <i
                class="fa-solid shrink-0"
                :class="sameBranch(branch, currentBranch) ? 'fa-circle-check text-success' : 'fa-code-branch opacity-50'"
              ></i>
              <span class="truncate grow min-w-0" :title="branch">{{ branch }}</span>
              <span v-if="branchCommitCount(branch)" class="badge badge-xs badge-ghost shrink-0">{{ branchCommitCount(branch) }}</span>
            </button>
          </div>
        </aside>

        <!-- Working tree -->
        <section class="w-full md:w-80 shrink-0 border-r border-base-content/10 flex flex-col overflow-hidden">
          <div class="flex items-center gap-1 px-2 py-1.5 border-b border-base-content/10 shrink-0">
            <i class="fa-solid fa-file-pen text-warning text-xs"></i>
            <span class="text-xs font-bold uppercase tracking-wide opacity-50 grow">Working tree</span>
            <span
              class="badge badge-xs"
              :class="workingTreeCount ? 'badge-warning badge-outline' : 'badge-ghost'"
              :title="`${workingTreeCount} changed file(s)`"
            >{{ workingTreeCount }}</span>
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

          <!-- Commit composer -->
          <div class="p-2 border-b border-base-content/10 flex flex-col gap-1.5 shrink-0">
            <textarea
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
              v-for="group in workingTreeGroups"
              :key="group.key"
              class="border-b border-base-content/5 last:border-b-0"
            >
              <div class="flex items-center gap-1.5 px-2 py-1.5 hover:bg-base-200/60">
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
                  >{{ group.files.length }}</span>
                </button>
                <input
                  v-if="group.files.length"
                  type="checkbox"
                  class="checkbox checkbox-xs shrink-0"
                  :checked="groupAllSelected(group.key)"
                  :aria-label="`Select all ${group.label}`"
                  @change="toggleGroupSelection(group.key)"
                />
                <button
                  v-if="group.files.length"
                  class="btn btn-xs btn-ghost btn-square shrink-0"
                  :disabled="busy"
                  :title="group.key === 'staged' ? 'Unstage all' : 'Stage all'"
                  :aria-label="group.key === 'staged' ? 'Unstage all' : 'Stage all'"
                  @click="group.key === 'staged'
                    ? unstagePaths(group.files.map(file => file.path))
                    : stagePaths(group.files.map(file => file.path))"
                >
                  <i class="fa-solid text-[10px]" :class="group.key === 'staged' ? 'fa-minus' : 'fa-plus'"></i>
                </button>
              </div>

              <template v-if="!isSectionCollapsed(group.key)">
                <p v-if="!group.files.length" class="px-4 pb-2 text-[11px] opacity-40">{{ group.empty }}</p>
                <div
                  v-for="file in group.files"
                  :key="`${group.key}-${file.path}`"
                  class="group flex items-center gap-1.5 pl-2 pr-1 py-0.5 cursor-pointer transition-colors"
                  :class="[
                    isFileOpen(group.key, file.path) ? 'bg-primary/15' : 'hover:bg-base-200',
                    isSelected(group.key, file.path) ? 'bg-primary/5' : ''
                  ]"
                  :title="`${file.label}: ${file.path} — click to view the diff, Shift+click to select a range`"
                  @click="onRowClick($event, group.key, file)"
                >
                  <input
                    type="checkbox"
                    class="checkbox checkbox-xs shrink-0"
                    :checked="isSelected(group.key, file.path)"
                    :aria-label="`Select ${file.path}`"
                    @click.stop.prevent="onCheckboxClick($event, group.key, file)"
                  />
                  <i class="fa-solid text-[11px] shrink-0" :class="[file.icon, file.color]"></i>
                  <span class="font-mono text-[11px] truncate shrink-0 max-w-[55%]">{{ fileName(file.path) }}</span>
                  <span class="font-mono text-[10px] opacity-40 truncate grow text-right">{{ fileDir(file.path) }}</span>
                  <button
                    class="btn btn-xs btn-ghost btn-square shrink-0"
                    :class="isFileOpen(group.key, file.path) ? 'text-primary' : 'opacity-60 hover:opacity-100'"
                    title="View diff"
                    aria-label="View diff"
                    @click.stop="openDiff(group.key, file)"
                  >
                    <i class="fa-solid fa-code-compare text-[10px]"></i>
                  </button>
                  <div class="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                    <button
                      class="btn btn-xs btn-ghost btn-square"
                      :disabled="busy"
                      :title="group.key === 'staged' ? 'Unstage file' : 'Stage file'"
                      :aria-label="group.key === 'staged' ? 'Unstage file' : 'Stage file'"
                      @click.stop="group.key === 'staged' ? unstagePaths([file.path]) : stagePaths([file.path])"
                    >
                      <i class="fa-solid text-[10px]" :class="group.key === 'staged' ? 'fa-minus' : 'fa-plus'"></i>
                    </button>
                    <button
                      class="btn btn-xs btn-ghost btn-square text-error"
                      :disabled="busy"
                      title="Roll back file"
                      aria-label="Roll back file"
                      @click.stop="discardPaths([file.path])"
                    >
                      <i class="fa-solid fa-rotate-left text-[10px]"></i>
                    </button>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </section>

        <!-- Diff / commits -->
        <div class="grow flex flex-col overflow-hidden min-w-0">
          <div class="flex items-center gap-2 px-3 py-1.5 border-b border-base-content/10 shrink-0 flex-wrap">
            <i class="fa-solid fa-code-commit text-warning text-xs"></i>
            <span class="font-mono text-sm font-semibold truncate min-w-0 max-w-[40%]" :title="selectedBranch">{{ selectedBranch || 'Select a branch' }}</span>
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
            <button class="btn btn-xs btn-ghost gap-1" @click="openMerge" :disabled="!branches.length || busy" title="Merge a branch into another">
              <i class="fa-solid fa-code-merge"></i> Merge
            </button>
            <button
              class="btn btn-xs btn-ghost"
              @click="onCheckout(selectedBranch)"
              :disabled="busy || !selectedBranch || sameBranch(selectedBranch, currentBranch)"
              title="Checkout branch"
            >
              <i class="fa-solid fa-arrow-right-to-bracket"></i>
            </button>
            <button
              class="btn btn-xs btn-ghost text-error"
              @click="deleteBranch(selectedBranch)"
              :disabled="busy || !selectedBranch || sameBranch(selectedBranch, currentBranch)"
              title="Delete branch"
            >
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>

          <!-- File diff (open from the working tree or the commits list) -->
          <RepoFileDiff
            v-if="selectedFile && api"
            :key="diffKey"
            :api="api"
            :file="selectedFile"
            class="flex-1 min-h-0"
            @close="closeDiff"
            @changed="onFileChanged"
          />

          <!-- Commits -->
          <div v-else class="flex-1 min-h-0 overflow-auto p-3 flex flex-col gap-2">
            <div v-if="commitsLoading" class="flex items-center gap-2 text-base-content/50 text-sm">
              <i class="fa-solid fa-spinner animate-spin"></i> Loading commits...
            </div>
            <div v-else-if="!commits.length" class="text-base-content/40 text-sm">No commits</div>
            <div v-for="commit in commits" :key="commit.id" class="card bg-base-200">
              <div class="card-body p-3 gap-1">
                <div class="flex items-center gap-2">
                  <i class="fa-solid fa-code-commit text-warning text-xs"></i>
                  <span class="font-mono text-xs opacity-60">{{ commit.short }}</span>
                  <span class="text-xs font-semibold truncate">{{ commit.message }}</span>
                  <span class="badge badge-xs badge-ghost ml-auto shrink-0">{{ commit.relative }}</span>
                </div>
                <div class="text-[10px] opacity-50">{{ commit.author }}</div>
              </div>
            </div>
          </div>
        </div>
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
      <div class="bg-base-100 border border-base-content/10 rounded-xl w-full max-w-lg shadow-xl">
        <div class="flex items-center justify-between px-4 py-3 border-b border-base-content/10">
          <h2 class="text-sm font-semibold flex items-center gap-2">
            <i class="fa-solid fa-code-merge text-warning"></i> Merge branches
          </h2>
          <button class="btn btn-xs btn-ghost" @click="showMerge = false" aria-label="Close">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <div class="px-4 py-3 flex flex-col gap-3">
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
              <ul class="max-h-32 overflow-auto flex flex-col gap-0.5 opacity-70">
                <li v-for="file in mergePreview.files" :key="file" class="truncate font-mono">{{ file }}</li>
              </ul>
            </div>
            <div v-else class="opacity-50">
              <i class="fa-solid fa-circle-info"></i> Select two different branches to compare.
            </div>
          </div>

          <div class="flex flex-col gap-1">
            <label class="text-xs opacity-60" for="merge-message">Merge commit message (optional)</label>
            <input
              id="merge-message"
              v-model="mergeMessage"
              type="text"
              class="input input-sm input-bordered w-full"
              placeholder="Merge message"
            />
          </div>
        </div>

        <div class="flex gap-2 px-4 py-3 border-t border-base-content/10">
          <button class="btn btn-sm btn-ghost grow" @click="showMerge = false">Cancel</button>
          <button
            class="btn btn-sm btn-warning grow"
            :disabled="merging || !mergeFrom || !mergeTo || sameBranch(mergeFrom, mergeTo)"
            @click="doMerge"
          >
            <i class="fa-solid fa-spinner animate-spin" v-if="merging"></i>
            <i class="fa-solid fa-code-merge" v-else></i>
            Merge {{ mergeFrom }} → {{ mergeTo }}
          </button>
        </div>
      </div>
    </div>

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