<script setup>
import PRView from '@/components/repo/PRView.vue'
import BranchSelector from '@/components/vibe/panels/BranchSelector.vue'
</script>

<template>
  <div class="flex flex-col h-full w-full">
    <!-- Header -->
    <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
      <i class="fa-solid fa-code-compare text-warning text-sm"></i>
      <span class="text-sm font-bold truncate grow">Changes</span>
      <button class="btn btn-xs btn-ghost" @click="loadAllProjects" :disabled="loadingChanges" title="Reload branches & changes">
        <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': loadingChanges }"></i>
      </button>
      <button class="btn btn-xs btn-ghost" @click="$emit('refresh')" title="Refresh changes">
        <i class="fa-solid fa-arrows-rotate"></i>
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loadingChanges" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/50">
      <i class="fa-solid fa-spinner text-3xl animate-spin"></i>
      <span class="text-sm font-medium">Loading changes...</span>
      <span class="text-xs opacity-60" v-if="loadingStep">{{ loadingStep }}</span>
    </div>

    <template v-else>
      <!-- No active session -->
      <div v-if="!chat" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
        <i class="fa-solid fa-inbox text-4xl"></i>
        <span class="text-sm">No active session</span>
      </div>

      <!-- No projects with git -->
      <div v-else-if="projectsWithBranches.length === 0" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
        <i class="fa-solid fa-exclamation-triangle text-4xl text-warning"></i>
        <span class="text-sm">No projects with git initialized</span>
      </div>

      <template v-else>
        <!-- Project tabs -->
        <div class="shrink-0 border-b border-base-content/10 bg-base-200/30 overflow-x-auto scrollbar-none">
          <div class="flex gap-1 px-2 py-1 min-w-max">
            <button
              v-for="proj in projectsWithBranches"
              :key="projId(proj)"
              @click="selectedProjectId = projId(proj)"
              :class="selectedProjectId === projId(proj) ? 'tab-active' : 'opacity-30 hover:underline'"
              class="tab tab-sm tab-bordered text-sm gap-1 whitespace-nowrap"
            >
              <span class="font-mono truncate max-w-[100px]">{{ proj.project_name }}</span>
              <span
                class="badge badge-xs"
                :class="changeCountClass(projId(proj))"
                v-if="changeCountByProject[projId(proj)]"
              >{{ changeCountByProject[projId(proj)] }}</span>
            </button>
          </div>
        </div>

        <!-- Branch selector -->
        <BranchSelector
          v-if="selectedProject"
          :project="selectedProject"
          :current-branch="currentBranch"
          :compare-branch="compareBranch"
          :available-branches="selectedBranches"
          :loading="false"
          @branch-changed="onBranchChanged"
          @compare-branch-changed="onCompareBranchChanged"
        />

        <!-- PRView: key forces re-mount when cache key changes -->
        <div v-if="cachedRepoChanges" class="grow min-h-0 overflow-hidden p-2">
          <PRView
            :key="cacheKey"
            ref="prView"
            :chat="chat"
            :from-branch="compareBranch"
            :to-branch="currentBranch"
            :project="selectedProject"
            :available-branches="selectedBranches"
            :repo-changes="cachedRepoChanges"
            class="h-full"
            @select-branch="onBranchSelected"
            @comment="$emit('comment', $event)"
            @change-column="$emit('change-column', $event)"
            @new-chat="$emit('new-chat', $event)"
            @chat-message="$emit('chat-message', $event)"
          />
        </div>
      </template>
    </template>
  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, default: null }
  },
  emits: ['refresh', 'select-branch', 'comment', 'change-column', 'new-chat', 'chat-message'],
  data() {
    return {
      loadingChanges: false,
      loadingStep: '',
      selectedProjectId: null,
      // projectId -> branches[]
      branchesByProject: {},
      // cacheKey -> repoChanges — always replaced as whole object for reactivity
      changesByProject: {},
      // projectId -> fileCount
      changeCountByProject: {},
      // per-project branch selections: projectId -> { current, compare }
      branchSelectionByProject: {},
    }
  },
  computed: {
    // All projects from chat + subtasks
    allProjects() {
      if (!this.chat) return []
      const map = new Map()
      const allChats = this.$storex.chats.allChats || []
      const related = [this.chat, ...allChats.filter(c => c.parent_id === this.chat.id)]
      related.forEach(c => {
        const id = this.projId(c)
        if (id && !map.has(id)) {
          const proj = this.$storex.projects.allProjectsById?.[id]
          if (proj) map.set(id, proj)
        }
      })
      return Array.from(map.values())
    },

    // Only projects that have branches loaded
    projectsWithBranches() {
      return this.allProjects.filter(p => {
        const branches = this.branchesByProject[this.projId(p)]
        return Array.isArray(branches) && branches.length > 0
      })
    },

    selectedProject() {
      if (!this.selectedProjectId) return null
      return this.$storex.projects.allProjectsById?.[this.selectedProjectId] || null
    },

    selectedBranches() {
      return this.branchesByProject[this.selectedProjectId] || []
    },

    currentBranch() {
      return this.branchSelectionByProject[this.selectedProjectId]?.current || 'main'
    },

    compareBranch() {
      return this.branchSelectionByProject[this.selectedProjectId]?.compare || 'local'
    },

    cacheKey() {
      if (!this.selectedProjectId) return null
      return `${this.selectedProjectId}:${this.compareBranch}:${this.currentBranch}`
    },

    cachedRepoChanges() {
      return this.cacheKey ? (this.changesByProject[this.cacheKey] || null) : null
    }
  },
  watch: {
    chat(newChat) {
      if (newChat?.id) this.loadAllProjects()
    },
    selectedProjectId(id) {
      if (id && !this.cachedRepoChanges) {
        this.loadChangesForProject(id)
      }
    },
    currentBranch() {
      this.loadChangesForProject(this.selectedProjectId)
    },
    compareBranch() {
      this.loadChangesForProject(this.selectedProjectId)
    }
  },
  mounted() {
    if (this.chat) this.loadAllProjects()
  },
  methods: {
    projId({ project_id, owner_project_id } = {}) {
      return project_id || owner_project_id
    },

    // Replace entire changesByProject object so Vue detects the new key reactively
    setChangesCache(key, value) {
      this.changesByProject = { ...this.changesByProject, [key]: value }
    },

    // Replace entire changeCountByProject object for reactivity
    setChangeCount(projectId, count) {
      this.changeCountByProject = { ...this.changeCountByProject, [projectId]: count }
    },

    // Replace entire branchesByProject object for reactivity
    setBranches(projectId, branches) {
      this.branchesByProject = { ...this.branchesByProject, [projectId]: branches }
    },

    // Main entry: load branches for all projects, then load changes
    async loadAllProjects() {
      if (!this.chat) return
      this.loadingChanges = true
      // Reset with fresh objects
      this.branchesByProject = {}
      this.changesByProject = {}
      this.changeCountByProject = {}
      this.branchSelectionByProject = {}

      try {
        for (const proj of this.allProjects) {
          const id = this.projId(proj)
          this.loadingStep = `Loading branches for ${proj.project_name}...`
          try {
            const branches = await proj.$api.repo.branches()
            if (Array.isArray(branches) && branches.length > 0) {
              this.setBranches(id, branches)
              this.initBranchSelection(id, branches)
            }
          } catch {
            // no git — skip
          }
        }

        // Load changes for all valid projects
        for (const proj of this.projectsWithBranches) {
          const id = this.projId(proj)
          this.loadingStep = `Loading changes for ${proj.project_name}...`
          await this.loadChangesForProject(id)
        }

        // Auto-select first project with branches — done AFTER changes are cached
        const first = this.projectsWithBranches[0]
        this.selectedProjectId = first ? this.projId(first) : null

      } finally {
        this.loadingChanges = false
        this.loadingStep = ''
      }
    },

    // Init branch selection from chat.pr_view or defaults
    initBranchSelection(projectId, branches) {
      const prConfig = this.chat?.pr_view?.pull_requests?.[projectId]
      this.branchSelectionByProject = {
        ...this.branchSelectionByProject,
        [projectId]: {
          current: prConfig?.fromBranch || branches[0] || 'main',
          compare: prConfig?.toBranch || 'local'
        }
      }
    },

    async loadChangesForProject(projectId) {
      if (!projectId) return
      const project = this.$storex.projects.allProjectsById?.[projectId]
      if (!project) return

      const sel = this.branchSelectionByProject[projectId] || {}
      const current = sel.current || 'main'
      const compare = sel.compare || 'local'
      const key = `${projectId}:${compare}:${current}`

      // Skip if already cached
      if (this.changesByProject[key]) return

      try {
        const changes = await project.$api.repo.changes({
          from_branch: current,
          to_branch: compare
        })
        // Use setter to replace whole object — guarantees Vue reactivity
        this.setChangesCache(key, changes)
        const count = Object.keys(changes?.branch_file_and_commits || {}).length
        this.setChangeCount(projectId, count)
      } catch {
        this.setChangeCount(projectId, 0)
      }
    },

    onBranchChanged(branch) {
      if (!this.selectedProjectId) return
      this.branchSelectionByProject = {
        ...this.branchSelectionByProject,
        [this.selectedProjectId]: {
          ...this.branchSelectionByProject[this.selectedProjectId],
          current: branch
        }
      }
      this.saveBranchConfig()
      this.loadChangesForProject(this.selectedProjectId)
    },

    onCompareBranchChanged(branch) {
      if (!this.selectedProjectId) return
      this.branchSelectionByProject = {
        ...this.branchSelectionByProject,
        [this.selectedProjectId]: {
          ...this.branchSelectionByProject[this.selectedProjectId],
          compare: branch
        }
      }
      this.saveBranchConfig()
      this.loadChangesForProject(this.selectedProjectId)
    },

    onBranchSelected({ fromBranch, toBranch }) {
      this.onBranchChanged(fromBranch)
      this.onCompareBranchChanged(toBranch)
      this.$emit('select-branch', { fromBranch, toBranch })
    },

    saveBranchConfig() {
      if (!this.chat || !this.selectedProjectId) return
      const sel = this.branchSelectionByProject[this.selectedProjectId]
      const updatedChat = {
        ...this.chat,
        pr_view: {
          ...(this.chat.pr_view || {}),
          pull_requests: {
            ...(this.chat.pr_view?.pull_requests || {}),
            [this.selectedProjectId]: {
              url: '',
              fromBranch: sel.current,
              toBranch: sel.compare
            }
          }
        }
      }
      this.$storex.chats.saveChat(updatedChat)
    },

    changeCountClass(projectId) {
      const count = this.changeCountByProject[projectId] || 0
      if (count === 0) return 'badge-ghost'
      if (count < 5) return 'badge-info'
      if (count < 10) return 'badge-warning'
      return 'badge-error'
    }
  }
}
</script>