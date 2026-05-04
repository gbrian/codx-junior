<script setup>
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex gap-2 my-2">
      <button class="btn btn-sm" @click="toggleAllNoneSelection">Select all/none</button>
      <label class="input input-sm input-bordered flex items-center gap-2">
        <input type="text" class="grow" placeholder="Search" v-model="fileFilter" />
        <i class="fa-solid fa-magnifying-glass"></i>
        <span class="-mt-1" v-if="fileFilter">({{ filteredFiles.length }})</span>
      </label>
    </div>
    <div class="flex my-2 flex-wrap gap-1">
      <div
        class="badge badge-xs click"
        v-for="(count, extension) in extensions"
        :key="extension"
        @click="fileFilter = '.' + extension"
      >
        {{ extension }} ({{ count }})
      </div>
    </div>
    <div class="max-h-60 overflow-auto" v-if="filteredFiles?.length">
      <div class="text-xs" v-for="file in filteredFiles" :key="file">
        <div class="flex gap-2">
          <input type="checkbox" v-model="selectedFiles[file]" class="checkbox" />
          <a class="underline click" @click="$ui.openFile(file)">
            {{ file.replace(projectPath, '') }}
          </a>
        </div>
      </div>
    </div>
    <div class="flex gap-2 flex-wrap">
      <button class="btn btn-primary btn-sm" @click="$emit('index-files', selectedFilePaths)" v-if="selectedFileCount">
        <i class="fa-solid fa-circle-info"></i> Index ({{ selectedFileCount }}) files now
      </button>
      <button
        class="btn btn-primary btn-sm btn-error text-white"
        @click="$emit('ignore-files', { paths: selectedFilePaths, asFolder: true })"
        v-if="selectedFileCount && activeTab !== 2"
      >
        <i class="fa-solid fa-folder"></i> Ignore ({{ selectedFileCount }}) folder
      </button>
      <button
        class="btn btn-primary btn-sm btn-error text-white"
        @click="$emit('ignore-files', { paths: selectedFilePaths, asFolder: false })"
        v-if="selectedFileCount && activeTab !== 2"
      >
        <i class="fa-solid fa-file"></i> Ignore ({{ selectedFileCount }}) files
      </button>
      <button
        class="btn btn-primary btn-sm btn-success text-white"
        @click="$emit('unignore-files', selectedFilePaths)"
        v-if="selectedFileCount && activeTab === 2"
      >
        <i class="fa-solid fa-plus"></i> Add ({{ selectedFileCount }}) files
      </button>
      <button
        class="btn btn-primary btn-sm btn-warning text-white"
        @click="$emit('drop-files', selectedFilePaths)"
        v-if="selectedFileCount"
      >
        <i class="fa-solid fa-trash-can"></i> Drop ({{ selectedFileCount }}) files
      </button>
    </div>
  </div>
</template>

<script>
export default {
  emits: ['index-files', 'ignore-files', 'unignore-files', 'drop-files'],
  props: {
    files: Array,
    projectPath: String,
    activeTab: Number
  },
  data() {
    return {
      fileFilter: null,
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
      return this.filteredFiles
        ?.filter(f => f.indexOf('.') !== -1)
        .reduce((acc, v) => {
          const extension = v.split('.').reverse()[0]
          acc[extension] = (acc[extension] || 0) + 1
          return acc
        }, {})
    }
  },
  methods: {
    toggleAllNoneSelection() {
      if (this.selectedFileCount) {
        this.selectedFiles = {}
      } else {
        this.selectedFiles = (this.filteredFiles || []).reduce(
          (acc, f) => ({ ...acc, [f]: true }),
          {}
        )
      }
    },
    clearSelection() {
      this.selectedFiles = {}
    }
  }
}
</script>