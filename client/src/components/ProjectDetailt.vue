<script setup>
import Modal from './Modal.vue'
</script>

<template>
  <div class="w-full">
    <!-- Trigger Button showing selected project -->
    <button
      @click="openModal"
      class="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-base-content/10 hover:border-base-content/15 rounded-lg text-base-content/70 hover: text-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50 w-full tooltip tooltip-right"
      :data-tip="project?.project_name"
    >
      <img 
        v-if="project?.project_icon" 
        :src="project.project_icon" 
        :alt="project.project_name" 
        class="w-5 h-5 rounded-md" 
      />
      <span v-if="!iconify" class="truncate">{{ project?.project_name }}</span>
      <i v-if="!iconify" class="fa-solid fa-right-left text-xs ml-auto"></i>
    </button>

    <!-- Modal: Project hierarchy (Parent / Children) + More projects -->
    <Modal v-if="isModalOpen" :close="true" @close="onModalClose">
      <template #header>
        <div class="flex items-center justify-between w-full gap-4">
          <h2 class="text-lg font-semibold  flex items-center gap-2">
            <i class="fa-solid fa-cube"></i>
            Projects
          </h2>
          <div class="flex-1 max-w-xs">
            <div class="relative">
              <i class="fa-solid fa-search absolute left-3 top-1/2 -translate-y-1/2 text-base-content/30 text-sm"></i>
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Search projects..."
                class="w-full bg-white/5 border border-base-content/10 rounded-lg pl-9 pr-3 py-2 text-xs  placeholder:text-base-content/30 outline-none focus:border-primary/50 focus:bg-white/[0.08] transition-all duration-200"
              />
            </div>
          </div>
        </div>
      </template>

      <!-- Content -->
      <div class="flex flex-col gap-4">
        <!-- Ordered sections: Parent Project -> Child Projects -> More/Recent (or Search Results) -->
        <div class="flex flex-col gap-4 max-h-96 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent pr-2">
          <div
            v-for="section in sections"
            :key="section.key"
            class="flex flex-col gap-2"
          >
            <!-- Section Header -->
            <div class="flex items-center justify-between">
              <h3 class="text-xs font-semibold text-base-content/60 uppercase tracking-wide flex items-center gap-2">
                <i :class="section.icon" class="text-[10px]"></i>
                {{ section.label }}
              </h3>
              <span class="text-[10px] font-medium text-base-content/30">{{ section.projects.length }}</span>
            </div>

            <!-- Section Items -->
            <button
              v-for="project in section.projects"
              :key="project.project_id"
              @click="onProjectSelected(project)"
              class="group flex items-start gap-3 p-3 bg-base-300 border rounded-lg hover:border-primary/30 hover:bg-[#1f1f1f] transition-all duration-200 text-left"
              :class="section.key === 'parent'
                ? 'border-primary/30 ring-1 ring-primary/20'
                : 'border-base-content/5'"
            >
              <!-- Icon -->
              <img
                v-if="project.project_icon"
                :src="project.project_icon"
                :alt="project.project_name"
                class="w-6 h-6 rounded-md flex-shrink-0 mt-0.5"
              />
              <i v-else class="fa-solid fa-folder text-base flex-shrink-0 mt-1"></i>

              <!-- Info -->
              <div class="flex-1 min-w-0">
                <div class="font-medium  transition-colors truncate">
                  {{ project.project_name }}
                </div>
                <div class="text-xs text-base-content/40 truncate">{{ project.abs_project_path }}</div>
                <div class="flex gap-2 mt-2 text-xs text-base-content/50">
                  <span v-if="project.metrics?.file_count" class="flex items-center gap-1">
                    <i class="fa-solid fa-file-lines text-primary/60"></i>
                    {{ project.metrics.file_count }}
                  </span>
                  <span v-if="project.metrics?.number_of_chats" class="flex items-center gap-1 text-info/70">
                    <i class="fa-brands fa-trello"></i>
                    {{ project.metrics.number_of_chats }}
                  </span>
                  <span class="ml-auto text-base-content/30">{{ formatLastUpdate(project) }}</span>
                </div>
              </div>
            </button>
          </div>

          <!-- Empty state -->
          <div v-if="totalVisibleCount === 0" class="py-8 text-center">
            <i class="fa-solid fa-inbox text-base-content/20 text-2xl mb-2 block"></i>
            <p class="text-xs text-base-content/40">{{ emptyStateMessage }}</p>
          </div>
        </div>

        <!-- More Projects / Show less -->
        <button
          v-if="showMoreButton"
          @click="showAllProjects = true"
          class="px-3 py-2 w-full text-sm font-medium border border-primary/20 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 hover:bg-primary/10"
        >
          <i class="fa-solid fa-ellipsis"></i>
          More Projects ({{ otherProjectsCount - displayLimit }})
        </button>

        <button
          v-if="showLessButton"
          @click="showAllProjects = false"
          class="px-3 py-2 w-full text-xs font-medium text-base-content/50 hover:text-base-content/80 bg-white/5 hover:bg-white/10 border border-base-content/5 rounded-lg transition-all duration-200"
        >
          Show less
        </button>
      </div>
    </Modal>
  </div>
</template>

<script>
import moment from 'moment'

