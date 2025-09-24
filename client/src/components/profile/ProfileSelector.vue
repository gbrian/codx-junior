<script setup>
  import ProfileCard from '../ProfileCard.vue';
  import ProjectBadge from '../project/ProjectBadge.vue';
</script>
<template>
  <div class="text-xl animate-pulse" v-if="!profiles.length">Loading profiles...</div>
    
  <div class="w-full h-full flex flex-col gap-2 h-96" v-else><
    <div class="flex gap-2 shrink-0 items-center justify-between">
      <ProjectBadge :project="project" />
      <input type="text" placeholder="Filter profiles..." class="input input-sm input-bordered" v-model="filterText" />
    </div>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <ProfileCard class="click" :profile="profile" v-for="profile in filteredProfiles" :key="profile.id" @click="$emit('select', profile)" />
    </div>
  </div>
</template>
<script>
export default {
  props: ['project'],
  data() {
    return {
      filterText: '',
      profiles: []
    }
  },
  async mounted () {
    this.profiles = await this.$storex.api.project(this.project)
                                .then(p => p.profiles.list())
  },
  computed: {
    filteredProfiles() {
      const filterText = this.filterText.toLowerCase()
      return this.profiles.filter(profile => profile.name.toLowerCase().includes(filterText))
    }
  }
}
</script>