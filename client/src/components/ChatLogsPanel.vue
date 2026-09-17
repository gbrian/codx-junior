<template>
  <div class="h-full flex flex-col gap-4 overflow-auto bg-base-100 p-4">
    <!-- Header -->
    <div class="flex items-center justify-between shrink-0">
      <h2 class="text-lg font-bold flex items-center gap-2">
        <i class="fa-solid fa-file-lines text-primary"></i>
        AI Logs
      </h2>
      <button 
        class="btn btn-sm btn-ghost"
        @click="refreshLogs"
        :class="isLoading ? 'loading' : ''"
        title="Refresh logs"
      >
        <i class="fa-solid fa-rotate-right"></i>
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="flex items-center justify-center py-8">
      <div class="loading loading-spinner loading-lg"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-error gap-3">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <div>
        <h3 class="font-bold">Failed to load logs</h3>
        <div class="text-sm">{{ error }}</div>
      </div>
      <button class="btn btn-sm" @click="refreshLogs">Retry</button>
    </div>

    <!-- Empty State -->
    <div v-else-if="!logs || !logs.total_log_records" class="flex flex-col items-center justify-center py-12 text-center">
      <i class="fa-solid fa-inbox text-4xl text-base-content/20 mb-3"></i>
      <p class="text-base-content/60">No AI logs found for this chat</p>
      <div v-if="logs?.fallback_used" class="text-xs text-base-content/40 mt-2">
        <i class="fa-solid fa-circle-info mr-1"></i>
        {{ logs.fallback_reason }}
      </div>
    </div>

    <!-- Logs Loaded -->
    <div v-else class="flex-1 overflow-y-auto space-y-4 min-h-0">
      <!-- Summary Stats Cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <!-- Total Records -->
        <div class="stats bg-base-200 shadow-sm">
          <div class="stat">
            <div class="stat-title text-xs">Total Records</div>
            <div class="stat-value text-2xl">{{ logs.total_log_records }}</div>
            <div class="stat-desc text-xs">
              <span class="badge badge-xs badge-info">{{ logs.total_requests }} req</span>
              <span class="badge badge-xs badge-success">{{ logs.total_responses }} res</span>
            </div>
          </div>
        </div>

        <!-- Duration -->
        <div class="stats bg-base-200 shadow-sm">
          <div class="stat">
            <div class="stat-title text-xs">Total Duration</div>
            <div class="stat-value text-2xl">{{ formatDuration(logs.total_duration_seconds) }}</div>
            <div v-if="logs.average_request_duration_seconds" class="stat-desc text-xs">
              Avg: {{ formatDuration(logs.average_request_duration_seconds) }}/req
            </div>
          </div>
        </div>

        <!-- Token Stats -->
        <div class="stats bg-base-200 shadow-sm">
          <div class="stat">
            <div class="stat-title text-xs">Est. Tokens</div>
            <div class="stat-value text-2xl">{{ formatNumber(logs.token_stats.total_estimated_tokens) }}</div>
            <div class="stat-desc text-xs">
              <span class="text-info">↓{{ formatNumber(logs.token_stats.total_estimated_input_tokens) }}</span>
              <span class="text-success">↑{{ formatNumber(logs.token_stats.total_estimated_output_tokens) }}</span>
            </div>
          </div>
        </div>

        <!-- Status -->
        <div class="stats bg-base-200 shadow-sm" :class="logs.has_errors ? 'bg-error/10' : ''">
          <div class="stat">
            <div class="stat-title text-xs">Status</div>
            <div class="stat-value text-2xl">
              <span v-if="!logs.has_errors" class="text-success">✓</span>
              <span v-else class="text-error">⚠</span>
            </div>
            <div class="stat-desc text-xs">
              <span class="badge badge-xs" 
                :class="logs.status_distribution.success > 0 ? 'badge-success' : 'badge-ghost'"
              >{{ logs.status_distribution.success }} ok</span>
              <span v-if="logs.status_distribution.error > 0" class="badge badge-xs badge-error">
                {{ logs.status_distribution.error }} err
              </span>
              <span v-if="logs.status_distribution.cancelled > 0" class="badge badge-xs badge-warning">
                {{ logs.status_distribution.cancelled }} cancel
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Status Distribution -->
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body gap-3">
          <h3 class="card-title text-sm">Status Distribution</h3>
          <div class="flex items-end justify-around gap-2 h-24">
            <div class="flex flex-col items-center gap-2 flex-1">
              <div class="h-full bg-success rounded-t-md transition-all" 
                :style="{ height: getStatusBarHeight('success') }"
                :title="`Success: ${logs.status_distribution.success}`"
              ></div>
              <div class="text-xs font-semibold">✓ Success</div>
              <div class="text-xs text-base-content/60">{{ logs.status_distribution.success }}</div>
            </div>
            <div class="flex flex-col items-center gap-2 flex-1">
              <div class="h-full bg-error rounded-t-md transition-all" 
                :style="{ height: getStatusBarHeight('error') }"
                :title="`Error: ${logs.status_distribution.error}`"
              ></div>
              <div class="text-xs font-semibold">✕ Error</div>
              <div class="text-xs text-base-content/60">{{ logs.status_distribution.error }}</div>
            </div>
            <div class="flex flex-col items-center gap-2 flex-1">
              <div class="h-full bg-warning rounded-t-md transition-all" 
                :style="{ height: getStatusBarHeight('cancelled') }"
                :title="`Cancelled: ${logs.status_distribution.cancelled}`"
              ></div>
              <div class="text-xs font-semibold">⊗ Cancelled</div>
              <div class="text-xs text-base-content/60">{{ logs.status_distribution.cancelled }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Model Usage -->
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body gap-3">
          <h3 class="card-title text-sm">Model Usage</h3>
          <div class="space-y-2">
            <div v-for="model in logs.model_usage" :key="`${model.model}-${model.provider}`"
              class="flex items-center justify-between gap-2 p-2 bg-base-100 rounded-lg"
            >
              <div class="flex-1 min-w-0">
                <div class="text-sm font-semibold truncate">{{ model.model }}</div>
                <div class="text-xs text-base-content/60 truncate">{{ model.provider }}</div>
              </div>
              <div class="text-right shrink-0">
                <div class="text-sm font-bold">{{ model.request_count }}</div>
                <div class="text-xs text-base-content/60">{{ formatDuration(model.total_duration_seconds) }}</div>
              </div>
            </div>
            <div v-if="!logs.model_usage || logs.model_usage.length === 0" class="text-xs text-base-content/40 text-center py-3">
              No model usage data
            </div>
          </div>
        </div>
      </div>

      <!-- Token Breakdown -->
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body gap-3">
          <h3 class="card-title text-sm">Token Breakdown</h3>
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs badge badge-info">Input</span>
                <span class="text-sm">Estimated input tokens</span>
              </div>
              <span class="font-bold text-info">{{ formatNumber(logs.token_stats.total_estimated_input_tokens) }}</span>
            </div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs badge badge-success">Output</span>
                <span class="text-sm">Estimated output tokens</span>
              </div>
              <span class="font-bold text-success">{{ formatNumber(logs.token_stats.total_estimated_output_tokens) }}</span>
            </div>
            <div class="divider my-1"></div>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-xs badge badge-primary">Total</span>
                <span class="text-sm font-semibold">Total estimated tokens</span>
              </div>
              <span class="font-bold text-lg text-primary">{{ formatNumber(logs.token_stats.total_estimated_tokens) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Error Details -->
      <div v-if="logs.has_errors && logs.error_details.length > 0" class="card bg-error/10 border border-error shadow-sm">
        <div class="card-body gap-3">
          <h3 class="card-title text-sm text-error flex items-center gap-2">
            <i class="fa-solid fa-triangle-exclamation"></i>
            Error Details
          </h3>
          <div class="space-y-2">
            <div v-for="(error, idx) in logs.error_details" :key="idx"
              class="text-xs bg-base-100 p-2 rounded border-l-2 border-error text-base-content/80"
            >
              {{ error }}
            </div>
          </div>
        </div>
      </div>

      <!-- Timestamp Info -->
      <div class="card bg-base-200 shadow-sm">
        <div class="card-body gap-3">
          <h3 class="card-title text-sm">Timeline</h3>
          <div class="space-y-2 text-sm">
            <div v-if="logs.first_timestamp" class="flex items-center justify-between">
              <span class="text-base-content/60">First log:</span>
              <span class="font-mono text-xs">{{ formatTimestamp(logs.first_timestamp) }}</span>
            </div>
            <div v-if="logs.last_timestamp" class="flex items-center justify-between">
              <span class="text-base-content/60">Last log:</span>
              <span class="font-mono text-xs">{{ formatTimestamp(logs.last_timestamp) }}</span>
            </div>
            <div v-if="logs.session_id" class="flex items-start justify-between">
              <span class="text-base-content/60">Session ID:</span>
              <span class="font-mono text-xs truncate break-all text-right">{{ logs.session_id }}</span>
            </div>
            <div v-if="logs.fallback_used" class="flex items-start gap-2 py-2 px-3 bg-warning/10 border border-warning/30 rounded">
              <i class="fa-solid fa-circle-info text-warning text-xs mt-0.5 shrink-0"></i>
              <div class="text-xs text-base-content/80">
                <strong>Fallback lookup used:</strong> {{ logs.fallback_reason }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chatId: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      logs: null,
      isLoading: false,
      error: null
    }
  },
  computed: {
    totalStatuses() {
      if (!this.logs) return 1
      return Math.max(
        this.logs.status_distribution.success,
        this.logs.status_distribution.error,
        this.logs.status_distribution.cancelled,
        1
      )
    }
  },
  methods: {
    async loadLogs() {
      this.isLoading = true
      this.error = null
      try {
        this.logs = await this.$storex.api.chats.getChatLogs({ id: this.chatId })
      } catch (err) {
        this.error = err.message || 'Failed to load chat logs'
        console.error('Error loading chat logs:', err)
      } finally {
        this.isLoading = false
      }
    },
    async refreshLogs() {
      await this.loadLogs()
    },
    formatDuration(seconds) {
      if (!seconds) return '0s'
      if (seconds < 1) return `${Math.round(seconds * 1000)}ms`
      if (seconds < 60) return `${seconds.toFixed(1)}s`
      const mins = Math.floor(seconds / 60)
      const secs = (seconds % 60).toFixed(0)
      return `${mins}m ${secs}s`
    },
    formatNumber(num) {
      if (!num) return '0'
      return num.toLocaleString()
    },
    formatTimestamp(timestamp) {
      try {
        const date = new Date(timestamp)
        return date.toLocaleString()
      } catch {
        return timestamp
      }
    },
    getStatusBarHeight(status) {
      const dist = this.logs.status_distribution
      const value = dist[status] || 0
      const height = (value / this.totalStatuses) * 100
      return `${Math.max(height, 5)}%`
    }
  },
  mounted() {
    this.loadLogs()
  }
}
</script>

<style scoped>
.stats {
  display: flex;
  flex-direction: column;
  padding: 0.75rem;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-title {
  font-size: 0.75rem;
  opacity: 0.6;
  font-weight: 500;
}

.stat-value {
  font-weight: bold;
  line-height: 1;
}

.stat-desc {
  display: flex;
  gap: 0.25rem;
  margin-top: 0.25rem;
}
</style>