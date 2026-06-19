<script setup>
import Document from '@/components/document/Document.vue'
import VerticalSplitter from '@/components/layout/VerticalSplitter.vue'
import WikiTree from '@/components/wiki/WikiTree.vue'
</script>

<template>
  <div class="flex flex-col h-full gap-2 p-1 md:p-2">
    <!-- Breadcrumb -->
    <div class="text-sm breadcrumbs">
      <ul>
        <li>
          <span class="click font-bold text-lg" @click="goHome()">Wiki</span>
        </li>
        <li v-if="activeDomain">
          <span class="click" @click="selectDomain(activeDomain)">{{ activeDomain.name }}</span>
        </li>
        <li v-if="selectedModule">
          <span class="truncate">{{ selectedModule.name || selectedModule.path }}</span>
        </li>
      </ul>
    </div>

    <VerticalSplitter class="grow overflow-hidden"
      :panels="{ left: { defaultSize: 28 }, right: { defaultSize: 72 } }">

      <template v-slot:left>
        <div class="flex flex-col h-full overflow-y-auto gap-1 pr-1">

          <!-- Home button -->
          <div class="menu-item click px-2 py-1 rounded hover:bg-base-200"
            :class="isHome ? 'bg-base-300 font-bold' : ''"
            @click="goHome()">
            <i class="fa-solid fa-house mr-1"></i> Home
          </div>

          <!-- Domains section -->
          <div v-if="domains.length" class="mt-2">
            <div class="text-xs font-bold uppercase opacity-50 px-2 mb-1">Domains</div>
            <div
              v-for="domain in domains"
              :key="domain.slug"
              class="click px-2 py-1 rounded hover:bg-base-200 flex items-center gap-1"
              :class="activeDomain?.slug === domain.slug ? 'bg-base-300 font-bold' : ''"
              @click="selectDomain(domain)">
              <i class="fa-solid fa-layer-group text-xs opacity-60"></i>
              <span class="truncate">{{ domain.name }}</span>
              <span class="ml-auto text-xs opacity-40">{{ domain.file_count || 0 }}</span>
            </div>
          </div>

          <!-- Modules list (when domain selected) -->
          <div v-if="activeDomain?.files?.length" class="mt-2">
            <div class="text-xs font-bold uppercase opacity-50 px-2 mb-1">Modules</div>
            <ul class="menu menu-sm p-0 space-y-1">
              <li
                v-for="filePath in activeDomain.files"
                :key="filePath"
                class="click px-2 py-1 rounded hover:bg-base-200 text-sm"
                :class="selectedModule?.path === filePath ? 'bg-base-300 font-bold' : ''"
                @click="selectModule(filePath)">
                <i class="fa-regular fa-file-code text-xs opacity-50"></i>
                <span class="truncate">{{ shortPath(filePath) }}</span>
              </li>
            </ul>
          </div>

          <div v-if="!domains.length && loading" class="px-2 text-sm opacity-50">
            <i class="loading loading-spinner loading-sm mr-1"></i> Loading...
          </div>
        </div>
      </template>

      <template v-slot:right>
        <div class="pl-2 h-full overflow-y-auto">

          <!-- Home / README -->
          <div v-if="isHome" class="prose prose-sm max-w-full">
            <Document :content="homeContent || ''" />
          </div>

          <!-- Domain page (L1) -->
          <div v-else-if="activeDomain && !selectedModule" class="flex flex-col gap-4">
            <div class="text-2xl font-bold flex items-center gap-2">
              <i class="fa-solid fa-layer-group"></i>
              {{ activeDomain.name }}
            </div>

            <div v-if="activeDomain.description" class="text-sm opacity-70">
              {{ activeDomain.description }}
            </div>

            <div v-if="activeDomain.keywords?.length" class="flex flex-wrap gap-1">
              <span v-for="kw in activeDomain.keywords" :key="kw" class="badge badge-outline badge-sm">
                {{ kw }}
              </span>
            </div>

            <div v-if="domainContent" class="prose prose-sm max-w-full">
              <Document :content="domainContent" />
            </div>
            <div v-else-if="loadingContent" class="flex items-center gap-2 opacity-50">
              <i class="loading loading-spinner loading-sm"></i> Loading domain content...
            </div>

            <!-- Domain file list -->
            <div v-if="activeDomain.files?.length" class="mt-4 border-t pt-4">
              <div class="text-sm font-bold mb-3 opacity-70">
                <i class="fa-solid fa-folder mr-1"></i> Files in this domain
              </div>
              <div class="flex flex-col gap-2">
                <div
                  v-for="filePath in activeDomain.files"
                  :key="filePath"
                  class="click flex items-center gap-2 px-2 py-1 rounded hover:bg-base-200 text-sm"
                  @click="selectModule(filePath)">
                  <i class="fa-regular fa-file-code text-xs opacity-50"></i>
                  <span class="truncate">{{ shortPath(filePath) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Module page (L2) -->
          <div v-else-if="selectedModule" class="flex flex-col gap-4">
            <div class="flex items-center gap-2 pb-2 border-b">
              <i class="fa-regular fa-file-code"></i>
              <div class="flex-1">
                <div class="text-lg font-bold">{{ selectedModule.name }}</div>
                <div class="text-xs opacity-50">{{ selectedModule.path }}</div>
              </div>
            </div>

            <div v-if="moduleContent" class="prose prose-sm max-w-full">
              <Document :content="moduleContent" />
            </div>
            <div v-else-if="loadingContent" class="flex items-center gap-2 opacity-50">
              <i class="loading loading-spinner loading-sm"></i> Building module documentation...
            </div>
            <div v-else class="text-sm opacity-50 italic">No documentation available</div>
          </div>

          <!-- Empty state -->
          <div v-else class="flex items-center justify-center h-full opacity-50">
            <div class="text-center">
              <i class="fa-solid fa-book text-3xl mb-2 opacity-30"></i>
              <p>Select a domain or module to view documentation</p>
            </div>
          </div>

        </div>
      </template>

    </VerticalSplitter>
  </div>
</template>

<script>
export default {
  data() {
    return {
      homeContent: null,
      domains: [],
      wikiIndex: null,
      activeDomain: null,
      selectedModule: null,
      domainContent: null,
      moduleContent: null,
      loading: false,
      loadingContent: false
    }
  },
  computed: {
    isHome() {
      return !this.activeDomain && !this.selectedModule
    }
  },
  created() {
    this.loadWiki()
  },
  methods: {
    async loadWiki() {
      this.loading = true
      try {
        // Load home content
        this.homeContent = await this.$storex.api.wiki.read('wiki/home.md')
      } catch {
        this.homeContent = '# Welcome to Wiki\n\nProject documentation not yet available.'
      }

      try {
        // Load wiki structure (domains)
        const index = await this.$storex.api.wiki.index()
        if (index?.domains) {
          this.domains = Object.values(index.domains)
          this.wikiIndex = index
        }
      } catch {
        // Wiki index not ready yet - likely need to build first
        this.domains = []
      } finally {
        this.loading = false
      }
    },

    // Navigate to home
    goHome() {
      this.activeDomain = null
      this.selectedModule = null
      this.domainContent = null
      this.moduleContent = null
    },

    // Select domain and load its content
    async selectDomain(domain) {
      this.selectedModule = null
      this.moduleContent = null
      this.activeDomain = domain
      this.domainContent = null

      // Load domain wiki content if available
      if (domain.wiki_path) {
        this.loadingContent = true
        try {
          this.domainContent = await this.$storex.api.wiki.read(domain.wiki_path)
        } catch {
          this.domainContent = null
        } finally {
          this.loadingContent = false
        }
      }
    },

    // Select module and build/load its documentation
    async selectModule(filePath) {
      this.selectedModule = { path: filePath, name: this.shortPath(filePath) }
      this.moduleContent = null
      this.loadingContent = true

      try {
        // Check if module page exists in index
        const fileEntry = this.wikiIndex?.files?.[filePath]

        if (fileEntry?.wiki_file) {
          // Load existing module documentation
          this.moduleContent = await this.$storex.api.files.read(fileEntry.wiki_file)
        } else {
          // Build module page first
          await this.$storex.api.wiki.buildModulePage(filePath)

          // Refresh index
          const refreshedIndex = await this.$storex.api.wiki.index()
          this.wikiIndex = refreshedIndex

          const entry = refreshedIndex?.files?.[filePath]
          if (entry?.wiki_file) {
            this.moduleContent = await this.$storex.api.files.read(entry.wiki_file)
          }
        }
      } catch (error) {
        this.moduleContent = '> Module documentation could not be loaded.\n\n' +
          'This may mean the wiki engine is still building or the file path is invalid.'
      } finally {
        this.loadingContent = false
      }
    },

    // Extract filename from full path
    shortPath(filePath) {
      if (!filePath) return filePath

      const projectPath = this.$project?.abs_project_path || ''
      let shortened = filePath.replace(projectPath, '').replace(/^\//, '')

      // Get just the filename
      return shortened.split('/').pop()
    }
  }
}
</script>