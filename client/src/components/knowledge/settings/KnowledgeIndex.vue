<script setup>
import KnowledgeFileList from './KnowledgeFileList.vue'
import KnowledgeIgnorePatterns from './KnowledgeIgnorePatterns.vue'
import moment from 'moment'
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
        @click="reloadStatus"
      >
        <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': isIndexing }"></i> Refresh
      </button>
    </div>

    <!-- Indexing progress bar -->
    <div v-if="isIndexing" class="w-full">
      <div class="flex items-center justify-between text-xs mb-1">
        <span class="text-warning font-medium flex items-center gap-1">
          <i class="fa-solid fa-bolt"></i> {{ indexProgress.stage || 'Indexing in progress' }}
        </span>
        <span class="text-base-content/50">{{ indexProgress.progress }}%</span>
      </div>
      <progress class="progress progress-warning w-full h-1.5" :value="indexProgress.progress" max="100"></progress>
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
          @index-files="handleIndexFiles"
          @ignore-files="handleIgnoreFiles"
          @unignore-files="handleUnignoreFiles"
          @drop-files="handleDropFiles"
        />
        <KnowledgeIgnorePatterns
          v-else
          :ignoredFolders="ignoredFolders"
          @add="handleAddIgnore"
          @remove="handleRemoveIgnore"
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
            <button class="btn btn-sm btn-error gap-2" @click="handleDeleteIndex">
              <i class="fa-solid fa-trash"></i> Delete
            </button>
          </div>
          <div v-else class="flex gap-2 items-center">
            <span class="text-sm text-error font-semibold">Are you sure?</span>
            <button class="btn btn-sm btn-error" @click="confirmAndDeleteIndex">Yes, Delete</button>
            <button class="btn btn-sm btn-ghost" @click="cancelDelete">Cancel</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script>
export default {
  emits: ['reload-status', 'set-setting'],
  props: {
    settings: Object,
    indexStatus: Object,
    project: Object
  },
  data() {
    return {
      activeTab: 0,
      confirmDelete: false
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
    pendingCount() {
      return this.indexStatus?.pending_files?.length || 0
    },
    indexedCount() {
      return this.indexStatus?.files?.length || 0
    },
    ignoredCount() {
      return this.ignoredFolders.length
    },
    totalCount() {
      return this.pendingCount + this.indexedCount
    },
    pendingPercent() {
      return this.totalCount ? Math.round((this.pendingCount / this.totalCount) * 100) : 0
    },
    indexedPercent() {
      return this.totalCount ? Math.round((this.indexedCount / this.totalCount) * 100) : 100
    },
    showFiles() {
      switch (this.activeTab) {
        case 0:
          return this.indexStatus?.pending_files || []
        case 1:
          return this.indexStatus?.files || []
        default:
          return this.ignoredFolders
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
      return this.$storex.projects.isIndexing
    },
    indexingFiles() {
      return this.$storex.projects.indexingFiles
    },
    indexingError() {
      return this.$storex.projects.indexingError
    },
    indexProgress() {
      return this.$storex.projects.indexProgress
    }
  },
  watch: {
    'indexStatus.pending_files'(newFiles) {
      if (!newFiles?.length && !this.isIndexing) {
        this.$storex.projects.clearIndexing()
      }
    },
    indexingError(error) {
      if (error) {
        this.$session.onError(`Indexing failed: ${error}`)
      }
    }
  },
  mounted() {
    this.$storex.projects.subscribeToIndexProgress()
  },
  beforeUnmount() {
    this.$storex.projects.unsubscribeFromIndexProgress()
  },
  methods: {
    setTab(ix) {
      this.activeTab = ix
      this.$refs.fileList?.clearSelection()
    },

    // Handle file indexing
    async handleIndexFiles(filePaths) {
      try {
        await this.$storex.projects.startIndexing(filePaths)
        this.$session.onInfo(`Indexing ${filePaths.length} file(s) in background...`)
      } catch (error) {
        this.$session.onError(`Failed to start indexing: ${error.message}`)
      }
    },

    // Handle file ignore
    async handleIgnoreFiles({ paths, asFolder }) {
      const projectPath = this.settings?.abs_project_path
      const relativePaths = paths.map(f => f.replace(projectPath, ''))
      const entries = asFolder
        ? relativePaths.map(f => f.split('/').reverse()[1])
        : relativePaths
      await this.addEntriesToIgnore(entries)
    },

    // Handle file unignore
    async handleUnignoreFiles(paths) {
      await this.removeEntriesFromIgnore(paths)
    },

    // Handle file drop
    async handleDropFiles(filePaths) {
      try {
        const api = this.project?.$api
        if (!api) throw new Error('API not initialized')

        await api.knowledge.delete(filePaths)
        await this.reloadStatus()
      } catch (error) {
        this.$session.onError(`Failed to delete files: ${error.message}`)
      }
    },

    // Handle ignore pattern add
    async handleAddIgnore(entries) {
      await this.addEntriesToIgnore(entries)
    },

    // Handle ignore pattern remove
    async handleRemoveIgnore(entries) {
      await this.removeEntriesFromIgnore(entries)
    },

    // Add entries to ignore list
    async addEntriesToIgnore(entries) {
      try {
        const currIgnore = this.settings?.knowledge_file_ignore?.split(',') || []
        const newIgnore = [...new Set([...currIgnore, ...entries])]
        this.settings.knowledge_file_ignore = newIgnore.join(',')

        const api = this.project?.$api
        if (!api) throw new Error('API not initialized')

        await api.settings.save(this.settings)
        await this.reloadStatus()
      } catch (error) {
        this.$session.onError(`Failed to add ignore patterns: ${error.message}`)
      }
    },

    // Remove entries from ignore list
    async removeEntriesFromIgnore(entries) {
      try {
        const currIgnore = this.settings?.knowledge_file_ignore?.split(',') || []
        const newIgnore = currIgnore.filter(e => !entries.includes(e))
        this.settings.knowledge_file_ignore = newIgnore.join(',')

        const api = this.project?.$api
        if (!api) throw new Error('API not initialized')

        await api.settings.save(this.settings)
        await this.reloadStatus()
      } catch (error) {
        this.$session.onError(`Failed to remove ignore patterns: ${error.message}`)
      }
    },

    // Reload knowledge status
    async reloadStatus() {
      this.$emit('reload-status')
    },

    // Delete index handler
    handleDeleteIndex() {
      this.confirmDelete = true
    },

    // Confirm and delete index
    async confirmAndDeleteIndex() {
      try {
        const api = this.project?.$api
        if (!api) throw new Error('API not initialized')

        await api.knowledge.deleteIndex('')
        await this.reloadStatus()
        this.confirmDelete = false
      } catch (error) {
        this.$session.onError(`Failed to delete index: ${error.message}`)
      }
    },

    // Cancel delete operation
    cancelDelete() {
      this.confirmDelete = false
    }
  }
}
</script>