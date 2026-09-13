<script setup>
import EditProfile from '@/components/EditProfile.vue'
import ProfileCard from '@/components/ProfileCard.vue';
</script>
<template>
  <div class="p-1 md:p-2 h-full overflow-auto">
    <EditProfile 
      :profile="selectedProfile"
      :allProfiles="profiles"
      :loading="loadingProfile"
      @save="saveSelectedProfile"
      @cancel="openEditProfile()"
      @delete="deleteSelectedProfile"
      v-if="selectedProfile" />
    <div v-else>
      <h1 class="text-2xl font-bold mb-4">Profiles</h1>
      <p class="mb-6">
        Explore your project's profiles here! Set up member behavior, instructions, AI model, and tools needed for their tasks.
      </p>  
      
      <!-- Filters Row -->
      <div class="flex flex-col gap-3 mb-4">
        <!-- Primary filters: Search + Tool dropdown + Tag dropdown + Actions -->
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <div class="flex items-center gap-2 flex-1 min-w-64">
            <input 
              type="text" 
              placeholder="Search profiles" 
              v-model="searchQuery" 
              class="input input-sm input-bordered flex-1" 
            />
            <select 
              v-model="toolDropdownValue" 
              @change="addToolFromDropdown"
              class="select select-sm select-bordered"
              title="Add tool filter"
            >
              <option value="">+ Add Tool</option>
              <option v-for="tool in availableTools" :key="tool" :value="tool">
                {{ tool }} ({{ getToolProfileCount(tool) }})
              </option>
            </select>
            <select 
              v-model="tagDropdownValue" 
              @change="addTagFromDropdown"
              class="select select-sm select-bordered"
              title="Add tag filter"
            >
              <option value="">+ Add Tag</option>
              <option v-for="tag in availableTags" :key="tag" :value="tag">
                {{ tag }} ({{ getTagProfileCount(tag) }})
              </option>
            </select>
          </div>
          <div class="flex gap-2 shrink-0">
            <button 
              class="btn btn-sm btn-ghost" 
              @click="loadProfiles" 
              title="Reload profiles"
              :disabled="loadingProfiles"
            >
              <i class="fa fa-rotate" :class="{ 'animate-spin': loadingProfiles }"></i>
            </button>
            <button class="btn btn-sm btn-primary" @click="createNewProfile">
              <i class="fa-solid fa-plus mr-1"></i> Create New
            </button>
          </div>
        </div>

        <!-- Selected Tools Display -->
        <div v-if="selectedTools.length" class="flex items-center gap-2 flex-wrap">
          <span class="text-sm font-semibold text-base-content/70">Selected tools:</span>
          <div class="flex gap-2 flex-wrap">
            <span 
              v-for="tool in selectedTools"
              :key="tool"
              class="badge badge-warning gap-1"
            >
              <i class="fa-solid fa-wrench"></i> {{ tool }}
              <button @click="removeTool(tool)" class="hover:text-error">
                <i class="fa-solid fa-x text-xs"></i>
              </button>
            </span>
          </div>
          <button 
            @click="selectedTools = []"
            class="text-xs text-primary hover:underline ml-2"
          >
            Clear tools
          </button>
        </div>

        <!-- Selected Tags Display -->
        <div v-if="selectedTags.length" class="flex items-center gap-2 flex-wrap">
          <span class="text-sm font-semibold text-base-content/70">Selected tags:</span>
          <div class="flex gap-2 flex-wrap">
            <span 
              v-for="tag in selectedTags"
              :key="tag"
              class="badge badge-info gap-1"
            >
              <i class="fa-solid fa-tag"></i> {{ tag }}
              <button @click="removeTag(tag)" class="hover:text-error">
                <i class="fa-solid fa-x text-xs"></i>
              </button>
            </span>
          </div>
          <button 
            @click="selectedTags = []"
            class="text-xs text-primary hover:underline ml-2"
          >
            Clear tags
          </button>
        </div>

        <!-- Results count -->
        <div v-if="profiles.length" class="text-xs text-base-content/60">
          Showing {{ filteredProfiles.length }} of {{ profiles.length }} profiles
        </div>
      </div>

      <!-- Profiles Grid -->
      <div v-if="profiles.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div 
          v-for="profile in filteredProfiles" 
          :key="profile.name"
          class="card bg-base-300 hover:bg-base-200 w-full shadow-lg rounded-lg cursor-pointer transition-colors" 
          @click="openEditProfile(profile)"
        >
          <ProfileCard class="h-96" :profile="profile" />
        </div>
      </div>

      <!-- No results state -->
      <div v-else-if="searchQuery || selectedTools.length || selectedTags.length" class="flex flex-col items-center justify-center gap-4 py-12">
        <i class="fa-solid fa-inbox text-4xl text-base-content/20"></i>
        <div class="text-center">
          <p class="font-semibold text-base-content/70">No profiles match your filters</p>
          <p class="text-sm text-base-content/50 mt-1">Try adjusting your search or filter selection</p>
        </div>
        <button class="btn btn-sm btn-ghost" @click="clearFilters">
          <i class="fa-solid fa-rotate-left mr-1"></i> Clear filters
        </button>
      </div>

      <!-- Empty state -->
      <div v-else class="flex flex-col items-center justify-center gap-4 py-12">
        <i class="fa-solid fa-inbox text-4xl text-base-content/20"></i>
        <div class="text-center">
          <p class="font-semibold text-base-content/70">No profiles yet</p>
          <p class="text-sm text-base-content/50 mt-1">Create your first profile to get started</p>
        </div>
        <button class="btn btn-sm btn-primary" @click="createNewProfile">
          <i class="fa-solid fa-plus mr-1"></i> Create Profile
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import toolsModel from '@/api/models/tools.js'

