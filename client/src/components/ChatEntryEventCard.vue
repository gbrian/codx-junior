<script setup>
import moment from 'moment'
</script>

<template>
  <div class="rounded-lg border border-base-300 bg-base-100 overflow-hidden hover:bg-base-200/50 transition-colors">
    <!-- Card header (always visible) -->
    <button 
      @click="$emit('toggle')"
      class="w-full text-left px-3 py-2 flex items-center gap-2 hover:bg-base-200"
    >
      <i :class="statusIcon" class="text-lg flex-shrink-0"></i>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-semibold text-base-content truncate">
          {{ getEventLabel() }}
        </p>
        <p class="text-xs text-base-content/60">
          {{ formatTimestamp(event.data.created_at || event.data.timestamp) }}
        </p>
      </div>
      <div class="flex items-center gap-1 flex-shrink-0">
        <span class="badge badge-xs" :class="statusBadgeClass">
          {{ event.data.status }}
        </span>
        <i :class="isExpanded ? 'fa-chevron-up' : 'fa-chevron-down'" class="fa-solid text-xs text-base-content/50"></i>
      </div>
    </button>

    <!-- Expanded content (always visible by default) -->
    <div v-if="isExpanded" class="px-3 py-2 border-t border-base-300 bg-base-100 space-y-3">
      <!-- Run ID -->
      <div v-if="event.data.run_id" class="bg-base-200 rounded p-2">
        <p class="text-[10px] text-base-content/60 mb-1">
          <i class="fa-solid fa-hashtag"></i> Run ID
        </p>
        <code class="text-xs font-mono text-primary break-all">{{ event.data.run_id }}</code>
      </div>

      <!-- Metrics grid -->
      <div v-if="hasMetrics" class="grid grid-cols-2 gap-2">
        <div v-if="event.data.duration_ms" class="bg-base-200 rounded p-2">
          <p class="text-[10px] text-base-content/60">
            <i class="fa-solid fa-hourglass-end"></i> Duration
          </p>
          <p class="text-sm font-semibold">{{ (event.data.duration_ms / 1000).toFixed(2) }}s</p>
        </div>
        <div v-if="event.data.error" class="bg-error/10 rounded p-2 border border-error/20">
          <p class="text-[10px] text-error font-semibold">
            <i class="fa-solid fa-circle-exclamation"></i> Status
          </p>
          <p class="text-xs text-error/80">Error</p>
        </div>
      </div>

      <!-- Analytics -->
      <div v-if="event.data.analytics && Object.keys(event.data.analytics).length > 0" class="border-t border-base-300 pt-2">
        <p class="text-xs font-semibold mb-2 text-base-content/70">
          <i class="fa-solid fa-chart-pie"></i> Analytics
        </p>
        <div class="space-y-1 text-xs">
          <div v-for="(value, key) in event.data.analytics" :key="key" class="flex justify-between text-base-content/60">
            <span>{{ formatKey(key) }}:</span>
            <span class="font-mono text-base-content">{{ formatValue(value) }}</span>
          </div>
        </div>
      </div>

      <!-- Error details -->
      <div v-if="event.data.status === 'error' && event.data.error" class="bg-error/5 border border-error/20 rounded p-2">
        <p class="text-xs font-semibold text-error mb-1">
          <i class="fa-solid fa-triangle-exclamation"></i> Error Details
        </p>
        <pre class="text-[10px] text-error whitespace-pre-wrap break-words overflow-auto max-h-24">{{ event.data.error }}</pre>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    event: {
      type: Object,
      required: true
    },
    isExpanded: {
      type: Boolean,
      default: true
    }
  },
  emits: ['toggle'],
  computed: {
    statusIcon() {
      const status = this.event.data.status
      switch (status) {
        case 'running':
          return 'fa-solid fa-circle-notch fa-spin text-info'
        case 'done':
        case 'completed':
          return 'fa-solid fa-circle-check text-success'
        case 'error':
          return 'fa-solid fa-circle-xmark text-error'
        case 'cancelled':
          return 'fa-solid fa-ban text-warning'
        default:
          return 'fa-solid fa-circle-dot text-base-content/40'
      }
    },
    statusBadgeClass() {
      const status = this.event.data.status
      switch (status) {
        case 'running':
          return 'badge-info'
        case 'done':
        case 'completed':
          return 'badge-success'
        case 'error':
          return 'badge-error'
        case 'cancelled':
          return 'badge-warning'
        default:
          return 'badge-ghost'
      }
    },
    hasMetrics() {
      return this.event.data.duration_ms || this.event.data.error
    }
  },
  methods: {
    formatTimestamp(timestamp) {
      if (!timestamp) return 'N/A'
      try {
        return moment(timestamp).format('HH:mm:ss')
      } catch {
        return String(timestamp).slice(0, 8)
      }
    },
    formatKey(key) {
      return key
        .replace(/_/g, ' ')
        .replace(/([A-Z])/g, ' $1')
        .toLowerCase()
        .trim()
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ')
    },
    formatValue(value) {
      if (typeof value === 'number') {
        return value.toLocaleString()
      }
      if (typeof value === 'boolean') {
        return value ? '✓' : '✗'
      }
      return String(value).slice(0, 50)
    },
    getEventLabel() {
      if (!this.event.data) return 'Event'
      
      const status = this.event.data.status
      const runId = this.event.data.run_id?.slice(0, 8) || 'run'
      
      switch (status) {
        case 'running':
          return `Execution Running (${runId})`
        case 'done':
        case 'completed':
          return `Execution Completed (${runId})`
        case 'error':
          return `Execution Failed (${runId})`
        case 'cancelled':
          return `Execution Cancelled (${runId})`
        default:
          return `Execution (${runId})`
      }
    }
  }
}
</script>