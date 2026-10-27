<script setup>
import Markdown from './Markdown.vue'
import moment from 'moment'
</script>

<template>
  <div v-if="toolEvent" :class="[
    'tool-event-container',
    compact ? 'compact-mode' : 'expanded-mode'
  ]">
    <!-- Wall summary: tool, status and arguments visible at a glance -->
    <div
      class="border-l-2 bg-base-200/40 rounded-r-md px-2.5 py-2 transition-colors duration-150 hover:bg-base-200/60"
      :class="wallAccentClass"
    >
      <!-- Header row -->
      <div class="flex items-center gap-2 min-w-0">
        <i :class="statusIcon" class="text-sm shrink-0"></i>
        <span class="font-semibold text-xs font-mono text-base-content truncate">
          {{ toolEvent.tool }}
        </span>
        <span class="badge badge-xs shrink-0" :class="statusBadgeClass">
          {{ toolEvent.status }}
        </span>
        <span v-if="durationLabel" class="text-[10px] tabular-nums text-base-content/50 shrink-0">
          {{ durationLabel }}
        </span>
        <span v-if="argCount" class="badge badge-xs badge-ghost gap-1 shrink-0" title="Arguments">
          <i class="fa-solid fa-arrow-right-to-bracket text-[9px]"></i>
          <span class="tabular-nums">{{ argCount }}</span>
        </span>
        <button
          v-if="compact"
          @click="detailsOpen = !detailsOpen"
          class="ml-auto btn btn-xs btn-ghost shrink-0 px-1"
          :aria-expanded="detailsOpen ? 'true' : 'false'"
          :title="detailsOpen ? 'Hide tool details' : 'Show tool details'"
        >
          <i :class="detailsOpen ? 'fa-chevron-down' : 'fa-chevron-right'" class="fa-solid text-[10px]"></i>
        </button>
      </div>

      <!-- Arguments wall -->
      <div
        v-if="visibleArgs.length"
        class="mt-1.5 grid grid-cols-[minmax(4.5rem,8rem)_1fr] gap-x-3 gap-y-0.5 items-baseline"
      >
        <template v-for="arg in visibleArgs" :key="arg.key">
          <span class="text-[10px] font-medium uppercase tracking-wide text-base-content/40 truncate" :title="arg.key">
            {{ arg.key }}
          </span>
          <span class="font-mono text-[11px] text-base-content/70 truncate" :title="arg.full">
            {{ arg.value }}
          </span>
        </template>
      </div>

      <!-- Remaining arguments -->
      <button
        v-if="hiddenArgsCount"
        @click="argsOpen = !argsOpen"
        class="mt-1 btn btn-xs btn-ghost h-5 min-h-0 px-1 gap-1 text-[10px] text-base-content/50"
        :aria-expanded="argsOpen ? 'true' : 'false'"
      >
        <i :class="argsOpen ? 'fa-chevron-up' : 'fa-chevron-down'" class="fa-solid text-[9px]"></i>
        {{ argsOpen ? 'show less' : `+${hiddenArgsCount} more` }}
      </button>

      <!-- Error always visible in the summary -->
      <div v-if="toolEvent.status === 'error' && toolEvent.error" class="mt-1 flex items-start gap-1 text-[11px] text-error">
        <i class="fa-solid fa-circle-exclamation text-[10px] mt-0.5 shrink-0"></i>
        <span class="line-clamp-2 break-all" :title="toolEvent.error">{{ toolEvent.error }}</span>
      </div>
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
      detailsOpen: false,
      argsOpen: false,
      maxVisibleArgs: 3
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
    },
    wallAccentClass() {
      switch (this.toolEvent?.status) {
        case 'running': return 'border-info'
        case 'done': return 'border-success'
        case 'error': return 'border-error'
        default: return 'border-base-content/20'
      }
    },
    durationLabel() {
      const ms = this.toolEvent?.duration_ms
      if (!ms) return null
      return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(2)}s`
    },
    requestObject() {
      const request = this.toolEvent?.request
      if (!request) return null
      if (typeof request === 'string') {
        try {
          return JSON.parse(request)
        } catch (err) {
          return { input: request }
        }
      }
      return request
    },
    requestArgs() {
      const request = this.requestObject
      if (!request || typeof request !== 'object') return []
      return Object.entries(request).map(([key, value]) => {
        const isSimple = value === null || ['string', 'number', 'boolean'].includes(typeof value)
        const full = isSimple ? String(value) : this.stringifyValue(value)
        return { key, full, value: this.truncateValue(full), simple: isSimple }
      })
    },
    argCount() {
      return this.requestArgs.length
    },
    visibleArgs() {
      return this.argsOpen ? this.requestArgs : this.requestArgs.slice(0, this.maxVisibleArgs)
    },
    hiddenArgsCount() {
      return Math.max(this.requestArgs.length - this.maxVisibleArgs, 0)
    }
  },
  methods: {
    truncateValue(value) {
      const text = String(value ?? '').replace(/\s+/g, ' ').trim()
      return text.length > 60 ? `${text.slice(0, 59)}…` : text
    },
    stringifyValue(value) {
      try {
        return JSON.stringify(value)
      } catch (err) {
        return String(value)
      }
    }
  }
}
</script>