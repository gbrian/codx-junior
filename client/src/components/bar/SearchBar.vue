<script setup>
import ProjectIcon from '../ProjectIcon.vue';
</script>

<template>
  <div class="group w-full flex gap-2 input input-sm items-center input-bordered w-full px-4" @click="executeSearch">
    <div class="text-nowrap text-xs">Ask codx-junior...</div> 
    <div class="click">
      <ProjectIcon class="group-hover:animate-pulse" width="w-6" />      
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