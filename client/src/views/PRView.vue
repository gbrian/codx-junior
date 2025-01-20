<script setup>
import Markdown from '@/components/Markdown.vue'
</script>

<template>
  <div class="pr-view p-4">
    <header class="flex justify-between items-center">
      <h1 class="text-lg font-bold">Latest Changes</h1>
      <button @click="$projects.refreshChangesSummary(true)" class="btn btn-outline btn-sm">
        <i class="fas fa-sync-alt"></i> Refresh
      </button>
    </header>
    <Markdown :text="$projects.changesSummary" v-if="$projects.changesSummary"/>
  </div>
</template>

<script>
export default {
  created () {
    this.$projects.refreshChangesSummary()
  }
}
</script>