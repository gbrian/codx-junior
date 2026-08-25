<script setup>
import Markdown from './Markdown.vue'
import moment from 'moment'
</script>

<template>
  <div v-if="toolEvent" class="border border-base-300 rounded-md p-3 bg-base-100 space-y-2">
    <!-- Header with tool name and status -->
    <div class="flex items-center justify-between gap-2">
      <div class="flex items-center gap-2">
        <i 
          :class="statusIcon" 
          class="text-lg"
        ></i>
        <span class="font-semibold text-sm">{{ toolEvent.tool }}</span>
        <span class="badge badge-xs" :class="statusBadgeClass">
          {{ toolEvent.status }}
        </span>
      </div>
      <span v-if="toolEvent.duration_ms !== null && toolEvent.duration_ms !== undefined" class="text-xs text-neutral-500">
        {{ (toolEvent.duration_ms / 1000).toFixed(2) }}s
      </span>
    </div>

    <!-- Request arguments -->
    <div v-if="toolEvent.request && Object.keys(toolEvent.request).length > 0" class="space-y-1">
      <p class="text-xs font-semibold text-neutral-600">Request</p>
      <pre class="bg-base-200 p-2 rounded text-xs overflow-auto max-h-40">{{ JSON.stringify(toolEvent.request, null, 2) }}</pre>
    </div>

    <!-- Response (for done status) -->
    <div v-if="toolEvent.status === 'done' && toolEvent.response" class="space-y-1">
      <p class="text-xs font-semibold text-neutral-600">Response</p>
      <div class="bg-success/5 border border-success/20 p-2 rounded text-xs overflow-auto max-h-40">
        <Markdown :text="toolEvent.response"></Markdown>
      </div>
    </div>

    <!-- Error (for error status) -->
    <div v-if="toolEvent.status === 'error' && toolEvent.error" class="space-y-1">
      <p class="text-xs font-semibold text-error">Error</p>
      <div class="bg-error/5 border border-error/20 p-2 rounded text-xs overflow-auto max-h-40">
        <pre>{{ toolEvent.error }}</pre>
      </div>
    </div>

    <!-- Loading indicator -->
    <div v-if="toolEvent.status === 'running'" class="flex items-center gap-2">
      <span class="loading loading-spinner loading-xs"></span>
      <span class="text-xs text-neutral-500">Processing tool call...</span>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    toolEvent: {
      type: Object,
      default: null
    }
  },
  computed: {
    statusIcon() {
      switch (this.toolEvent?.status) {
        case 'running':
          return 'fa-solid fa-spinner fa-spin text-info'
        case 'done':
          return 'fa-solid fa-check-circle text-success'
        case 'error':
          return 'fa-solid fa-exclamation-circle text-error'
        default:
          return 'fa-solid fa-wrench text-neutral-400'
      }
    },
    statusBadgeClass() {
      switch (this.toolEvent?.status) {
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
  }
}
</script>