<script setup>
import Markdown from './Markdown.vue'
import moment from 'moment'
</script>

<template>
  <div v-if="toolEvent" :class="[
    'tool-event-container',
    compact ? 'compact-mode' : 'expanded-mode'
  ]">
    <!-- Compact: one-liner with expandable detail -->
    <div v-if="compact" class="flex items-center gap-2 text-xs">
      <i :class="statusIcon" class="text-sm"></i>
      <span class="font-semibold text-base-content">{{ toolEvent.tool }}</span>
      <span class="badge badge-xs" :class="statusBadgeClass">
        {{ toolEvent.status }}
      </span>
      <span v-if="toolEvent.duration_ms" class="text-base-content/60">
        {{ (toolEvent.duration_ms / 1000).toFixed(2) }}s
      </span>
      <button 
        @click="detailsOpen = !detailsOpen"
        class="ml-auto btn btn-xs btn-ghost"
      >
        <i :class="detailsOpen ? 'fa-chevron-down' : 'fa-chevron-right'" class="fa-solid text-[10px]"></i>
      </button>
    </div>

    <!-- Expanded details (show when detailsOpen or not compact) -->
    <div v-if="!compact || detailsOpen" class="space-y-2 mt-2">
      <!-- Request args (collapsible) -->
      <details class="group cursor-pointer">
        <summary class="text-xs font-semibold text-base-content/70 hover:text-base-content">
          Request Arguments
        </summary>
        <pre v-if="toolEvent.request" class="bg-base-200 p-2 rounded text-xs overflow-auto max-h-32 mt-1">
{{ JSON.stringify(toolEvent.request, null, 2) }}
        </pre>
      </details>

      <!-- Response preview -->
      <div v-if="toolEvent.status === 'done' && toolEvent.response" class="space-y-1">
        <p class="text-xs font-semibold text-success">Response</p>
        <div class="bg-success/5 border border-success/20 p-2 rounded text-xs overflow-auto max-h-24">
          <Markdown :text="toolEvent.response"></Markdown>
        </div>
      </div>

      <!-- Error block -->
      <div v-if="toolEvent.status === 'error' && toolEvent.error" class="space-y-1">
        <p class="text-xs font-semibold text-error">Error</p>
        <pre class="bg-error/5 border border-error/20 p-2 rounded text-xs text-error whitespace-pre-wrap break-all">
{{ toolEvent.error }}
        </pre>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    toolEvent: Object,
    compact: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      detailsOpen: false
    }
  },
  computed: {
    statusIcon() {
      switch (this.toolEvent?.status) {
        case 'running': return 'fa-solid fa-spinner fa-spin text-info'
        case 'done': return 'fa-solid fa-check-circle text-success'
        case 'error': return 'fa-solid fa-exclamation-circle text-error'
        default: return 'fa-solid fa-wrench text-base-content/40'
      }
    },
    statusBadgeClass() {
      switch (this.toolEvent?.status) {
        case 'running': return 'badge-info'
        case 'done': return 'badge-success'
        case 'error': return 'badge-error'
        default: return 'badge-ghost'
      }
    }
  }
}
</script>
