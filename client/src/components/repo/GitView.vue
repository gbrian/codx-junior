<script>
import ChangesPanel from '@/components/vibe/panels/ChangesPanel.vue'
import RepoFileDiff from '@/components/repo/RepoFileDiff.vue'
import moment from 'moment'

export default {
  name: 'GitView',
  components: { ChangesPanel, RepoFileDiff },
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
      // working tree
      selection: {},
      // Anchor for shift+click range selection: { group, path }
      selectionAnchor: null,
      selectedFile: null,
      // new branch
      showNewBranch: false,
      newBranchName: '',
      newBranchFrom: '',
      // commit
      commitMessage: '',
      committing: false,
      // merge
      showMerge: false,
      mergeFrom: '',
      mergeTo: '',
      mergeMessage: '',
      mergePreview: null,
      mergePreviewLoading: false,
      merging: false
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
    }
  },
  created() {
    this.loadRepo()
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
      this.selectedFile = {
        path: file.path,
        group,
        code: file.code,
        icon: file.icon,
        color: file.color,
        label: file.label
      }
    },

    /** Keep the diff pane in sync with the reloaded working tree */
    syncSelectedFile() {
      if (!this.selectedFile) return
      const current = this.selectedFile.group
      const order = current === 'staged'
        ? ['staged', 'changes']
        : ['changes', 'staged']

      for (const group of order) {
        const match = this.groupFiles(group).find(file => file.path === current.path || file.path === this.selectedFile.path)
        if (match) {
          this.selectedFile = {
            path: match.path,
            group,
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

    // ── Working tree operations ─────────────────────────────────────────
    async stagePaths(paths) {
      const list = paths || []
      if (!list.length || !this.api) return
      await this.runOperation(
        () => this.api.post('/api/git/repo/stage', { paths: list }),
        `${list.length} file(s) staged`
      )
      this.clearSelection()
    },

    async unstagePaths(paths) {
      const list = paths || []
      if (!list.length || !this.api) return
      await this.runOperation(
        () => this.api.post('/api/git/repo/unstage', { paths: list }),
        `${list.length} file(s) unstaged`
      )
      this.clearSelection()
    },

    async discardPaths(paths) {
      const list = paths || []
      if (!list.length || !this.api) return
      const label = list.length === 1 ? `"${list[0]}"` : `${list.length} files`
      if (!window.confirm(`Roll back ${label} to the last commit? This cannot be undone.`)) return
      await this.runOperation(
        () => this.api.post('/api/git/repo/discard', { paths: list, include_staged: true }),
        `${list.length} file(s) rolled back`
      )
      this.clearSelection()
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
        await fn()
        if (successMessage) this.notice = successMessage
        await this.loadRepo()
      } catch (ex) {
        this.error = ex?.response?.data?.detail || ex?.message || String(ex)
      } finally {
        this.busy = false
      }
    },

    // ── Remote operations ───────────────────────────────────────────────
    onFetch() {
      this.runOperation(() => this.api.post('/api/git/repo/fetch', {}), 'Fetched from remote')
    },
    onPull() {
      this.runOperation(() => this.api.post('/api/git/repo/pull', {}), 'Pulled from remote')
    },
    onPush() {
      this.runOperation(() => this.api.post('/api/git/repo/push', {}), 'Pushed to remote')
    },

    // ── Branch operations ───────────────────────────────────────────────
    onCheckout(branch) {
      if (!branch || this.sameBranch(branch, this.currentBranch)) return
      this.runOperation(
        () => this.api.post('/api/git/repo/branch/checkout', { branch }),
        `Checked out ${branch}`
      )
    },

    toggleNewBranch() {
      this.showNewBranch = !this.showNewBranch
      this.newBranchName = ''
      this.newBranchFrom = this.selectedBranch || this.currentBranch || ''
    },

    async createBranch() {
      const name = this.newBranchName.trim()
      if (!name || !this.api) return
      await this.runOperation(
        () => this.api.post('/api/git/repo/branch', {
          branch: name,
          from_branch: this.newBranchFrom || this.currentBranch
        }),
        `Branch ${name} created`
      )
      this.showNewBranch = false
      this.selectedBranch = name
      this.loadCommitsForBranch(name)
    },

    async deleteBranch(branch) {
      if (!branch || !this.api) return
      if (!window.confirm(`Delete branch "${branch}"?`)) return
      await this.runOperation(
        () => this.api.delete(`/api/git/repo/branch?branch=${encodeURIComponent(branch)}`),
        `Branch ${branch} deleted`
      )
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
        await this.api.post('/api/git/repo/commit', { message, stage_all: stageAll })
        this.notice = 'Changes committed'
        this.commitMessage = ''
        this.clearSelection()
        await this.loadRepo()
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
        await this.api.post('/api/git/repo/merge', {
          from_branch: this.mergeFrom,
          to_branch: this.mergeTo,
          message: this.mergeMessage.trim() || undefined
        })
        this.notice = `Merged ${this.mergeFrom} into ${this.mergeTo}`
        this.showMerge = false
        await this.loadRepo()
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
      <span v-if="currentBranch" class="badge badge-sm badge-primary badge-outline gap-1" title="Current branch">
        <i class="fa-solid fa-check text-[9px]"></i> {{ currentBranch }}
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

      <!-- ── Repository: working tree + branches + diff/commits ─────────── -->
      <div v-show="activeTab === 'repository'" class="grow flex overflow-hidden">
        <!-- Branches sidebar -->
        <aside class="hidden lg:flex lg:w-52 shrink-0 border-r border-base-content/10 flex-col overflow-hidden">
          <div class="flex items-center gap-1 px-2 py-1.5 border-b border-base-content/10 shrink-0">
            <span class="text-xs font-bold uppercase tracking-wide opacity-50 grow">Branches</span>
            <button class="btn btn-xs btn-ghost" @click="toggleNewBranch" title="New branch" aria-label="New branch">
              <i class="fa-solid fa-plus text-[10px]"></i>
            </button>
          </div>

          <!-- New branch form -->
          <div v-if="showNewBranch" class="p-2 border-b border-base-content/10 flex flex-col gap-1 shrink-0">
            <input
              v-model="newBranchName"
              type="text"
              placeholder="new-branch-name"
              class="input input-xs input-bordered w-full"
              @keyup.enter="createBranch"
              @keyup.esc="showNewBranch = false"
            />
            <select v-model="newBranchFrom" class="select select-xs select-bordered w-full" title="Branch from">
              <option v-for="b in branches" :key="`from-${b}`" :value="b">{{ b }}</option>
            </select>
            <div class="flex gap-1 justify-end">
              <button class="btn btn-xs btn-ghost" @click="showNewBranch = false">Cancel</button>
              <button class="btn btn-xs btn-primary" :disabled="!newBranchName.trim() || busy" @click="createBranch">Create</button>
            </div>
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
              @click="selectBranch(branch)"
            >
              <i
                class="fa-solid"
                :class="sameBranch(branch, currentBranch) ? 'fa-circle-check text-success' : 'fa-code-branch opacity-50'"
              ></i>
              <span class="truncate grow" :title="branch">{{ branch }}</span>
              <span v-if="branchCommitCount(branch)" class="badge badge-xs badge-ghost">{{ branchCommitCount(branch) }}</span>
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
            <input
              v-model="commitMessage"
              type="text"
              class="input input-xs input-bordered w-full"
              :placeholder="`Message (Ctrl+Enter to commit on '${currentBranch || 'HEAD'}')`"
              aria-label="Commit message"
              @keydown.ctrl.enter.prevent="doCommit"
              @keydown.meta.enter.prevent="doCommit"
            />
            <p class="text-[10px] opacity-50 leading-tight">{{ commitHint }}</p>
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
            <span class="font-mono text-sm font-semibold truncate" :title="selectedBranch">{{ selectedBranch || 'Select a branch' }}</span>
            <span v-if="sameBranch(selectedBranch, currentBranch)" class="badge badge-xs badge-success">current</span>
            <div class="grow"></div>

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

          <!-- File diff (open from the working tree) -->
          <RepoFileDiff
            v-if="selectedFile && api"
            :api="api"
            :file="selectedFile"
            class="grow min-h-0"
            @close="selectedFile = null"
            @changed="onFileChanged"
          />

          <!-- Commits -->
          <div v-else class="grow overflow-auto p-3 flex flex-col gap-2">
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
  </div>
</template>