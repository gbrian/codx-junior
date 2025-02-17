<script setup>
import Markdown from '@/components/Markdown.vue'
</script>

<template>
  <div class="pr-view p-4">
    <header class="flex justify-between items-center">
      <h1 class="text-lg font-bold">Latest Changes</h1>
      <div class="flex gap-2 items-center">
        <button class="btn btn-sm" @click="$ui.copyTextToClipboard($projects.changesSummary)">
          <i class="fa-solid fa-copy"></i>
        </button>
        <button @click="$projects.refreshChangesSummary(true)" class="btn btn-outline btn-sm">
          <i class="fas fa-sync-alt"></i> Refresh
        </button>
      </div>
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