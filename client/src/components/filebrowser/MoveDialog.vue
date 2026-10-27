<script setup>
</script>

<template>
  <div v-if="isVisible" class="modal modal-open">
    <div class="modal-box flex flex-col gap-3 max-h-[85vh]">
      <!-- Header -->
      <h3 class="font-bold text-lg flex items-center gap-2">
        <i class="fa-solid fa-folder-tree text-primary"></i>
        Move {{ sources.length }} {{ sources.length === 1 ? 'item' : 'items' }}
      </h3>

      <!-- Items being moved -->
      <div class="flex flex-wrap gap-1 max-h-20 overflow-auto">
        <span
          v-for="source in sources"
          :key="source"
          class="badge badge-ghost badge-sm font-mono max-w-44 truncate"
          :title="source"
        >
          <i :class="sourceIcon(source)" class="mr-1 text-xs"></i>
          {{ baseName(source) }}
        </span>
      </div>

      <!-- Destination picker toolbar -->
      <div class="flex items-center gap-2">
        <button
          class="btn btn-sm btn-ghost"
          title="Parent folder"
          :disabled="isRoot || loading"
          @click="goUp"
        >
          <i class="fa-solid fa-arrow-turn-up"></i>
        </button>

        <div class="breadcrumbs text-sm py-0 flex-1 overflow-x-auto">
          <ul>
            <li>
              <a class="gap-1" title="Project root" @click="browseTo(projectRoot)">
                <i class="fa-solid fa-house text-xs"></i>
              </a>
            </li>
            <li v-for="(part, ix) in breadcrumbParts" :key="part.path">
              <a v-if="ix < breadcrumbParts.length - 1" @click="browseTo(part.path)">{{ part.name }}</a>
              <span v-else class="font-semibold">{{ part.name }}</span>
            </li>
          </ul>
        </div>

        <button
          class="btn btn-sm btn-ghost"
          title="Refresh folders"
          @click="loadFolders(browsePath)"
        >
          <i class="fa-solid fa-arrows-rotate" :class="loading && 'animate-spin'"></i>
        </button>
      </div>

      <!-- Folders of the browsed directory: fixed height, scrolls internally
           so a folder with many subfolders never grows the dialog -->
      <div class="h-64 shrink-0 overflow-y-auto overscroll-contain border border-base-300 rounded-lg">
        <div class="flex items-center justify-center h-full" v-if="loading">
          <span class="loading loading-spinner loading-md"></span>
        </div>
        <div class="flex flex-col divide-y divide-base-300" v-else>
          <div
            v-for="folder in folders"
            :key="folder.path"
            class="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-base-200"
            :class="folder.path === browsePath && 'bg-base-200'"
            :title="folder.path"
            @click="browseTo(folder.path)"
          >
            <i class="fa-solid fa-folder text-warning w-4"></i>
            <span class="text-sm font-mono flex-1 truncate">{{ folder.name }}</span>
            <i class="fa-solid fa-chevron-right text-xs opacity-40"></i>
          </div>
          <div class="text-center opacity-50 py-6 text-sm" v-if="!folders.length">
            No subfolders
          </div>
        </div>
      </div>

      <!-- Destination summary -->
      <p class="text-xs opacity-70 flex items-center gap-1">
        <i class="fa-solid fa-location-arrow"></i>
        Destination:
        <span class="font-mono truncate" :title="browsePath">{{ displayPath }}</span>
      </p>

      <div v-if="error" class="alert alert-error py-2">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span class="text-sm">{{ error }}</span>
      </div>

      <div v-if="invalidTarget" class="alert alert-warning py-2">
        <i class="fa-solid fa-ban"></i>
        <span class="text-sm">A folder cannot be moved inside itself.</span>
      </div>

      <!-- Actions -->
      <div class="modal-action">
        <button class="btn btn-ghost" @click="$emit('cancel')">Cancel</button>
        <button
          class="btn btn-primary"
          :disabled="loading || invalidTarget"
          @click="confirm"
        >
          <i class="fa-solid fa-folder-tree"></i>
          Move here
        </button>
      </div>
    </div>
    <div class="modal-backdrop" @click="$emit('cancel')"></div>
  </div>
