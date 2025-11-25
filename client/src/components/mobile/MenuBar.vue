<script setup>
</script>

<template>
  <div class="w-full h-full flex items-center gap-2">
    <!-- Bars Icon for Popup Menu -->
    <button class="flex items-center">
      <i class="fa-solid fa-bars"></i>
    </button>
    
    <!-- Project Selector Component -->
    <ProjectSelector />

    <!-- Spacer -->
    <div class="flex-grow"></div>

    <!-- Search Bar in Icon Mode -->
    <SearchBar class="icon-mode" />

    <!-- Notifications Component -->
    <Notifications />

    <!-- User Menu Component -->
    <UserMenu />
  </div>
</template>

<script>
export default {
  data() {
    return {
      // Add any reactive data properties here if needed
    }
  },
  computed: {
    // Add computed properties here if needed
  },
  watch: {
    // Add watch properties here if needed
  },
  methods: {
    // Add component methods here if needed
  }
}
</script>