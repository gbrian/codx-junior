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
            Chat sessions & enriched analytics · {{ isAdminView ? 'Admin — all users' : 'Your logs' }}
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

    <!-- Session filter breadcrumb -->
    <div v-if="sessionIdFilter" class="alert alert-info mb-4 py-2">
      <i class="fa-solid fa-sitemap text-sm"></i>
      <span class="text-sm">
        Showing entries for <span class="font-mono font-bold">session_id: {{ sessionIdFilter }}</span>
      </span>
      <button class="btn btn-xs btn-ghost ml-auto" @click="clearSessionIdFilter">
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
        @navigate-session="onNavigateSession"
      />
    </div>

    <!-- Detail modal -->
    <LogEntryDetail
      v-if="selectedLog"
      :is-admin="isAdminView"
      :chat-session="selectedSession"
      :loading="detailLoading"
      @close="closeDetail"
      @navigate-parent="onNavigateParent"
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
      selectedSession: null,
      autoRefreshTimer: null,
      sessionIdFilter: null,
      filters: {
        startDate: today,
        endDate: today,
        projectName: '',
        username: '',
        autoRefresh: null,
      }
    }
  },
  computed: {
    isAdminView() {
      return !!this.$storex.users.isAdmin
    },
    availableModels() {
      return [...new Set(this.logs.map(s => s.llm_model).filter(Boolean))].sort()
    },
    availableProviders() {
      // Extract provider from model name if present, or use 'unknown'
      return [...new Set(this.logs.map(s => {
        const model = s.llm_model || 'unknown'
        // Models typically follow pattern like "claude-haiku-4-5" or "gpt-4"
        // Extract provider from model name
        if (model.includes('claude')) return 'anthropic'
        if (model.includes('gpt')) return 'openai'
        if (model.includes('gemini')) return 'google'
        return 'unknown'
      }).filter(Boolean))].sort()
    }
  },

  watch: {
    'filters.autoRefresh'(val) { 
      this.setupAutoRefresh(val)
    }
  },

  methods: {
    async loadProfiles() {
      const chatprojects = [...new Set(this.logs.map(l => l.project_id))]
                            .map(project_id => this.$projects.allProjectsById[project_id])
      this.profiles = {}
      chatprojects.forEach(async project => {
        const projectProfiles = await this.$storex.profiles.loadProjectProfiles(project)
        projectProfiles.forEach(profile => {
          this.profiles[project.project_id] = {
            ...this.profiles[project.project_id],
            [profile.name]: profile
          }
        })
      })
    },

    onFilterChange() { this.page = 1; this.loadLogs() },

    clearFilters() {
      const today = new Date().toISOString().split('T')[0]
      const sevenDaysAgo = new Date(Date.now() - 7 * 86400_000).toISOString().split('T')[0]
      this.filters = {
        startDate: sevenDaysAgo,
        endDate: today,
        projectName: '',
        username: '',
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
        projectName: f.projectName || undefined,
        username: f.username || undefined,
      }
    },
    getLogProfiles({ project_id, profiles }) {
      project_id = project_id || this.$project.project_id
      const projectProfiles = this.profiles[project_id]
      return projectProfiles ? profiles.map(name => projectProfiles[name])
                .filter(p => !!p) : []
    },
    /**
     * Transform nested chat_session response into flat table format
     * Each response item has: { chat_session, metrics, llm_request_count, tool_call_count }
     */
    async transformSessions(rawSessions) {
      if (!rawSessions || !Array.isArray(rawSessions)) return []
      
      await this.loadProfiles()

      return rawSessions.map(item => {
        const cs = item.chat_session || {}
        const metrics = item.metrics || {}
        
        return {
          // Chat session fields
          chat_id: cs.chat_id,
          id: cs.chat_id, // Alias for table compatibility
          chat_name: cs.chat_name,
          username: cs.username,
          project_name: cs.project_name,
          project_id: cs.project_id || this.$project.project_id,
          mode: cs.mode,
          profiles: this.getLogProfiles(cs),
          files: cs.files || [],
          parent_chat_id: cs.parent_chat_id,
          iteration: cs.iteration,
          max_iterations: cs.max_iterations,
          llm_model: cs.llm_model,
          parent_request_id: cs.parent_request_id,
          session_id: cs.session_id,
          started_at: cs.started_at,
          ended_at: cs.ended_at,
          duration_seconds: cs.duration_seconds,
          input_message_count: cs.input_message_count,
          output_message_count: cs.output_message_count,
          cancelled: cs.cancelled,
          error: cs.error,
          timestamp: cs.timestamp,
          iso_date: cs.iso_date,
          
          // Metrics fields
          total_input_tokens: metrics.total_input_tokens,
          total_output_tokens: metrics.total_output_tokens,
          total_tokens: metrics.total_tokens,
          llm_calls: metrics.llm_calls,
          total_llm_duration_seconds: metrics.total_llm_duration_seconds,
          total_cxjcoins: metrics.total_cxjcoins,
          tool_calls: metrics.tool_calls,
          successful_tool_calls: metrics.successful_tool_calls,
          failed_tool_calls: metrics.failed_tool_calls,
          total_tool_duration_seconds: metrics.total_tool_duration_seconds,
          
          // Aggregated fields
          llm_request_count: item.llm_request_count,
          tool_call_count: item.tool_call_count,
          
          // For table display compatibility
          model: cs.llm_model,
          provider: this.extractProvider(cs.llm_model),
          direction: 'response', // Chat sessions are complete interactions
          payload_preview: cs.chat_name || '—',
        }
      })
    },

    /**
     * Extract provider from model name
     */
    extractProvider(model) {
      if (!model) return 'unknown'
      if (model.includes('claude')) return 'anthropic'
      if (model.includes('gpt')) return 'openai'
      if (model.includes('gemini')) return 'google'
      if (model.includes('llama')) return 'meta'
      return 'unknown'
    },

    async loadLogs() {
      this.loading = true
      this.error = null
      try {
        const params = this.buildParams()
        // Use chatSessions endpoint for both user and admin views
        const response = this.isAdminView
          ? await this.$project.$api.analytics.admin.chatSessions(params)
          : await this.$project.$api.analytics.chatSessions(params)
        
        // Transform nested response into flat format
        const transformed = await this.transformSessions(response)
        this.logs = transformed
        this.total = transformed.length
        this.hasMore = false
      } catch (err) {
        console.error('Failed to load chat sessions:', err)
        this.error = 'Failed to load chat sessions. Please try again.'
      } finally {
        this.loading = false
      }
    },

    async loadChatSession(chatId) {
      try {
        const params = {
          startDate: this.filters.startDate,
          endDate: this.filters.endDate,
        }
        return this.isAdminView
          ? await this.$project.$api.analytics.admin.chatSession(chatId, params)
          : await this.$project.$api.analytics.chatSession(chatId, params)
      } catch (err) {
        console.error('Failed to load chat session:', err)
        throw err
      }
    },

    async openDetail(log) {
      this.selectedLog = log
      this.selectedSession = null
      this.detailLoading = true
      try {
        const session = await this.loadChatSession(log.chat_id || log.id)
        this.selectedSession = session
      } catch (err) {
        console.error('Failed to load chat session detail:', err)
        this.error = 'Failed to load chat session detail.'
      } finally {
        this.detailLoading = false
      }
    },

    closeDetail() {
      this.selectedLog = null
      this.selectedSession = null
    },

    onNavigateParent(parentSessionId) {
      this.closeDetail()
      this.sessionIdFilter = parentSessionId
      this.page = 1
      this.loadLogs()
    },

    onNavigateSession(sessionId) {
      this.sessionIdFilter = sessionId
      this.page = 1
      this.loadLogs()
    },

    clearSessionIdFilter() {
      this.sessionIdFilter = null
      this.page = 1
      this.loadLogs()
    },
  },

  mounted() { this.loadLogs() },
  beforeUnmount() { if (this.autoRefreshTimer) clearInterval(this.autoRefreshTimer) }
}
</script>