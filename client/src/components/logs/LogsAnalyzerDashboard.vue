<script setup>
import LogsLiveMetrics from './LogsLiveMetrics.vue'
import LogsFilterBar from './LogsFilterBar.vue'
import LogsTable from './LogsTable.vue'
import LogsAnalytics from './LogsAnalytics.vue'
import LogEntryDetail from './LogEntryDetail.vue'
</script>

<template>
  <div class="logs-analyzer bg-base-200 p-4 h-full overflow-auto">

    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
      <div class="flex items-center gap-3">
        <i class="fa-solid fa-magnifying-glass-chart text-primary text-3xl"></i>
        <div>
          <h1 class="text-2xl font-bold text-base-content">Chat Logs Analyzer</h1>
          <p class="text-xs text-base-content/50">
            Raw AI JSONL logs · {{ isAdminView ? 'Admin — all users' : 'Your logs' }}
          </p>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-2">

        <div class="join">
          <button class="join-item btn btn-sm" :class="viewMode === 'table' ? 'btn-primary' : 'btn-ghost'" @click="viewMode = 'table'">
            <i class="fa-solid fa-table-list"></i>
          </button>
          <button class="join-item btn btn-sm" :class="viewMode === 'analytics' ? 'btn-primary' : 'btn-ghost'" @click="viewMode = 'analytics'">
            <i class="fa-solid fa-chart-pie"></i>
          </button>
          <button class="join-item btn btn-sm" :class="viewMode === 'both' ? 'btn-primary' : 'btn-ghost'" @click="viewMode = 'both'">
            <i class="fa-solid fa-layer-group"></i>
          </button>
        </div>

        <div v-if="filters.autoRefresh" class="badge badge-success gap-1 animate-pulse">
          <i class="fa-solid fa-clock text-xs"></i>
          Live {{ filters.autoRefresh }}s
        </div>

        <button class="btn btn-sm btn-primary" @click="loadLogs" :disabled="loading">
          <i class="fa-solid fa-rotate-right" :class="{ 'animate-spin': loading }"></i>
          Refresh
        </button>
      </div>
    </div>

    <!-- Filter bar -->
    <div class="mb-6">
      <LogsFilterBar
        v-model="filters"
        :is-admin="isAdminView"
        :models="availableModels"
        :providers="availableProviders"
        @change="onFilterChange"
        @clear="clearFilters"
      />
    </div>

    <!-- Live metrics strip -->
    <div class="mb-6">
      <LogsLiveMetrics :logs="logs" :total="total" />
    </div>

    <!-- Request trace breadcrumb -->
    <div v-if="requestIdFilter" class="alert alert-info mb-4 py-2">
      <i class="fa-solid fa-sitemap text-sm"></i>
      <span class="text-sm">
        Showing entries for <span class="font-mono font-bold">request_id: {{ requestIdFilter }}</span>
      </span>
      <button class="btn btn-xs btn-ghost ml-auto" @click="clearRequestIdFilter">
        <i class="fa-solid fa-xmark"></i> Clear
      </button>
    </div>

    <!-- Error alert -->
    <div v-if="error" class="alert alert-error mb-4">
      <i class="fa-solid fa-circle-exclamation"></i>
      <span>{{ error }}</span>
      <button class="btn btn-sm btn-ghost" @click="error = null">Dismiss</button>
    </div>

    <!-- Analytics view -->
    <div v-if="viewMode === 'analytics' || viewMode === 'both'" class="mb-6">
      <LogsAnalytics :logs="logs" />
    </div>

    <!-- Table view -->
    <div v-if="viewMode === 'table' || viewMode === 'both'">
      <LogsTable
        :logs="logs"
        :total="total"
        :page="page"
        :page-size="pageSize"
        :has-more="hasMore"
        :loading="loading"
        @select="openDetail"
        @page="goToPage"
        @page-size="onPageSizeChange"
        @navigate-request="onNavigateRequest"
      />
    </div>

    <!-- Detail modal -->
    <LogEntryDetail
      v-if="selectedLog"
      :request-entry="detailRequest"
      :response-entry="detailResponse"
      :loading="detailLoading"
      @close="closeDetail"
      @navigate-parent="onNavigateParent"
      @find-pair="onFindPair"
      @open-entry="onOpenPairedEntry"
    />
  </div>
</template>

