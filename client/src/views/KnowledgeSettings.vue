<script setup>
import WikiSettingsVue from '@/components/wiki/WikiSettings.vue'
import DataExplorerVue from '../components/data/DataExplorer.vue'
import KnowledgeSearch from '../components/knowledge/settings/KnowledgeSearch.vue'
import KnowledgeIndex from '../components/knowledge/settings/KnowledgeIndex.vue'
import ProjectDetailt from '../components/ProjectDetailt.vue'
</script>

<template>
  <div class="flex flex-col gap-2 h-full px-4" v-if="settings">
    <!-- Header with tabs and project selector -->
    <div class="font-medium flex flex-col gap-2">
      <div class="text-3xl flex justify-between items-center">
        <div class="flex items-center gap-4">
          <!-- Project Selector -->
          <ProjectDetailt 
            v-model="currentProject"
            :options="{ showIcon: true }"
            @select="onProjectSelected"
          />
          Knowledge
        </div>
        <div role="tablist" class="tabs tabs-box flex gap-2">
          <a
            role="tab"
            class="tab flex gap-2"
            :class="{ 'tab-active text-warning': selectedTab === 'Search' }"
            @click="selectedTab = 'Search'"
          >
            <i class="fa-solid fa-magnifying-glass"></i> Search
          </a>
          <a
            role="tab"
            class="tab flex gap-2"
            :class="{ 'tab-active text-warning': selectedTab === 'Index' }"
            @click="selectedTab = 'Index'"
          >
            <i class="fa-solid fa-file-import"></i> Index
          </a>
          <a
            role="tab"
            class="tab flex gap-2"
            :class="{ 'tab-active text-warning': selectedTab === 'Wiki' }"
            @click="selectedTab = 'Wiki'"
          >
            <i class="fa-solid fa-file"></i> Wiki
          </a>
          <a
            role="tab"
            class="tab flex gap-2"
            :class="{ 'tab-active text-warning': selectedTab === 'Data' }"
            @click="selectedTab = 'Data'"
          >
            <i class="fa-solid fa-database"></i> Data
          </a>
        </div>
      </div>
    </div>

    <!-- Loading state when no knowledge exists -->
    <div class="flex items-center justify-center py-8" v-if="isLoading">
      <div class="flex flex-col items-center gap-4">
        <span class="loading loading-spinner loading-lg text-warning"></span>
        <p class="text-sm text-base-content/70">Loading knowledge base...</p>
      </div>
    </div>

    <!-- Linked sub-projects badge list -->
    <div class="text-xs flex gap-2" v-if="subProjects?.length && !isLoading">
      Linked projects:
      <span class="badge badge-xs badge-warning" v-for="sp in subProjects" :key="sp">
        {{ sp }}
      </span>
    </div>

    <!-- Tab: Wiki -->
    <WikiSettingsVue 
        :project="currentProject"
        class="mt-2" 
        v-if="selectedTab === 'Wiki' && !isLoading" />

    <!-- Tab: Search -->
    <KnowledgeSearch
      v-if="selectedTab === 'Search' && !isLoading"
      :project="currentProject"
      :settings="settings"
      @toggle-watch="toggleWatch"
    />

    <!-- Tab: Index -->
    <KnowledgeIndex
      v-if="selectedTab === 'Index' && !isLoading"
      :settings="settings"
      :indexStatus="indexStatus"
      :confirmDelete="resetKnowledge"
      :project="currentProject"
      @reload-status="reloadStatus"
      @set-setting="setSettings"
    />

    <!-- Tab: Data -->
    <div v-if="selectedTab === 'Data' && !isLoading">
      <DataExplorerVue 
        :project="currentProject"
        :status="indexStatus"
        @drop="dropSelectedFiles" />
    </div>
  </div>
</template>

<script>

export default {
  props: ['params'],
  data() {
    return {
      selectedTab: 'Search',
      indexStatus: null,
      settings: null,
      resetKnowledge: false,
      currentProject: null,
      isLoading: true
    }
  },
  async created() {
    if (this.$ui.activeTab === 'wiki_settings') {
      this.selectedTab = 'Wiki'
    }
    this.currentProject = this.$project
    await this.loadProject()
    this.setupSocketListeners()
  },
  computed: {
    subProjects() {
      const { sub_projects } = this.settings || {}
      if (!sub_projects) return []
      return Array.isArray(sub_projects) ? sub_projects : sub_projects.split(',')
    },
    api() {
      return this.currentProject?.$api
    },
    // Check if knowledge base is empty
    hasKnowledge() {
      return this.indexStatus?.indexed_files?.length > 0
    }
  },
  watch: {
    $projectId() {
      this.loadProject()
    },
    currentProject() {
      this.loadProject()
    }
  },
  methods: {
    setupSocketListeners() {
      const api = this.api
      if (!api?.socket) return

      api.socket.on('codx-junior-index-knowledge-complete', (data) => {
        console.log('Indexing complete:', data)
        this.reloadStatus()
      })

      api.socket.on('codx-junior-index-knowledge-error', (data) => {
        console.error('Indexing error:', data)
        this.$session.onError(`Indexing failed: ${data.message}`)
      })
    },

    async loadProject() {
      this.isLoading = true
      try {
        await this.reloadStatus()
      } finally {
        this.isLoading = false
      }
    },

    async loadSettings() {
      this.settings = await this.api.settings.read()
    },

    async reloadStatus() {
      if (!this.api) return
      this.indexStatus = await this.api.knowledge.status()
      await this.loadSettings()
    },

    async dropSelectedFiles(filePaths) {
      if (!this.api) return
      await this.api.knowledge.delete(filePaths)
      await this.reloadStatus()
    },

    async toggleWatch() {
      await this.$service.project.watch(!this.settings.watching)
      await this.reloadStatus()
    },

    async setSettings(newSettings) {
      if (!this.api) return
      await this.api.settings.read()
      await this.$projects.saveSettings({ ...this.settings, ...newSettings })
    },

    // Handle project selection from ProjectDetailt
    onProjectSelected(project) {
      this.currentProject = project
    }
  }
}
</script>