</template>

<script>
export default {
  name: 'MoveDialog',
  props: {
    isVisible: {
      type: Boolean,
      default: false
    },
    // Paths ('/src/a.js' or '<project>/src/a.js') of the selected entries
    sources: {
      type: Array,
      default: () => []
    },
    // Folder currently open in the explorer, used as starting point
    startPath: {
      type: String,
      default: ''
    }
  },
  emits: ['move', 'cancel'],
  data() {
    return {
      browsePath: '',
      entries: [],
      loading: false,
      error: null
    }
  },
  computed: {
    $api() {
      return this.$project.$api
    },
    // Absolute project path: browsed paths are always resolved inside it
    projectRoot() {
      return this.normalizePath(this.$project.abs_project_path) || '/'
    },
    isRoot() {
      return this.browsePath === this.projectRoot
    },
    // Portion of the browsed path relative to the project root
    relativeParts() {
      if (this.isRoot) return []
      const prefix = this.projectRoot === '/' ? '' : this.projectRoot
      const relative = this.browsePath.startsWith(prefix)
        ? this.browsePath.substring(prefix.length)
        : this.browsePath
      return relative.split('/').filter(Boolean)
    },
    breadcrumbParts() {
      return this.relativeParts.map((name, ix) => ({
        name,
        path: this.joinPath(this.projectRoot, this.relativeParts.slice(0, ix + 1).join('/'))
      }))
    },
    displayPath() {
      return '/' + this.relativeParts.join('/')
    },
    folders() {
      return this.entries
        .filter(entry => entry.is_dir && entry.name)
        .map(entry => ({
          name: entry.name,
          path: this.normalizePath(entry.file_path || this.joinPath(this.browsePath, entry.name))
        }))
        .sort((a, b) => a.name.localeCompare(b.name))
    },
    // Moving a folder into itself (or into one of its descendants) is not allowed
    invalidTarget() {
      return this.sources.some(source =>
        this.browsePath === source || this.browsePath.startsWith(`${source}/`)
      )
    }
  },
  watch: {
    isVisible: {
      immediate: true,
      handler(visible) {
        if (visible) this.reset()
      }
    }
  },
  methods: {
    normalizePath(path) {
      if (!path) return ''
      return String(path).replace(/\\/g, '/').replace(/\/+/g, '/').replace(/\/$/, '')
    },
    joinPath(base, name) {
      if (!name) return base
      const prefix = base === '/' ? '' : base
      return this.normalizePath(`${prefix}/${name}`)
    },
    baseName(path) {
      return this.normalizePath(path).split('/').filter(Boolean).pop() || path
    },
    sourceIcon(source) {
      // Files have an extension in the last segment, folders do not
      return this.baseName(source).includes('.')
        ? 'fa-regular fa-file'
        : 'fa-solid fa-folder'
    },
    reset() {
      this.error = null
      this.entries = []
      const root = this.projectRoot
      let start = this.normalizePath(this.startPath) || root
      if (start !== '/' && !start.startsWith('/')) {
        start = this.joinPath(root, start)
      }
      // Never browse outside the project
      this.browsePath = start.startsWith(root) ? start : root
      this.loadFolders(this.browsePath)
    },
    async loadFolders(path) {
      this.loading = true
      this.error = null
      try {
        const response = await this.$api.files.list(path)
        this.entries = response.files || []
      } catch (ex) {
        console.error('Error listing folders', ex)
        this.error = `Could not list "${this.displayPath}"`
        this.entries = []
      } finally {
        this.loading = false
      }
    },
    browseTo(path) {
      this.browsePath = this.normalizePath(path) || this.projectRoot
      this.loadFolders(this.browsePath)
    },
    goUp() {
      if (this.isRoot) return
      const parent = this.browsePath.substring(0, this.browsePath.lastIndexOf('/'))
      this.browseTo(parent && parent.startsWith(this.projectRoot) ? parent : this.projectRoot)
    },
    confirm() {
      if (this.invalidTarget) return
      this.$emit('move', this.browsePath)
    }
  }
}
</script>