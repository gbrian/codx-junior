<script setup>
import PRView from '@/components/repo/PRView.vue'
import PRViewer from '@/components/repo/PRViewer.vue'
import BranchSelector from '@/components/vibe/panels/BranchSelector.vue'
</script>

<template>
  <div class="flex flex-col h-full w-full overflow-auto">
    <!-- Header -->
    <div class="flex items-center gap-2 px-2 py-1.5 bg-base-200/60 shrink-0 border-b border-base-content/10">
      <i class="fa-solid fa-code-compare text-warning text-sm"></i>
      <span class="text-sm font-bold truncate grow">Changes</span>
      <button 
        v-if="availableProjectsToAdd.length > 0"
        class="btn btn-xs btn-ghost" 
        @click="toggleAddProjectdropdown" 
        title="Add more projects"
      >
        <i class="fa-solid fa-plus text-base-content/60"></i>
      </button>
      <button class="btn btn-xs btn-ghost" @click="loadAllProjects" :disabled="loadingChanges" title="Reload branches & changes">
        <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': loadingChanges }"></i>
      </button>
      <button class="btn btn-xs btn-ghost" @click="$emit('refresh')" title="Refresh changes">
        <i class="fa-solid fa-arrows-rotate"></i>
      </button>

      <!-- Add Projects dropdown Menu -->
      <div 
        v-if="showAddProjectdropdown && availableProjectsToAdd.length > 0"
        class="absolute top-12 right-2 dropdown-content bg-base-100 menu bg-base-100 rounded-box z-50 w-64 p-2 shadow border border-base-content/10"
      >
        <li v-for="proj in availableProjectsToAdd" :key="projId(proj)">
          <a @click="addProjectToPanel(proj)" class="text-info gap-2">
            <i class="fa-solid fa-plus"></i>
            <span class="truncate">{{ proj.project_name }}</span>
          </a>
        </li>
      </div>
    </div>

    <!-- Loading state: only replaces the panel while there is nothing to show yet,
         so reloading keeps the branch selector reachable -->
    <div v-if="loadingChanges && !cachedRepoChanges" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/50">
      <i class="fa-solid fa-spinner text-3xl animate-spin"></i>
      <span class="text-sm font-medium">Loading changes...</span>
      <span class="text-xs opacity-60" v-if="loadingStep">{{ loadingStep }}</span>
    </div>

    <template v-else>
      <!-- No active session (needs a chat or a project to work with) -->
      <div v-if="!chat && !project" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
        <i class="fa-solid fa-inbox text-4xl"></i>
        <span class="text-sm">No active session</span>
      </div>

      <!-- No active projects -->
      <div v-else-if="projectsWithBranches.length === 0" class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40">
        <i class="fa-solid fa-exclamation-triangle text-4xl text-warning"></i>
        <span class="text-sm">No projects added. Click + to add projects</span>
      </div>

      <template v-else>
        <!-- Project selector + Branch selector row (chat mode only).
             Standalone mode uses the BranchSelector inside PRViewer. -->
        <div v-if="chat" class="shrink-0 border-b border-base-content/10 bg-base-200/30 px-2 py-2">
          <div class="flex items-center gap-3">
            <!-- Project dropdown -->
            <div class="dropdown dropdown-hover">
              <button 
                class="btn btn-sm btn-ghost gap-2 min-w-[200px] justify-start"
                :title="selectedProject?.project_name"
              >
                <i class="fa-solid fa-folder text-base-content/60"></i>
                <span class="truncate font-mono text-sm">{{ selectedProject?.project_name || 'Select project' }}</span>
                <span
                  class="badge badge-xs ml-auto"
                  :class="changeCountClass(selectedProjectId)"
                  v-if="changeCountByProject[selectedProjectId]"
                >
                  {{ changeCountByProject[selectedProjectId] }}
                </span>
              </button>
              <ul class="dropdown-content bg-base-100 menu bg-base-100 rounded-box z-50 w-64 p-2 shadow border border-base-content/10">
                <li v-for="proj in projectsWithBranches" :key="projId(proj)">
                  <a 
                    @click="selectedProjectId = projId(proj)"
                    :class="{ active: selectedProjectId === projId(proj) }"
                    class="flex justify-between items-center group"
                  >
                    <div class="flex justify-between flex-1">
                      <span class="truncate">{{ proj.project_name }}</span>
                      <span
                        class="badge badge-xs"
                        :class="changeCountClass(projId(proj))"
                        v-if="changeCountByProject[projId(proj)]"
                      >
                        {{ changeCountByProject[projId(proj)] }}
                      </span>
                    </div>
                    <!-- Remove button visible on hover -->
                    <button
                      @click.stop="removeProjectFromPanel(projId(proj))"
                      class="btn btn-xs btn-ghost opacity-0 group-hover:opacity-100 transition-opacity ml-2"
                      title="Remove project"
                    >
                      <i class="fa-solid fa-times text-error text-xs"></i>
                    </button>
                  </a>
                </li>
                <!-- Divider -->
                <li v-if="availableProjectsToAdd.length > 0" class="divider my-1"></li>
                <!-- Add more projects section -->
                <li v-for="proj in availableProjectsToAdd" :key="projId(proj)">
                  <a @click="addProjectToPanel(proj)" class="text-info gap-2">
                    <i class="fa-solid fa-plus"></i>
                    <span class="truncate">{{ proj.project_name }}</span>
                  </a>
                </li>
              </ul>
            </div>

            <!-- Branch selector: left = source (from_branch), right = target (to_branch) -->
            <div class="grow min-h-0">
              <BranchSelector
                v-if="selectedProject"
                :project="selectedProject"
                :current-branch="fromBranch"
                :compare-branch="toBranch"
                :available-branches="selectedBranches"
                :loading="loadingChanges"
                @branch-changed="onFromBranchChanged"
                @compare-branch-changed="onToBranchChanged"
              />
            </div>
          </div>
        </div>

        <!-- Chat mode: full PRView (comments, columns, sub-chats) -->
        <div v-if="chat && cachedRepoChanges" class="grow min-h-0 overflow-hidden p-2">
          <!-- Key forces re-mount when the branch pair cache key changes -->
          <PRView
            :key="cacheKey"
            ref="prView"
            :chat="chat"
            :from-branch="fromBranch"
            :to-branch="toBranch"
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

        <!-- Standalone mode (no chat): the viewer is always mounted so the branch
             pair stays selectable even when the comparison has no changes -->
        <div v-else-if="!chat && selectedProject" class="grow min-h-0 overflow-hidden p-2">
          <PRViewer
            :key="cacheKey"
            :project="selectedProject"
            :from-branch="fromBranch"
            :to-branch="toBranch"
            :available-branches="selectedBranches"
            :repo-changes="cachedRepoChanges"
            :loading="loadingChanges"
            class="h-full"
            @refresh="loadChangesForProject(selectedProjectId, true)"
            @branch-changed="onFromBranchChanged"
            @compare-branch-changed="onToBranchChanged"
            @open-file="onOpenFile"
            @open-chat="$emit('open-chat', $event)"
            @jump-to-message="$emit('jump-to-message', $event)"
          />
        </div>

        <!-- Standalone mode without a selected project -->
        <div
          v-else-if="!chat"
          class="grow flex flex-col items-center justify-center gap-3 p-4 text-base-content/40"
        >
          <i class="fa-solid fa-code-compare text-4xl"></i>
          <span class="text-sm">No changes to compare</span>
        </div>
      </template>
    </template>
  </div>
