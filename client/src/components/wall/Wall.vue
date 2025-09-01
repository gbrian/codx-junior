<script setup>
import ChatEntry from '../ChatEntry.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col">
    <div class="overflow-hidden bg-white border border-gray-300 shadow-md rounded-lg m-2">
      <ChatEntry />
      <!-- replicate ChatEntry component for more entries -->
    </div>
    <!-- More entries can be appended with similar structure -->
  </div>
</template>

<script>
export default {
  data() {
    return {}
  },
  computed: {
    lastMessages() {
      return this.$projects.lastMessages
    }
  }
}
</script>