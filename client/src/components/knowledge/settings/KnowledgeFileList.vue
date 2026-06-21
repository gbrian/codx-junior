<script setup>
</script>

<template>
  <div class="flex flex-col gap-0 h-full">
    <!-- Header: Search + Actions -->
    <div class="flex items-center gap-2 mb-3">
      <label class="input input-sm input-bordered flex-1 flex items-center gap-2">
        <i class="fa-solid fa-magnifying-glass text-base-content-ERROR-40 text-xs"></i>
        <input
          type="text"
          class="grow text-xs"
          placeholder="Search files..."
          v-model="fileFilter"
        />
        <span class="text-xs text-base-content-ERROR-40" v-if="fileFilter">({{ filteredFiles.length }})</span>
        <button v-if="fileFilter" @click="fileFilter = ''" class="text-base-content-ERROR-40 hover:text-base-content">
          <i class="fa-solid fa-xmark text-xs"></i>
        </button>
      </label>
      <button class="btn btn-xs btn-ghost gap-1 text-base-content/60" @click="toggleAllNoneSelection">
        <i class="fa-solid fa-check-double text-xs"></i> Select
        <span class="">{{ selectedFileCount ? 'None' : 'All' }}</span>
      </button>
    </div>

    <!-- Extension Filter Pills -->
    <div class="flex flex-wrap gap-1 mb-3" v-if="Object.keys(extensions).length">
      <button
        v-for="(count, ext) in extensions"
        :key="ext"
        class="badge badge-sm cursor-pointer transition-all"
        :class="fileFilter === '.' + ext ? 'badge-warning' : 'badge-ghost hover:badge-warning'"
        @click="fileFilter = fileFilter === '.' + ext ? '' : '.' + ext"
      >
        .{{ ext }} <span class="ml-1 opacity-60">{{ count }}</span>
      </button>
    </div>

    <!-- File Grid -->
    <div class="flex-1 overflow-auto" v-if="filteredFiles?.length">
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-1">
        <label
          v-for="file in filteredFiles"
          :key="file"
          class="flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-all"
          :class="selectedFiles[file] ? 'bg-warning/10 border border-warning/30' : 'hover:bg-base-300 border border-transparent'"
        >
          <input type="checkbox" v-model="selectedFiles[file]" class="checkbox checkbox-xs checkbox-warning" />
          <i class="fa-solid fa-file text-xs opacity-40 flex-shrink-0"></i>
          <a
            class="text-xs truncate flex-1 hover:text-primary hover:underline cursor-pointer"
            :title="file.replace(projectPath, '')"
            @click.prevent="$ui.openFile(file)"
          >
            {{ file.replace(projectPath, '') }}
          </a>
        </label>
      </div>
    </div>

    <div v-else class="flex-1 flex items-center justify-center text-base-content/30 text-sm">
      <div class="text-center">
        <i class="fa-solid fa-folder-open text-2xl mb-2 block"></i>
        No files found
      </div>
    </div>

    <!-- Action Bar -->
    <div class="flex gap-2 flex-wrap pt-3 border-t border-base-300 mt-3" v-if="selectedFileCount">
      <span class="text-xs text-base-content/60 flex items-center">
        <i class="fa-solid fa-check-circle mr-1 text-warning"></i>
        {{ selectedFileCount }} selected
      </span>
      <div class="flex gap-1 flex-wrap ml-auto">
        <button
          class="btn btn-xs btn-warning gap-1"
          @click="$emit('index-files', selectedFilePaths)"
          v-if="activeTab === 0"
        >
          <i class="fa-solid fa-circle-up text-xs"></i> Index
        </button>
        <button
          class="btn btn-xs btn-error gap-1"
          @click="$emit('ignore-files', { paths: selectedFilePaths, asFolder: true })"
          v-if="activeTab !== 2"
        >
          <i class="fa-solid fa-folder text-xs"></i> Ignore folder
        </button>
        <button
          class="btn btn-xs btn-error btn-outline gap-1"
          @click="$emit('ignore-files', { paths: selectedFilePaths, asFolder: false })"
          v-if="activeTab !== 2"
        >
          <i class="fa-solid fa-file text-xs"></i> Ignore files
        </button>
        <button
          class="btn btn-xs btn-success gap-1"
          @click="$emit('unignore-files', selectedFilePaths)"
          v-if="activeTab === 2"
        >
          <i class="fa-solid fa-plus text-xs"></i> Unignore
        </button>
        <button
          class="btn btn-xs btn-ghost text-error gap-1"
          @click="$emit('drop-files', selectedFilePaths)"
        >
          <i class="fa-solid fa-trash-can text-xs"></i> Drop
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  emits: ['index-files', 'ignore-files', 'unignore-files', 'drop-files'],
  props: {
    files: Array,
    projectPath: String,
    activeTab: Number,
    indexingFiles: { type: Array, default: () => [] }
  },
  data() {
    return {
      fileFilter: '',
      selectedFiles: {}
    }
  },
  computed: {
    filteredFiles() {
      const { fileFilter } = this
      return this.files?.filter(f => !fileFilter || f.indexOf(fileFilter) !== -1)
    },
    selectedFilePaths() {
      return Object.keys(this.selectedFiles).filter(k => !!this.selectedFiles[k])
    },
    selectedFileCount() {
      return this.selectedFilePaths.length
    },
    extensions() {
      return (this.filteredFiles || [])
        .filter(f => f.indexOf('.') !== -1)
        .reduce((acc, v) => {
          const ext = v.split('.').reverse()[0]
          acc[ext] = (acc[ext] || 0) + 1
          return acc
        }, {})
    },
    // Files currently being indexed (for progress indicator)
    isIndexing() {
      return this.indexingFiles?.length > 0
    }
  },
  watch: {
    // Clear selection when files list changes (e.g. tab switch)
    files() {
      this.selectedFiles = {}
      this.fileFilter = ''
    }
  },
  methods: {
    toggleAllNoneSelection() {
      if (this.selectedFileCount) {
        this.selectedFiles = {}
      } else {
        this.selectedFiles = (this.filteredFiles || []).reduce(
          (acc, f) => ({ ...acc, [f]: true }), {}
        )
      }
    },
    clearSelection() {
      this.selectedFiles = {}
    }
  }
}
</script>