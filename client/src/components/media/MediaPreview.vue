<template>
  <div class="relative w-full h-full bg-base-300 rounded-lg overflow-hidden flex items-center justify-center">
    <!-- Image -->
    <img
      v-if="media.type === 'image'"
      :src="media.url"
      :alt="media.name"
      class="w-full h-full object-cover"
    />

    <!-- Video -->
    <div v-else-if="media.type === 'video'" class="relative w-full h-full">
      <video
        :src="media.url"
        class="w-full h-full object-cover"
        controls
      ></video>
      <div class="absolute top-1 right-1 badge badge-primary">
        <i class="fa-solid fa-video mr-1"></i>Video
      </div>
    </div>

    <!-- Audio -->
    <div v-else-if="media.type === 'audio'" class="flex flex-col items-center justify-center w-full h-full gap-2 p-3">
      <i class="fa-solid fa-music text-3xl text-base-content/40"></i>
      <audio :src="media.url" controls class="w-full"></audio>
    </div>

    <!-- Document -->
    <div v-else-if="media.type === 'document'" class="flex flex-col items-center justify-center w-full h-full gap-2 text-base-content/60">
      <i class="fa-solid fa-file-pdf text-3xl"></i>
      <span class="text-xs font-semibold text-center px-2 line-clamp-2">{{ media.name }}</span>
    </div>

    <!-- Other -->
    <div v-else class="flex flex-col items-center justify-center w-full h-full gap-2 text-base-content/60">
      <i class="fa-solid fa-file text-3xl"></i>
      <span class="text-xs text-center">{{ media.type }}</span>
    </div>

    <!-- Badge with info -->
    <div v-if="showInfo" class="absolute bottom-1 left-1 text-xs text-white bg-black/60 px-2 py-1 rounded">
      {{ formatFileSize(media.size) }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'MediaPreview',
  props: {
    media: { type: Object, required: true },
    showInfo: { type: Boolean, default: true }
  },
  methods: {
    formatFileSize(bytes) {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
    }
  }
}
</script>