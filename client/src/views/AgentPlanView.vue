<script setup>
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import Code from '@/components/Code.vue'
import ProjectIcon from '@/components/ProjectIcon.vue'
</script>

<template>
  <div class="flex flex-col gap-2 h-full px-4 overflow-hidden">
    <!-- Header -->
    <div class="font-medium flex flex-col gap-2 shrink-0">
      <div class="text-3xl flex gap-2 items-center">
        <ProjectDetailt v-model="project" />
        Agent Resource Plan
      </div>
      
      <!-- Request input form -->
      <div class="flex gap-2 items-center">
        <input
          v-model="userRequest"
          type="text"
          placeholder="Describe the task for the agent..."
          @keydown.enter="performSearch"
          class="input input-bordered w-full"
          :disabled="loading"
        />
        <button
          @click="performSearch"
          class="btn btn-primary"
          :disabled="loading || !userRequest.trim()"
        >
          <span v-if="loading" class="loading loading-spinner loading-sm"></span>
          <i v-else class="fas fa-robot"></i>
        </button>
        <button
          @click="clearResults"
          class="btn btn-ghost"
          :disabled="loading"
        >
          <i class="fas fa-times"></i>
        </button>
      </div>
    </div>

    <!-- Loading state with progress -->
    <div v-if="loading" class="flex flex-col items-center gap-3 py-10 text-base-content/70">
      <span class="loading loading-spinner loading-lg"></span>
      <span class="text-sm font-medium">Agent is planning the task...</span>
      <span v-if="progressMessage" class="text-xs text-base-content/50">
        {{ progressMessage }}
      </span>
    </div>

    <!-- Results area -->
    <template v-if="plan && !loading">
      <!-- Plan header card -->
      <div class="card bg-base-200 shadow-md shrink-0">
        <div class="card-body gap-3 p-4">
          <!-- Stats row -->
          <div class="flex flex-wrap gap-2 items-center">
            <div class="badge badge-primary gap-1">
              <i class="fas fa-robot text-xs"></i>
              Agent Plan
            </div>
            <div class="badge badge-neutral gap-1">
              <i class="fas fa-rotate text-xs"></i>
              {{ plan.total_iterations }}/3 iterations
            </div>
            <div class="badge badge-neutral gap-1">
              <i class="fas fa-file text-xs"></i>
              {{ plan.documents.length }} doc{{ plan.documents.length !== 1 ? 's' : '' }}
            </div>
            <div
              v-for="proj in plan.projects_searched"
              :key="proj"
              class="badge badge-ghost gap-1"
            >
              <i class="fas fa-folder text-xs"></i>
              {{ proj }}
            </div>
          </div>

          <!-- Overview section -->
          <div class="flex flex-col gap-1">
            <div class="text-sm font-semibold text-primary flex items-center gap-2">
              <i class="fas fa-lightbulb"></i> Overview
            </div>
            <div class="text-sm text-base-content bg-base-300 rounded-box p-3">
              {{ plan.overview }}
            </div>
          </div>

          <!-- Additional context -->
          <div v-if="plan.additional_context" class="flex flex-col gap-1">
            <div class="text-sm font-semibold text-warning flex items-center gap-2">
              <i class="fas fa-triangle-exclamation"></i> Additional Context
            </div>
            <div class="text-sm text-base-content bg-base-300 rounded-box p-3">
              {{ plan.additional_context }}
            </div>
          </div>

          <!-- Queries used -->
          <div
            v-if="plan.queries_used && plan.queries_used.length"
            class="collapse collapse-arrow bg-base-300 rounded-box"
          >
            <input type="checkbox" />
            <div class="collapse-title text-sm font-medium py-2 min-h-0">
              <i class="fas fa-magnifying-glass-chart mr-1"></i>
              Queries used ({{ plan.queries_used.length }})
            </div>
            <div class="collapse-content">
              <ul class="flex flex-col gap-1 pt-1">
                <li
                  v-for="(q, i) in plan.queries_used"
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

      <!-- Files sections -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <!-- Files to read -->
        <div v-if="plan.files_to_read.length" class="card bg-info/10 border border-info">
          <div class="card-body p-4 gap-2">
            <h3 class="card-title text-base flex items-center gap-2 text-info">
              <i class="fas fa-book"></i> Read ({{ plan.files_to_read.length }})
            </h3>
            <div class="flex flex-col gap-2">
              <div
                v-for="file in plan.files_to_read"
                :key="file.source"
                class="bg-base-100 rounded p-2 text-xs"
              >
                <div class="font-mono text-info mb-1 truncate" :title="file.source">
                  {{ shortPath(file.source) }}
                </div>
                <div class="text-base-content/70">{{ file.reason }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Files to modify -->
        <div v-if="plan.files_to_modify.length" class="card bg-warning/10 border border-warning">
          <div class="card-body p-4 gap-2">
            <h3 class="card-title text-base flex items-center gap-2 text-warning">
              <i class="fas fa-edit"></i> Modify ({{ plan.files_to_modify.length }})
            </h3>
            <div class="flex flex-col gap-2">
              <div
                v-for="file in plan.files_to_modify"
                :key="file.source"
                class="bg-base-100 rounded p-2 text-xs"
              >
                <div class="font-mono text-warning mb-1 truncate" :title="file.source">
                  {{ shortPath(file.source) }}
                </div>
                <div class="text-base-content/70 mb-1">{{ file.reason }}</div>
                <div v-if="file.suggested_action" class="badge badge-outline badge-sm">
                  {{ file.suggested_action }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Files to create -->
        <div v-if="plan.files_to_create.length" class="card bg-success/10 border border-success">
          <div class="card-body p-4 gap-2">
            <h3 class="card-title text-base flex items-center gap-2 text-success">
              <i class="fas fa-file-circle-plus"></i> Create ({{ plan.files_to_create.length }})
            </h3>
            <div class="flex flex-col gap-2">
              <div
                v-for="file in plan.files_to_create"
                :key="file.source"
                class="bg-base-100 rounded p-2 text-xs"
              >
                <div class="font-mono text-success mb-1 truncate" :title="file.source">
                  {{ shortPath(file.source) }}
                </div>
                <div class="text-base-content/70">{{ file.reason }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Supporting documents -->
      <div v-if="plan.documents.length" class="mt-4">
        <div class="text-sm text-base-content/60 font-medium mb-2">
          {{ plan.documents.length }} supporting document{{ plan.documents.length !== 1 ? 's' : '' }}
        </div>
        <div class="flex flex-col gap-2 overflow-y-auto max-h-48">
          <div
            v-for="(doc, idx) in plan.documents"
            :key="doc.metadata.source + idx"
            class="bg-base-200 rounded p-2 text-xs"
          >
            <div class="flex items-center justify-between gap-2 mb-1">
              <span class="font-mono truncate text-primary">{{ shortPath(doc.metadata.source) }}</span>
              <span v-if="doc.metadata.score" class="badge badge-primary badge-sm">
                {{ formatScore(doc.metadata.score) }}
              </span>
            </div>
            <div class="text-base-content/70 line-clamp-2">{{ doc.page_content.substring(0, 100) }}...</div>
          </div>
        </div>
      </div>
    </template>

    <!-- Empty state -->
    <div
      v-if="!loading && !plan && !error"
      class="flex flex-col items-center gap-3 py-10 text-base-content/50"
    >
      <i class="fas fa-robot text-5xl"></i>
      <span class="text-lg">Describe a task for the agent</span>
      <span class="text-sm">The AI will create a structured plan showing which files to read, modify, or create</span>
    </div>

    <!-- Error state -->
    <div v-if="error && !loading" class="alert alert-error shrink-0">
      <i class="fas fa-circle-exclamation"></i>
      <span>{{ error }}</span>
      <button class="btn btn-sm btn-ghost" @click="error = null">Dismiss</button>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      userRequest: '',
      project: null,
      plan: null,
      loading: false,
      error: null,
      progressMessage: ''
    }
  },
  created() {
    this.project = this.$project
  },
  methods: {
    async performSearch() {
      if (!this.userRequest.trim()) return
      
      this.loading = true
      this.error = null
      this.progressMessage = ''
      this.plan = null

      try {
        // Use socket for background execution with progress updates
        this.setupProgressListeners()
        const result = await this.$project.$api.knowledge.agentSearchBackground(
          this.userRequest.trim(),
          3
        )
        this.plan = result.plan || result
      } catch (e) {
        console.error('Agent search error:', e)
        this.error = 'Agent search failed. ' + e.message
      } finally {
        this.loading = false
      }
    },

    setupProgressListeners() {
      try {
        this.$project.$api.knowledge.onAgentSearchProgress((data) => {
          this.progressMessage = `Iteration ${data.iteration}: ${data.documents_found} documents found`
        })

        this.$project.$api.knowledge.onAgentSearchComplete((data) => {
          this.plan = data.plan
          this.loading = false
          this.error = null
        })

        this.$project.$api.knowledge.onAgentSearchError((data) => {
          this.error = data.message
          this.loading = false
        })
      } catch (e) {
        console.warn('Could not setup socket listeners:', e)
      }
    },

    shortPath(source) {
      return source ? source.split('/').slice(-2).join('/') : source
    },

    formatScore(score) {
      return score != null ? Number(score).toFixed(2) : 'N/A'
    },

    clearResults() {
      this.userRequest = ''
      this.plan = null
      this.error = null
    }
  }
}
</script>