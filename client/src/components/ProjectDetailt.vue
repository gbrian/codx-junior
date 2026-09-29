<script setup>
import Modal from './Modal.vue'
</script>

<template>
  <div class="w-full">
    <!-- Trigger Button showing selected project -->
    <button
      @click="isModalOpen = true"
      class="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/15 rounded-lg text-white/70 hover:text-white text-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/50"
    >
      <img 
        v-if="project?.project_icon" 
        :src="project.project_icon" 
        :alt="project.project_name" 
        class="w-5 h-5 rounded-md" 
      />
      <i v-else class="fa-solid fa-folder text-primary"></i>
      <span class="truncate">{{ project?.project_name || 'Select Project' }}</span>
      <i class="fa-solid fa-chevron-down text-xs ml-auto"></i>
    </button>

    <!-- Modal: Recent Projects with Search & More -->
    <Modal v-if="isModalOpen" :close="true" @close="onModalClose">
      <template #header>
        <div class="flex items-center justify-between w-full gap-4">
          <h2 class="text-lg font-semibold text-white flex items-center gap-2">
            <i class="fa-solid fa-folder-open text-primary"></i>
            Projects
          </h2>
          <div class="flex-1 max-w-xs">
            <div class="relative">
              <i class="fa-solid fa-search absolute left-3 top-1/2 -translate-y-1/2 text-white/30 text-sm"></i>
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Search projects..."
                class="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder:text-white/30 outline-none focus:border-primary/50 focus:bg-white/[0.08] transition-all duration-200"
              />
            </div>
          </div>
        </div>
      </template>

      <!-- Content -->
      <div class="flex flex-col gap-4">
        <!-- Section Header -->
        <h3 class="text-xs font-semibold text-white/60 uppercase tracking-wide">
          {{ sectionLabel }}
        </h3>

        <!-- Unified Results List -->
        <div class="flex flex-col gap-2 max-h-64 overflow-y-auto scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent pr-2">
          <button
            v-for="project in displayedProjects"
            :key="project.project_id"
            @click="onProjectSelected(project)"
            class="group flex items-start gap-3 p-3 bg-[#1a1a1a] border border-white/5 rounded-lg hover:border-primary/30 hover:bg-[#1f1f1f] transition-all duration-200 text-left"
          >
            <!-- Icon -->
            <img
              v-if="project.project_icon"
              :src="project.project_icon"
              :alt="project.project_name"
              class="w-6 h-6 rounded-md flex-shrink-0 mt-0.5"
            />
            <i v-else class="fa-solid fa-folder text-primary/60 text-base flex-shrink-0 mt-1"></i>

            <!-- Info -->
            <div class="flex-1 min-w-0">
              <div class="font-medium text-white group-hover:text-primary transition-colors truncate">
                {{ project.project_name }}
              </div>
              <div class="text-xs text-white/40 truncate">{{ project.abs_project_path }}</div>
              <div class="flex gap-2 mt-2 text-xs text-white/50">
                <span v-if="project.metrics?.file_count" class="flex items-center gap-1">
                  <i class="fa-solid fa-file-lines text-primary/60"></i>
                  {{ project.metrics.file_count }}
                </span>
                <span v-if="project.metrics?.number_of_chats" class="flex items-center gap-1 text-info/70">
                  <i class="fa-brands fa-trello"></i>
                  {{ project.metrics.number_of_chats }}
                </span>
                <span class="ml-auto text-white/30">{{ formatLastUpdate(project) }}</span>
              </div>
            </div>
          </button>

          <!-- Empty state -->
          <div v-if="displayedProjects.length === 0" class="py-8 text-center">
            <i class="fa-solid fa-inbox text-white/20 text-2xl mb-2 block"></i>
            <p class="text-xs text-white/40">{{ emptyStateMessage }}</p>
          </div>
        </div>

        <!-- Load More / Back to Recent Button -->
        <button
          v-if="showLoadMoreButton"
          @click="showAllProjects = true"
          class="px-3 py-2 text-sm font-medium text-primary hover:text-primary/80 bg-primary/10 hover:bg-primary/20 border border-primary/20 rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
        >
          <i class="fa-solid fa-ellipsis"></i>
          More Projects ({{ totalProjectsCount - displayLimit }})
        </button>

        <button
          v-if="showBackButton"
          @click="showAllProjects = false"
          class="px-3 py-2 w-full text-xs font-medium text-white/50 hover:text-white/80 bg-white/5 hover:bg-white/10 border border-white/5 rounded-lg transition-all duration-200"
        >
          Back to Recent
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
    }
  },
  emits: ['update:modelValue', 'select'],
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

    // Total count of all projects
    totalProjectsCount() {
      return this.allProjects.length
    },

    // When filtering: use all projects, otherwise use paginated recent
    baseProjects() {
      if (this.searchQuery) {
        // When searching, filter ALL projects
        return this.allProjects.filter(p => this.matchesSearch(p))
      }
      // When not searching, show paginated recent projects
      if (this.showAllProjects) {
        return this.allProjects
      }
      return this.allProjects.slice(0, this.displayLimit)
    },

    // Display projects (baseProjects is already filtered if searching)
    displayedProjects() {
      return this.baseProjects
    },

    // Section label based on current state
    sectionLabel() {
      if (this.searchQuery) return 'Search Results'
      if (this.showAllProjects) return 'All Recent'
      return 'Recent'
    },

    // Empty state message based on current state
    emptyStateMessage() {
      if (this.searchQuery) return 'No projects match your search'
      return 'No recent projects'
    },

    // Show "Load More" button: only when not searching and on Recent view and more projects exist
    showLoadMoreButton() {
      return !this.searchQuery && !this.showAllProjects && this.totalProjectsCount > this.displayLimit
    },

    // Show "Back to Recent" button: only when expanded to All Recent and not searching
    showBackButton() {
      return !this.searchQuery && this.showAllProjects
    }
  },

  methods: {
    onProjectSelected(project) {
      this.$emit('update:modelValue', project)
      this.$emit('select', project)
      this.isModalOpen = false
      this.showAllProjects = false
      this.searchQuery = ''
    },

    onModalClose() {
      this.isModalOpen = false
      this.showAllProjects = false
      this.searchQuery = ''
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