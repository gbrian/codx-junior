<script setup>
import KnowledgeFileList from './KnowledgeFileList.vue'
import KnowledgeIgnorePatterns from './KnowledgeIgnorePatterns.vue'
</script>

<template>
  <div class="flex flex-col gap-4 h-full">

    <!-- Status Banner -->
    <div
      class="flex items-center gap-3 rounded-xl border-l-4 py-3 px-4"
      :class="settings?.use_knowledge
        ? 'border-success bg-success/10 text-success'
        : 'border-error bg-error/10 text-error'"
    >
      <i
        :class="settings?.use_knowledge ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"
        class="text-xl flex-shrink-0"
      ></i>
      <div class="flex flex-col min-w-0 flex-1">
        <span class="font-semibold text-sm">
          Knowledge Search {{ settings?.use_knowledge ? 'Active' : 'Disabled' }}
        </span>
        <span class="text-xs opacity-70" v-if="!settings?.use_knowledge">
          Enable in project settings to allow AI-powered search
        </span>
        <span class="text-xs opacity-70" v-else>
          Last synced {{ lastRefresh || 'never' }}
        </span>
      </div>

      <!-- Indexing progress indicator -->
      <div v-if="isIndexing" class="flex items-center gap-2 text-warning flex-shrink-0">
        <span class="loading loading-spinner loading-xs"></span>
        <span class="text-xs font-medium">Indexing {{ indexingFiles.length }} file{{ indexingFiles.length > 1 ? 's' : '' }}…</span>
      </div>

      <button
        class="btn btn-xs ml-auto gap-1 flex-shrink-0"
        :class="settings?.use_knowledge ? 'btn-success' : 'btn-error'"
        :disabled="isIndexing"
        @click="$emit('reload-status')"
      >
        <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': isIndexing }"></i> Refresh
      </button>
    </div>

    <!-- Indexing progress bar (full width, shown during indexing) -->
    <div v-if="isIndexing" class="w-full">
      <div class="flex items-center justify-between text-xs mb-1">
        <span class="text-warning font-medium flex items-center gap-1">
          <i class="fa-solid fa-bolt"></i> Indexing in progress
        </span>
        <span class="text-base-content/50">{{ indexingFiles.length }} file{{ indexingFiles.length > 1 ? 's' : '' }} queued</span>
      </div>
      <progress class="progress progress-warning w-full h-1.5"></progress>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-3 gap-3">

      <!-- Pending Files Card -->
      <button
        class="card bg-base-200 hover:bg-base-300 transition-all cursor-pointer border-2 p-4 text-left"
        :class="activeTab === 0 ? 'border-warning shadow-md' : 'border-transparent'"
        @click="setTab(0)"
      >
        <div class="flex items-start justify-between">
          <div>
            <div class="text-xs text-base-content/60 uppercase tracking-wider mb-1">Pending</div>
            <div
              class="text-3xl font-bold"
              :class="pendingCount > 0 ? 'text-warning' : 'text-base-content'"
            >{{ pendingCount }}</div>
            <div class="text-xs mt-1 opacity-60">files to index</div>
          </div>
          <div
            class="w-10 h-10 rounded-full flex items-center justify-center"
            :class="pendingCount > 0 ? 'bg-warning/20 text-warning' : 'bg-base-300 text-base-content/40'"
          >
            <i class="fa-solid fa-hourglass-half"></i>
          </div>
        </div>
        <div class="mt-3 h-1 rounded-full bg-base-300 overflow-hidden">
          <div
            class="h-full bg-warning rounded-full transition-all"
            :style="{ width: pendingPercent + '%' }"
          ></div>
        </div>
      </button>

      <!-- Indexed Files Card -->
      <button
        class="card bg-base-200 hover:bg-base-300 transition-all cursor-pointer border-2 p-4 text-left"
        :class="activeTab === 1 ? 'border-success shadow-md' : 'border-transparent'"
        @click="setTab(1)"
      >
        <div class="flex items-start justify-between">
          <div>
            <div class="text-xs text-base-content/60 uppercase tracking-wider mb-1">Indexed</div>
            <div class="text-3xl font-bold text-success">{{ indexedCount }}</div>
            <div class="text-xs mt-1 opacity-60">files in knowledge base</div>
          </div>
          <div class="w-10 h-10 rounded-full bg-success/20 text-success flex items-center justify-center">
            <i class="fa-solid fa-database"></i>
          </div>
        </div>
        <div class="mt-3 h-1 rounded-full bg-base-300 overflow-hidden">
          <div
            class="h-full bg-success rounded-full transition-all"
            :style="{ width: indexedPercent + '%' }"
          ></div>
        </div>
      </button>

      <!-- Ignored Patterns Card -->
      <button
        class="card bg-base-200 hover:bg-base-300 transition-all cursor-pointer border-2 p-4 text-left"
        :class="activeTab === 2 ? 'border-error shadow-md' : 'border-transparent'"
        @click="setTab(2)"
      >
        <div class="flex items-start justify-between">
          <div>
            <div class="text-xs text-base-content/60 uppercase tracking-wider mb-1">Ignored</div>
            <div class="text-3xl font-bold text-error">{{ ignoredCount }}</div>
            <div class="text-xs mt-1 opacity-60">patterns excluded</div>
          </div>
          <div class="w-10 h-10 rounded-full bg-error/20 text-error flex items-center justify-center">
            <i class="fa-solid fa-ban"></i>
          </div>
        </div>
        <div class="mt-3 h-1 rounded-full bg-base-300 overflow-hidden">
          <div class="h-full bg-error/60 rounded-full w-full"></div>
        </div>
      </button>
    </div>

    <!-- Active Tab Content Panel -->
    <div class="card bg-base-200 flex-1 overflow-hidden flex flex-col">

      <!-- Tab Header Row -->
      <div class="flex items-center justify-between px-4 pt-4 pb-3 border-b border-base-300">
        <div class="flex items-center gap-2 font-semibold">
          <i :class="tabIcon" class="text-warning"></i>
          <span>{{ tabLabel }}</span>
          <span class="badge badge-sm badge-warning">{{ showFiles.length }}</span>
          <!-- Spinning indicator on Pending tab while indexing -->
          <span v-if="activeTab === 0 && isIndexing" class="loading loading-spinner loading-xs text-warning"></span>
        </div>
        <div class="flex gap-2" v-if="activeTab < 2">
          <slot name="file-actions"></slot>
        </div>
      </div>

      <!-- File List or Ignore Patterns -->
      <div class="flex-1 overflow-auto p-4">
        <KnowledgeFileList
          v-if="activeTab < 2"
          ref="fileList"
          :files="showFiles"
          :projectPath="settings?.abs_project_path"
          :activeTab="activeTab"
          :indexingFiles="indexingFiles"
          @index-files="onIndexFiles"
          @ignore-files="onIgnoreFiles"
          @unignore-files="$emit('unignore-files', $event)"
          @drop-files="$emit('drop-files', $event)"
        />
        <KnowledgeIgnorePatterns
          v-else
          :ignoredFolders="ignoredFolders"
          @add="$emit('add-ignore', $event)"
          @remove="$emit('remove-ignore', $event)"
        />
      </div>
    </div>

    <!-- Danger Zone -->
    <div class="collapse collapse-arrow bg-error/5 border border-error/20 rounded-xl">
      <input type="checkbox" />
      <div class="collapse-title text-sm font-medium text-error/80 flex items-center gap-2">
        <i class="fa-solid fa-triangle-exclamation"></i>
        Danger Zone
      </div>
      <div class="collapse-content">
        <div class="flex items-center justify-between pt-2">
          <div>
            <div class="text-sm font-medium">Delete Index</div>
            <div class="text-xs opacity-60">
              Permanently remove all {{ indexStatus?.db_info?.embeddings?.row_count }} indexed embeddings
            </div>
          </div>
          <div v-if="!confirmDelete">
            <button class="btn btn-sm btn-error gap-2" @click="$emit('delete-index')">
              <i class="fa-solid fa-trash"></i> Delete
            </button>
          </div>
          <div v-else class="flex gap-2 items-center">
            <span class="text-sm text-error font-semibold">Are you sure?</span>
            <button class="btn btn-sm btn-error" @click="$emit('delete-index')">Yes, Delete</button>
            <button class="btn btn-sm btn-ghost" @click="$emit('cancel-delete')">Cancel</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
