<script setup>
import ProjectDetailt from '@/components/ProjectDetailt.vue';
</script>
<template>
  <div class="flex flex-col gap-2 h-full px-4">
      <div class="font-medium flex flex-col gap-2">
        <div class="text-3xl flex gap-2 items-center">
          <ProjectDetailt 
            v-model="project" />
            Knowledge
        </div>
        <!-- Search Form -->
        <div class="flex gap-2 items-center">
          <input v-model="searchQuery" type="text" placeholder="Search..." class="input input-bordered w-full" />
          <i @click="search" class="fas fa-search text-xl cursor-pointer"></i>
          <i @click="clearSearch" class="fas fa-times text-xl cursor-pointer"></i>
        </div>
      </div>
  </div>
</template>
<script>
export default {
  data () {
    return {
      searchQuery: '',
      project: null
    }
  },
  created() {
    this.project = this.$project
  },
  methods: {
    // Method to perform search, adds logic to handle search
    async search() {
      if(this.searchQuery.trim() !== '') {
        const res = await this.project.$api.knowledge.query(this.searchQuery.trim())
      }
    },
    // Method to clear search input and results
    clearSearch() {
      this.searchQuery = ''
      console.log('Search cleared')
      // Add clear logic here, e.g., reset list view
    }
  }
}
</script>