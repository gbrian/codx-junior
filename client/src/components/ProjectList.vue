<script setup>
import ProjectCard from './ProjectCard.vue'
</script>

<template>
  <div class="flex flex-col gap-0 flex-1 overflow-hidden h-full">
    <!-- Search Bar -->
    <div class="input input-bordered input-sm bg-base-200 flex items-center gap-2 flex-shrink-0 mx-4 my-3">
      <i class="fa-solid fa-magnifying-glass text-base-content/50"></i>
      <input
        v-model="searchQuery"
        @input="onSearchInput"
        type="text"
        placeholder="Search projects..."
        class="flex-1 bg-transparent outline-none text-sm"
      />
      <button
        v-if="searchQuery"
        @click="clearSearch"
        class="btn btn-ghost btn-xs btn-circle"
      >
        <i class="fa-solid fa-xmark"></i>
      </button>
      <div class="divider divider-horizontal m-0"></div>
      <!-- Project Count Badge -->
      <div class="badge badge-sm badge-ghost gap-1 flex-shrink-0">
        <i class="fa-solid fa-list text-xs"></i>
        <span>{{ visibleProjectCount }}</span>
      </div>
    </div>

    <!-- Projects List (scrollable) -->
    <div class="flex-1 overflow-y-auto overflow-x-hidden border-t border-base-300">
      <!-- List Items -->
      <div v-if="sortedFilteredProjects.length > 0" class="divide-y divide-base-300">
        <!-- Child Projects Section (if any) -->
        <div v-if="childProjectsToShow.length > 0">
          <div class="sticky top-0 bg-base-100/95 backdrop-blur-sm px-4 py-2 border-b border-base-300 flex items-center gap-2">
            <i class="fa-solid fa-sitemap text-primary text-xs"></i>
            <span class="text-xs font-semibold text-base-content/70">Child Projects</span>
            <span class="badge badge-xs badge-primary/50">{{ childProjectsToShow.length }}</span>
          </div>
          <ProjectCard
            v-for="project in childProjectsToShow"
            :key="project.project_name"
            :project="project"
            :is-current="project.project_name === currentProject?.project_name"
            :current-project="currentProject"
            @select="onProjectSelect"
            @open-folder="$ui.coderOpenPath(project)"
          />
        </div>

        <!-- Other Projects Section (if child projects exist) -->
        <div v-if="childProjectsToShow.length > 0 && otherProjectsToShow.length > 0">
          <div class="sticky top-0 bg-base-100/95 backdrop-blur-sm px-4 py-2 border-b border-base-300 flex items-center gap-2">
            <i class="fa-solid fa-folder text-base-content/50 text-xs"></i>
            <span class="text-xs font-semibold text-base-content/70">Other Projects</span>
            <span class="badge badge-xs badge-ghost">{{ otherProjectsToShow.length }}</span>
          </div>
          <ProjectCard
            v-for="project in otherProjectsToShow"
            :key="project.project_name"
            :project="project"
            :is-current="project.project_name === currentProject?.project_name"
            :current-project="currentProject"
            @select="onProjectSelect"
            @open-folder="$ui.coderOpenPath(project)"
          />
        </div>

        <!-- Single Section if no child projects -->
        <div v-if="childProjectsToShow.length === 0">
          <ProjectCard
            v-for="project in sortedFilteredProjects"
            :key="project.project_name"
            :project="project"
            :is-current="project.project_name === currentProject?.project_name"
            :current-project="currentProject"
            @select="onProjectSelect"
            @open-folder="$ui.coderOpenPath(project)"
          />
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="flex flex-col items-center justify-center gap-3 h-40 text-center text-base-content/50">
        <i class="fa-solid fa-inbox text-4xl"></i>
        <div>
          <p class="font-semibold">No projects found</p>
          <p class="text-xs">{{ searchQuery ? 'Try adjusting your search' : 'Start by adding a project' }}</p>
        </div>
      </div>
    </div>

    <!-- Footer Actions -->
    <div class="flex justify-end items-center gap-2 pt-3 px-4 pb-3 border-t border-base-300 flex-shrink-0">
      <button
        @click="$emit('open-new-project')"
        class="btn btn-primary btn-sm gap-2"
      >
        <i class="fa-solid fa-folder-plus"></i>
        New Project
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    currentProject: Object
  },
  emits: ['select-project', 'open-new-project'],
  data() {
    return {
      searchQuery: '',
      debouncedQuery: '',
      debounceTimer: null,
      minChars: 3,
      debounceDelay: 300
    }
  },
  computed: {
    allProjects() {
      return this.$storex.projects.allProjects || []
    },
    activeProject() {
      return this.$storex.projects.activeProject
    },
    // Get child projects of the active project
    childProjectsOfActive() {
      if (!this.activeProject) return []
      const parentPath = this.activeProject.abs_project_path
      const normalizedParentPath = parentPath.endsWith('/') ? parentPath : `${parentPath}/`
      return this.allProjects.filter(p =>
        p.abs_project_path !== parentPath &&
        p.abs_project_path?.startsWith(normalizedParentPath)
      )
    },
    // Filter child projects based on search
    filteredChildProjects() {
      if (!this.debouncedQuery.trim() || this.debouncedQuery.length < this.minChars) {
        return this.childProjectsOfActive
      }
      const query = this.debouncedQuery.toLowerCase()
      return this.childProjectsOfActive.filter(p =>
        p.project_name.toLowerCase().includes(query)
      )
    },
    // Filter all projects (minus child projects)
    filteredOtherProjects() {
      if (!this.debouncedQuery.trim() || this.debouncedQuery.length < this.minChars) {
        return this.allProjects.filter(p =>
          !this.childProjectsOfActive.find(cp => cp.project_id === p.project_id)
        )
      }
      const query = this.debouncedQuery.toLowerCase()
      return this.allProjects
        .filter(p => !this.childProjectsOfActive.find(cp => cp.project_id === p.project_id))
        .filter(p => p.project_name.toLowerCase().includes(query))
    },
    // Sort child projects by last access
    sortedChildProjects() {
      return [...this.filteredChildProjects].sort((a, b) => {
        if (a.last_access_time && b.last_access_time) {
          return new Date(b.last_access_time) - new Date(a.last_access_time)
        }
        return a.project_name.localeCompare(b.project_name)
      })
    },
    // Sort other projects with scoring
    sortedOtherProjects() {
      const query = this.debouncedQuery.toLowerCase()
      
      if (!query.trim() || query.length < this.minChars) {
        return [...this.filteredOtherProjects].sort((a, b) => {
          if (a.last_access_time && b.last_access_time) {
            return new Date(b.last_access_time) - new Date(a.last_access_time)
          }
          return a.project_name.localeCompare(b.project_name)
        })
      }

      const scored = this.filteredOtherProjects.map(p => ({
        project: p,
        score: this.calculateMatchScore(p, query)
      }))

      return scored
        .sort((a, b) => b.score - a.score)
        .map(item => item.project)
    },
    // Projects to display with hierarchy prioritization
    childProjectsToShow() {
      return this.sortedChildProjects
    },
    otherProjectsToShow() {
      return this.sortedOtherProjects
    },
    sortedFilteredProjects() {
      return [...this.childProjectsToShow, ...this.otherProjectsToShow]
    },
    visibleProjectCount() {
      return this.sortedFilteredProjects.length
    }
  },
  methods: {
    calculateMatchScore(project, query) {
      const nameLower = project.project_name.toLowerCase()
      const pathLower = project.abs_project_path.toLowerCase()

      if (nameLower === query) return 1000
      if (nameLower.startsWith(query)) return 500
      
      const nameIndex = nameLower.indexOf(query)
      if (nameIndex !== -1) return 300 - (nameIndex * 0.1)

      if (pathLower.startsWith(query)) return 100
      if (pathLower.includes(query)) return 50

      return 0
    },
    onSearchInput() {
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer)
      }
      
      this.debounceTimer = setTimeout(() => {
        this.debouncedQuery = this.searchQuery
      }, this.debounceDelay)
    },
    clearSearch() {
      this.searchQuery = ''
      this.debouncedQuery = ''
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer)
      }
    },
    onProjectSelect(project) {
      this.$emit('select-project', project)
    }
  },
  beforeUnmount() {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer)
    }
  }
}
</script>