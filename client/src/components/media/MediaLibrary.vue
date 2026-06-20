<script setup>
import MediaPreview from './MediaPreview.vue'
import MediaUploadDialog from './MediaUploadDialog.vue'
</script>

<template>
  <div class="flex flex-col gap-4 p-4 h-full">
    <!-- Header -->
    <div class="flex items-center justify-between shrink-0">
      <div>
        <h2 class="font-bold text-lg">{{ library.name }}</h2>
        <p v-if="library.description" class="text-xs text-base-content/50 mt-1">
          {{ library.description }}
        </p>
      </div>
      <button class="btn btn-sm btn-primary" @click="showUploadDialog = true">
        <i class="fa-solid fa-cloud-arrow-up mr-1"></i>
        Upload Media
      </button>
    </div>

    <!-- Search + Filter -->
    <div class="flex gap-2 shrink-0">
      <div class="flex-1 flex items-center gap-1 input input-sm input-bordered bg-base-300">
        <i class="fa-solid fa-magnifying-glass text-xs text-base-content/50"></i>
        <input
          v-model="searchQuery"
          class="bg-transparent flex-1 min-w-0 text-sm"
          placeholder="Search media..."
        />
      </div>
      <select v-model="filterType" class="select select-sm select-bordered">
        <option value="">All Types</option>
        <option value="image">Images</option>
        <option value="video">Videos</option>
        <option value="audio">Audio</option>
        <option value="document">Documents</option>
      </select>
    </div>

    <!-- Media Grid -->
    <div class="flex-1 min-h-0 overflow-y-auto">
      <div v-if="filteredMedia.length" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
        <div
          v-for="media in filteredMedia"
          :key="media.id"
          class="group relative rounded-lg overflow-hidden bg-base-300 cursor-pointer transform transition-transform hover:scale-105"
        >
          <!-- Preview -->
          <MediaPreview :media="media" class="w-full h-40" />

          <!-- Info overlay -->
          <div class="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-end">
            <div class="w-full p-2 text-white opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-t from-black/80">
              <div class="text-xs font-semibold truncate">{{ media.name }}</div>
              <div class="text-xs text-white/70">{{ formatFileSize(media.size) }}</div>
            </div>
          </div>

          <!-- Actions -->
          <div class="absolute top-1 right-1 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              class="btn btn-xs btn-ghost btn-circle text-info"
              @click.stop="viewMedia(media)"
              title="View"
            >
              <i class="fa-solid fa-eye text-xs"></i>
            </button>
            <button
              class="btn btn-xs btn-ghost btn-circle text-warning"
              @click.stop="editMedia(media)"
              title="Edit"
            >
              <i class="fa-solid fa-pen text-xs"></i>
            </button>
            <button
              class="btn btn-xs btn-ghost btn-circle text-error"
              @click.stop="deleteMedia(media.id)"
              title="Delete"
            >
              <i class="fa-solid fa-trash text-xs"></i>
            </button>
          </div>

          <!-- Badge -->
          <div class="absolute top-1 left-1 badge badge-sm" :class="getTypeBadgeClass(media.type)">
            {{ media.type }}
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else class="h-full flex flex-col items-center justify-center text-base-content/40 gap-4">
        <i class="fa-solid fa-image text-5xl"></i>
        <div class="text-center">
          <p class="font-semibold">No media found</p>
          <p class="text-sm mt-1">Upload media or try adjusting your search</p>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <modal v-if="showUploadDialog">
      <MediaUploadDialog
        :library-id="library.id"
        :resource-type="library.type"
        :resource-id="library.resourceId"
        @uploaded="onMediaUploaded"
        @close="showUploadDialog = false"
      />
    </modal>

    <!-- Media viewer -->
    <modal v-if="selectedMedia" close="true" @close="selectedMedia = null">
      <div class="flex flex-col gap-4 p-4 w-full max-w-2xl max-h-screen overflow-y-auto">
        <MediaPreview :media="selectedMedia" class="w-full h-80 rounded-lg" />
        
        <div class="flex flex-col gap-2">
          <div>
            <label class="label label-text text-xs font-semibold">Name</label>
            <p class="text-sm">{{ selectedMedia.name }}</p>
          </div>
          <div>
            <label class="label label-text text-xs font-semibold">Type</label>
            <p class="text-sm capitalize">{{ selectedMedia.type }}</p>
          </div>
          <div>
            <label class="label label-text text-xs font-semibold">Size</label>
            <p class="text-sm">{{ formatFileSize(selectedMedia.size) }}</p>
          </div>
          <div v-if="selectedMedia.tags.length">
            <label class="label label-text text-xs font-semibold">Tags</label>
            <div class="flex flex-wrap gap-1">
              <span v-for="tag in selectedMedia.tags" :key="tag" class="badge badge-sm badge-primary">
                {{ tag }}
              </span>
            </div>
          </div>
          <div>
            <label class="label label-text text-xs font-semibold">Created</label>
            <p class="text-sm">{{ new Date(selectedMedia.createdAt).toLocaleDateString() }}</p>
          </div>
        </div>

        <div class="flex gap-2">
          <button class="btn btn-sm btn-primary flex-1" @click="copyLink">
            <i class="fa-solid fa-link mr-1"></i>Copy Link
          </button>
          <button class="btn btn-sm btn-error flex-1" @click="deleteMedia(selectedMedia.id); selectedMedia = null">
            <i class="fa-solid fa-trash mr-1"></i>Delete
          </button>
        </div>
      </div>
    </modal>

    <!-- Edit media -->
    <modal v-if="editingMedia" close="true" @close="editingMedia = null">
      <div class="flex flex-col gap-4 p-4 w-96">
        <h3 class="font-bold text-lg">Edit Media</h3>
        
        <div class="form-control gap-1">
          <label class="label label-text text-xs font-semibold">Name</label>
          <input
            v-model="editingMedia.name"
            type="text"
            class="input input-bordered input-sm"
            placeholder="Media name"
          />
        </div>

        <div class="form-control gap-1">
          <label class="label label-text text-xs font-semibold">Tags (comma-separated)</label>
          <input
            v-model="editingMediaTags"
            type="text"
            class="input input-bordered input-sm"
            placeholder="tag1, tag2, tag3"
          />
        </div>

        <div class="flex gap-2 justify-end">
          <button class="btn btn-sm" @click="editingMedia = null">Cancel</button>
          <button class="btn btn-sm btn-primary" @click="saveMediaEdit">Save</button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  name: 'MediaLibrary',
  props: {
    library: { type: Object, required: true }
  },
  data() {
    return {
      searchQuery: '',
      filterType: '',
      showUploadDialog: false,
      selectedMedia: null,
      editingMedia: null,
      editingMediaTags: ''
    }
  },
  computed: {
    mediaItems() {
      return this.$storex.media.mediaByLibrary(this.library.id)
    },
    filteredMedia() {
      let items = this.mediaItems

      // Search filter
      if (this.searchQuery) {
        const q = this.searchQuery.toLowerCase()
        items = items.filter(m =>
          m.name.toLowerCase().includes(q) ||
          m.tags.some(t => t.toLowerCase().includes(q))
        )
      }

      // Type filter
      if (this.filterType) {
        items = items.filter(m => m.type === this.filterType)
      }

      return items.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt))
    }
  },
  methods: {
    viewMedia(media) {
      this.selectedMedia = media
    },

    editMedia(media) {
      this.editingMedia = { ...media }
      this.editingMediaTags = media.tags.join(', ')
    },

    saveMediaEdit() {
      if (this.editingMedia) {
        this.editingMedia.tags = this.editingMediaTags
          .split(',')
          .map(t => t.trim())
          .filter(t => t)
        this.$storex.media.updateMediaItem(this.editingMedia)
        this.editingMedia = null
      }
    },

    deleteMedia(mediaId) {
      if (confirm('Delete this media permanently?')) {
        this.$storex.media.deleteMediaItem(mediaId)
      }
    },

    async onMediaUploaded(items) {
      this.showUploadDialog = false
      this.$toast.success(`Uploaded ${items.length} media item(s)`)
    },

    copyLink() {
      if (this.selectedMedia?.url) {
        navigator.clipboard.writeText(this.selectedMedia.url)
        this.$toast.success('Link copied to clipboard')
      }
    },

    formatFileSize(bytes) {
      if (!bytes) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
    },

    getTypeBadgeClass(type) {
      const classes = {
        image: 'badge-primary',
        video: 'badge-secondary',
        audio: 'badge-accent',
        document: 'badge-warning'
      }
      return classes[type] || 'badge-ghost'
    }
  }
}
</script>