<script>
export default {
  name: 'LogsAnalyzerDashboard',
  data() {
    const today = new Date().toISOString().split('T')[0]
    const sevenDaysAgo = new Date(Date.now() - 7 * 86400_000).toISOString().split('T')[0]
    return {
      loading: false,
      detailLoading: false,
      error: null,
      viewMode: 'table',
      logs: [],
      total: 0,
      page: 1,
      pageSize: 50,
      hasMore: false,
      selectedLog: null,
      detailRequest: null,
      detailResponse: null,
      autoRefreshTimer: null,
      requestIdFilter: null,
      filters: {
        startDate: sevenDaysAgo,
        endDate: today,
        direction: '',
        model: '',
        provider: '',
        sessionId: '',
        tags: '',
        username: '',
        project: '',
        autoRefresh: null,
      }
    }
  },

  computed: {
    // Auto-detect admin mode from store — no manual toggle needed
    isAdminView() {
      return !!this.$storex.users.isAdmin
    },
    availableModels() {
      return [...new Set(this.logs.map(l => l.model).filter(Boolean))].sort()
    },
    availableProviders() {
      return [...new Set(this.logs.map(l => l.provider).filter(Boolean))].sort()
    }
  },

  watch: {
    'filters.autoRefresh'(val) { this.setupAutoRefresh(val) }
  },

  methods: {
    onFilterChange() { this.page = 1; this.loadLogs() },

    clearFilters() {
      const today = new Date().toISOString().split('T')[0]
      const sevenDaysAgo = new Date(Date.now() - 7 * 86400_000).toISOString().split('T')[0]
      this.filters = {
        startDate: sevenDaysAgo, endDate: today,
        direction: '', model: '', provider: '', sessionId: '',
        tags: '', username: '', project: '',
        autoRefresh: this.filters.autoRefresh,
      }
      this.page = 1
      this.loadLogs()
    },

    goToPage(p) { this.page = p; this.loadLogs() },
    onPageSizeChange(size) { this.pageSize = size; this.page = 1; this.loadLogs() },

    setupAutoRefresh(intervalSecs) {
      if (this.autoRefreshTimer) { clearInterval(this.autoRefreshTimer); this.autoRefreshTimer = null }
      if (!intervalSecs) return
      this.autoRefreshTimer = setInterval(() => this.loadLogs(), intervalSecs * 1000)
    },

    buildParams() {
      const f = this.filters
      return {
        startDate: f.startDate,
        endDate: f.endDate,
        direction: f.direction || undefined,
        model: f.model || undefined,
        provider: f.provider || undefined,
        sessionId: f.sessionId || undefined,
        project: f.project || undefined,
        requestId: this.requestIdFilter || undefined,
        page: this.page,
        pageSize: this.pageSize,
      }
    },

    async loadLogs() {
      this.loading = true
      this.error = null
      try {
        const params = this.buildParams()
        // Admins use the admin endpoint which returns logs for all users
        const result = this.isAdminView
          ? await this.$project.$api.logs.ai.admin.list({ ...params, username: this.filters.username || undefined })
          : await this.$project.$api.logs.ai.list(params)
        this.logs = result?.items || []
        this.total = result?.total || 0
        this.hasMore = result?.has_more || false
      } catch (err) {
        console.error('Failed to load logs:', err)
        this.error = 'Failed to load log entries. Please try again.'
      } finally {
        this.loading = false
      }
    },

    async fetchFull(logId) {
      return this.isAdminView
        ? await this.$project.$api.logs.ai.admin.get(logId)
        : await this.$project.$api.logs.ai.get(logId)
    },

    async fetchByRequestId(requestId) {
      const result = this.isAdminView
        ? await this.$project.$api.logs.ai.admin.list({ requestId, pageSize: 10 })
        : await this.$project.$api.logs.ai.list({ requestId, pageSize: 10 })
      return result?.items || []
    },

    async openDetail(log) {
      this.selectedLog = log
      this.detailRequest = null
      this.detailResponse = null
      this.detailLoading = true
      try {
        const full = await this.fetchFull(log.log_id)
        if (!full?.request_id) {
          this.assignEntry(full)
          return
        }
        const siblings = await this.fetchByRequestId(full.request_id)
        await this.resolveRequestResponse(full, siblings)
      } catch (err) {
        console.error('Failed to load log detail:', err)
        this.error = 'Failed to load log detail.'
      } finally {
        this.detailLoading = false
      }
    },

    assignEntry(entry) {
      if (entry?.direction === 'request') {
        this.detailRequest = entry
      } else {
        this.detailResponse = entry
      }
    },

    async resolveRequestResponse(full, siblings) {
      const siblingMeta = siblings.find(s => s.log_id !== full.log_id)
      this.assignEntry(full)
      if (!siblingMeta) return
      try {
        const siblingFull = await this.fetchFull(siblingMeta.log_id)
        this.assignEntry(siblingFull)
      } catch (err) {
        console.error('Failed to fetch sibling:', err)
        this.assignEntry(siblingMeta)
      }
    },

    closeDetail() {
      this.selectedLog = null
      this.detailRequest = null
      this.detailResponse = null
    },

    onNavigateParent(parentRequestId) {
      this.closeDetail()
      this.requestIdFilter = parentRequestId
      this.page = 1
      this.loadLogs()
    },

    onNavigateRequest(requestId) {
      this.requestIdFilter = requestId
      this.page = 1
      this.loadLogs()
    },

    onFindPair(requestId) {
      this.closeDetail()
      this.requestIdFilter = requestId
      this.page = 1
      this.loadLogs()
    },

    clearRequestIdFilter() {
      this.requestIdFilter = null
      this.page = 1
      this.loadLogs()
    },

    onOpenPairedEntry(entry) {
      this.openDetail(entry)
    },
  },

  mounted() { this.loadLogs() },
  beforeUnmount() { if (this.autoRefreshTimer) clearInterval(this.autoRefreshTimer) }
}
</script>