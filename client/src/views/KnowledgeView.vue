<script setup>
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import Code from '@/components/Code.vue'
import ProjectIcon from '@/components/ProjectIcon.vue'
</script>

<template>
  <div class="flex flex-col gap-2 h-full px-4">
    <!-- Header -->
    <div class="font-medium flex flex-col gap-2">
      <div class="text-3xl flex gap-2 items-center">
        <ProjectDetailt v-model="project" />
        Knowledge
      </div>
      <!-- Search Form -->
      <div class="flex gap-2 items-center">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search..."
          @keydown.enter="search"
          class="input input-bordered w-full"
        />
        <i @click="search" class="fas fa-search text-xl cursor-pointer"></i>
        <i @click="clearSearch" class="fas fa-times text-xl cursor-pointer"></i>
      </div>
    </div>

    <!-- Loading indicator -->
    <div v-if="loading" class="flex items-center gap-2 py-4 text-base-content/70">
      <span class="loading loading-spinner loading-md"></span>
      <span class="text-sm font-medium">Searching...</span>
    </div>

    <template v-if="searchResult && !loading">
      <!-- AI Answer card -->
      <div class="card bg-base-200 shadow-md">
        <div class="card-body gap-3 p-4">
          <!-- Stats row -->
          <div class="flex flex-wrap gap-2 items-center">
            <div class="badge badge-neutral gap-1">
              <i class="fas fa-rotate text-xs"></i>
              {{ searchResult.total_iterations }}/{{ searchResult.max_iterations }} iterations
            </div>
            <div class="badge badge-neutral gap-1">
              <i class="fas fa-file text-xs"></i>
              {{ resultList.length }} document{{ resultList.length !== 1 ? 's' : '' }}
            </div>
          </div>

          <!-- AI Answer -->
          <div class="flex flex-col gap-1">
            <div class="text-sm font-semibold text-primary flex items-center gap-2">
              <i class="fas fa-robot"></i> AI Answer
            </div>
            <div class="text-sm text-base-content whitespace-pre-wrap bg-base-300 rounded-box p-3 max-h-64 overflow-y-auto">
              {{ searchResult.answer }}
            </div>
          </div>

          <!-- Queries used -->
          <div v-if="searchResult.queries_used && searchResult.queries_used.length" class="collapse collapse-arrow bg-base-300 rounded-box">
            <input type="checkbox" />
            <div class="collapse-title text-sm font-medium py-2 min-h-0">
              <i class="fas fa-magnifying-glass-chart mr-1"></i>
              Queries used ({{ searchResult.queries_used.length }})
            </div>
            <div class="collapse-content">
              <ul class="flex flex-col gap-1 pt-1">
                <li
                  v-for="(q, i) in searchResult.queries_used"
                  :key="i"
                  class="text-xs text-base-content/70 flex items-start gap-2"
                >
                  <span class="badge badge-xs badge-outline mt-0.5">{{ i + 1 }}</span>
                  {{ q }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Results count -->
      <div class="text-sm text-base-content/60 font-medium">
        {{ resultList.length }} result{{ resultList.length !== 1 ? 's' : '' }} found
      </div>

      <!-- Results List -->
      <div v-if="resultList.length" class="flex flex-col gap-3 overflow-y-auto">
        <div
          v-for="(result, idx) in resultList"
          :key="result.metadata.source + idx"
          class="card bg-base-200 shadow-sm"
        >
          <div class="card-body p-4 gap-2">
            <!-- File source header -->
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-2 text-sm text-primary font-semibold truncate">
                <i class="fas fa-file-code"></i>
                <span class="truncate" :title="result.metadata.source">
                  {{ shortSource(result.metadata.source) }}
                </span>
              </div>
              <!-- Score badge -->
              <div v-if="result.metadata.score != null" class="badge badge-primary badge-lg font-bold shrink-0">
                <i class="fas fa-star text-xs mr-1"></i>
                {{ formatScore(result.metadata.score) }}
              </div>
              <!-- Project icon from the document's project_id -->
              <ProjectIcon
                  v-if="docProject(result)"
                  :project="docProject(result)"
                  class="w-4 h-4 shrink-0"
              />
            </div>

            <!-- Project name badge -->
            <div v-if="result.metadata.project_name" class="flex items-center gap-1">
              <span class="badge badge-ghost badge-sm gap-1">
                <i class="fas fa-folder text-xs"></i>
                {{ Array.isArray(result.metadata.project_name) ? result.metadata.project_name[0] : result.metadata.project_name }}
              </span>
            </div>

            <!-- Metadata badges -->
            <div class="flex flex-wrap gap-2 text-xs">
              <div v-if="result.metadata.language" class="badge badge-outline">{{ result.metadata.language }}</div>
              <div v-if="result.metadata.loader_type" class="badge badge-outline">{{ result.metadata.loader_type }}</div>
              <div v-if="result.metadata.index != null" class="badge badge-outline">
                chunk {{ result.metadata.index + 1 }}/{{ result.metadata.total_docs }}
              </div>
              <div v-if="result.metadata.length" class="badge badge-outline">{{ result.metadata.length }} chars</div>
              <div v-if="result.metadata.index_date" class="badge badge-outline">{{ result.metadata.index_date }}</div>
            </div>

            <!-- Tabs: content preview + raw metadata -->
            <div role="tablist" class="tabs tabs-bordered tabs-sm mt-1">
              <input
                type="radio"
                :name="`doc-tabs-${idx}`"
                role="tab"
                class="tab"
                aria-label="Preview"
                checked
              />
              <div role="tabpanel" class="tab-content pt-2">
                <div class="collapse collapse-arrow bg-base-300 rounded-box">
                  <input type="checkbox" />
                  <div class="collapse-title text-sm font-medium">
                    Preview content
                  </div>
                  <div class="collapse-content overflow-auto max-h-64">
                    <Code
                      :text="result.page_content"
                      :text-language="result.metadata.language || 'text'"
                      :file-name="result.metadata.source"
                      :project="project"
                    />
                  </div>
                </div>
              </div>

              <input
                type="radio"
                :name="`doc-tabs-${idx}`"
                role="tab"
                class="tab"
                aria-label="Metadata"
              />
              <div role="tabpanel" class="tab-content pt-2">
                <div class="bg-base-300 rounded-box p-3 overflow-auto max-h-64">
                  <pre class="text-xs text-base-content/80 whitespace-pre-wrap break-all">{{ formatMetadata(result.metadata) }}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty results -->
      <div v-else class="flex flex-col items-center gap-2 py-10 text-base-content/50">
        <i class="fas fa-search text-4xl"></i>
        <span class="text-lg">No documents found</span>
      </div>
    </template>

    <!-- Initial empty state -->
    <div v-else-if="!loading && !searchResult" class="flex flex-col items-center gap-2 py-10 text-base-content/50">
      <i class="fas fa-database text-4xl"></i>
      <span class="text-lg">Enter a query to search the knowledge base</span>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      searchQuery: '',
      project: null,
      searchResult: null,
      loading: false
    }
  },
  computed: {
    // Documents sorted by score descending
    resultList() {
      if (!this.searchResult?.documents) return []
      return [...this.searchResult.documents].sort((a, b) => {
        const scoreA = a.metadata?.score ?? 0
        const scoreB = b.metadata?.score ?? 0
        return scoreB - scoreA
      })
    }
  },
  created() {
    this.project = this.$project
  },
  methods: {
    shortSource(source) {
      return source ? source.split('/').slice(-2).join('/') : source
    },
    formatScore(score) {
      return score != null ? Number(score).toFixed(2) : 'N/A'
    },
    // Resolve the project object for a document using its project_id metadata
    docProject(result) {
      const projectId = result?.metadata?.project_id
      if (!projectId) return null
      return this.$projects.allProjectsById[projectId] || null
    },
    // Pretty-print metadata as JSON, excluding page_content
    formatMetadata(metadata) {
      return JSON.stringify(metadata, null, 2)
    },
    async search() {
      if (!this.searchQuery.trim()) return
      this.loading = true
      this.searchResult = null
      try {
        const res = await this.project.$api.knowledge.aiSearch(this.searchQuery.trim())
        this.searchResult = res || null
      } catch (e) {
        console.error('Knowledge search error:', e)
        this.searchResult = null
      } finally {
        this.loading = false
      }
    },
    clearSearch() {
      this.searchQuery = ''
      this.searchResult = null
    }
  }
}
</script>