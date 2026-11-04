<script setup>
import FileViewer from './FileViewer.vue'
</script>

<template>
  <div class="fixed inset-0 z-[60] flex flex-col bg-black/90 backdrop-blur-sm select-none">
    <!-- Header -->
    <div class="flex items-center gap-3 px-4 py-2 text-white/80 shrink-0">
      <i class="fa-solid fa-photo-film text-primary"></i>
      <span class="text-sm font-semibold truncate" :title="activeFile?.name">
        {{ activeFile?.name || 'Slide show' }}
      </span>
      <span class="text-xs opacity-60" v-if="files.length">
        {{ activeIndex + 1 }} / {{ files.length }}
      </span>
      <div class="grow"></div>

      <!-- Fit / full size switch for the active slide -->
      <button
        class="btn btn-sm btn-ghost text-white/80"
        :title="fullSize ? 'Fit slide (80%)' : 'Full size slide'"
        :aria-label="fullSize ? 'Fit slide' : 'Full size slide'"
        :aria-pressed="fullSize ? 'true' : 'false'"
        @click="toggleFullSize"
      >
        <i :class="fullSize ? 'fa-solid fa-compress' : 'fa-solid fa-expand'"></i>
        {{ fullSize ? 'Fit' : 'Full' }}
      </button>

      <button
        class="btn btn-sm btn-ghost text-white/80"
        title="Close slide show"
        aria-label="Close slide show"
        @click="$emit('close')"
      >
        <i class="fa-solid fa-xmark"></i> Close
      </button>
    </div>

    <!-- Slides area -->
    <div class="relative flex-1 min-h-0 mx-4 overflow-hidden">
      <!-- Previous slide -->
      <button
        class="btn btn-circle btn-sm absolute left-2 top-1/2 -translate-y-1/2 z-40 bg-black/40 border-white/10 text-white/80"
        title="Previous"
        aria-label="Previous slide"
        :disabled="activeIndex === 0"
        @click="previous"
      >
        <i class="fa-solid fa-chevron-left"></i>
      </button>

      <!-- Next slide -->
      <button
        class="btn btn-circle btn-sm absolute right-2 top-1/2 -translate-y-1/2 z-40 bg-black/40 border-white/10 text-white/80"
        title="Next"
        aria-label="Next slide"
        :disabled="activeIndex >= files.length - 1"
        @click="next"
      >
        <i class="fa-solid fa-chevron-right"></i>
      </button>

      <!-- Slides: the active one is 80% x 80% of this area (or the whole area in
           full size mode); the neighbours stay behind, smaller -->
      <div
        v-for="(file, ix) in files"
        :key="file.path"
        class="absolute overflow-hidden shadow-2xl bg-base-200 ring-1 ring-white/10 transition-all duration-500 ease-out"
        :class="fullSize && ix === activeIndex ? 'rounded-none' : 'rounded-xl'"
        :style="slideStyle(ix)"
        :title="file.name"
        @click="select(ix)"
        @dblclick.stop="toggleFullSize"
      >
        <FileViewer
          v-if="shouldRender(ix)"
          :params="{ filePath: file.path }"
          slide-mode
          class="w-full h-full"
        />
        <div class="w-full h-full flex flex-col items-center justify-center gap-2 text-white/50" v-else>
          <i class="fa-regular fa-file text-4xl"></i>
          <span class="text-xs font-mono max-w-full px-2 truncate text-center">{{ file.name }}</span>
        </div>
      </div>

      <!-- Empty state -->
      <div class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-white/50" v-if="!files.length">
        <i class="fa-regular fa-images text-4xl"></i>
        <span class="text-sm">No files to show</span>
      </div>
    </div>

    <!-- Thumbnails of the current files, centered under the slides.
         Same tiles as the explorer's preview mode (see FileExplorer). -->
    <div
      ref="strip"
      class="shrink-0 h-32 flex items-center overflow-x-auto scrollbar-thin"
      v-if="files.length"
    >
      <!-- `mx-auto w-max` centers the track when it fits and keeps it scrollable when it does not -->
      <div class="flex items-center gap-2 px-4 py-3 mx-auto w-max h-full">
        <button
          v-for="(file, ix) in files"
          :key="'thumb-' + file.path"
          class="relative h-24 w-24 shrink-0 rounded-lg overflow-hidden bg-base-200 border transition-all duration-200"
          :class="ix === activeIndex
            ? 'border-primary ring-2 ring-primary/60 scale-105'
            : 'border-base-100 opacity-70 hover:opacity-100 hover:border-primary/40'"
          :data-thumb-index="ix"
          :title="file.name"
          :aria-label="file.name"
          @click="select(ix)"
        >
          <!-- Icon fallback: shown while the thumbnail loads or when it cannot be rendered -->
          <div class="absolute inset-0 flex flex-col items-center justify-center gap-2 px-2">
            <i class="text-3xl" :class="fileIcon(file)"></i>
            <span class="text-[10px] uppercase tracking-wide opacity-50">
              {{ fileTypeLabel(file) }}
            </span>
          </div>

          <!-- Image thumbnail -->
          <img
            v-if="previewKind(file) === 'image' && !hasThumbError(file)"
            :src="previewUrl(file)"
            :alt="file.name"
            loading="lazy"
            decoding="async"
            class="absolute inset-0 w-full h-full object-cover"
            @error="onThumbError(file)"
          />

          <!-- Video thumbnail (first frame) -->
          <video
            v-else-if="previewKind(file) === 'video' && !hasThumbError(file)"
            :src="videoThumbUrl(file)"
            preload="metadata"
            muted
            playsinline
            class="absolute inset-0 w-full h-full object-cover"
            @error="onThumbError(file)"
          ></video>

          <!-- PDF / audio: no thumbnail, a type badge over the icon -->
          <div class="absolute inset-0 flex items-center justify-center" v-else-if="previewKind(file)">
            <span
              class="badge badge-sm gap-1"
              :class="previewKind(file) === 'pdf' ? 'badge-error' : 'badge-secondary'"
            >
              <i :class="previewKind(file) === 'pdf' ? 'fa-solid fa-file-pdf' : 'fa-solid fa-music'"></i>
              {{ previewKind(file).toUpperCase() }}
            </span>
          </div>

          <!-- Name + size overlay -->
          <div class="absolute inset-x-0 bottom-0 px-2 py-1 bg-black/60">
            <div class="text-[11px] font-mono truncate text-white">{{ file.name }}</div>
            <div class="text-[10px] text-white/60" v-if="file.size !== undefined && file.size !== null">
              {{ formatSize(file.size) }}
            </div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
