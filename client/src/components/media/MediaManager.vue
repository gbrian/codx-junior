<script setup>
import MediaLibrary from './MediaLibrary.vue'
import MediaGallery from './MediaGallery.vue'
</script>

<template>
  <div class="flex flex-col gap-4 h-full p-4">
    <!-- Libraries list -->
    <div class="flex items-center justify-between shrink-0">
      <h2 class="font-bold text-lg">Media Manager</h2>
      <button class="btn btn-sm btn-primary" @click="showCreateLibrary = true">
        <i class="fa-solid fa-plus mr-1"></i>
        New Library
      </button>
    </div>

    <!-- Library tabs -->
    <div v-if="libraries.length" class="flex gap-1 overflow-x-auto shrink-0 pb-2">
      <button
        v-for="lib in libraries"
        :key="lib.id"
        class="btn btn-sm"
        :class="selectedLibraryId === lib.id ? 'btn-primary' : 'btn-ghost'"
        @click="selectedLibraryId = lib.id"
      >
        {{ lib.name }}
        <span class="text-xs text-base-content/50 ml-1">
          {{ getMediaCount(lib.id) }}
        </span>
      </button>
    </div>

    <!-- Library content -->
    <div class="flex-1 min-h-0">
      <MediaLibrary
        v-if="selectedLibrary"
        :library="selectedLibrary"
      />
      <div v-else class="h-full flex items-center justify-center text-base-content/50">
        <p class="text-sm">No libraries yet. Create one to get started.</p>
      </div>
    </div>

    <!-- Create library modal -->
    <modal v-if="showCreateLibrary">
      <div class="flex flex-col gap-4 p-4 w-80">
        <h3 class="font-bold text-lg">Create Media Library</h3>

        <div class="form-control gap-1">
          <label class="label label-text text-xs font-semibold">Library Name *</label>
          <input
            v-model="newLibraryName"
            type="text"
            class="input input-bordered input-sm"
            placeholder="My Library"
            @keydown.enter="createLibrary"
          />
        </div>

        <div class="form-control gap-1">
          <label class="label label-text text-xs font-semibold">Description</label>
          <textarea
            v-model="newLibraryDesc"
            class="textarea textarea-bordered textarea-sm resize-none"
            placeholder="Library description..."
            rows="2"
          />
        </div>

        <div class="flex gap-2 justify-end">
          <button class="btn btn-sm" @click="showCreateLibrary = false">Cancel</button>
          <button
            class="btn btn-sm btn-primary"
            :disabled="!newLibraryName.trim()"
            @click="createLibrary"
          >
            Create
          </button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  name: 'MediaManager',
  props: {
    resourceType: { type: String, default: 'team' },
    resourceId: { type: String, default: null }
  },
  data() {
    return {
      selectedLibraryId: null,
      showCreateLibrary: false,
      newLibraryName: '',
      newLibraryDesc: ''
    }
  },
  created() {
    this.$storex.media.init()
  },
  computed: {
    libraries() {
      return this.$storex.media.librariesByResource(this.resourceType, this.resourceId)
    },
    selectedLibrary() {
      return this.$storex.media.libraryById(this.selectedLibraryId) || this.libraries[0] || null
    }
  },
  watch: {
    selectedLibrary(lib) {
      if (lib) this.selectedLibraryId = lib.id
    }
  },
  methods: {
    getMediaCount(libraryId) {
      return this.$storex.media.mediaByLibrary(libraryId).length
    },

    createLibrary() {
      if (!this.newLibraryName.trim()) return

      const lib = this.$storex.media.createLibrary({
        name: this.newLibraryName.trim(),
        description: this.newLibraryDesc.trim(),
        resourceType: this.resourceType,
        resourceId: this.resourceId
      })

      this.selectedLibraryId = lib.id
      this.newLibraryName = ''
      this.newLibraryDesc = ''
      this.showCreateLibrary = false
    }
  }
}
</script>