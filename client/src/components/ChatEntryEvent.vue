<script setup>
import moment from 'moment'
</script>

<template>
  <div v-if="lifecycleEvent" :class="[
    'lifecycle-event',
    compact ? 'compact-layout' : 'expanded-layout'
  ]">
    <!-- Compact: timeline-friendly layout -->
    <div v-if="compact" class="flex items-start gap-2 text-xs">
      <i :class="statusIcon" class="text-sm mt-0.5 flex-shrink-0"></i>
      <div class="flex-1 min-w-0">
        <div class="font-semibold text-base-content">
          {{ getEventLabel() }}
        </div>
        <p class="text-base-content/60 text-[10px]">
          {{ formatTimestamp(lifecycleEvent.created_at || lifecycleEvent.timestamp) }}
        </p>
      </div>
      <span class="badge badge-xs flex-shrink-0" :class="statusBadgeClass">
        {{ lifecycleEvent.status }}
      </span>
      <span v-if="lifecycleEvent.duration_ms" class="text-base-content/60 text-[10px] flex-shrink-0">
        {{ (lifecycleEvent.duration_ms / 1000).toFixed(2) }}s
      </span>
    </div>

    <!-- Expanded: full card layout -->
    <div v-if="!compact" class="rounded-lg border border-base-300 bg-base-100 p-3 space-y-3">
      <!-- Header -->
      <div class="flex items-start justify-between gap-2">
        <div class="flex items-start gap-2 flex-1">
          <i :class="statusIcon" class="text-lg mt-0.5 flex-shrink-0"></i>
          <div class="flex-1 min-w-0">
            <h4 class="font-semibold text-sm text-base-content">
              {{ getEventLabel() }}
            </h4>
            <p class="text-xs text-base-content/60 mt-0.5">
              {{ formatTimestamp(lifecycleEvent.created_at || lifecycleEvent.timestamp) }}
            </p>
          </div>
        </div>
        <span class="badge" :class="statusBadgeClass">
          {{ lifecycleEvent.status }}
        </span>
      </div>

      <!-- Run ID -->
      <div v-if="lifecycleEvent.run_id" class="bg-base-200 rounded p-2">
        <p class="text-[10px] text-base-content/60 mb-1">
          <i class="fa-solid fa-hashtag"></i> Run ID
        </p>
        <code class="text-xs font-mono text-primary">{{ lifecycleEvent.run_id }}</code>
      </div>

      <!-- Metrics -->
      <div v-if="hasMetrics" class="grid grid-cols-2 gap-2">
        <div v-if="lifecycleEvent.duration_ms" class="bg-base-200 rounded p-2">
          <p class="text-[10px] text-base-content/60">
            <i class="fa-solid fa-hourglass-end"></i> Duration
          </p>
          <p class="text-sm font-semibold">{{ (lifecycleEvent.duration_ms / 1000).toFixed(2) }}s</p>
        </div>
        <div v-if="lifecycleEvent.error" class="bg-error/10 rounded p-2 border border-error/20">
          <p class="text-[10px] text-error font-semibold">
            <i class="fa-solid fa-circle-exclamation"></i> Error
          </p>
          <p class="text-xs text-error/80 truncate">{{ lifecycleEvent.error }}</p>
        </div>
      </div>

      <!-- Analytics (if available) -->
      <div v-if="lifecycleEvent.analytics && Object.keys(lifecycleEvent.analytics).length > 0" class="border-t border-base-300 pt-2">
        <p class="text-xs font-semibold mb-2 text-base-content/70">
          <i class="fa-solid fa-chart-pie"></i> Analytics
        </p>
        <div class="space-y-1 text-xs">
          <div v-for="(value, key) in lifecycleEvent.analytics" :key="key" class="flex justify-between text-base-content/60">
            <span>{{ formatKey(key) }}:</span>
            <span class="font-mono text-base-content">{{ formatValue(value) }}</span>
          </div>
        </div>
      </div>

      <!-- Error details (if error status) -->
      <div v-if="lifecycleEvent.status === 'error' && lifecycleEvent.error" class="bg-error/5 border border-error/20 rounded p-2">
        <p class="text-xs font-semibold text-error mb-1">
          <i class="fa-solid fa-triangle-exclamation"></i> Error Details
        </p>
        <pre class="text-[10px] text-error whitespace-pre-wrap break-words overflow-auto max-h-32">{{ lifecycleEvent.error }}</pre>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    lifecycleEvent: {
      type: Object,
      required: false,
      default: null
    },
    compact: {
      type: Boolean,
      default: false
    }
  },
  computed: {
    statusIcon() {
      switch (this.lifecycleEvent?.status) {
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
      switch (this.lifecycleEvent?.status) {
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
      return this.lifecycleEvent?.duration_ms || this.lifecycleEvent?.error
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
      if (!this.lifecycleEvent) return 'Event'
      
      const status = this.lifecycleEvent.status
      const runId = this.lifecycleEvent.run_id?.slice(0, 8) || 'run'
      
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