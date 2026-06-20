<script setup>
import MediaManager from '@/components/media/MediaManager.vue'
</script>

<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- Header -->
    <div class="flex items-center gap-2 px-4 py-3 border-b border-base-content/10 bg-base-200/50 shrink-0">
      <i class="fa-solid fa-image text-primary"></i>
      <span class="font-bold text-sm">Media Library</span>
      <span v-if="team" class="text-xs text-base-content/50 ml-1">— {{ team.name }}</span>
    </div>

    <!-- Media manager body -->
    <div class="flex-1 min-h-0 overflow-hidden">
      <MediaManager
        v-if="team"
        :resource-type="'team'"
        :resource-id="team.id"
      />
      <div v-else class="flex-1 flex items-center justify-center text-base-content/50 h-full">
        <div class="text-center">
          <i class="fa-solid fa-image text-4xl mb-2 opacity-30"></i>
          <p class="text-sm">No team selected</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TeamMediaLibrary',
  props: {
    params: { type: Object, default: () => ({}) }
  },
  computed: {
    team() {
      return this.params?.team || null
    }
  }
}
</script>