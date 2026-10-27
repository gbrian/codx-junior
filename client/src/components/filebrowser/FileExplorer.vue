<script setup>
import moment from 'moment'
import ContextMenu from './ContextMenu.vue'
import CreateFileDialog from './CreateFileDialog.vue'
import MoveDialog from './MoveDialog.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2 p-2 overflow-hidden bg-base-300">
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

      <!-- View mode toggle (list / icon grid / preview) -->
      <button
        class="btn btn-sm btn-ghost"
        :title="viewToggleTitle"
        :aria-label="viewToggleTitle"
        @click="toggleViewMode"
      >
        <i :class="viewToggleIcon"></i>
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
      ref="listContainer"
      class="grow overflow-auto border border-base-100 rounded-lg relative"
      @mousedown="onSelectionMouseDown"
      @dragover.prevent="onDragOver"
      @dragleave.prevent="onDragLeave"
      @drop.prevent="onDrop"
      @contextmenu.prevent="onContextMenu"
      :class="isDragOverBlank && 'bg-blue-50 dark:bg-blue-900 border-blue-400'"
    >
      <!-- Marquee selection rectangle (see onSelectionMouseDown) -->
      <div
        class="absolute border border-primary bg-primary/20 pointer-events-none z-10"
        :style="selectionBox"
        v-if="selectionBox"
      ></div>

      <div class="flex items-center justify-center h-32" v-if="loading">
        <span class="loading loading-spinner loading-md"></span>
      </div>

      <!-- List view -->
      <div class="flex flex-col divide-y divide-base-300" v-else-if="viewMode === 'list'">
        <!-- Parent folder row -->
        <div
          class="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-base-200"
          @click="goUp"
          data-no-marquee
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
          @contextmenu.prevent.stop="onEntryContextMenu($event, entry)"
          @dragstart="onDragStart($event, entry)"
          @dragend="onDragEnd"
          @dragover.stop.prevent="onDragOverEntry($event, entry)"
          @dragleave.prevent="onDragLeaveEntry"
          @drop.stop.prevent="onDropEntry($event, entry)"
          draggable="true"
          :data-entry-path="entryPath(entry)"
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

      <!-- Icon / grid view -->
      <div class="p-3" v-else-if="viewMode === 'grid'">
        <div class="grid gap-2 grid-cols-[repeat(auto-fill,minmax(96px,1fr))]">
          <!-- Parent folder tile -->
          <div
            class="flex flex-col items-center gap-2 p-3 rounded-lg cursor-pointer hover:bg-base-200 transition-colors"
            @click="goUp"
            data-no-marquee
            v-if="currentPath !== '.' && !isSearching"
          >
            <i class="fa-solid fa-folder text-warning text-4xl"></i>
            <span class="text-xs font-mono w-full text-center truncate">..</span>
          </div>

          <!-- Entries: folders and files -->
          <div
            v-for="entry in visibleEntries"
            :key="getEntryKey(entry)"
            class="flex flex-col items-center gap-2 p-3 rounded-lg cursor-pointer hover:bg-base-200 group transition-colors"
            :class="[
              isEntrySelected(entry) && 'bg-blue-100 dark:bg-blue-900',
              entry.is_ignored && 'opacity-50',
              isDragOverFolder === entryPath(entry) && entry.is_dir && 'bg-blue-50 dark:bg-blue-900 ring-2 ring-blue-400'
            ]"
            @click="handleEntryClick(entry, $event)"
            @contextmenu.prevent.stop="onEntryContextMenu($event, entry)"
            @dragstart="onDragStart($event, entry)"
            @dragend="onDragEnd"
            @dragover.stop.prevent="onDragOverEntry($event, entry)"
            @dragleave.prevent="onDragLeaveEntry"
            @drop.stop.prevent="onDropEntry($event, entry)"
            draggable="true"
            :data-entry-path="entryPath(entry)"
            :data-folder-path="entry.is_dir ? entryPath(entry) : null"
            :title="entry.name"
          >
            <i class="text-4xl" :class="getFileIcon(entry)"></i>
            <span class="text-xs font-mono w-full text-center truncate">{{ entry.name }}</span>

            <span class="text-[10px] opacity-60" v-if="!entry.is_dir && !isContentSearching">
              {{ formatSize(entry.size) }}
            </span>

            <!-- Content search match count badge -->
            <span class="badge badge-xs badge-warning" v-if="isContentSearching && entry.matches">
              {{ entry.matches.length }}
            </span>
          </div>

          <!-- Empty state -->
          <div class="col-span-full text-center opacity-50 py-8 text-sm" v-if="!visibleEntries.length">
            {{ isSearching ? 'No files found matching your search' : 'No files found' }}
          </div>
        </div>
      </div>

      <!-- Preview mode: visual thumbnails for images, video, PDF and audio -->
      <div class="p-3" v-else>
        <div class="grid gap-2 grid-cols-[repeat(auto-fill,minmax(140px,1fr))]">
          <!-- Parent folder tile -->
          <div
            class="flex flex-col items-center justify-center gap-2 aspect-square rounded-lg cursor-pointer bg-base-200 hover:bg-base-300 transition-colors"
            @click="goUp"
            data-no-marquee
            v-if="currentPath !== '.' && !isSearching"
          >
            <i class="fa-solid fa-folder-open text-warning text-3xl"></i>
            <span class="text-xs font-mono max-w-full px-2 truncate">..</span>
          </div>

          <!-- Entries: thumbnail tiles -->
          <div
            v-for="entry in visibleEntries"
            :key="getEntryKey(entry)"
            class="group relative aspect-square rounded-lg overflow-hidden cursor-pointer bg-base-200 border transition-colors"
            :class="[
              isEntrySelected(entry) ? 'border-primary ring-2 ring-primary/60' : 'border-base-100 hover:border-primary/40',
              entry.is_ignored && 'opacity-50',
              isDragOverFolder === entryPath(entry) && entry.is_dir && 'ring-2 ring-blue-400'
            ]"
            @click="handleEntryClick(entry, $event)"
            @contextmenu.prevent.stop="onEntryContextMenu($event, entry)"
            @dragstart="onDragStart($event, entry)"
            @dragend="onDragEnd"
            @dragover.stop.prevent="onDragOverEntry($event, entry)"
            @dragleave.prevent="onDragLeaveEntry"
            @drop.stop.prevent="onDropEntry($event, entry)"
            draggable="true"
            :data-entry-path="entryPath(entry)"
            :data-folder-path="entry.is_dir ? entryPath(entry) : null"
            :title="entry.name"
          >
            <!-- Icon fallback: shown while the thumbnail loads or when it cannot be rendered -->
            <div class="absolute inset-0 flex flex-col items-center justify-center gap-2 px-2">
              <i class="text-4xl" :class="getFileIcon(entry)"></i>
              <span class="text-[10px] uppercase tracking-wide opacity-50">
                {{ fileTypeLabel(entry) }}
              </span>
            </div>

            <!-- Image thumbnail -->
            <img
              v-if="getPreviewKind(entry) === 'image' && !hasPreviewError(entry)"
              :src="previewUrl(entry)"
              :alt="entry.name"
              loading="lazy"
              decoding="async"
              class="absolute inset-0 w-full h-full object-cover"
              @error="onPreviewError(entry)"
            />

            <!-- Video thumbnail (first frame) -->
            <video
              v-else-if="getPreviewKind(entry) === 'video' && !hasPreviewError(entry)"
              :src="videoThumbUrl(entry)"
              preload="metadata"
              muted
              playsinline
              class="absolute inset-0 w-full h-full object-cover"
              @error="onPreviewError(entry)"
            ></video>

            <!-- PDF / audio: no thumbnail, a type badge over the icon -->
            <div class="absolute inset-0 flex items-center justify-center" v-else-if="getPreviewKind(entry)">
              <span
                class="badge badge-sm gap-1"
                :class="getPreviewKind(entry) === 'pdf' ? 'badge-error' : 'badge-secondary'"
              >
                <i :class="getPreviewKind(entry) === 'pdf' ? 'fa-solid fa-file-pdf' : 'fa-solid fa-music'"></i>
                {{ getPreviewKind(entry).toUpperCase() }}
              </span>
            </div>

            <!-- Name + size overlay -->
            <div class="absolute inset-x-0 bottom-0 px-2 py-1 bg-black/60">
              <div class="text-[11px] font-mono truncate text-white">{{ entry.name }}</div>
              <div class="text-[10px] text-white/60" v-if="!entry.is_dir">{{ formatSize(entry.size) }}</div>
            </div>
          </div>

          <!-- Empty state -->
          <div class="col-span-full text-center opacity-50 py-8 text-sm" v-if="!visibleEntries.length">
            {{ isSearching ? 'No files found matching your search' : 'No files found' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Pagination controls (search results only) -->
    <div class="flex items-center justify-between px-2 py-2 border-t border-base-100" v-if="isSearching && totalFiles > pageSize">
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

    <!-- Context Menu -->
    <ContextMenu
      :isVisible="contextMenuVisible"
      :position="contextMenuPosition"
      :hasSelection="selectedEntries.length > 0"
      :isMultiSelect="selectedEntries.length > 1"
      :selectionCount="selectedEntries.length"
      @upload="handleContextUpload"
      @create="handleContextCreate"
      @rename="handleContextRename"
      @move="handleContextMove"
      @copy-path="handleContextCopyPath"
      @copy-relative-path="handleContextCopyRelativePath"
      @delete="handleContextDelete"
    />

    <!-- Hidden picker used by the "Upload files" context menu action -->
    <input
      ref="uploadInput"
      type="file"
      multiple
      class="hidden"
      @change="onUploadInputChange"
    />

    <!-- Create File/Folder Dialog -->
    <CreateFileDialog
      :isVisible="showCreateDialog"
      :isDir="createDialogIsDir"
      @create="onCreateDialogSubmit"
      @cancel="showCreateDialog = false"
    />

    <!-- Move files/folders Dialog -->
    <MoveDialog
      :isVisible="showMoveDialog"
      :sources="moveSources"
      :startPath="getAbsolutePath(currentPath)"
      @move="onMoveConfirm"
      @cancel="showMoveDialog = false"
    />
  </div>
</template>

<script>
import ContextMenu from './ContextMenu.vue'
import CreateFileDialog from './CreateFileDialog.vue'
import MoveDialog from './MoveDialog.vue'
import { onFileEvent, isDirectoryAffected } from '@/utils/fileEvents'

// Formats the browser can render a thumbnail / preview for.
// Anything else falls back to its file-type icon.
const IMAGE_PREVIEW_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'avif', 'ico', 'svg']
const VIDEO_PREVIEW_EXTENSIONS = ['mp4', 'webm', 'mov', 'm4v', 'ogv', 'mkv']
const AUDIO_PREVIEW_EXTENSIONS = ['mp3', 'wav', 'ogg', 'oga', 'flac', 'aac', 'm4a', 'opus']
const PDF_PREVIEW_EXTENSIONS = ['pdf']

// Toolbar view modes, in cycling order
const VIEW_MODES = ['list', 'grid', 'preview']

// Delay used to coalesce the backend file events: a single save emits several
// of them (write + reload) and a bulk operation emits one per file.
const FILE_EVENT_REFRESH_DELAY = 400

export default {
  name: 'FileExplorer',
  components: { ContextMenu, CreateFileDialog, MoveDialog },
  props: ['root-path'],
  data() {
    return {
      currentPath: '.',
      entries: [],
      filter: '',
      searchMode: 'filename',
      searchAllFiles: false,
      // File navigation presentation: 'list' | 'grid' | 'preview'
      viewMode: 'grid',
      loading: false,
      error: null,
      draggedEntry: null,
      selectedEntries: [],
      lastSelectedIndex: null,
      // Marquee ("rubber band") selection: drag state + rectangle geometry.
      // `selectionBox` holds CSS values (content coordinates, see
      // updateSelectionBox) and is null while not dragging.
      marquee: null,
      marqueeBaseSelection: [],
      selectionBox: null,
      // Thumbnails that failed to load, keyed by entry path (see onPreviewError)
      previewErrors: {},
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
      contextMenuVisible: false,
      contextMenuPosition: { x: 0, y: 0 },
      contextMenuEntry: null,
      showCreateDialog: false,
      createDialogIsDir: false,
      showMoveDialog: false,
      moveSources: [],
      // Backend file events (see `utils/fileEvents`): unsubscribe function and
      // the debounce timer of the automatic refreshes.
      unsubscribeFileEvents: null,
      fileEventRefreshTimer: null,
      extensionIconMap: {
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
        'ejs': 'fa-regular fa-file-code text-yellow-600',
        'hbs': 'fa-regular fa-file-code text-orange-700',
        'pug': 'fa-regular fa-file-code text-brown-600',
        'sql': 'fa-solid fa-database text-blue-600',
        'db': 'fa-solid fa-database text-slate-600',
        'sqlite': 'fa-solid fa-database text-blue-400',
        'md': 'fa-brands fa-markdown text-slate-600',
        'txt': 'fa-regular fa-file-lines text-slate-500',
        'pdf': 'fa-solid fa-file-pdf text-red-600',
        'doc': 'fa-solid fa-file-word text-blue-600',
        'docx': 'fa-solid fa-file-word text-blue-600',
        'xls': 'fa-solid fa-file-excel text-green-600',
        'xlsx': 'fa-solid fa-file-excel text-green-600',
        'ppt': 'fa-solid fa-file-powerpoint text-orange-600',
        'pptx': 'fa-solid fa-file-powerpoint text-orange-600',
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
        'zip': 'fa-regular fa-file-zipper text-slate-600',
        'rar': 'fa-regular fa-file-zipper text-slate-600',
        'tar': 'fa-regular fa-file-zipper text-slate-600',
        'gz': 'fa-regular fa-file-zipper text-slate-600',
        '7z': 'fa-regular fa-file-zipper text-slate-600',
        'bz2': 'fa-regular fa-file-zipper text-slate-600',
        'env': 'fa-solid fa-gear text-slate-500',
        'config': 'fa-solid fa-gear text-slate-500',
        'conf': 'fa-solid fa-gear text-slate-500',
        'ini': 'fa-solid fa-gear text-slate-500',
        'sh': 'fa-solid fa-terminal text-slate-700',
        'bash': 'fa-solid fa-terminal text-slate-700',
        'zsh': 'fa-solid fa-terminal text-slate-700',
        'fish': 'fa-solid fa-terminal text-slate-700',
        'bat': 'fa-solid fa-terminal text-slate-700',
        'git': 'fa-brands fa-git-alt text-orange-600',
        'gitignore': 'fa-brands fa-git-alt text-orange-600',
        'lock': 'fa-solid fa-lock text-amber-600',
        'key': 'fa-solid fa-key text-yellow-600'
      }
    }
  },
  computed: {
    basePath() {
      return this.normalizePath(this.rootPath || this.$project.abs_project_path)
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
    // Next value of the toolbar view toggle (the button shows where it leads)
    nextViewMode() {
      const index = VIEW_MODES.indexOf(this.viewMode)
      return VIEW_MODES[(index + 1) % VIEW_MODES.length]
    },
    viewToggleIcon() {
      return {
        list: 'fa-solid fa-list',
        grid: 'fa-solid fa-grip',
        preview: 'fa-solid fa-images'
      }[this.nextViewMode]
    },
    viewToggleTitle() {
      return {
        list: 'List view',
        grid: 'Grid view',
        preview: 'Preview mode'
      }[this.nextViewMode]
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
    document.addEventListener('click', this.closeContextMenu)
    // Keep the listing in sync with files changed anywhere else (a chat, the
    // terminal, another tab...). See `utils/fileEvents`.
    this.unsubscribeFileEvents = onFileEvent(this.onFileEvent)
  },
  beforeUnmount() {
    document.removeEventListener('click', this.closeContextMenu)
    // A drag can still be running when the explorer is unmounted
    this.endMarquee()
    this.unsubscribeFileEvents?.()
    this.unsubscribeFileEvents = null
    clearTimeout(this.fileEventRefreshTimer)
    this.fileEventRefreshTimer = null
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
    // Preview kind the browser can render for an entry: image | video | audio | pdf
    getPreviewKind(entry) {
      if (!entry || entry.is_dir) return null
      const ext = this.getFileExtension(entry.name || '')
      if (IMAGE_PREVIEW_EXTENSIONS.includes(ext)) return 'image'
      if (VIDEO_PREVIEW_EXTENSIONS.includes(ext)) return 'video'
      if (AUDIO_PREVIEW_EXTENSIONS.includes(ext)) return 'audio'
      if (PDF_PREVIEW_EXTENSIONS.includes(ext)) return 'pdf'
      return null
    },
    // Streaming URL of the raw file, safe for <img>/<video> sources
    previewUrl(entry) {
      if (!this.getPreviewKind(entry)) return ''
      return this.$api.files.getFilePreviewUrl(this.entryPath(entry))
    },
    // Ask the browser to render the first frame instead of a black poster
    videoThumbUrl(entry) {
      const url = this.previewUrl(entry)
      return url ? `${url}#t=0.1` : ''
    },
    onPreviewError(entry) {
      this.previewErrors = { ...this.previewErrors, [this.entryPath(entry)]: true }
    },
    hasPreviewError(entry) {
      return !!this.previewErrors[this.entryPath(entry)]
    },
    // Short label shown under the fallback icon of a preview tile
    fileTypeLabel(entry) {
      if (entry.is_dir) return ''
      const name = entry.name || ''
      if (!name.includes('.')) return 'file'
      return this.getFileExtension(name)
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
        this.previewErrors = {}
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
    // Cycle list -> grid -> preview -> list
    toggleViewMode() {
      this.viewMode = this.nextViewMode
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
    // Project scoped path: `project-name/relative/path` (used by chats and prompts)
    getProjectRelativePath(absolutePath) {
      const relative = this.getRelativePath(absolutePath)
      return relative === '.' ? this.projectName : `${this.projectName}/${relative}`
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
    /**
     * Entry click.
     *
     *  - Shift      → range selection from the anchor (never opens anything)
     *  - Ctrl / Cmd → toggles the entry in the selection (no new tab)
     *  - plain      → single selection + open (file) / enter (folder)
     */
    handleEntryClick(entry, event) {
      const isCtrlClick = event.ctrlKey || event.metaKey
      const isShiftClick = event.shiftKey
      const index = this.visibleEntries.indexOf(entry)

      if (isShiftClick) {
        if (this.lastSelectedIndex === null) {
          // No anchor yet: behave like a single selection
          this.clearSelection()
          this.addSelection(entry)
        } else {
          this.selectRange(this.lastSelectedIndex, index)
        }
        this.lastSelectedIndex = index
        return
      }

      if (isCtrlClick) {
        this.toggleSelection(entry)
        this.lastSelectedIndex = index
        return
      }

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

    // ── Marqueize ("rubber band") selection ───────────────────────────────
    // Pressing on the empty area and dragging selects every entry the
    // rectangle touches. Entries are `draggable`, so the gesture may only
    // start on blank space: drags from a tile/row keep moving files around.
    onSelectionMouseDown(event) {
      if (event.button !== 0) return
      if (event.target.closest('[data-entry-path]')) return
      if (event.target.closest('[data-no-marquee]')) return
      const container = this.$refs.listContainer
      if (!container) return

      // Avoid the native text selection while the rectangle is drawn
      event.preventDefault()

      const additive = event.ctrlKey || event.metaKey
      this.marquee = {
        additive,
        startX: event.clientX,
        startY: event.clientY
      }
      this.marqueeBaseSelection = additive ? [...this.selectedEntries] : []
      if (!additive) this.clearSelection()

      this.applyMarqueeSelection(event)
      window.addEventListener('mousemove', this.onSelectionMouseMove)
      window.addEventListener('mouseup', this.endMarquee)
    },
    onSelectionMouseMove(event) {
      if (!this.marquee) return
      this.applyMarqueeSelection(event)
    },
    endMarquee() {
      window.removeEventListener('mousemove', this.onSelectionMouseMove)
      window.removeEventListener('mouseup', this.endMarquee)
      const hadSelection = !!this.marquee && this.selectedEntries.length > 0
      this.marquee = null
      this.selectionBox = null
      this.marqueeBaseSelection = []
      if (!hadSelection) return
      // Keep shift+click anchored on the last entry the marquee selected
      const last = this.selectedEntries[this.selectedEntries.length - 1]
      this.lastSelectedIndex = this.visibleEntries.indexOf(last)
    },
    // Rectangle in viewport coordinates: used for hit-testing, so scrolling
    // mid-drag can never skew which entries are considered "touched".
    marqueeRect(event) {
      const { startX, startY } = this.marquee
      return {
        left: Math.min(startX, event.clientX),
        top: Math.min(startY, event.clientY),
        right: Math.max(startX, event.clientX),
        bottom: Math.max(startY, event.clientY)
      }
    },
    // The overlay is positioned in the container's CONTENT coordinates so it
    // scrolls together with the entries instead of floating above them.
    updateSelectionBox(rect) {
      const container = this.$refs.listContainer
      if (!container) return
      const bounds = container.getBoundingClientRect()
      const offsetX = bounds.left + container.clientLeft - container.scrollLeft
      const offsetY = bounds.top + container.clientTop - container.scrollTop
      this.selectionBox = {
        left: `${rect.left - offsetX}px`,
        top: `${rect.top - offsetY}px`,
        width: `${rect.right - rect.left}px`,
        height: `${rect.bottom - rect.top}px`
      }
    },
    applyMarqueeSelection(event) {
      const container = this.$refs.listContainer
      if (!container || !this.marquee) return

      const rect = this.marqueeRect(event)
      this.updateSelectionBox(rect)

      const selected = [...this.marqueeBaseSelection]
      container.querySelectorAll('[data-entry-path]').forEach(element => {
        const bounds = element.getBoundingClientRect()
        const intersects = bounds.left < rect.right &&
          bounds.right > rect.left &&
          bounds.top < rect.bottom &&
          bounds.bottom > rect.top
        if (!intersects) return

        const path = element.dataset.entryPath
        if (selected.some(entry => this.entryPath(entry) === path)) return

        const entry = this.visibleEntries.find(item => this.entryPath(item) === path)
        if (entry) selected.push(entry)
      })

      this.selectedEntries = selected
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
      this.previewErrors = {}
      if (this.isSearching) {
        this.performSearch(this.filter)
      } else {
        this.loadDir(this.getAbsolutePath(this.currentPath))
      }
    },

    // ── Backend file events ────────────────────────────────────────────────
    /**
     * A file changed somewhere else: a chat wrote it, the terminal deleted it,
     * another tab renamed it...
     *
     * Only the folder on screen matters: the event is ignored when it belongs to
     * another project, or when the changed file lives deeper in the tree.
     */
    onFileEvent(fileEvent) {
      if (!this.belongsToThisProject(fileEvent)) return
      if (!isDirectoryAffected(this.getAbsolutePath(this.currentPath), fileEvent)) return
      this.scheduleFileEventRefresh()
    },
    /**
     * The event must belong to the project open in this explorer. Projects are
     * matched by id, then by `codx_path`; when the event carries neither, the
     * path itself decides (it has to be inside the project root).
     */
    belongsToThisProject({ projectId, codxPath, filePath }) {
      const project = this.$storex.projects.activeProject
      if (projectId && project?.project_id) return projectId === project.project_id
      if (codxPath && project?.codx_path) return codxPath === project.codx_path
      return !!filePath && filePath.startsWith(`${this.basePath}/`)
    },
    /**
     * Coalesce bursts of events into a single reload: a save emits more than one
     * event and a bulk operation emits one per file.
     *
     * Skipped while a request is in flight or a marquee selection is running —
     * reloading the list then would fight with the user.
     */
    scheduleFileEventRefresh() {
      clearTimeout(this.fileEventRefreshTimer)
      this.fileEventRefreshTimer = setTimeout(() => {
        this.fileEventRefreshTimer = null
        if (this.loading || this.marquee) return
        this.refresh()
      }, FILE_EVENT_REFRESH_DELAY)
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
    onContextMenu(event) {
      // Right clicking the empty area targets the current folder
      this.clearSelection()
      this.contextMenuPosition = {
        x: event.clientX,
        y: event.clientY
      }
      this.contextMenuEntry = null
      this.contextMenuVisible = true
    },
    onEntryContextMenu(event, entry) {
      if (!this.isEntrySelected(entry)) {
        this.clearSelection()
        this.addSelection(entry)
      }
      this.contextMenuPosition = {
        x: event.clientX,
        y: event.clientY
      }
      this.contextMenuEntry = entry
      this.contextMenuVisible = true
    },
    closeContextMenu() {
      this.contextMenuVisible = false
    },
    handleContextUpload() {
      this.closeContextMenu()
      this.triggerUpload()
    },
    // Opens the native file picker; uploads always go to the folder currently open
    triggerUpload() {
      this.$refs.uploadInput?.click()
    },
    async onUploadInputChange(event) {
      const input = event.target
      try {
        await this.handleFilesUpload(this.getAbsolutePath(this.currentPath), input.files)
      } finally {
        input.value = ''
      }
    },
    handleContextCreate({ isDir }) {
      this.closeContextMenu()
      this.createDialogIsDir = isDir
      this.showCreateDialog = true
    },
    async onCreateDialogSubmit({ name }) {
      this.showCreateDialog = false
      const parentPath = this.getAbsolutePath(this.currentPath)
      const newPath = this.normalizePath(`${parentPath}/${name}`)
      
      try {
        await this.$api.files.create(newPath, this.createDialogIsDir)
        
        if (!this.createDialogIsDir) {
          this.$emit('createFile', {
            path: newPath,
            name: name,
            isNew: true
          })
        } else {
          await this.refresh()
        }
      } catch (error) {
        console.error('Error creating file/folder', error)
        this.error = `Failed to create ${this.createDialogIsDir ? 'folder' : 'file'}: ${error.message}`
      }
    },
    async handleContextRename() {
      this.closeContextMenu()
      if (this.selectedEntries.length !== 1) return
      
      const entry = this.selectedEntries[0]
      const oldName = entry.name
      const newName = prompt('Enter new name:', oldName)
      
      if (!newName || newName === oldName) return
      
      const oldPath = this.entryPath(entry)
      const parentPath = oldPath.substring(0, oldPath.lastIndexOf('/'))
      const newPath = this.normalizePath(`${parentPath}/${newName}`)
      
      try {
        await this.$api.files.rename(oldPath, newPath)
        await this.refresh()
      } catch (error) {
        console.error('Error renaming file', error)
        this.error = `Failed to rename file: ${error.message}`
      }
    },
    // Opens the folder picker for the current selection (one or many entries)
    handleContextMove() {
      this.closeContextMenu()
      if (!this.selectedEntries.length) return
      this.moveSources = this.selectedEntries.map(entry => this.entryPath(entry))
      this.showMoveDialog = true
    },
    // Copy the absolute path(s) of the selection to the clipboard
    handleContextCopyPath() {
      this.copySelectedPaths(false)
    },
    // Copy the project relative path(s): `project-name/relative/path`
    handleContextCopyRelativePath() {
      this.copySelectedPaths(true)
    },
    /**
     * Copy one path per line to the clipboard.
     *
     * Uses the current selection, or the folder being viewed when nothing is
     * selected (right click on the empty area).
     */
    copySelectedPaths(relative) {
      this.closeContextMenu()
      const paths = this.selectedEntries.length
        ? this.selectedEntries.map(entry => this.entryPath(entry))
        : [this.getAbsolutePath(this.currentPath)]
      const text = paths
        .map(path => relative ? this.getProjectRelativePath(path) : path)
        .join('\n')

      this.$ui.copyTextToClipboard(text)
      this.$ui.addNotification({
        text: `Copied ${relative ? 'relative' : 'absolute'} path${paths.length > 1 ? 's' : ''}`
      })
    },
    async onMoveConfirm(targetPath) {
      this.showMoveDialog = false
      const sources = this.moveSources
      this.moveSources = []
      await this.moveEntries(sources, targetPath)
    },
    /**
     * Move the given paths into `targetDir`.
     *
     * No-op moves (already inside the folder), moves into itself and moves that
     * would clash with an existing name are filtered out before calling the API.
     */
    async moveEntries(sources, targetDir) {
      const target = this.normalizePath(targetDir) || '/'
      const paths = [...new Set((sources || []).filter(Boolean))].filter(source => {
        const parent = source.substring(0, source.lastIndexOf('/')) || '/'
        if (parent === target || source === target) return false
        return !target.startsWith(`${source}/`)
      })

      if (!paths.length) return

      this.error = null
      try {
        const listing = await this.$api.files.list(target)
        const existing = new Set((listing.files || []).map(file => file.name))
        const clashes = paths
          .map(source => source.split('/').filter(Boolean).pop())
          .filter(name => existing.has(name))

        if (clashes.length) {
          this.error = `Target folder already contains: ${clashes.join(', ')}`
          return
        }

        await this.$api.files.move(paths, target)
        this.$ui.addNotification({
          text: `Moved ${paths.length} item${paths.length > 1 ? 's' : ''} to ${this.getRelativePath(target) === '.' ? '/' : '/' + this.getRelativePath(target)}`
        })
        this.clearSelection()
        await this.refresh()
      } catch (error) {
        console.error('Error moving files', error)
        this.error = `Failed to move items: ${error.message}`
      }
    },
    // Paths carried by the current internal drag (multi-select aware)
    draggedSources() {
      if (!this.draggedEntry) return []
      const entries = this.isEntrySelected(this.draggedEntry) && this.selectedEntries.length > 1
        ? this.selectedEntries
        : [this.draggedEntry]
      return entries.map(entry => this.entryPath(entry))
    },
    async moveDraggedTo(targetDir) {
      const sources = this.draggedSources()
      this.draggedEntry = null
      this.isDragOverBlank = false
      this.isDragOverFolder = null
      await this.moveEntries(sources, targetDir)
    },
    async handleContextDelete() {
      this.closeContextMenu()
      if (this.selectedEntries.length === 0) return
      
      const count = this.selectedEntries.length
      const message = count === 1
        ? `Delete "${this.selectedEntries[0].name}"?`
        : `Delete ${count} items?`
      
      if (!confirm(message)) return
      
      try {
        for (const entry of this.selectedEntries) {
          await this.$api.files.delete(this.entryPath(entry))
        }
        await this.refresh()
      } catch (error) {
        console.error('Error deleting files', error)
        this.error = `Failed to delete items: ${error.message}`
      }
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
      event.dataTransfer.dropEffect = this.draggedEntry ? 'move' : 'copy'
      this.isDragOverBlank = true
    },
    onDragLeave(event) {
      if (event.target === event.currentTarget) {
        this.isDragOverBlank = false
      }
    },
    onDragOverEntry(event, entry) {
      if (!entry.is_dir) return
      // Internal drag: moving entries into a folder of the same explorer
      event.dataTransfer.dropEffect = this.draggedEntry ? 'move' : 'copy'
      this.isDragOverFolder = this.entryPath(entry)
    },
    onDragLeaveEntry() {
      this.isDragOverFolder = null
    },
    async onDrop(event) {
      this.isDragOverBlank = false

      // Internal drag dropped on the empty area: move into the folder being viewed
      if (this.draggedEntry) {
        await this.moveDraggedTo(this.getAbsolutePath(this.currentPath))
        return
      }

      const files = event.dataTransfer.files
      if (files.length === 0) return
      
      const targetPath = this.getAbsolutePath(this.currentPath)
      await this.handleFilesUpload(targetPath, files)
    },
    async onDropEntry(event, entry) {
      this.isDragOverFolder = null
      if (!entry.is_dir) return

      // Internal drag dropped on a folder: move the dragged entries there
      if (this.draggedEntry) {
        await this.moveDraggedTo(this.entryPath(entry))
        return
      }

      const files = event.dataTransfer.files
      if (files.length === 0) return
      
      const targetPath = this.entryPath(entry)
      await this.handleFilesUpload(targetPath, files)
    },
    async handleFilesUpload(targetPath, fileList) {
      if (!fileList || fileList.length === 0) return
      
      this.isUploading = true
      this.uploadProgress = 0
      this.uploadProgressBytes = 0
      this.uploadTotalBytes = 0
      this.error = null
      
      try {
        const files = Array.from(fileList)
        
        this.uploadTotalBytes = files.reduce((sum, f) => sum + f.size, 0)
        this.uploadingFileName = files.length === 1 ? files[0].name : `${files.length} files`
        
        await Promise.all(
          files.map(file => this.$api.files.upload(file, targetPath)))
        
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