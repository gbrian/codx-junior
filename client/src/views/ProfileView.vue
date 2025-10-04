<script setup>
import EditProfile from '@/components/EditProfile.vue'
import ProfileCard from '@/components/ProfileCard.vue';
</script>
<template>
  <div class="p-6">
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
        <button class="btn btn-sm btn-primary ml-4" @click="createNewProfile">Create New</button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="profile in filteredProfiles" :key="profile.name"
          class="card bg-base-300 hover:bg-base-200 w-full shadow-lg rounded-lg" @click="openEditProfile(profile)">
          <ProfileCard class="click" :profile="profile" />
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
      loadingProfile: false
    }
  },
  computed: {
    profiles() {
      return this.$projects.profiles
    },
    selectedProfile() {
      return this.$projects.selectedProfile
    },
    filteredProfiles() {
      return this.profiles.filter(profile =>
        profile.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        profile.category.toLowerCase().includes(this.searchQuery.toLowerCase())
      ).sort((a, b) => a.name > b.name ? 1 : -1);
    }
  },
  created() {
    this.loadProfiles()
  },
  methods: {
    loadProfiles() {
      this.$projects.loadProfiles()
    },
    openEditProfile(selectedProfile) {
      this.$projects.setSelectedProfile(selectedProfile)
    },
    async deleteSelectedProfile() {
      this.$projects.deleteSelectedProfile(this.selectedProfile)
    },
    async saveSelectedProfile(profile) {
      this.loadingProfile = true
      try {
        this.$projects.saveProfile(profile)
      } catch {}
      this.loadingProfile = false
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