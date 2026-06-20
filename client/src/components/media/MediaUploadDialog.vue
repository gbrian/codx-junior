<script setup>
import MediaPreview from './MediaPreview.vue'
</script>

<template>
  <div class="flex flex-col gap-4 p-2 w-full max-w-2xl">
    <h3 class="font-bold text-lg flex items-center gap-2">
      <i class="fa-solid fa-cloud-arrow-up text-primary"></i>
      Upload Media
    </h3>

    <!-- Tabs -->
    <div class="tabs tabs-bordered">
      <button
        class="tab"
        :class="uploadMode === 'file' ? 'tab-active' : ''"
        @click="uploadMode = 'file'"
      >
        <i class="fa-solid fa-file mr-2"></i>Upload Files
      </button>
      <button
        class="tab"
        :class="uploadMode === 'url' ? 'tab-active' : ''"
        @click="uploadMode = 'url'"
      >
        <i class="fa-solid fa-link mr-2"></i>From URL
      </button>
    </div>

    <!-- File upload mode -->
    <template v-if="uploadMode === 'file'">
      <div
        class="border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-all"
        :class="dragover ? 'border-primary bg-primary/10' : 'border-base-content/20'"
        @dragover.prevent="dragover = true"
        @dragleave.prevent="dragover = false"
        @drop.prevent="onFilesDrop"
        @click="$refs.fileInput?.click()"
      >
        <input
          ref="fileInput"
          type="file"
          multiple
          class="hidden"
          @change="onFilesSelected"
          accept="image/*,video/*,audio/*,.pdf,.doc,.docx"
        />
        <i class="fa-solid fa-cloud-arrow-up text-3xl text-base-content/40 mb-2"></i>
        <div class="text-sm font-semibold">Drag files here or click to browse</div>
        <div class="text-xs text-base-content/50 mt-1">
          Supported: Images, Videos, Audio, Documents (Max 50MB each)
        </div>
      </div>
    </template>

    <!-- URL upload mode -->
    <template v-else>
      <div class="form-control gap-2">
        <label class="label label-text text-xs font-semibold">Media URL</label>
        <input
          v-model="mediaUrl"
          type="url"
          class="input input-bordered input-sm"
          placeholder="https://example.com/image.jpg"
          @keydown.enter="addUrlMedia"
        />
        <button
          class="btn btn-sm btn-primary"
          :disabled="!mediaUrl.trim()"
          @click="addUrlMedia"
        >
          <i class="fa-solid fa-plus mr-1"></i>Add Media
        </button>
      </div>
    </template>

    <!-- Media items to upload -->
    <template v-if="pendingMedias.length">
      <div class="divider my-2">Previews</div>
      
      <div class="grid grid-cols-2 gap-3 max-h-60 overflow-y-auto">
        <div
          v-for="(media, idx) in pendingMedias"
          :key="idx"
          class="relative group"
        >
          <MediaPreview :media="media" class="w-full h-32 rounded-lg" />
          
          <!-- Progress overlay -->
          <div
            v-if="uploadProgress[media.id]"
            class="absolute inset-0 bg-black/50 flex items-center justify-center rounded-lg"
          >
            <div class="flex flex-col items-center gap-1">
              <progress
                class="progress progress-primary w-16"
                :value="uploadProgress[media.id]"
                max="100"
              ></progress>
              <span class="text-xs text-white font-semibold">
                {{ uploadProgress[media.id] }}%
              </span>
            </div>
          </div>

          <!-- Delete button -->
          <button
            v-if="!uploadProgress[media.id]"
            class="absolute top-1 right-1 btn btn-xs btn-ghost btn-circle text-error opacity-0 group-hover:opacity-100 transition-opacity"
            @click.stop="removePendingMedia(idx)"
          >
            <i class="fa-solid fa-trash text-xs"></i>
          </button>

          <!-- Tags input -->
          <div class="mt-1">
            <input
              v-model="mediaNames[idx]"
              type="text"
              class="input input-bordered input-xs w-full"
              placeholder="Name"
              maxlength="50"
            />
          </div>
        </div>
      </div>

      <!-- Tags input -->
      <div class="form-control gap-1">
        <label class="label label-text text-xs font-semibold">Tags (comma-separated)</label>
        <input
          v-model="commonTags"
          type="text"
          class="input input-bordered input-sm"
          placeholder="project, important, review"
        />
      </div>
    </template>

    <!-- Empty state -->
    <div v-else class="text-center py-4 text-base-content/50">
      <p class="text-sm">No media selected</p>
    </div>

    <!-- Actions -->
    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')" :disabled="uploading">
        Cancel
      </button>
      <button
        class="btn btn-sm btn-primary"
        :disabled="!pendingMedias.length || uploading"
        :class="uploading ? 'loading' : ''"
        @click="uploadAll"
      >
        <i v-if="!uploading" class="fa-solid fa-cloud-arrow-up mr-1"></i>
        {{ uploading ? 'Uploading...' : 'Upload All' }}
      </button>
    </div>
  </div>
