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
        <li v-if="activeProject">
          <span class="click text-xs opacity-60" @click="selectProject(activeProject)">{{ activeProject.project_name }}</span>
        </li>
        <li v-if="activeDomain">
          <span class="click" @click="selectDomain(activeDomain)">{{ activeDomain.name }}</span>
        </li>
        <li v-if="selectedModule">
          <span class="truncate">{{ selectedModule.name || selectedModule.path }}</span>
        </li>
      </ul>
    </div>

    <!-- Search Bar -->
    <div class="flex gap-2 items-center shrink-0">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Search wiki with AI..."
        @keydown.enter="performSearch"
        class="input input-bordered w-full"
        :disabled="searchLoading"
      />
      <button
        @click="performSearch"
        class="btn btn-primary"
        :disabled="searchLoading || !searchQuery.trim()"
      >
        <span v-if="searchLoading" class="loading loading-spinner loading-sm"></span>
        <i v-else class="fas fa-search"></i>
      </button>
      <button
        v-if="isSearchActive"
        @click="clearSearch"
        class="btn btn-ghost"
        :disabled="searchLoading"
      >
        <i class="fas fa-times"></i>
      </button>
    </div>

    <!-- Loading indicator -->
    <div v-if="searchLoading" class="flex flex-col items-center gap-2 py-4 text-base-content/70 text-sm shrink-0">
      <span class="loading loading-spinner loading-sm"></span>
      <span>Searching wiki...</span>
    </div>

    <!-- Search error -->
    <div v-if="searchError && !searchLoading" class="alert alert-error shrink-0">
      <i class="fas fa-circle-exclamation"></i>
      <span>{{ searchError }}</span>
      <button class="btn btn-sm btn-ghost" @click="searchError = null">Dismiss</button>
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

          <!-- Search Results Section -->
          <template v-if="isSearchActive && !searchLoading">
            <div class="text-xs font-bold uppercase opacity-50 px-2 mb-1 mt-2">Search Results</div>
            
            <!-- Domains Results -->
            <div v-if="searchResults.domains.length" class="mb-2">
              <div class="text-xs font-semibold uppercase opacity-60 px-2 mb-1 text-primary">
                Domains ({{ searchResults.domains.length }})
              </div>
              <div
                v-for="domain in searchResults.domains"
                :key="domain.slug"
                class="click px-2 py-1 rounded hover:bg-base-200 flex items-center gap-1 text-sm"
                :class="activeDomain?.slug === domain.slug ? 'bg-base-300 font-bold' : ''"
                @click="selectDomain(domain)">
                <i class="fa-solid fa-layer-group text-xs opacity-60"></i>
                <span class="truncate">{{ domain.name }}</span>
              </div>
            </div>

            <!-- Modules Results -->
            <div v-if="searchResults.modules.length" class="mb-2">
              <div class="text-xs font-semibold uppercase opacity-60 px-2 mb-1 text-primary">
                Modules ({{ searchResults.modules.length }})
              </div>
              <div
                v-for="mod in searchResults.modules"
                :key="mod.path"
                class="click px-2 py-1 rounded hover:bg-base-200 flex items-center gap-1 text-sm"
                :class="selectedModule?.path === mod.path ? 'bg-base-300 font-bold' : ''"
                @click="selectModule(mod.path)">
                <i class="fa-regular fa-file-code text-xs opacity-50"></i>
                <span class="truncate">{{ shortPath(mod.path) }}</span>
              </div>
            </div>

            <!-- No Results -->
            <div v-if="!searchResults.domains.length && !searchResults.modules.length"
              class="text-xs opacity-50 px-2 py-2">
              No results found for "{{ searchQuery }}"
            </div>
          </template>

          <!-- Projects section (with child projects) -->
          <div v-else-if="availableProjects.length" class="mt-2">
            <div class="text-xs font-bold uppercase opacity-50 px-2 mb-1">Projects</div>
            <div
              v-for="project in availableProjects"
              :key="project.project_id"
              class="click px-2 py-1 rounded hover:bg-base-200 flex items-center gap-1 text-sm"
              :class="activeProject?.project_id === project.project_id ? 'bg-base-300 font-bold' : ''"
              @click="selectProject(project)">
              <i class="fa-solid fa-folder text-xs opacity-60"></i>
              <span class="truncate">{{ project.project_name }}</span>
            </div>
          </div>

          <!-- Domains section -->
          <div v-if="!isSearchActive && domains.length" class="mt-2">
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
          <div v-if="!isSearchActive && activeDomain?.files?.length" class="mt-2">
            <div class="text-xs font-bold uppercase opacity-50 px-2 mb-1">Modules</div>
            <ul class="menu menu-sm p-0 space-y-1">
              <li
                v-for="filePath in activeDomain.files"
                :key="filePath"
                class="click px-2 py-1 rounded hover:bg-base-200 text-sm"
                :class="selectedModule?.path === filePath ? 'bg-base-300 font-bold' : ''"
                @click="selectModule(filePath)">
                <a>
                  <i class="fa-regular fa-file-code text-xs opacity-50"></i>
                  <div class="truncate">{{ shortPath(filePath) }}</div>
                </a>
              </li>
            </ul>
          </div>

          <div v-if="!isSearchActive && !domains.length && loading" class="px-2 text-sm opacity-50">
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

          <!-- AI Search Results -->
          <div v-else-if="isSearchActive && !searchLoading && searchResult" class="flex flex-col gap-4">
            <!-- Search Stats -->
            <div class="card bg-base-200 shadow-md">
              <div class="card-body gap-3 p-4">
                <div class="flex flex-wrap gap-2 items-center">
                  <div class="badge badge-primary gap-1">
                    <i class="fas fa-robot text-xs"></i>
                    AI Search
                  </div>
                  <div class="badge badge-neutral gap-1">
                    <i class="fas fa-file text-xs"></i>
                    {{ aiSearchResults.length }} doc{{ aiSearchResults.length !== 1 ? 's' : '' }}
                  </div>
                </div>

                <!-- AI Answer -->
                <div v-if="searchResult.answer" class="flex flex-col gap-1">
                  <div class="text-sm font-semibold text-primary flex items-center gap-2">
                    <i class="fas fa-robot"></i> AI Answer
                  </div>
                  <div class="text-sm text-base-content whitespace-pre-wrap bg-base-300 rounded-box p-3 max-h-48 overflow-y-auto">
                    {{ searchResult.answer }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Supporting Documents -->
            <div v-if="aiSearchResults.length" class="flex flex-col gap-3">
              <div class="text-sm text-base-content/60 font-medium">
                {{ aiSearchResults.length }} supporting document{{ aiSearchResults.length !== 1 ? 's' : '' }}
              </div>
              <div
                v-for="(result, idx) in aiSearchResults"
                :key="result.metadata.source + idx"
                class="card bg-base-200 shadow-sm cursor-pointer hover:shadow-md transition-shadow"
                @click="selectModuleFromSearch(result)">
                <div class="card-body p-4 gap-2">
                  <div class="flex items-center justify-between gap-2">
                    <div class="flex items-center gap-2 text-sm text-primary font-semibold truncate">
                      <i class="fas fa-file-code"></i>
                      <span class="truncate" :title="result.metadata.source">
                        {{ shortSource(result.metadata.source) }}
                      </span>
                    </div>
                    <div v-if="result.metadata.score != null" class="badge badge-primary badge-lg font-bold">
                      <i class="fas fa-star text-xs mr-1"></i>
                      {{ formatScore(result.metadata.score) }}
                    </div>
                  </div>

                  <!-- Preview -->
                  <div class="text-xs text-base-content/70 line-clamp-3">
                    {{ result.page_content.substring(0, 150) }}...
                  </div>
                </div>
              </div>
            </div>
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

            <div v-if="domainContent" class="prose prose-sm max-w-full" ref="domainContentRef">
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
      activeProject: null,
      activeDomain: null,
      selectedModule: null,
      domainContent: null,
      moduleContent: null,
      loading: false,
      loadingContent: false,
      searchQuery: '',
      searchLoading: false,
      searchError: null,
      searchResult: null,
      searchResults: {
        domains: [],
        modules: []
      }
    }
  },
  computed: {
    isHome() {
      return !this.activeDomain && !this.selectedModule
    },
    isSearchActive() {
      return this.searchQuery.trim().length > 0
    },
    availableProjects() {
      const current = this.$storex.projects.activeProject
      const children = this.$storex.projects.childProjects || []
      return [current, ...children].filter(p => p)
    },
    aiSearchResults() {
      if (!this.searchResult?.documents) return []
      return [...this.searchResult.documents].sort((a, b) => {
        const scoreA = a.metadata?.score ?? 0
        const scoreB = b.metadata?.score ?? 0
        return scoreB - scoreA
      })
    }
  },
  watch: {
    domainContent() {
      this.$nextTick(() => this.attachDomainContentLinks())
    }
  },
  created() {
    this.activeProject = this.$storex.projects.activeProject
    this.loadWiki()
  },
  methods: {
    async loadWiki() {
      this.loading = true
      try {
        const api = this.activeProject?.$api || this.$storex.api
        this.homeContent = await api.wiki.read('wiki/home.md')
      } catch {
        this.homeContent = '# Welcome to Wiki\n\nProject documentation not yet available.'
      }

      try {
        const api = this.activeProject?.$api || this.$storex.api
        const index = await api.wiki.index()
        if (index?.domains) {
          this.domains = Object.values(index.domains)
          this.wikiIndex = index
        }
      } catch {
        this.domains = []
      } finally {
        this.loading = false
      }
    },

    async performSearch() {
      if (!this.searchQuery.trim()) return

      this.searchLoading = true
      this.searchError = null
      this.searchResult = null
      this.searchResults = { domains: [], modules: [] }

      try {
        const api = this.activeProject?.$api || this.$storex.api
        const res = await api.knowledge.aiSearch(this.searchQuery.trim())
        this.searchResult = res || null

        // Extract unique domains and modules from search results
        const domainSet = new Set()
        const moduleSet = new Set()

        if (res?.documents) {
          res.documents.forEach(doc => {
            const source = doc.metadata?.source || ''
            const filePath = source.split('/').slice(0, -1).join('/')

            // Try to match with existing domains
            this.domains.forEach(domain => {
              if (domain.files?.some(f => f.includes(source))) {
                domainSet.add(domain.slug)
              }
            })

            // Add module if it has a file path
            if (source) {
              moduleSet.add(source)
            }
          })
        }

        this.searchResults = {
          domains: Array.from(domainSet).map(slug => 
            this.domains.find(d => d.slug === slug)
          ).filter(Boolean),
          modules: Array.from(moduleSet).map(path => ({ path }))
        }
      } catch (e) {
        console.error('Wiki AI search error:', e)
        this.searchError = 'Search failed. Please try again.'
      } finally {
        this.searchLoading = false
      }
    },

    clearSearch() {
      this.searchQuery = ''
      this.searchResult = null
      this.searchError = null
      this.searchResults = { domains: [], modules: [] }
    },

    selectProject(project) {
      this.activeProject = project
      this.activeDomain = null
      this.selectedModule = null
      this.domainContent = null
      this.moduleContent = null
      this.domains = []
      this.clearSearch()
      this.loadWiki()
    },

    goHome() {
      this.activeDomain = null
      this.selectedModule = null
      this.domainContent = null
      this.moduleContent = null
      this.clearSearch()
    },

    async selectDomain(domain) {
      this.selectedModule = null
      this.moduleContent = null
      this.activeDomain = domain
      this.domainContent = null
      this.clearSearch()

      if (domain.wiki_path) {
        this.loadingContent = true
        try {
          const api = this.activeProject?.$api || this.$storex.api
          this.domainContent = await api.wiki.read(domain.wiki_path)
        } catch {
          this.domainContent = null
        } finally {
          this.loadingContent = false
        }
      }
    },

    async selectModule(filePath) {
      this.selectedModule = { path: filePath, name: this.shortPath(filePath) }
      this.moduleContent = null
      this.loadingContent = true
      this.clearSearch()

      try {
        const api = this.activeProject?.$api || this.$storex.api
        const fileEntry = this.wikiIndex?.files?.[filePath]

        if (fileEntry?.wiki_file) {
          this.moduleContent = await api.files.read(fileEntry.wiki_file)
        } else {
          await api.wiki.buildModulePage(filePath)

          const refreshedIndex = await api.wiki.index()
          this.wikiIndex = refreshedIndex

          const entry = refreshedIndex?.files?.[filePath]
          if (entry?.wiki_file) {
            this.moduleContent = await api.files.read(entry.wiki_file)
          }
        }
      } catch (error) {
        this.moduleContent = '> Module documentation could not be loaded.\n\n' +
          'This may mean the wiki engine is still building or the file path is invalid.'
      } finally {
        this.loadingContent = false
      }
    },

    selectModuleFromSearch(result) {
      const source = result.metadata?.source
      if (source) {
        this.selectModule(source)
      }
    },

    shortPath(filePath) {
      if (!filePath) return filePath

      const projectPath = this.activeProject?.abs_project_path || ''
      let shortened = filePath.replace(projectPath, '').replace(/^\//, '')

      return shortened.split('/').pop()
    },

    shortSource(source) {
      return source ? source.split('/').slice(-2).join('/') : source
    },

    formatScore(score) {
      return score != null ? Number(score).toFixed(2) : 'N/A'
    },

    attachDomainContentLinks() {
      const contentEl = this.$refs.domainContentRef
      if (!contentEl) return

      const links = contentEl.querySelectorAll('a')
      links.forEach(link => {
        const href = link.getAttribute('href')
        if (href?.endsWith('.md')) {
          const filePath = this.findFileByName(href)
          if (filePath) {
            link.classList.add('link', 'link-primary', 'cursor-pointer')
            link.style.textDecoration = 'none'
            link.onclick = (e) => {
              e.preventDefault()
              this.selectModule(filePath)
            }
          }
        }
      })
    },

    findFileByName(fileName) {
      if (!this.activeDomain?.files) return null
      return this.activeDomain.files.find(filePath => 
        filePath.endsWith(fileName) || filePath.endsWith(`/${fileName}`)
      )
    }
  }
}
</script>