import moment from 'moment'

export default {
  emits: [
    'reload-status', 'set-setting', 'set-tab',
    'index-files', 'ignore-files', 'unignore-files',
    'drop-files', 'add-ignore', 'remove-ignore',
    'delete-index', 'cancel-delete'
  ],
  props: {
    settings: Object,
    indexStatus: Object,
    confirmDelete: Boolean,
    project: Object
  },
  data() {
    return {
      activeTab: 0,
      // Track files currently being sent for indexing
      indexingFiles: []
    }
  },
  computed: {
    lastRefresh() {
      if (this.indexStatus?.last_update) {
        return moment(new Date(parseInt(this.indexStatus.last_update, 10) * 1000)).fromNow()
      }
      return null
    },
    ignoredFolders() {
      return this.settings?.knowledge_file_ignore
        ?.trim()?.split(',').filter(e => e.trim().length) || []
    },
    pendingCount() { return this.indexStatus?.pending_files?.length || 0 },
    indexedCount() { return this.indexStatus?.files?.length || 0 },
    ignoredCount() { return this.ignoredFolders.length },
    totalCount() { return this.pendingCount + this.indexedCount },
    pendingPercent() {
      return this.totalCount ? Math.round((this.pendingCount / this.totalCount) * 100) : 0
    },
    indexedPercent() {
      return this.totalCount ? Math.round((this.indexedCount / this.totalCount) * 100) : 100
    },
    showFiles() {
      switch (this.activeTab) {
        case 0: return this.indexStatus?.pending_files || []
        case 1: return this.indexStatus?.files || []
        default: return this.ignoredFolders
      }
    },
    tabLabel() {
      return ['Pending Files', 'Indexed Files', 'Ignored Patterns'][this.activeTab]
    },
    tabIcon() {
      return [
        'fa-solid fa-hourglass-half',
        'fa-solid fa-database',
        'fa-solid fa-ban'
      ][this.activeTab]
    },
    isIndexing() {
      return this.indexingFiles.length > 0
    }
  },
  watch: {
    // Clear indexing state when pending files list updates (indexing completed)
    'indexStatus.pending_files'(newFiles) {
      if (!newFiles?.length) {
        this.indexingFiles = []
      }
    }
  },
  methods: {
    setTab(ix) {
      this.activeTab = ix
      this.$refs.fileList?.clearSelection()
    },
    onIgnoreFiles({ paths, asFolder }) {
      this.$emit('ignore-files', { paths, asFolder })
    },
    // Track files being indexed before emitting to parent
    onIndexFiles(filePaths) {
      this.indexingFiles = [...filePaths]
      this.$emit('index-files', filePaths)
    }
  }
}
</script>