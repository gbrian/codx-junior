<script setup>
import MediaPreview from './MediaPreview.vue'
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="font-semibold text-base">Media Gallery</h3>
        <p class="text-xs text-base-content/50">{{ mediaItems.length }} item(s)</p>
      </div>
      <button class="btn btn-sm btn-primary" @click="$emit('upload')">
        <i class="fa-solid fa-cloud-arrow-up mr-1"></i>
        Add Media
      </button>
    </div>

    <!-- Search + Filter -->
    <div class="flex gap-2">
      <div class="flex-1 flex items-center gap-1 input input-sm input-bordered bg-base-300">
        <i class="fa-solid fa-magnifying-glass text-xs text-base-content/50"></i>
        <input
          v-model="searchQuery"
          class="bg-transparent flex-1 min-w-0 text-xs"
          placeholder="Search..."
        />
      </div>
      <select v-model="filterType" class="select select-sm select-bordered">
        <option value="">All</option>
        <option value="image">Images</option>
        <option value="video">Videos</option>
        <option value="audio">Audio</option>
        <option value="document">Documents</option>
      </select>
    </div>

    <!-- Media Grid -->
    <div class="grid grid-cols-2 md:grid-cols-3 gap-2 max-h-96 overflow-y-auto">
      <div
        v-for="media in filteredMedia"
        :key="media.id"
        class="group relative rounded cursor-pointer transform transition-transform hover:scale-105"
        @click="selectMedia(media)"
      >
        <MediaPreview :media="media" class="w-full h-24 rounded" />
        <div class="absolute inset-0 bg-black/0 group-hover:bg-primary/20 transition-all rounded"></div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!mediaItems.length" class="text-center py-6 text-base-content/50">
      <i class="fa-solid fa-image text-2xl block mb-2"></i>
      <p class="text-sm">No media yet</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MediaGallery',
  emits: ['select', 'upload'],
  props: {
    libraryId: { type: String, required: true },
    maxItems: { type: Number, default: null }
  },
  data() {
    return {
      searchQuery: '',
      filterType: ''
    }
  },
  computed: {
    mediaItems() {
      const items = this.$storex.media.mediaByLibrary(this.libraryId)
      return this.maxItems ? items.slice(0, this.maxItems) : items
    },
    filteredMedia() {
      let items = this.mediaItems

      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase()
        items = items.filter(m =>
          m.name.toLowerCase().includes(q) ||
          m.tags.some(t => t.toLowerCase().includes(q))
        )
      }

      if (this.filterType) {
        items = items.filter(m => m.type === this.filterType)
      }

      return items.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    }
  },
  methods: {
    selectMedia(media) {
      this.$emit('select', media)
    }
  }
}
</script>