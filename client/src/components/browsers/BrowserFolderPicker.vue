<script setup>
</script>

<template>
  <!--
    Project folder picker used by the browser session settings.

    Folders are browsed with the project files API (one level per request), so
    the list never has to load the whole tree. Every folder can be selected
    without leaving the current level: navigating and selecting are two
    different affordances (checkbox/radio + folder name).

    multiple  → checkboxes, several folders, emits an array
    single    → radios, one folder, emits an array with one entry
  -->
  <div
    class="modal modal-open"
    role="dialog"
    aria-modal="true"
    :aria-label="title"
    @click.self="cancel"
  >
    <div class="modal-box w-11/12 max-w-xl flex flex-col gap-3 max-h-[85vh]">
      <!-- Header -->
      <div class="flex items-start gap-2">
        <div class="min-w-0 flex-1">
          <h3 class="text-base font-bold">{{ title }}</h3>
          <p class="text-[11px] opacity-60">
            {{ allowMultiple
              ? 'Select the project folders the browser must be able to read and write.'
              : 'Select the project folder the browser must use.' }}
          </p>
        </div>
        <button
          class="btn btn-sm btn-circle btn-ghost"
          aria-label="Close folder picker"
          @click="cancel"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- Breadcrumb -->
      <nav class="flex items-center gap-1 overflow-x-auto text-xs" aria-label="Folder path">
        <button class="btn btn-xs btn-ghost gap-1 flex-shrink-0" @click="goTo('')">
          <i class="fa-solid fa-folder-open text-[10px]"></i>
          <span class="max-w-32 truncate">{{ projectName }}</span>
        </button>
        <template v-for="(part, index) in breadcrumb" :key="`${part}-${index}`">
          <i class="fa-solid fa-chevron-right text-[9px] opacity-40 flex-shrink-0" aria-hidden="true"></i>
          <button class="btn btn-xs btn-ghost flex-shrink-0" @click="goTo(pathUntil(index))">
            {{ part }}
          </button>
        </template>
      </nav>

      <!-- Folder listing -->
      <div class="flex-1 min-h-0 overflow-y-auto rounded-lg border border-base-content/10 divide-y divide-base-content/10">
        <div v-if="loading" class="flex items-center justify-center gap-2 p-6 text-xs opacity-70">
          <span class="loading loading-spinner loading-xs"></span>
          Loading folders...
        </div>

        <p v-else-if="error" class="p-4 text-xs text-error">
          <i class="fa-solid fa-triangle-exclamation mr-1"></i>{{ error }}
        </p>

        <template v-else>
          <!-- Up -->
          <button
            v-if="currentPath"
            class="w-full flex items-center gap-2 px-2 py-2 text-left hover:bg-base-200/60 transition-colors duration-150"
            :aria-label="`Go up to ${parentPathLabel}`"
            @click="goUp"
          >
            <i class="fa-solid fa-arrow-turn-up text-[11px] opacity-50 w-3.5 text-center"></i>
            <span class="text-xs font-mono">..</span>
          </button>

          <!-- Project root: mounts every folder at once -->
          <div v-if="!currentPath" class="flex items-center gap-2 px-2 py-2">
            <input
              id="browser-picker-root"
              :type="allowMultiple ? 'checkbox' : 'radio'"
              :class="allowMultiple ? 'checkbox checkbox-xs checkbox-primary' : 'radio radio-xs radio-primary'"
              :checked="isRootSelected"
              @change="toggleRoot"
            />
            <label for="browser-picker-root" class="min-w-0 flex-1 cursor-pointer">
              <span class="block text-xs font-semibold">Whole project</span>
              <span class="block text-[10px] opacity-55">
                {{ rootMountPath }}
              </span>
            </label>
          </div>

          <!-- Subfolders -->
          <div
            v-for="folder in folders"
            :key="folder.path"
            class="flex items-center gap-2 px-2 py-2"
          >
            <input
              :id="`browser-picker-${folder.path}`"
              :type="allowMultiple ? 'checkbox' : 'radio'"
              :class="allowMultiple ? 'checkbox checkbox-xs checkbox-primary' : 'radio radio-xs radio-primary'"
              :checked="isSelected(folder.path)"
              @change="toggle(folder)"
            />
            <button
              class="flex min-w-0 flex-1 items-center gap-1.5 rounded text-left focus:outline-none focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-primary"
              :aria-label="`Open folder ${folder.name}`"
              @click="goTo(folder.path)"
            >
              <i class="fa-solid fa-folder text-warning text-[11px] flex-shrink-0" aria-hidden="true"></i>
              <span class="truncate text-xs font-mono">{{ folder.name }}</span>
              <i class="fa-solid fa-chevron-right text-[9px] opacity-40 flex-shrink-0" aria-hidden="true"></i>
            </button>
          </div>

          <p v-if="!folders.length" class="p-4 text-center text-xs opacity-60">
            {{ currentPath ? 'This folder has no subfolders' : 'This project has no folders' }}
          </p>
        </template>
      </div>

      <!-- Footer -->
      <div class="flex items-center gap-2">
        <span class="min-w-0 flex-1 truncate text-[11px] opacity-60" :title="selectionLabel">
          {{ selectionLabel }}
        </span>
        <button class="btn btn-sm btn-ghost" @click="cancel">Cancel</button>
        <button class="btn btn-sm btn-primary" :disabled="!selection.length" @click="confirm">
          <i class="fa-solid fa-check"></i>
          {{ confirmLabel }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'BrowserFolderPicker',
  emits: ['select', 'close'],
  props: {
    /** 'multiple' selects several folders, 'single' one folder. */
    mode: { type: String, default: 'multiple' },
    /** Already selected project-relative paths ('' means the project root). */
    modelValue: { type: Array, default: () => [] },
    title: { type: String, default: 'Project folders' }
  },
  data() {
    return {
      // Project-relative folder being listed ('' = project root)
      currentPath: '',
      folders: [],
      loading: false,
      error: null,
      selected: [...(this.modelValue || [])]
    }
  },
  computed: {
    // `$project.$api` is the convention used by the file explorer; the store
    // API is the fallback when the project of the current view is not resolved.
    api() {
      return this.$project?.$api || this.$storex?.api || null
    },
    projectName() {
      return this.$project?.project_name ||
        this.$storex?.projects?.activeProject?.project_name ||
        'project'
    },
    basePath() {
      const root = this.$project?.abs_project_path ||
        this.$storex?.projects?.activeProject?.abs_project_path ||
        ''
      return String(root).replace(/\/+$/, '')
    },
    allowMultiple() {
      return this.mode !== 'single'
    },
    breadcrumb() {
      return this.currentPath ? this.currentPath.split('/').filter(Boolean) : []
    },
    parentPathLabel() {
      return this.pathUntil(this.breadcrumb.length - 2) || this.projectName
    },
    rootMountPath() {
      return `/home/${this.safeProjectName(this.projectName)}`
    },
    isRootSelected() {
      return this.selection.includes('')
    },
    /**
     * Current selection as an array. Single mode keeps a single entry and the
     * root always wins because it already mounts every folder.
     */
    selection() {
      const unique = [...new Set(this.selected)]
      if (unique.includes('')) return ['']
      // A folder already covered by a selected parent is redundant
      const kept = unique.filter(path => !unique.some(other =>
        other && other !== path && path.startsWith(`${other}/`)
      ))
      if (this.allowMultiple) return kept
      return kept.slice(0, 1)
    },
    selectionLabel() {
      if (!this.selection.length) return 'Nothing selected'
      return this.selection
        .map(path => (path ? path : 'whole project'))
        .join(', ')
    },
    confirmLabel() {
      const total = this.selection.length
      if (!total) return 'Select'
      return this.allowMultiple ? `Add ${total} folder(s)` : 'Select folder'
    }
  },
  methods: {
    /** Mirror of the backend rule used to build `/home/<project_name>`. */
    safeProjectName(value) {
      const name = String(value || '')
        .replace(/[^A-Za-z0-9._-]+/g, '-')
        .replace(/^[-._]+|[-._]+$/g, '')
      return name || 'project'
    },
    absolutePath(relativePath) {
      return relativePath ? `${this.basePath}/${relativePath}` : this.basePath
    },
    /** Project-relative path of the crumbs up to `index` (inclusive). */
    pathUntil(index) {
      if (index < 0) return ''
      return this.breadcrumb.slice(0, index + 1).join('/')
    },
    async load(relativePath) {
      if (!this.api?.files?.list) {
        this.error = 'File API not available for this project'
        this.folders = []
        return
      }
      this.loading = true
      this.error = null
      try {
        const response = await this.api.files.list(this.absolutePath(relativePath))
        const base = this.basePath
        this.folders = (response?.files || [])
          .filter(entry => entry?.is_dir)
          .map((entry) => {
            const absolute = String(entry.file_path || '').replace(/\/+$/, '')
            const relative = base && absolute.startsWith(base)
              ? absolute.slice(base.length).replace(/^\//, '')
              : (entry.name || '')
            return { name: entry.name || relative, path: relative }
          })
          .filter(folder => folder.path)
          .sort((a, b) => String(a.name).localeCompare(String(b.name)))
        this.currentPath = relativePath
      } catch (ex) {
        console.error('[BrowserFolderPicker] Error listing folders:', ex)
        this.error = ex?.message || 'Could not list the project folders'
        this.folders = []
      } finally {
        this.loading = false
      }
    },
    goTo(relativePath) {
      this.load(relativePath || '')
    },
    goUp() {
      this.goTo(this.pathUntil(this.breadcrumb.length - 2))
    },
    isSelected(relativePath) {
      return this.selection.includes(relativePath)
    },
    toggleRoot() {
      this.selected = this.isRootSelected ? [] : ['']
    },
    toggle(folder) {
      if (!this.allowMultiple) {
        this.selected = [folder.path]
        return
      }
      this.selected = this.isSelected(folder.path)
        ? this.selected.filter(path => path !== folder.path)
        : [...this.selected.filter(path => path !== ''), folder.path]
    },
    confirm() {
      const selection = this.selection
      if (!selection.length) return
      this.$emit('select', selection)
      this.$emit('close')
    },
    cancel() {
      this.$emit('close')
    },
    handleWindowKeydown(event) {
      if (event.key === 'Escape') this.cancel()
    }
  },
  mounted() {
    window.addEventListener('keydown', this.handleWindowKeydown)
    this.load('')
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.handleWindowKeydown)
  }
}
</script>