export default {
  data() {
    return {
      searchQuery: '',
      selectedTools: [],
      selectedTags: [],
      toolDropdownValue: '',
      tagDropdownValue: '',
      searchKeys: ['name', 'description', 'category', 'file_match', 'content', 'llm_model', 'user', 'tags'],
      loadingProfile: false,
      loadingProfiles: false,
      tools: []
    }
  },
  computed: {
    profiles() {
      return this.$storex.profiles.profiles || []
    },
    selectedProfile() {
      return this.$projects.selectedProfile
    },
    // Extract unique tools from all profiles sorted alphabetically
    availableTools() {
      const toolsSet = new Set()
      this.profiles.forEach(profile => {
        if (profile.tools && Array.isArray(profile.tools)) {
          profile.tools.forEach(tool => toolsSet.add(tool))
        }
      })
      return Array.from(toolsSet).sort()
    },
    // Extract unique tags from all tools sorted alphabetically
    availableTags() {
      return toolsModel.extractTags(this.tools)
    },
    // Filter profiles by search query AND all selected tools AND all selected tags
    filteredProfiles() {
      const filter = this.searchQuery.toLowerCase()
      
      return (this.profiles || []).filter(profile => {
        try {
          // Search filter: check if profile matches search query
          const searchMatch = !filter || this.searchKeys
            .map(k => Array.isArray(profile[k]) ? profile[k].join(' ') : (profile[k] || ''))
            .join(' ')
            .toLowerCase()
            .includes(filter)

          // Tool filter: check if profile has ALL selected tools
          const toolMatch = this.selectedTools.length === 0 || 
            (profile.tools && Array.isArray(profile.tools) && 
             this.selectedTools.every(tool => profile.tools.includes(tool)))

          // Tag filter: check if profile tools have ANY of the selected tags
          const tagMatch = this.selectedTags.length === 0 || 
            this.profileHasTaggedTools(profile)

          return searchMatch && toolMatch && tagMatch
        } catch(ex) {
          console.error(ex)
          return true // Don't hide profiles on error
        }
      }).sort((a, b) => a.name > b.name ? 1 : -1)
    }
  },
  created() {
    this.loadProfiles()
    this.loadTools()
  },
  methods: {
    async loadProfiles() {
      this.loadingProfiles = true
      try {
        await this.$projects.loadProfiles()
      } finally {
        this.loadingProfiles = false
      }
    },
    async loadTools() {
      try {
        this.tools = await this.$project.$api.profiles.tools()
      } catch (error) {
        console.error('Failed to load tools:', error)
      }
    },
    // Count profiles that have a specific tool
    getToolProfileCount(tool) {
      return this.profiles.filter(profile => 
        profile.tools && Array.isArray(profile.tools) && profile.tools.includes(tool)
      ).length
    },
    // Count profiles with tools that have a specific tag
    getTagProfileCount(tag) {
      return this.profiles.filter(profile => this.profileHasTag(profile, tag)).length
    },
    // Check if a profile has tools with a specific tag
    profileHasTag(profile, tag) {
      if (!profile.tools || !Array.isArray(profile.tools)) return false
      
      return profile.tools.some(toolName => {
        const tool = this.tools.find(t => t.tool_json?.function?.name === toolName)
        return tool?.tags && Array.isArray(tool.tags) && tool.tags.includes(tag)
      })
    },
    // Check if profile has tools with ANY of the selected tags
    profileHasTaggedTools(profile) {
      return this.selectedTags.some(tag => this.profileHasTag(profile, tag))
    },
    // Add tool from dropdown
    addToolFromDropdown() {
      if (this.toolDropdownValue && !this.selectedTools.includes(this.toolDropdownValue)) {
        this.selectedTools.push(this.toolDropdownValue)
      }
      this.toolDropdownValue = ''
    },
    // Add tag from dropdown
    addTagFromDropdown() {
      if (this.tagDropdownValue && !this.selectedTags.includes(this.tagDropdownValue)) {
        this.selectedTags.push(this.tagDropdownValue)
      }
      this.tagDropdownValue = ''
    },
    // Remove specific tool from selected tools
    removeTool(tool) {
      this.selectedTools = this.selectedTools.filter(t => t !== tool)
    },
    // Remove specific tag from selected tags
    removeTag(tag) {
      this.selectedTags = this.selectedTags.filter(t => t !== tag)
    },
    openEditProfile(selectedProfile) {
      this.$projects.setSelectedProfile(selectedProfile)
    },
    async deleteSelectedProfile() {
      this.$projects.deleteProfile(this.selectedProfile)
    },
    async saveSelectedProfile(profile) {
      this.loadingProfile = true
      try {
        this.$projects.saveProfile({ ...profile, project: null })
      } catch {}
      this.loadProfiles()
      this.loadingProfile = false
      this.$ui.addNotification({ text: `Profile '${profile.name}' saved` })
    },
    createNewProfile() {
      this.$projects.createNewProfile({ 
          project: this.$project,
          api_settings: {}
        })
    },
    clearFilters() {
      this.searchQuery = ''
      this.selectedTools = []
      this.selectedTags = []
    }
  }
}
</script>