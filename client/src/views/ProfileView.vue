<script setup>
import EditProfile from '@/components/EditProfile.vue';
</script>
<template>
  <div class="p-6">
    <EditProfile 
      :profile="selectedProfile"
      :allProfiles="profiles"
      :loading="loadingProfile"
      @save="saveSelectedProfile"
      @cancel="selectedProfile = null"
      @delete="deleteSelectedProfile"
      v-if="selectedProfile" />
    <div v-else>
      <h1 class="text-2xl font-bold mb-4">Profiles</h1>
      <p class="mb-6">
        With the profiles you can define the behavior of codx-junior when managing your tasks and files. Use it to define how you like the chatting style, coding best practices, architectural constraints, security restrictions, preferred development tools, and collaboration settings.
      </p>  
      <div class="flex items-center justify-between mb-4">
        <input type="text" placeholder="Search profiles" v-model="searchQuery" class="input input-sm input-bordered w-full max-w-xs" />
        <button class="btn btn-sm btn-primary ml-4" @click="selectedProfile = {}">Create New</button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div v-for="profile in filteredProfiles" :key="profile.name" class="card bg-base-300 hover:bg-base-200 w-full shadow-lg rounded-lg" @click="openEditProfile(profile)">
          <div class="card-body p-4 click hover:shadow-xl overflow-hidden">
            <h2 class="card-title text-xl font-semibold mb-2">{{ profile.name }}</h2>
            <p class="mb-2 text-xs">{{ profile.description?.substring(0, 100) }}</p>
            <div class="badge badge-accent badge-outline">{{ profile.category }}</div>
          </div>
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
      profiles: [],
      selectedProfile: null,
      loadingProfile: false
    };
  },
  created() {
    this.fetchProfiles();
  },
  computed: {
    filteredProfiles() {
      return this.profiles.filter(profile =>
        profile.name.toLowerCase().includes(this.searchQuery.toLowerCase()) ||
        profile.category.toLowerCase().includes(this.searchQuery.toLowerCase())
      ).sort((a, b) => a.name > b.name ? 1 : -1);
    }
  },
  methods: {
    async fetchProfiles() {
      const { data: profiles } = await this.$storex.api.profiles.list();
      this.profiles = profiles
    },
    openEditProfile(selectedProfile) {
      this.selectedProfile = selectedProfile
    },
    async deleteSelectedProfile() {
      await this.$storex.api.profiles.delete(this.selectedProfile.name)
      this.profiles = this.profiles.filter(p => p.name !== this.selectedProfile.name)
      this.selectedProfile = null
    },
    async saveSelectedProfile(profile) {
      this.loadingProfile = true
      try {
        const { data } = await this.$storex.api.profiles.save(profile)
        if (this.selectedProfile.name) {
          const ix = this.profiles.findIndex(p => p.name === data.name)
          this.profiles.splice(ix, 1, data)
          this.selectedProfile = data
        } else {
          this.profiles = [...this.profiles, data]
        }
      } catch{}
      this.loadingProfile = false
    }
  }
};
</script>