</template>

<script>
export default {
  props: {
    // Chat mode: projects are derived from the chat, its subtasks and chat.pr_view
    chat: { type: Object, default: null },
    // Standalone mode (e.g. embedded in GitView): project to compare branches for
    project: { type: Object, default: null }
  },
  emits: ['refresh', 'select-branch', 'comment', 'change-column', 'new-chat', 'chat-message', 'open-chat', 'jump-to-message'],
  data() {
    return {
      loadingChanges: false,
      loadingStep: '',
      selectedProjectId: null,
      branchesByProject: {},
      changesByProject: {},
      changeCountByProject: {},
      // per-project branch pair: projectId -> { from, to }
      //   from = source branch (from_branch, left selector) - the branch that will be merged
      //   to   = target branch (to_branch, right selector) - where the source is merged into
      branchSelectionByProject: {},
      showAddProjectdropdown: false
    }
  },
  computed: {
    chatProject() {
      return this.chat ? this.$chats.chatProject(this.chat) : null
    },

    relatedProjects() {
      if (!this.chat) return []
      
      const related = new Map()
      const state = this.chatProject.$state

      // Get child projects from state getter
      const childProjects = state.childProjects || []
      childProjects.forEach(p => {
        const id = this.projId(p)
        if (id) related.set(id, p)
      })

      // Get linked projects from state getter
      const linkedProjects = state.linkedProjects || []
      linkedProjects.forEach(p => {
        const id = this.projId(p)
        if (id) related.set(id, p)
      })

      return Array.from(related.values())
    },

    activeProjectIds() {
      // First priority: use pr_view if it exists
      if (this.chat?.pr_view?.pull_requests) {
        return Object.keys(this.chat.pr_view.pull_requests)
      }

      // Fallback: use chat's own project_id or owner_project_id for first load
      const chatProjectId = this.chat?.project_id || this.chat?.owner_project_id
      if (chatProjectId) return [chatProjectId]

      // Standalone: the project given as prop
      const projectId = this.project ? this.projId(this.project) : null
      return projectId ? [projectId] : []
    },

    projectsWithBranches() {
      return this.activeProjectIds
        .map(id => this.$storex.projects.allProjectsById?.[id])
        .filter(p => p && Array.isArray(this.branchesByProject[this.projId(p)]) && this.branchesByProject[this.projId(p)].length > 0)
    },

    availableProjectsToAdd() {
      return this.relatedProjects.filter(p => {
        const id = this.projId(p)
        return !this.activeProjectIds.includes(id)
      })
    },

    selectedProject() {
      if (!this.selectedProjectId) return null
      return this.$storex.projects.allProjectsById?.[this.selectedProjectId] || this.project || null
    },

    selectedBranches() {
      return this.branchesByProject[this.selectedProjectId] || []
    },

    // Left selector: source branch (from_branch) - what will be merged
    fromBranch() {
      return this.branchSelectionByProject[this.selectedProjectId]?.from || 'main'
    },

    // Right selector: target branch (to_branch) - where the source is merged into
    toBranch() {
      return this.branchSelectionByProject[this.selectedProjectId]?.to || 'local'
    },

    cacheKey() {
      if (!this.selectedProjectId) return null
      return `${this.selectedProjectId}:${this.fromBranch}:${this.toBranch}`
    },

    cachedRepoChanges() {
      return this.cacheKey ? (this.changesByProject[this.cacheKey] || null) : null
    }
  },
  watch: {
    chat(newChat) {
      if (newChat?.id) this.loadAllProjects()
    },
    project(newProject, previousProject) {
      if (!newProject) return
      if (newProject.project_id === previousProject?.project_id) return
      if (newProject.project_id !== this.selectedProjectId) this.loadAllProjects()
    },
    selectedProjectId(id) {
      if (id && !this.cachedRepoChanges) {
        this.loadChangesForProject(id)
      }
    },
    fromBranch() {
      this.loadChangesForProject(this.selectedProjectId)
    },
    toBranch() {
      this.loadChangesForProject(this.selectedProjectId)
    }
  },
  mounted() {
    if (this.chat || this.project) this.loadAllProjects()
    document.addEventListener('click', this.closedropdown)
  },
  beforeUnmount() {
    document.removeEventListener('click', this.closedropdown)
  },
  methods: {
    projId({ project_id, owner_project_id } = {}) {
      return project_id || owner_project_id
    },

    toggleAddProjectdropdown() {
      this.showAddProjectdropdown = !this.showAddProjectdropdown
    },

    closedropdown(event) {
      const headerBtn = event.target.closest('[title="Add more projects"]')
      const dropdown = event.target.closest('.dropdown-content bg-base-100')
      if (!headerBtn && !dropdown) {
        this.showAddProjectdropdown = false
      }
    },

    setChangesCache(key, value) {
      this.changesByProject = { ...this.changesByProject, [key]: value }
    },

    setChangeCount(projectId, count) {
      this.changeCountByProject = { ...this.changeCountByProject, [projectId]: count }
    },

    setBranches(projectId, branches) {
      this.branchesByProject = { ...this.branchesByProject, [projectId]: branches }
    },

    async loadBranchesForProject(project) {
      const id = this.projId(project)
      if (!id) return false

      try {
        const { branches } = await project.$api.repo.branches()
        if (Array.isArray(branches) && branches.length > 0) {
          this.setBranches(id, branches)
          this.initBranchSelection(id, branches)
          return true
        }
        return false
      } catch {
        return false
      }
    },

    async loadAllProjects() {
      if (!this.activeProjectIds.length) return
      this.loadingChanges = true
      this.branchesByProject = {}
      this.changesByProject = {}
      this.changeCountByProject = {}
      this.branchSelectionByProject = {}

      try {
        // Load branches for all active projects from pr_view
        for (const projectId of this.activeProjectIds) {
          const project = this.$storex.projects.allProjectsById?.[projectId]
          if (!project) continue
          
          this.loadingStep = `Loading branches for ${project.project_name}...`
          await this.loadBranchesForProject(project)
        }

        // Load changes for projects with branches
        for (const proj of this.projectsWithBranches) {
          const id = this.projId(proj)
          this.loadingStep = `Loading changes for ${proj.project_name}...`
          await this.loadChangesForProject(id)
        }

        // Select first project if none selected
        const first = this.projectsWithBranches[0]
        this.selectedProjectId = first ? this.projId(first) : null

      } finally {
        this.loadingChanges = false
        this.loadingStep = ''
      }
    },

    async addProjectToPanel(project) {
      if (!this.chat) return
      const id = this.projId(project)
      if (!id) return

      // Create entry in pr_view with empty config
      const updatedChat = {
        ...this.chat,
        pr_view: {
          ...(this.chat.pr_view || {}),
          pull_requests: {
            ...(this.chat.pr_view?.pull_requests || {}),
            [id]: {
              url: '',
              fromBranch: '',
              toBranch: ''
            }
          }
        }
      }

      // Save to storage immediately
      await this.$storex.chats.saveChat(updatedChat)
      this.showAddProjectdropdown = false

      // Load branches for newly added project
      this.loadingStep = `Loading branches for ${project.project_name}...`
      const hasBranches = await this.loadBranchesForProject(project)

      if (hasBranches) {
        // Load changes for added project
        this.loadingStep = `Loading changes for ${project.project_name}...`
        await this.loadChangesForProject(id)

        // Select the newly added project
        this.selectedProjectId = id
      }
    },

    async removeProjectFromPanel(projectId) {
      if (!this.chat) return
      const project = this.$storex.projects.allProjectsById?.[projectId]
      if (!project) return

      // Remove from pr_view
      const { [projectId]: _, ...remainingProjects } = this.chat.pr_view?.pull_requests || {}
      const updatedChat = {
        ...this.chat,
        pr_view: {
          ...(this.chat.pr_view || {}),
          pull_requests: remainingProjects
        }
      }

      // Save to storage immediately
      await this.$storex.chats.saveChat(updatedChat)

      // Clear data for removed project
      const keysToDelete = Object.keys(this.changesByProject).filter(key => 
        key.startsWith(`${projectId}:`)
      )
      const newChanges = { ...this.changesByProject }
      keysToDelete.forEach(key => delete newChanges[key])
      this.changesByProject = newChanges

      // Clear other data
      const { [projectId]: __, ...restBranches } = this.branchesByProject
      const { [projectId]: ___, ...restCounts } = this.changeCountByProject
      const { [projectId]: ____, ...restSelection } = this.branchSelectionByProject

      this.branchesByProject = restBranches
      this.changeCountByProject = restCounts
      this.branchSelectionByProject = restSelection

      // Reset selection if removed project is selected
      if (this.selectedProjectId === projectId) {
        const first = this.projectsWithBranches[0]
        this.selectedProjectId = first ? this.projId(first) : null
      }
    },

    initBranchSelection(projectId, branches) {
      const prConfig = this.chat?.pr_view?.pull_requests?.[projectId]
      this.branchSelectionByProject = {
        ...this.branchSelectionByProject,
        [projectId]: {
          // from = source (left selector), to = target (right selector)
          from: prConfig?.fromBranch || branches[0] || 'main',
          to: prConfig?.toBranch || 'local'
        }
      }
    },

    async loadChangesForProject(projectId, force = false) {
      if (!projectId) return
      const project = this.$storex.projects.allProjectsById?.[projectId]
      if (!project) return

      const sel = this.branchSelectionByProject[projectId] || {}
      const from = sel.from || 'main'
      const to = sel.to || 'local'
      const key = `${projectId}:${from}:${to}`

      if (!force && this.changesByProject[key]) return

      try {
        const changes = await project.$api.repo.changes({
          from_branch: from,
          to_branch: to
        })
        this.setChangesCache(key, changes)
        const count = Object.keys(changes?.branch_file_and_commits || {}).length
        this.setChangeCount(projectId, count)
      } catch (ex) {
        // Empty/identical branch pairs (or a git error) must not lock the user
        // out of the branch selectors: cache an empty, valid result instead.
        console.warn('Unable to load branch changes:', ex)
        this.setChangesCache(key, {
          repo_path: project.abs_project_path || '',
          branch_file_and_commits: {}
        })
        this.setChangeCount(projectId, 0)
      }
    },

    /** Left selector changed: source branch (from_branch) */
    onFromBranchChanged(branch) {
      if (!this.selectedProjectId) return
      this.branchSelectionByProject = {
        ...this.branchSelectionByProject,
        [this.selectedProjectId]: {
          ...this.branchSelectionByProject[this.selectedProjectId],
          from: branch
        }
      }
      this.saveBranchConfig()
      this.loadChangesForProject(this.selectedProjectId)
    },

    /** Right selector changed: target branch (to_branch) */
    onToBranchChanged(branch) {
      if (!this.selectedProjectId) return
      this.branchSelectionByProject = {
        ...this.branchSelectionByProject,
        [this.selectedProjectId]: {
          ...this.branchSelectionByProject[this.selectedProjectId],
          to: branch
        }
      }
      this.saveBranchConfig()
      this.loadChangesForProject(this.selectedProjectId)
    },

    onBranchSelected({ fromBranch, toBranch }) {
      this.onFromBranchChanged(fromBranch)
      this.onToBranchChanged(toBranch)
      this.$emit('select-branch', { fromBranch, toBranch })
    },

    onOpenFile(filePath) {
      if (!filePath) return
      this.$ui.openProjectFile(filePath)
    },

    saveBranchConfig() {
      if (!this.chat || !this.selectedProjectId) return
      const sel = this.branchSelectionByProject[this.selectedProjectId]
      if (!sel) return
      const updatedChat = {
        ...this.chat,
        pr_view: {
          ...(this.chat.pr_view || {}),
          pull_requests: {
            ...(this.chat.pr_view?.pull_requests || {}),
            [this.selectedProjectId]: {
              url: '',
              fromBranch: sel.from,
              toBranch: sel.to
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