</template>

<script>
import { createMediaItem } from '@/store/media'

export default {
  name: 'MediaUploadDialog',
  emits: ['uploaded', 'close'],
  props: {
    libraryId: { type: String, default: null },
    resourceType: { type: String, default: null },
    resourceId: { type: String, default: null }
  },
  data() {
    return {
      uploadMode: 'file',
      dragover: false,
      mediaUrl: '',
      pendingMedias: [],
      mediaNames: [],
      commonTags: '',
      uploading: false
    }
  },
  computed: {
    uploadProgress() {
      return this.$storex.media.uploadProgress
    }
  },
  methods: {
    onFilesDrop(e) {
      this.dragover = false
      this.processFiles(Array.from(e.dataTransfer.files))
    },

    onFilesSelected(e) {
      this.processFiles(Array.from(e.target.files))
      this.$refs.fileInput.value = ''
    },

    processFiles(files) {
      files.forEach((file, idx) => {
        if (file.size > 50 * 1024 * 1024) {
          alert(`File ${file.name} exceeds 50MB limit`)
          return
        }

        const reader = new FileReader()
        reader.onload = (e) => {
          const media = createMediaItem({
            name: file.name,
            url: e.target.result,
            mimeType: file.type,
            size: file.size,
            type: this.getMediaType(file.type),
            metadata: { originalFile: file }
          })

          this.pendingMedias.push(media)
          this.mediaNames.push(file.name.split('.')[0])
        }
        reader.readAsDataURL(file)
      })
    },

    getMediaType(mimeType) {
      if (mimeType.startsWith('image/')) return 'image'
      if (mimeType.startsWith('video/')) return 'video'
      if (mimeType.startsWith('audio/')) return 'audio'
      if (mimeType.includes('pdf') || mimeType.includes('document')) return 'document'
      return 'other'
    },

    async addUrlMedia() {
      if (!this.mediaUrl.trim()) return

      const media = createMediaItem({
        name: this.mediaUrl.split('/').pop() || 'media',
        url: this.mediaUrl,
        type: this.guessMediaTypeFromUrl(this.mediaUrl)
      })

      this.pendingMedias.push(media)
      this.mediaNames.push(media.name)
      this.mediaUrl = ''
    },

    guessMediaTypeFromUrl(url) {
      const ext = url.split('.').pop().toLowerCase()
      if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext)) return 'image'
      if (['mp4', 'webm', 'avi', 'mov'].includes(ext)) return 'video'
      if (['mp3', 'wav', 'flac', 'aac'].includes(ext)) return 'audio'
      if (['pdf', 'doc', 'docx'].includes(ext)) return 'document'
      return 'other'
    },

    removePendingMedia(idx) {
      this.pendingMedias.splice(idx, 1)
      this.mediaNames.splice(idx, 1)
    },

    async uploadAll() {
      if (!this.pendingMedias.length) return

      this.uploading = true
      const tags = this.commonTags
        .split(',')
        .map(t => t.trim())
        .filter(t => t)

      try {
        const uploaded = []

        for (let i = 0; i < this.pendingMedias.length; i++) {
          const media = this.pendingMedias[i]
          const name = this.mediaNames[i].trim() || media.name

          const item = await this.$storex.media.uploadMedia({
            file: media.metadata?.originalFile || null,
            url: media.metadata?.originalFile ? null : media.url,
            libraryId: this.libraryId,
            name,
            tags,
            resourceType: this.resourceType,
            resourceId: this.resourceId
          })

          uploaded.push(item)
        }

        this.$emit('uploaded', uploaded)
        this.pendingMedias = []
        this.mediaNames = []
        this.commonTags = ''
      } finally {
        this.uploading = false
      }
    }
  }
}
</script>