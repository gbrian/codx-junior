<script setup>
</script>
<template>
  <div class="flex flex-col gap-2 h-full px-4">
      <div class="font-medium flex flex-col gap-2">
        <div class="text-3xl flex justify-between items-center">
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
      searchQuery: '' // Reactive data for search input
    }
  },
  methods: {
    // Method to perform search, adds logic to handle search
    search() {
      if(this.searchQuery.trim() !== '') {
        console.log('Searching for:', this.searchQuery)
        // Add search logic here, e.g., call API or filter list
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