// Formats the browser can render a thumbnail for. Kept in sync with the
// explorer's preview mode (FileExplorer.vue).
const IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'avif', 'ico', 'svg']
const VIDEO_EXTENSIONS = ['mp4', 'webm', 'mov', 'm4v', 'ogv', 'mkv']
const AUDIO_EXTENSIONS = ['mp3', 'wav', 'ogg', 'oga', 'flac', 'aac', 'm4a', 'opus']
const PDF_EXTENSIONS = ['pdf']

export default {
  name: 'FileSlideShow',
  components: { FileViewer },
  props: {
    // Files to show: [{ path, name, size?, icon? }]
    files: { type: Array, default: () => [] },
    startIndex: { type: Number, default: 0 }
  },
  emits: ['close'],
  data() {
    const max = Math.max((this.files?.length || 0) - 1, 0)
    const start = Math.min(Math.max(this.startIndex || 0, 0), max)
    return {
      activeIndex: start,
      // Show the active slide over the whole slides area instead of 80% x 80%
      fullSize: false,
      // Thumbnails that failed to load, keyed by file path
      thumbErrors: {}
    }
  },
  computed: {
    $api() {
      return this.$project.$api
    },
    activeFile() {
      return this.files[this.activeIndex] || null
    }
  },
  watch: {
    activeIndex() {
      this.scrollThumbIntoView()
    }
  },
  mounted() {
    window.addEventListener('keydown', this.onKeydown)
    this.scrollThumbIntoView()
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    // Position + scale of a slide, relative to the active one.
    //
    // Fit mode: the active slide keeps an 80% x 80% footprint and the
    // neighbours move aside, shrink and fade so they peek from behind it.
    // Full size mode: the active slide fills the whole slides area and the
    // neighbours are pushed out of view, so nothing peeks from behind.
    slideStyle(ix) {
      const offset = ix - this.activeIndex
      const distance = Math.abs(offset)
      const direction = offset < 0 ? -1 : 1

      if (this.fullSize) {
        if (offset === 0) {
          return {
            left: '50%',
            top: '50%',
            width: '100%',
            height: '100%',
            transform: 'translate(-50%, -50%) scale(1)',
            opacity: '1',
            zIndex: '30'
          }
        }
        return {
          left: `${50 + direction * 60}%`,
          top: '50%',
          width: '100%',
          height: '100%',
          transform: `translate(-50%, -50%) scale(${distance === 1 ? 0.8 : 0.6})`,
          opacity: '0',
          zIndex: distance === 1 ? '20' : '10'
        }
      }

      let left = 50
      let scale = 1
      let opacity = 1
      let zIndex = 30

      if (offset !== 0) {
        if (distance === 1) {
          left = 50 + direction * 32
          scale = 0.6
          opacity = 0.6
          zIndex = 20
        } else {
          left = 50 + direction * 48
          scale = 0.4
          opacity = 0
          zIndex = 10
        }
      }

      return {
        left: `${left}%`,
        top: '50%',
        width: '80%',
        height: '80%',
        transform: `translate(-50%, -50%) scale(${scale})`,
        opacity: `${opacity}`,
        zIndex: `${zIndex}`
      }
    },
    // Only the active slide and its two neighbours mount a FileViewer, so a large
    // folder does not trigger a file read for every entry.
    shouldRender(ix) {
      return Math.abs(ix - this.activeIndex) <= 1
    },
    select(ix) {
      const max = Math.max(this.files.length - 1, 0)
      this.activeIndex = Math.min(Math.max(ix, 0), max)
    },
    next() {
      this.select(this.activeIndex + 1)
    },
    previous() {
      this.select(this.activeIndex - 1)
    },
    // Switch the active slide between the 80% x 80% card and the whole area
    toggleFullSize() {
      this.fullSize = !this.fullSize
    },
    onKeydown(event) {
      if (event.target?.tagName === 'INPUT' || event.target?.tagName === 'TEXTAREA') return
      if (event.key === 'ArrowRight') {
        event.preventDefault()
        this.next()
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault()
        this.previous()
      } else if (event.key === 'f' || event.key === 'F') {
        event.preventDefault()
        this.toggleFullSize()
      } else if (event.key === 'Escape') {
        this.$emit('close')
      }
    },
    fileExtension(file) {
      const name = file?.name || file?.path || ''
      if (!name.includes('.')) return ''
      return name.split('.').pop()?.toLowerCase() || ''
    },
    // Preview kind the browser can render, mirroring the explorer's tiles
    previewKind(file) {
      const ext = this.fileExtension(file)
      if (IMAGE_EXTENSIONS.includes(ext)) return 'image'
      if (VIDEO_EXTENSIONS.includes(ext)) return 'video'
      if (AUDIO_EXTENSIONS.includes(ext)) return 'audio'
      if (PDF_EXTENSIONS.includes(ext)) return 'pdf'
      return null
    },
    // Icon class resolved by the explorer (it owns the extension -> icon map)
    fileIcon(file) {
      return file?.icon || 'fa-regular fa-file text-info'
    },
    // Short uppercase label shown under the fallback icon
    fileTypeLabel(file) {
      const name = file?.name || ''
      if (!name.includes('.')) return 'file'
      return this.fileExtension(file)
    },
    previewUrl(file) {
      return this.$api.files.getFilePreviewUrl(file.path)
    },
    // Ask the browser to render the first frame instead of a black poster
    videoThumbUrl(file) {
      const url = this.previewUrl(file)
      return url ? `${url}#t=0.1` : ''
    },
    onThumbError(file) {
      this.thumbErrors = { ...this.thumbErrors, [file.path]: true }
    },
    hasThumbError(file) {
      return !!this.thumbErrors[file.path]
    },
    formatSize(size) {
      if (size === null || size === undefined) return ''
      if (size < 1024) return `${size} B`
      if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
      return `${(size / (1024 * 1024)).toFixed(1)} MB`
    },
    // Keep the active thumbnail visible in the centered strip. The thumbnails
    // live inside the track wrapper, so they are resolved by index attribute.
    scrollThumbIntoView() {
      this.$nextTick(() => {
        const strip = this.$refs.strip
        if (!strip) return
        const thumb = strip.querySelector(`[data-thumb-index="${this.activeIndex}"]`)
        if (thumb && thumb.scrollIntoView) {
          thumb.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
        }
      })
    }
  }
}
</script>