export default {
  props: {
    displayLimit: {
      type: Number,
      default: 5
    },
    modelValue: {
      type: Object,
      default: () => null
    },
    iconify: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update:modelValue', 'select', 'open', 'close'],
  data() {
    return {
      isModalOpen: false,
      showAllProjects: false,
      searchQuery: ''
    }
  },
  computed: {
    project() {
      return this.modelValue || this.$project
    },

    // Get all projects directly from store (already sorted by last update)
    allProjects() {
      return this.$projects?.allProjects || []
    },

    // Parent of the current project (path based), if any
    parentProject() {
      const current = this.project
      const childPath = current?.abs_project_path
      if (!childPath) return null
      return this.allProjects.find(p => {
        if (p.project_id === current.project_id) return false
        if (p.abs_project_path === childPath) return false
        const parentPath = p.abs_project_path?.endsWith('/')
          ? p.abs_project_path
          : `${p.abs_project_path}/`
        return childPath.startsWith(parentPath)
      }) || null
    },

    // Child projects of the current project (path based)
    childProjects() {
      const current = this.project
      const parentPath = current?.abs_project_path
      if (!parentPath) return []
      const normalizedParentPath = parentPath.endsWith('/') ? parentPath : `${parentPath}/`
      return this.allProjects.filter(p =>
        p.project_id !== current.project_id &&
        p.abs_project_path !== parentPath &&
        p.abs_project_path?.startsWith(normalizedParentPath)
      )
    },

    // Every project that is not the current one, its parent nor its children
    otherProjects() {
      const excluded = new Set(
        [this.project?.project_id, this.parentProject?.project_id]
          .concat(this.childProjects.map(p => p.project_id))
          .filter(Boolean)
      )
      return this.allProjects.filter(p => !excluded.has(p.project_id))
    },

    // Total count of "other" projects (used by the More option)
    otherProjectsCount() {
      return this.otherProjects.length
    },

    // Limited list of the other projects (fully expanded when More is used)
    otherProjectsToDisplay() {
      if (this.showAllProjects) return this.otherProjects
      return this.otherProjects.slice(0, this.displayLimit)
    },

    isSearching() {
      return !!this.searchQuery.trim()
    },

    // When searching, filter ALL projects
    searchResults() {
      return this.allProjects.filter(p => this.matchesSearch(p))
    },

    // Ordered sections shown top down: Parent -> Children -> More (or Search Results)
    sections() {
      if (this.isSearching) {
        return [{
          key: 'search',
          label: 'Search Results',
          icon: 'fa-solid fa-magnifying-glass',
          projects: this.searchResults
        }]
      }

      const sections = []

      // 1) Current project parent (if any)
      if (this.parentProject) {
        sections.push({
          key: 'parent',
          label: 'Parent Project',
          icon: 'fa-solid fa-arrow-up',
          projects: [this.parentProject]
        })
      }

      // 2) Current project children (if any)
      if (this.childProjects.length) {
        sections.push({
          key: 'children',
          label: 'Child Projects',
          icon: 'fa-solid fa-sitemap',
          projects: this.childProjects
        })
      }

      // 3) More option (remaining projects)
      if (this.otherProjectsToDisplay.length) {
        sections.push({
          key: 'more',
          label: this.showAllProjects ? 'Other Projects' : 'More',
          icon: 'fa-solid fa-folder',
          projects: this.otherProjectsToDisplay
        })
      }

      return sections
    },

    // Total projects currently visible (used for the empty state)
    totalVisibleCount() {
      return this.sections.reduce((total, section) => total + section.projects.length, 0)
    },

    // Empty state message based on current state
    emptyStateMessage() {
      if (this.isSearching) return 'No projects match your search'
      return 'No projects available'
    },

    // Show "More Projects" only when not searching, collapsed and more projects exist
    showMoreButton() {
      return !this.isSearching && !this.showAllProjects && this.otherProjectsCount > this.displayLimit
    },

    // Show "Show less" only when the list has been expanded
    showLessButton() {
      return !this.isSearching && this.showAllProjects && this.otherProjectsCount > this.displayLimit
    }
  },

  methods: {
    openModal() {
      this.isModalOpen = true
      this.$emit('open')
    },

    closeModal() {
      if (!this.isModalOpen) return
      this.isModalOpen = false
      this.showAllProjects = false
      this.searchQuery = ''
      this.$emit('close')
    },

    onProjectSelected(project) {
      this.$emit('update:modelValue', project)
      this.$emit('select', project)
      this.closeModal()
    },

    onModalClose() {
      this.closeModal()
    },

    formatLastUpdate(project) {
      const chats = this.$storex?.chats?.allChats || []
      const lastChat = chats
        .filter(c => c.project_id === project.project_id || c.owner_project_id === project.project_id)
        .sort((a, b) => {
          const timeA = a.updated_at ? new Date(a.updated_at).getTime() : 0
          const timeB = b.updated_at ? new Date(b.updated_at).getTime() : 0
          return timeB - timeA
        })[0]

      if (!lastChat) return 'Never'

      const updateTime = lastChat.updated_at || lastChat.created_at
      if (!updateTime) return 'Never'

      const now = moment()
      const then = moment(updateTime)
      const diffHours = now.diff(then, 'hours')
      const diffDays = now.diff(then, 'days')

      if (diffHours < 1) return 'Now'
      if (diffHours < 24) return `${diffHours}h ago`
      if (diffDays < 7) return `${diffDays}d ago`

      return then.format('MMM DD')
    },

    matchesSearch(project) {
      const query = this.searchQuery.toLowerCase()
      return (
        project.project_name.toLowerCase().includes(query) ||
        project.abs_project_path.toLowerCase().includes(query)
      )
    }
  }
}
</script>