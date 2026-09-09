<script setup>
import moment from 'moment'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2 p-2 overflow-hidden">
    <!-- Toolbar: breadcrumb + actions -->
    <div class="flex items-center gap-2">
      <div class="breadcrumbs text-sm py-0 flex-1 overflow-x-auto">
        <ul>
          <li>
            <a class="gap-1" @click="goToRoot">
              <i class="fa-solid fa-house text-xs"></i>
              {{ projectName }}
            </a>
          </li>
          <li v-for="(part, ix) in breadcrumbParts" :key="ix">
            <a v-if="ix < breadcrumbParts.length - 1" @click="goToPart(ix)">
              {{ part }}
            </a>
            <span class="font-semibold" v-else>{{ part }}</span>
          </li>
        </ul>
      </div>

      <div class="input input-sm input-bordered flex items-center gap-2 flex-1">
        <!-- Search mode dropdown -->
        <div tabindex="0" class="btn btn-ghost btn-xs px-2 h-auto" 
          title="Select search mode"
          @click.stop="tooggleSearchMode()"  
        >
          <i :class="isContentSearch ? 'fa-solid fa-file-lines' : 'fa-solid fa-magnifying-glass'"></i>
        </div>
          
        <input
          type="text"
          v-model="filter"
          @keydown.enter="onEnterKey"
          :placeholder="isContentSearch ? 'Search content...' : 'Filter...'"
          class="grow bg-transparent outline-none text-sm"
        />

        <span class="cursor-pointer" @click="clearFilter" v-if="filter">
          <i class="fa-regular fa-circle-xmark"></i>
        </span>
      </div>

      <!-- Search scope toggle -->
      <button 
        class="btn btn-sm btn-ghost"
        :title="`${searchAllFiles ? 'Searching all files' : 'Searching only project files'}`"
        @click="toggleSearchScope"
      >
        <i :class="searchAllFiles ? 'fa-solid fa-asterisk text-warning' : 'fa-solid fa-code-branch text-info'"></i>
      </button>

      <button class="btn btn-sm btn-ghost" title="Refresh" @click="refresh">
        <i class="fa-solid fa-arrows-rotate" :class="loading && 'animate-spin'"></i>
      </button>
    </div>

    <!-- Search mode and scope indicator -->
    <div class="text-xs opacity-70 px-2 flex items-center gap-2" v-if="filter">
      <i class="fa-solid fa-circle-info"></i>
      <span v-if="isContentSearch">Searching file contents</span>
      <span v-else>Searching filenames</span>
      <span class="mx-1">•</span>
      <span :class="searchAllFiles ? 'text-warning' : 'text-info'">
        {{ searchAllFiles ? 'All files' : 'Project files only' }}
      </span>
    </div>

    <!-- Error banner -->
    <div class="alert alert-error py-2" v-if="error">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <span class="text-sm">{{ error }}</span>
    </div>

    <!-- Upload progress -->
    <div class="alert alert-info py-2" v-if="isUploading">
      <i class="fa-solid fa-arrow-up-from-bracket animate-bounce"></i>
      <div class="flex-1">
        <div class="text-sm font-semibold">Uploading {{ uploadingFileName }}</div>
        <progress class="progress progress-primary w-full h-2 mt-1" :value="uploadProgress" max="100"></progress>
        <div class="text-xs opacity-70 mt-1">{{ uploadProgress }}% • {{ formatSize(uploadProgressBytes) }} / {{ formatSize(uploadTotalBytes) }}</div>
      </div>
    </div>

    <!-- Directory tree listing -->
    <div 
      class="grow overflow-auto border border-base-300 rounded-lg"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
      :class="isDragOverBlank && 'bg-blue-50 dark:bg-blue-900 border-blue-400'"
    >
      <div class="flex items-center justify-center h-32" v-if="loading">
        <span class="loading loading-spinner loading-md"></span>
      </div>
      <div class="flex flex-col divide-y divide-base-300" v-else>
        <!-- Parent folder row -->
        <div
          class="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-base-200"
          @click="goUp"
          v-if="currentPath !== '.' && !isSearching"
        >
          <i class="fa-solid fa-folder text-warning w-4"></i>
          <span class="text-sm font-mono">..</span>
        </div>

        <!-- Entries: folders and files -->
        <div
          v-for="entry in visibleEntries"
          :key="getEntryKey(entry)"
          class="flex flex-col px-3 py-2 cursor-pointer hover:bg-base-200 group transition-colors"
          :class="[
            isEntrySelected(entry) && 'bg-blue-100 dark:bg-blue-900',
            entry.is_ignored && 'opacity-50',
            isDragOverFolder === entryPath(entry) && entry.is_dir && 'bg-blue-50 dark:bg-blue-900 border-l-4 border-blue-400'
          ]"
          @click="handleEntryClick(entry, $event)"
          @dragstart="onDragStart($event, entry)"
          @dragend="onDragEnd"
          @dragover.prevent="onDragOverEntry($event, entry)"
          @dragleave.prevent="onDragLeaveEntry"
          @drop.prevent="onDropEntry($event, entry)"
          draggable="true"
          :data-folder-path="entry.is_dir ? entryPath(entry) : null"
        >
          <!-- First row: icon, name, size, date -->
          <div class="flex items-center gap-3">
            <i
              class="w-4 text-sm flex-shrink-0"
              :class="getFileIcon(entry)"
            ></i>
            <span class="text-sm font-mono flex-1 truncate" :title="entry.name">
              {{ entry.name }}
            </span>
            
            <span class="text-xs opacity-70 flex-shrink-0" v-if="!entry.is_dir && !isContentSearching">
              {{ formatSize(entry.size) }}
            </span>
            <span class="text-xs opacity-70 flex-shrink-0 whitespace-nowrap">
              {{ formatLastModification(entry.last_modification) }}
            </span>
          </div>

          <!-- Second row: relative path (search results) or matched content (content search) -->
          <div class="text-xs opacity-60 font-mono pl-7 mt-1" v-if="isSearching">
            {{ getRelativeEntryPath(entry) }}
          </div>

          <!-- Content match preview (content search results only) -->
          <div class="text-xs opacity-70 pl-7 mt-1 bg-yellow-50 dark:bg-yellow-900 p-1 rounded" v-if="isContentSearching && entry.matches">
            <div v-for="(match, idx) in entry.matches.slice(0, 2)" :key="idx" class="line-clamp-1">
              <span class="font-semibold">Line {{ match.line_number }}:</span>
              {{ match.preview }}
            </div>
            <div v-if="entry.matches.length > 2" class="text-opacity-60">
              +{{ entry.matches.length - 2 }} more matches
            </div>
          </div>
        </div>

        <div class="text-center opacity-50 py-8 text-sm" v-if="!visibleEntries.length">
          {{ isSearching ? 'No files found matching your search' : 'No files found' }}
        </div>
      </div>
    </div>

    <!-- Pagination controls (search results only) -->
    <div class="flex items-center justify-between px-2 py-2 border-t border-base-300" v-if="isSearching && totalFiles > pageSize">
      <span class="text-xs opacity-70">
        Showing {{ (currentPage) * pageSize + 1 }}-{{ Math.min((currentPage + 1) * pageSize, totalFiles) }} of {{ totalFiles }}
      </span>
      <div class="flex items-center gap-2">
        <button
          class="btn btn-xs btn-ghost"
          @click="previousPage"
          :disabled="currentPage === 0"
        >
          <i class="fa-solid fa-chevron-left"></i>
        </button>
        <span class="text-xs px-2">
          Page {{ currentPage + 1 }} / {{ totalPages }}
        </span>
        <button
          class="btn btn-xs btn-ghost"
          @click="nextPage"
          :disabled="currentPage >= totalPages - 1"
        >
          <i class="fa-solid fa-chevron-right"></i>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FileExplorer',
  data() {
    return {
      currentPath: '.',
      entries: [],
      filter: '',
      searchMode: 'filename',
      searchAllFiles: false,
      loading: false,
      error: null,
      draggedEntry: null,
      selectedEntries: [],
      lastSelectedIndex: null,
      searchDebounceTimer: null,
      currentPage: 0,
      totalFiles: 0,
      pageSize: 50,
      isDragOverBlank: false,
      isDragOverFolder: null,
      isUploading: false,
      uploadProgress: 0,
      uploadProgressBytes: 0,
      uploadTotalBytes: 0,
      uploadingFileName: '',
      extensionIconMap: {
        // Code files
        'js': 'fa-brands fa-js text-yellow-500',
        'ts': 'fa-brands fa-js text-blue-500',
        'jsx': 'fa-brands fa-react text-blue-400',
        'tsx': 'fa-brands fa-react text-blue-400',
        'vue': 'fa-brands fa-vuejs text-green-500',
        'py': 'fa-brands fa-python text-blue-600',
        'java': 'fa-brands fa-java text-red-600',
        'cpp': 'fa-regular fa-file-code text-blue-600',
        'c': 'fa-regular fa-file-code text-blue-600',
        'cs': 'fa-brands fa-microsoft text-purple-600',
        'rb': 'fa-brands fa-gem text-red-700',
        'php': 'fa-brands fa-php text-indigo-600',
        'go': 'fa-regular fa-file-code text-cyan-500',
        'rs': 'fa-regular fa-file-code text-orange-600',
        'swift': 'fa-brands fa-swift text-orange-500',
        'kt': 'fa-regular fa-file-code text-purple-600',
        // Markup & Style
        'html': 'fa-brands fa-html5 text-orange-600',
        'css': 'fa-brands fa-css3-alt text-blue-500',
        'scss': 'fa-brands fa-sass text-pink-600',
        'sass': 'fa-brands fa-sass text-pink-600',
        'less': 'fa-regular fa-file-code text-blue-400',
        'xml': 'fa-regular fa-file-code text-orange-600',
        'json': 'fa-regular fa-file-code text-yellow-600',
        'yaml': 'fa-regular fa-file-code text-red-600',
        'yml': 'fa-regular fa-file-code text-red-600',
        'toml': 'fa-regular fa-file-code text-orange-700',
        'svg': 'fa-regular fa-file-image text-orange-400',
        // Templates
        'ejs': 'fa-regular fa-file-code text-yellow-600',
        'hbs': 'fa-regular fa-file-code text-orange-700',
        'pug': 'fa-regular fa-file-code text-brown-600',
        // Databases
        'sql': 'fa-solid fa-database text-blue-600',
        'db': 'fa-solid fa-database text-slate-600',
        'sqlite': 'fa-solid fa-database text-blue-400',
        // Documents
        'md': 'fa-brands fa-markdown text-slate-600',
        'txt': 'fa-regular fa-file-lines text-slate-500',
        'pdf': 'fa-solid fa-file-pdf text-red-600',
        'doc': 'fa-solid fa-file-word text-blue-600',
        'docx': 'fa-solid fa-file-word text-blue-600',
        'xls': 'fa-solid fa-file-excel text-green-600',
        'xlsx': 'fa-solid fa-file-excel text-green-600',
        'ppt': 'fa-solid fa-file-powerpoint text-orange-600',
        'pptx': 'fa-solid fa-file-powerpoint text-orange-600',
        // Media
        'png': 'fa-regular fa-file-image text-pink-500',
        'jpg': 'fa-regular fa-file-image text-pink-500',
        'jpeg': 'fa-regular fa-file-image text-pink-500',
        'gif': 'fa-regular fa-file-image text-pink-500',
        'webp': 'fa-regular fa-file-image text-pink-500',
        'ico': 'fa-regular fa-file-image text-slate-500',
        'mp4': 'fa-regular fa-file-video text-red-500',
        'avi': 'fa-regular fa-file-video text-red-500',
        'mov': 'fa-regular fa-file-video text-red-500',
        'mkv': 'fa-regular fa-file-video text-red-500',
        'flv': 'fa-regular fa-file-video text-red-500',
        'wmv': 'fa-regular fa-file-video text-red-500',
        'webm': 'fa-regular fa-file-video text-red-500',
        'mp3': 'fa-regular fa-file-audio text-purple-500',
        'wav': 'fa-regular fa-file-audio text-purple-500',
        'flac': 'fa-regular fa-file-audio text-purple-500',
        'aac': 'fa-regular fa-file-audio text-purple-500',
        'wma': 'fa-regular fa-file-audio text-purple-500',
        'ogg': 'fa-regular fa-file-audio text-purple-500',
        // Archives
        'zip': 'fa-regular fa-file-zipper text-slate-600',
        'rar': 'fa-regular fa-file-zipper text-slate-600',
        'tar': 'fa-regular fa-file-zipper text-slate-600',
        'gz': 'fa-regular fa-file-zipper text-slate-600',
        '7z': 'fa-regular fa-file-zipper text-slate-600',
        'bz2': 'fa-regular fa-file-zipper text-slate-600',
        // Config
        'env': 'fa-solid fa-gear text-slate-500',
        'config': 'fa-solid fa-gear text-slate-500',
        'conf': 'fa-solid fa-gear text-slate-500',
        'ini': 'fa-solid fa-gear text-slate-500',
        // Shell
        'sh': 'fa-solid fa-terminal text-slate-700',
        'bash': 'fa-solid fa-terminal text-slate-700',
        'zsh': 'fa-solid fa-terminal text-slate-700',
        'fish': 'fa-solid fa-terminal text-slate-700',
        'bat': 'fa-solid fa-terminal text-slate-700',
        // Version Control
        'git': 'fa-brands fa-git-alt text-orange-600',
        'gitignore': 'fa-brands fa-git-alt text-orange-600',
        // Other
        'lock': 'fa-solid fa-lock text-amber-600',
        'key': 'fa-solid fa-key text-yellow-600'
      }
    }
  },
  computed: {
    basePath() {
      return this.normalizePath(this.$project.abs_project_path)
    },
    $api() {
      return this.$project.$api
    },
    projectName() {
      return this.$storex.projects.activeProject?.project_name || 'root'
    },
    projectId() {
      return this.$storex.projects.activeProject?.project_id
    },
    breadcrumbParts() {
      return this.currentPath === '.' ? [] : this.currentPath.split('/')
    },
    isSearching() {
      return this.filter.trim().length > 0
    },
    isContentSearch() {
      return this.searchMode === 'content'
    },
    isContentSearching() {
      return this.isSearching && this.isContentSearch
    },
    totalPages() {
      return Math.ceil(this.totalFiles / this.pageSize)
    },
    visibleEntries() {
      return this.entries
        .filter(e => e.name?.trim())
        .sort((a, b) => {
          if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
          return a.name.localeCompare(b.name)
        })
    }
  },
  watch: {
    projectId() {
      this.currentPath = '.'
      this.currentPage = 0
      this.clearSelection()
      this.loadDir(this.basePath)
    }
  },
  mounted() {
    this.loadDir(this.basePath)
  },
  methods: {
    normalizePath(path) {
      if (!path) return ''
      return path.replace(/\/+/g, '/').replace(/\/$/, '')
    },
    getFileExtension(fileName) {
      return fileName.split('.').pop()?.toLowerCase() || ''
    },
    getFileIcon(entry) {
      if (entry.is_dir) {
        return 'fa-solid fa-folder text-warning'
      }
      const ext = this.getFileExtension(entry.name)
      return this.extensionIconMap[ext] || 'fa-regular fa-file text-info'
    },
    async loadDir(path) {
      const normalizedPath = this.normalizePath(path)
      this.loading = true
      this.error = null
      try {
        const response = await this.$api.files.list(normalizedPath)
        this.currentPath = this.getRelativePath(normalizedPath)
        this.entries = response.files || []
        this.totalFiles = 0
        this.currentPage = 0
        this.filter = ''
        this.searchMode = 'filename'
        this.clearSelection()
      } catch (ex) {
        console.error('Error listing files', ex)
        this.error = `Error listing "${normalizedPath}"`
      } finally {
        this.loading = false
      }
    },
    async performSearch(searchText) {
      if (!searchText.trim()) {
        this.loadDir(this.getAbsolutePath(this.currentPath))
        return
      }

      const absolutePath = this.getAbsolutePath(this.currentPath)
      this.loading = true
      this.error = null
      this.currentPage = 0

      try {
        if (this.isContentSearch) {
          await this.searchContentFiles(searchText, absolutePath)
        } else {
          await this.searchFilenames(searchText, absolutePath)
        }
        this.clearSelection()
      } catch (ex) {
        console.error('Error searching files', ex)
        this.error = `Error searching for "${searchText}"`
      } finally {
        this.loading = false
      }
    },
    async searchFilenames(searchText, absolutePath) {
      const response = await this.$api.files.search({
        search: searchText,
        searchPath: absolutePath,
        rawSearch: this.searchAllFiles,
        page: this.currentPage,
        pageSize: this.pageSize
      })
      this.entries = response.files || []
      this.totalFiles = response.total_files || 0
    },
    async searchContentFiles(searchText, absolutePath) {
      const response = await this.$api.files.searchContent({
        query: searchText,
        searchPath: absolutePath,
        rawSearch: this.searchAllFiles,
        page: this.currentPage,
        pageSize: this.pageSize
      })
      this.entries = response.files || []
      this.totalFiles = response.total_files || 0
    },
    onEnterKey() {
      if (this.filter.trim()) {
        this.performSearch(this.filter)
      }
    },
    tooggleSearchMode() {
      if (this.isContentSearch) {
        this.searchMode = 'filename'
      } else {
        this.searchMode = 'content'
      }
    },
    toggleSearchScope() {
      this.searchAllFiles = !this.searchAllFiles
      if (this.isSearching) {
        this.performSearch(this.filter)
      }
    },
    clearFilter() {
      this.filter = ''
      this.loadDir(this.getAbsolutePath(this.currentPath))
    },
    getRelativePath(absolutePath) {
      const normalized = this.normalizePath(absolutePath)
      if (normalized === this.basePath) {
        return '.'
      }
      if (normalized.startsWith(this.basePath)) {
        return normalized.substring(this.basePath.length).replace(/^\//, '')
      }
      return normalized
    },
    getAbsolutePath(relativePath) {
      if (relativePath === '.') {
        return this.basePath
      }
      return this.normalizePath(`${this.basePath}/${relativePath}`)
    },
    entryPath(entry) {
      return this.normalizePath(entry.file_path)
    },
    getRelativeEntryPath(entry) {
      const absolutePath = this.entryPath(entry)
      return this.getRelativePath(absolutePath)
    },
    getEntryKey(entry) {
      return `${this.entryPath(entry)}-${this.searchMode}`
    },
    isEntrySelected(entry) {
      return this.selectedEntries.some(e => this.entryPath(e) === this.entryPath(entry))
    },
    clearSelection() {
      this.selectedEntries = []
      this.lastSelectedIndex = null
    },
    handleEntryClick(entry, event) {
      const isCtrlClick = event.ctrlKey || event.metaKey
      const isShiftClick = event.shiftKey
      const index = this.visibleEntries.indexOf(entry)

      if (isShiftClick && this.lastSelectedIndex !== null) {
        this.selectRange(this.lastSelectedIndex, index)
      } else if (isCtrlClick) {
        this.$ui.openFileInViewer(this.entryPath(entry))
      } else {
        this.clearSelection()
        this.addSelection(entry)
        if (entry.is_dir && !this.isSearching) {
          this.loadDir(this.entryPath(entry))
        } else if (!entry.is_dir) {
          this.$emit('open', {
            path: this.entryPath(entry),
            name: entry.name
          })
        }
      }

      this.lastSelectedIndex = index
    },
    addSelection(entry) {
      if (!this.isEntrySelected(entry)) {
        this.selectedEntries.push(entry)
      }
    },
    toggleSelection(entry) {
      const index = this.selectedEntries.findIndex(e => this.entryPath(e) === this.entryPath(entry))
      if (index >= 0) {
        this.selectedEntries.splice(index, 1)
      } else {
        this.selectedEntries.push(entry)
      }
    },
    selectRange(startIndex, endIndex) {
      const start = Math.min(startIndex, endIndex)
      const end = Math.max(startIndex, endIndex)
      const rangeEntries = this.visibleEntries.slice(start, end + 1)
      this.selectedEntries = rangeEntries
    },
    goToRoot() {
      this.clearSelection()
      this.loadDir(this.basePath)
    },
    goToPart(ix) {
      this.clearSelection()
      const relativePath = this.breadcrumbParts.slice(0, ix + 1).join('/')
      this.loadDir(this.getAbsolutePath(relativePath))
    },
    goUp() {
      const parts = this.breadcrumbParts.slice(0, -1)
      this.clearSelection()
      const relativePath = parts.length ? parts.join('/') : '.'
      this.loadDir(this.getAbsolutePath(relativePath))
    },
    previousPage() {
      if (this.currentPage > 0) {
        this.currentPage--
        this.loadSearchPage()
      }
    },
    nextPage() {
      if (this.currentPage < this.totalPages - 1) {
        this.currentPage++
        this.loadSearchPage()
      }
    },
    async loadSearchPage() {
      const absolutePath = this.getAbsolutePath(this.currentPath)
      this.loading = true
      this.error = null
      try {
        if (this.isContentSearch) {
          await this.searchContentFiles(this.filter, absolutePath)
        } else {
          await this.searchFilenames(this.filter, absolutePath)
        }
        this.clearSelection()
      } catch (ex) {
        console.error('Error loading search page', ex)
        this.error = `Error loading page ${this.currentPage + 1}`
      } finally {
        this.loading = false
      }
    },
    refresh() {
      this.currentPage = 0
      if (this.isSearching) {
        this.performSearch(this.filter)
      } else {
        this.loadDir(this.getAbsolutePath(this.currentPath))
      }
    },
    formatSize(size) {
      if (size === null || size === undefined) return ''
      if (size < 1024) return `${size} B`
      if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
      return `${(size / (1024 * 1024)).toFixed(1)} MB`
    },
    formatLastModification(timestamp) {
      if (!timestamp) return '—'
      const modified = moment(timestamp)
      const daysDiff = moment().diff(modified, 'days')
      return daysDiff < 5 ? modified.fromNow() : modified.format('MMM DD, YYYY')
    },
    onDragStart(event, entry) {
      this.draggedEntry = entry
      const filesToDrag = this.isEntrySelected(entry) && this.selectedEntries.length > 1
        ? this.selectedEntries
        : [entry]

      const plainTextPaths = filesToDrag.map(e => this.entryPath(e)).join('\n')
      event.dataTransfer.setData('text/plain', plainTextPaths)

      const fileData = JSON.stringify({
        source: 'file-explorer',
        files: filesToDrag.map(e => ({
          path: this.entryPath(e),
          name: e.name,
          is_dir: e.is_dir
        }))
      })
      event.dataTransfer.setData('application/x-file-list-json', fileData)
    },
    onDragEnd() {
      this.draggedEntry = null
      this.isDragOverBlank = false
      this.isDragOverFolder = null
    },
    onDragOver(event) {
      if (this.draggedEntry) return
      event.dataTransfer.dropEffect = 'copy'
      this.isDragOverBlank = true
    },
    onDragLeave(event) {
      if (event.target === event.currentTarget) {
        this.isDragOverBlank = false
      }
    },
    onDragOverEntry(event, entry) {
      if (this.draggedEntry || !entry.is_dir) return
      event.dataTransfer.dropEffect = 'copy'
      this.isDragOverFolder = this.entryPath(entry)
    },
    onDragLeaveEntry() {
      this.isDragOverFolder = null
    },
    async onDrop(event) {
      this.isDragOverBlank = false
      const files = event.dataTransfer.files
      if (files.length === 0) return
      
      const targetPath = this.getAbsolutePath(this.currentPath)
      await this.handleFilesUpload(targetPath, files)
    },
    async onDropEntry(event, entry) {
      this.isDragOverFolder = null
      if (!entry.is_dir) return
      
      const files = event.dataTransfer.files
      if (files.length === 0) return
      
      const targetPath = this.entryPath(entry)
      await this.handleFilesUpload(targetPath, files)
    },
    async handleFilesUpload(targetPath, fileList) {
      if (fileList.length === 0) return
      
      this.isUploading = true
      this.uploadProgress = 0
      this.uploadProgressBytes = 0
      this.uploadTotalBytes = 0
      this.error = null
      
      try {
        const files = Array.from(fileList)
        
        this.uploadTotalBytes = files.reduce((sum, f) => sum + f.size, 0)
        this.uploadingFileName = files.length === 1 ? files[0].name : `${files.length} files`
        
        await this.$api.files.upload(targetPath, files, (progress) => {
          this.uploadProgress = progress.percent
          this.uploadProgressBytes = progress.loaded
          this.uploadTotalBytes = progress.total
        })
        
        await this.refresh()
      } catch (error) {
        console.error('Upload error:', error)
        this.error = `Upload failed: ${error.message}`
      } finally {
        this.isUploading = false
        this.uploadProgress = 0
        this.uploadProgressBytes = 0
        this.uploadTotalBytes = 0
      }
    }
  }
}
</script>