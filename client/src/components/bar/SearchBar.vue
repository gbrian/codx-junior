<script setup>
</script>

<template>
  <!-- Search bar with FontAwesome icon and modal for additional search options -->
  <div class="w-full h-full flex gap-2 input input-bordered w-full py-2 px-4" @click="executeSearch">
    Search... 
    <div class="click">
      <i class="fa-solid fa-search"></i>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return { 
    }
  },
  methods: {
    executeSearch() {
      this.$ui.setActiveTab('assistant')
    }
  }
}
</script>