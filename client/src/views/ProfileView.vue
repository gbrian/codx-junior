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
      <div class="flex items-center justify-between mb-4">
        <input type="text" placeholder="Search profiles" v-model="searchQuery" class="input input-sm input-bordered w-full max-w-xs" />
        <div class="flex gap-2 ml-4">
          <button class="btn btn-sm btn-ghost" @click="loadProfiles" title="Reload profiles">
            <i class="fa fa-rotate" :class="{ 'animate-spin': loadingProfiles }"></i>
          </button>
          <button class="btn btn-sm btn-primary" @click="createNewProfile">Create New</button>
        </div>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" v-if="profiles">
        <div v-for="profile in filteredProfiles" :key="profile.name"
          class="card bg-base-300 hover:bg-base-200 w-full shadow-lg rounded-lg" @click="openEditProfile(profile)">
          <ProfileCard class="click h-96" :profile="profile" />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      searchQuery: '',
      searchKeys: ['name', 'description', 'category', 'file_match', 'content', 'llm_model', 'user', 'tools', 'tags'],
      loadingProfile: false,
      loadingProfiles: false
    }
  },
  computed: {
    profiles() {
      return this.$storex.projects.profiles
    },
    selectedProfile() {
      return this.$projects.selectedProfile
    },
    filteredProfiles() {
      const filter = this.searchQuery.toLowerCase()
      return (this.profiles || []).filter(profile => {
        try {
          // Safely stringify each key value, joining arrays if needed
          const text = this.searchKeys
            .map(k => Array.isArray(profile[k]) ? profile[k].join(' ') : (profile[k] || ''))
            .join(' ')
            .toLowerCase()
          return text.includes(filter)
        } catch(ex) {
          console.error(ex)
          return true // Don't hide profiles on error
        }
      }).sort((a, b) => a.name > b.name ? 1 : -1)
    }
  },
  created() {
    this.loadProfiles()
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
    }
  }
}
</script>