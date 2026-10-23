<template>
  <div class="h-full flex flex-col gap-4 overflow-auto bg-base-100 p-4">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-3 shrink-0">
      <div>
        <h2 class="text-lg font-bold flex items-center gap-2">
          <i class="fa-solid fa-diagram-project text-primary"></i>
          Decision Model Logs
        </h2>
        <p class="text-xs text-base-content/60">
          Inspect, filter and audit decision-model reasoning and outputs
        </p>
      </div>
      <div class="flex items-center gap-2">
        <label class="input input-sm input-bordered flex items-center gap-2">
          <i class="fa-solid fa-magnifying-glass opacity-50"></i>
          <input v-model="search" type="text" class="grow" placeholder="Search records..." />
        </label>
        <button
          class="btn btn-sm btn-ghost"
          :class="isLoading ? 'loading' : ''"
          @click="refresh"
          title="Refresh logs"
        >
          <i v-if="!isLoading" class="fa-solid fa-rotate-right"></i>
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="card bg-base-200 shadow-sm shrink-0">
      <div class="card-body p-3 flex-row flex-wrap items-end gap-3">
        <div class="form-control">
          <label class="label py-0"><span class="label-text text-xs">From</span></label>
          <input v-model="filters.startDate" type="date" class="input input-sm input-bordered" />
        </div>
        <div class="form-control">
          <label class="label py-0"><span class="label-text text-xs">To</span></label>
          <input v-model="filters.endDate" type="date" class="input input-sm input-bordered" />
        </div>
        <div class="form-control">
          <label class="label py-0"><span class="label-text text-xs">Model</span></label>
          <select v-model="filters.model" class="select select-sm select-bordered">
            <option value="">All models</option>
            <option v-for="m in availableModels" :key="m" :value="m">{{ m }}</option>
          </select>
        </div>
        <div class="form-control">
          <label class="label py-0"><span class="label-text text-xs">Direction</span></label>
          <select v-model="filters.direction" class="select select-sm select-bordered">
            <option value="">All</option>
            <option value="request">Request</option>
            <option value="response">Response</option>
          </select>
        </div>
        <div class="flex items-center gap-2 ml-auto">
          <button class="btn btn-sm btn-ghost" @click="resetFilters">
            <i class="fa-solid fa-filter-circle-xmark"></i>
            Clear
          </button>
          <button class="btn btn-sm btn-primary" @click="applyFilters">
            <i class="fa-solid fa-filter"></i>
            Apply
          </button>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex-1 flex items-center justify-center py-12">
      <span class="loading loading-spinner loading-lg text-primary"></span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-error gap-3">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <div>
        <h3 class="font-bold">Failed to load decision model logs</h3>
        <div class="text-sm">{{ error }}</div>
      </div>
      <button class="btn btn-sm" @click="refresh">Retry</button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!records.length" class="flex-1 flex flex-col items-center justify-center py-12 text-center">
      <i class="fa-solid fa-inbox text-4xl text-base-content/20 mb-3"></i>
      <p class="text-base-content/60">No decision model logs found</p>
      <p class="text-xs text-base-content/40 mt-1">Try widening the date range or clearing the filters</p>
    </div>

    <template v-else>
      <!-- Summary Statistics -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3 shrink-0">
        <div class="stat bg-base-200 rounded-box shadow-sm">
          <div class="stat-title text-xs">Records</div>
          <div class="stat-value text-2xl">{{ formatNumber(records.length) }}</div>
          <div class="stat-desc text-xs">
            {{ summary.total_requests || 0 }} req · {{ summary.total_responses || 0 }} res
          </div>
        </div>

        <div class="stat bg-base-200 rounded-box shadow-sm">
          <div class="stat-title text-xs">Avg Latency</div>
          <div class="stat-value text-2xl">{{ formatDuration(avgDuration) }}</div>
          <div class="stat-desc text-xs">total {{ formatDuration(summary.total_duration_seconds) }}</div>
        </div>

        <div class="stat bg-base-200 rounded-box shadow-sm">
          <div class="stat-title text-xs">Tokens</div>
          <div class="stat-value text-2xl">{{ formatNumber(totalTokens) }}</div>
          <div class="stat-desc text-xs">
            <span class="text-info">↓{{ formatNumber(summary.token_stats?.total_estimated_input_tokens) }}</span>
            <span class="text-success">↑{{ formatNumber(summary.token_stats?.total_estimated_output_tokens) }}</span>
          </div>
        </div>

        <div class="stat bg-base-200 rounded-box shadow-sm" :class="hasErrors ? 'bg-error/10' : ''">
          <div class="stat-title text-xs">Status</div>
          <div class="stat-value text-2xl" :class="hasErrors ? 'text-error' : 'text-success'">
            <i :class="hasErrors ? 'fa-solid fa-triangle-exclamation' : 'fa-solid fa-circle-check'"></i>
          </div>
          <div class="stat-desc text-xs">
            <span class="badge badge-xs badge-success">{{ successCount }} ok</span>
            <span v-if="errorCount" class="badge badge-xs badge-error">{{ errorCount }} err</span>
          </div>
        </div>
      </div>

      <!-- Records List -->
      <div class="flex-1 min-h-0 space-y-3">
        <div
          v-for="record in paginatedRecords"
          :key="keyOf(record)"
          class="card bg-base-200 shadow-sm hover:shadow-md transition-shadow"
        >
          <div class="card-body p-3 gap-2">
            <!-- Record Header -->
            <div
              class="flex items-start justify-between gap-3 cursor-pointer"
              @click="toggleRecord(keyOf(record))"
            >
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 flex-wrap">
                  <i class="fa-solid fa-diagram-project text-primary text-sm"></i>
                  <span class="font-bold text-sm truncate">
                    {{ record.decision || record.title || record.model || 'Decision' }}
                  </span>
                  <span v-if="record.provider" class="badge badge-xs badge-outline">{{ record.provider }}</span>
                  <span class="badge badge-xs" :class="directionBadge(record.direction)">
                    {{ record.direction || 'request' }}
                  </span>
                  <span v-if="record.cached" class="badge badge-xs badge-info">cached</span>
                </div>
                <div class="text-xs text-base-content/60 mt-1 flex items-center gap-3 flex-wrap">
                  <span><i class="fa-solid fa-clock mr-1"></i>{{ formatTimestamp(record.timestamp) }}</span>
                  <span v-if="record.model"><i class="fa-solid fa-microchip mr-1"></i>{{ record.model }}</span>
                  <span v-if="record.duration_seconds != null">
                    <i class="fa-solid fa-stopwatch mr-1"></i>{{ formatDuration(record.duration_seconds) }}
                  </span>
                </div>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <span class="badge badge-sm" :class="record.error ? 'badge-error' : 'badge-success'">
                  {{ record.error ? 'error' : 'ok' }}
                </span>
                <i
                  class="fa-solid fa-chevron-down text-xs transition-transform"
                  :class="isExpanded(record) ? 'rotate-180' : ''"
                ></i>
              </div>
            </div>

            <!-- Expanded Details -->
            <div v-if="isExpanded(record)" class="border-t border-base-100 pt-3 space-y-3">
              <div v-if="record.prompt" class="space-y-1">
                <label class="text-xs font-bold text-base-content/70">Prompt</label>
                <pre class="bg-base-100 p-2 rounded text-xs max-h-48 overflow-auto whitespace-pre-wrap break-words font-mono text-base-content/80">{{ record.prompt }}</pre>
              </div>

              <div v-if="record.decision || record.output || record.result" class="space-y-1">
                <label class="text-xs font-bold text-base-content/70">Decision / Output</label>
                <pre class="bg-base-100 p-2 rounded text-xs max-h-48 overflow-auto whitespace-pre-wrap break-words font-mono text-base-content/80">{{ pretty(record.decision || record.output || record.result) }}</pre>
              </div>

              <div v-if="record.reasoning" class="space-y-1">
                <label class="text-xs font-bold text-base-content/70">Reasoning</label>
                <pre class="bg-base-100 p-2 rounded text-xs max-h-48 overflow-auto whitespace-pre-wrap break-words font-mono text-base-content/80">{{ record.reasoning }}</pre>
              </div>

              <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                <div class="bg-base-100 rounded p-2">
                  <div class="text-base-content/50">Input tokens</div>
                  <div class="font-semibold">{{ formatNumber(record.input_tokens) }}</div>
                </div>
                <div class="bg-base-100 rounded p-2">
                  <div class="text-base-content/50">Output tokens</div>
                  <div class="font-semibold">{{ formatNumber(record.output_tokens) }}</div>
                </div>
                <div class="bg-base-100 rounded p-2">
                  <div class="text-base-content/50">Duration</div>
                  <div class="font-semibold">{{ formatDuration(record.duration_seconds) }}</div>
                </div>
                <div class="bg-base-100 rounded p-2 min-w-0">
                  <div class="text-base-content/50">Session</div>
                  <div class="font-semibold truncate" :title="record.session_id">{{ record.session_id || '—' }}</div>
                </div>
              </div>

              <div v-if="record.error" class="alert alert-error py-2 text-xs">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <span>{{ record.error_message || record.error }}</span>
              </div>

              <div class="space-y-1">
                <label class="text-xs font-bold text-base-content/70">Raw Record</label>
                <pre class="bg-base-100 p-2 rounded text-xs max-h-64 overflow-auto text-base-content/70">{{ pretty(record) }}</pre>
              </div>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="flex items-center justify-center gap-2 py-2">
          <button class="btn btn-sm btn-ghost" :disabled="page === 1" @click="page = Math.max(1, page - 1)">
            <i class="fa-solid fa-chevron-left"></i>
          </button>
          <span class="text-sm">Page {{ page }} of {{ totalPages }}</span>
          <button class="btn btn-sm btn-ghost" :disabled="page === totalPages" @click="page = Math.min(totalPages, page + 1)">
            <i class="fa-solid fa-chevron-right"></i>
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script>
export default {
  name: 'DecisionModelLogs',
  data() {
    return {
      response: null,
      isLoading: false,
      error: null,
      expandedKey: null,
      search: '',
      page: 1,
      pageSize: 15,
      filters: {
        startDate: '',
        endDate: '',
        model: '',
        direction: ''
      }
    }
  },
  computed: {
    summary() {
      return this.response?.summary || {}
    },
    rawRecords() {
      const response = this.response
      if (!response) return []
      if (Array.isArray(response)) return response
      return response.records || response.logs || response.items || []
    },
    records() {
      const query = (this.search || '').toLowerCase().trim()
      if (!query) return this.rawRecords
      return this.rawRecords.filter(record =>
        this.pretty(record).toLowerCase().includes(query)
      )
    },
    availableModels() {
      const fromResponse = this.response?.models
      if (Array.isArray(fromResponse) && fromResponse.length) {
        return fromResponse
          .map(m => (typeof m === 'string' ? m : m.model))
          .filter(Boolean)
      }
      return [...new Set(this.rawRecords.map(r => r.model).filter(Boolean))].sort()
    },
    paginatedRecords() {
      const start = (this.page - 1) * this.pageSize
      return this.records.slice(start, start + this.pageSize)
    },
    totalPages() {
      return Math.max(1, Math.ceil(this.records.length / this.pageSize))
    },
    avgDuration() {
      if (this.summary.average_request_duration_seconds != null) {
        return this.summary.average_request_duration_seconds
      }
      const withDuration = this.rawRecords.filter(r => r.duration_seconds != null)
      if (!withDuration.length) return 0
      return withDuration.reduce((acc, r) => acc + r.duration_seconds, 0) / withDuration.length
    },
    totalTokens() {
      if (this.summary.token_stats?.total_estimated_tokens != null) {
        return this.summary.token_stats.total_estimated_tokens
      }
      return this.rawRecords.reduce(
        (acc, r) => acc + (r.input_tokens || 0) + (r.output_tokens || 0),
        0
      )
    },
    successCount() {
      return this.rawRecords.filter(r => !r.error).length
    },
    errorCount() {
      return this.rawRecords.filter(r => r.error).length
    },
    hasErrors() {
      return this.errorCount > 0
    }
  },
  methods: {
    async loadLogs() {
      this.isLoading = true
      this.error = null
      try {
        const api = this.$storex.api.analytics
        if (!api || typeof api.decisionLogs !== 'function') {
          throw new Error('Analytics API is not available')
        }
        // The settings entry is admin-only, so prefer the admin-scoped
        // endpoints (every user's logs); they fall back to the user-scoped
        // listing when no admin route is deployed on the backend.
        const isAdmin = !!this.$storex.api.permissions?.isAdmin
        const scoped = (isAdmin && typeof api.admin?.decisionLogs === 'function')
          ? api.admin
          : api
        const params = { ...this.filters }
        Object.keys(params).forEach(key => {
          if (!params[key]) delete params[key]
        })
        this.response = await scoped.decisionLogs(params)
        this.page = 1
      } catch (err) {
        this.error = err?.message || 'Failed to load decision model logs'
        console.error('Error loading decision model logs:', err)
      } finally {
        this.isLoading = false
      }
    },
    refresh() {
      return this.loadLogs()
    },
    applyFilters() {
      this.page = 1
      this.loadLogs()
    },
    resetFilters() {
      this.filters = { startDate: '', endDate: '', model: '', direction: '' }
      this.search = ''
      this.loadLogs()
    },
    keyOf(record) {
      return record.id || record.message_id || record.timestamp
    },
    toggleRecord(key) {
      this.expandedKey = this.expandedKey === key ? null : key
    },
    isExpanded(record) {
      return this.expandedKey === this.keyOf(record)
    },
    pretty(value) {
      if (value == null) return ''
      if (typeof value === 'string') return value
      try {
        return JSON.stringify(value, null, 2)
      } catch {
        return String(value)
      }
    },
    formatNumber(num) {
      if (num == null) return '0'
      return Number(num).toLocaleString()
    },
    formatDuration(seconds) {
      if (!seconds) return '0s'
      if (seconds < 1) return `${Math.round(seconds * 1000)}ms`
      if (seconds < 60) return `${seconds.toFixed(1)}s`
      const mins = Math.floor(seconds / 60)
      const secs = Math.round(seconds % 60)
      return `${mins}m ${secs}s`
    },
    formatTimestamp(timestamp) {
      if (!timestamp) return '—'
      try {
        const date = typeof timestamp === 'number' ? new Date(timestamp * 1000) : new Date(timestamp)
        if (isNaN(date.getTime())) return String(timestamp)
        return date.toLocaleString()
      } catch {
        return String(timestamp)
      }
    },
    directionBadge(direction) {
      if (direction === 'response') return 'badge-warning'
      if (direction === 'request') return 'badge-info'
      return 'badge-ghost'
    },
    toISODate(date) {
      return date.toISOString().split('T')[0]
    }
  },
  mounted() {
    // Default to the last 7 days so the view opens with useful data.
    const today = new Date()
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
    this.filters.startDate = this.toISODate(weekAgo)
    this.filters.endDate = this.toISODate(today)
    this.loadLogs()
  }
}
</script>
