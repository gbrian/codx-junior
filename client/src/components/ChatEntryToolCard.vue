<script setup>
import Markdown from './Markdown.vue'
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
          <i class="fa-solid fa-wrench"></i> {{ event.data.tool }}
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
      <!-- Duration -->
      <div v-if="event.data.duration_ms" class="bg-base-200 rounded p-2">
        <p class="text-[10px] text-base-content/60 mb-1">
          <i class="fa-solid fa-hourglass-end"></i> Duration
        </p>
        <p class="text-sm font-semibold">{{ (event.data.duration_ms / 1000).toFixed(2) }}s</p>
      </div>

      <!-- Request info -->
      <div v-if="event.data.request" class="bg-info/10 border border-info/20 rounded p-2">
        <details class="group cursor-pointer">
          <summary class="text-xs font-semibold text-info hover:text-info/80 select-none flex items-center gap-1">
            <i class="fa-solid fa-chevron-right group-open:fa-chevron-down text-[10px]"></i>
            <i class="fa-solid fa-arrow-up"></i> Request ({{ getRequestSize() }})
          </summary>
          <pre class="bg-base-200 p-2 rounded text-xs overflow-auto max-h-32 mt-2 text-base-content/70">{{ JSON.stringify(event.data.request, null, 2) }}</pre>
        </details>
      </div>

      <!-- Response -->
      <div v-if="event.data.status === 'done' && event.data.response" class="bg-success/10 border border-success/20 rounded p-2">
        <details class="group cursor-pointer">
          <summary class="text-xs font-semibold text-success hover:text-success/80 select-none flex items-center gap-1">
            <i class="fa-solid fa-chevron-right group-open:fa-chevron-down text-[10px]"></i>
            <i class="fa-solid fa-arrow-down"></i> Response ({{ getResponseSize() }})
          </summary>
          <div class="bg-base-100 p-2 rounded text-xs overflow-auto max-h-32 mt-2">
            <Markdown :text="event.data.response"></Markdown>
          </div>
        </details>
      </div>

      <!-- Error block -->
      <div v-if="event.data.status === 'error' && event.data.error" class="bg-error/5 border border-error/20 rounded p-2">
        <p class="text-xs font-semibold text-error mb-1">
          <i class="fa-solid fa-circle-exclamation"></i> Error
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
          return 'fa-solid fa-spinner fa-spin text-info'
        case 'done':
          return 'fa-solid fa-check-circle text-success'
        case 'error':
          return 'fa-solid fa-exclamation-circle text-error'
        default:
          return 'fa-solid fa-wrench text-base-content/40'
      }
    },
    statusBadgeClass() {
      const status = this.event.data.status
      switch (status) {
        case 'running':
          return 'badge-info'
        case 'done':
          return 'badge-success'
        case 'error':
          return 'badge-error'
        default:
          return 'badge-ghost'
      }
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
    getRequestSize() {
      const size = JSON.stringify(this.event.data.request || {}).length
      return this.formatBytes(size)
    },
    getResponseSize() {
      const size = (this.event.data.response || '').length
      return this.formatBytes(size)
    },
    formatBytes(bytes) {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return Math.round(bytes / Math.pow(k, i) * 10) / 10 + ' ' + sizes[i]
    }
  }
}
</script>