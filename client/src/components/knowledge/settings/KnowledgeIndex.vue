<script setup>
import KnowledgeIndexStats from './KnowledgeIndexStats.vue'
import KnowledgeFileList from './KnowledgeFileList.vue'
import KnowledgeIgnorePatterns from './KnowledgeIgnorePatterns.vue'
</script>

<template>
  <div class="flex flex-col gap-2">
    <!-- Header card with stats -->
    <div class="card">
      <div class="flex flex-col gap-2">
        <div class="text-xl">Settings</div>
        <div class="text-error text-xs" v-if="!settings?.use_knowledge">Knowledge search is disabled!</div>
        <KnowledgeIndexStats
          :indexStatus="indexStatus"
          :activeTab="activeTab"
          :ignoredCount="ignoredFolders?.length"
          :project="project"
          @set-tab="setTab"
          @set-setting="$emit('set-setting', $event)"
        />
      </div>
    </div>

    <!-- Index management section -->
    <div class="index flex flex-col gap-2">
      <div class="flex justify-between items-center">
        <div class="text-xl font-bold">Knowledge index settings</div>
        <button class="btn btn-sm flex gap-2" @click="$emit('reload-status')">
          <i class="fa-solid fa-rotate-right"></i> Update
        </button>
      </div>

      <div class="flex gap-2 items-center">
        <div class="text-secondary"><i class="fa-solid fa-clock"></i></div>
        <div class="stat-title">Last refresh</div>
        <div class="stat-value text-wrap text-sm">{{ lastRefresh }}</div>
      </div>

      <div class="p-4 flex flex-col gap-2">
        <KnowledgeFileList
          ref="fileList"
          :files="showFiles"
          :projectPath="settings?.abs_project_path"
          :activeTab="activeTab"
          @index-files="$emit('index-files', $event)"
          @ignore-files="onIgnoreFiles"
          @unignore-files="$emit('unignore-files', $event)"
          @drop-files="$emit('drop-files', $event)"
        />
      </div>

      <KnowledgeIgnorePatterns
        :ignoredFolders="ignoredFolders"
        @add="$emit('add-ignore', $event)"
        @remove="$emit('remove-ignore', $event)"
      />

      <!-- Delete index -->
      <div class="pb-2 flex gap-2 mt-4 justify-end">
        <button class="btn btn-sm btn-error flex gap-2" @click="$emit('delete-index')">
          Delete Index ({{ indexStatus?.db_info?.embeddings?.row_count }})
          <div v-if="confirmDelete">
            (Really?
            <span class="hover:underline">YES</span> /
            <span class="hover:underline" @click.stop="$emit('cancel-delete')">NO</span>)
          </div>
        </button>
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
      activeTab: 0
    }
  },
  computed: {
    lastRefresh() {
      if (this.indexStatus?.last_update) {
        const ts = parseInt(this.indexStatus.last_update, 10) * 1000
        return moment(new Date(ts)).fromNow()
      }
      return null
    },
    ignoredFolders() {
      const files = this.settings?.knowledge_file_ignore?.trim()
      return files?.split(',').filter(e => e.trim().length)
    },
    showFilesSelected() {
      switch (this.activeTab) {
        case 0: return this.indexStatus?.pending_files
        case 1: return this.indexStatus?.files
        default: return this.ignoredFolders
      }
    },
    showFiles() {
      return this.showFilesSelected || []
    }
  },
  methods: {
    setTab(ix) {
      this.activeTab = ix
      this.$refs.fileList?.clearSelection()
    },
    onIgnoreFiles({ paths, asFolder }) {
      this.$emit('ignore-files', { paths, asFolder })
    }
  }
}
</script>