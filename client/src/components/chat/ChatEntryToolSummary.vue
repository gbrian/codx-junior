<template>
  <!-- ── Tool summary strip ──
       THE always-visible trace of what the assistant executed: one line with the
       LAST execution (status · tool · argument · duration) and the run totals.
       It answers "what is it doing / what did it just do?" without a click, and it
       is the trigger of the full wall below (same `show-events` event as the
       header wrench, so both share the parent's state).
       Container queries (`/panel`, set by the chat panel) drop the argument and
       then the timings as the panel narrows: the tool name is the last thing to
       go, never the status, because the status is the whole point. -->
  <div
    class="flex items-stretch w-full min-w-0 overflow-hidden rounded-lg border transition-colors duration-150"
    :class="stripClass"
  >
    <!-- Main line — status + last tool + argument + totals -->
    <button
      type="button"
      class="flex items-center gap-2 min-w-0 flex-1 px-2 py-1 text-left"
      :title="summaryTip"
      :aria-expanded="eventsOpen ? 'true' : 'false'"
      :aria-controls="panelId"
      @click.stop="$emit('toggle')"
    >
      <!-- Status: icon + color + tooltip text, never color alone -->
      <span class="w-3.5 flex justify-center shrink-0">
        <span v-if="isRunning" class="loading loading-spinner loading-xs text-info"></span>
        <i v-else-if="isFailed" class="fa-solid fa-circle-xmark text-error text-xs"></i>
        <i v-else-if="isCompleted" class="fa-solid fa-circle-check text-success text-xs"></i>
        <i v-else class="fa-solid fa-circle text-base-content/30 text-xs"></i>
      </span>

      <span
        class="font-mono text-xs font-semibold truncate shrink-0 max-w-[45%]"
        :class="isFailed ? 'text-error' : 'text-base-content'"
      >{{ toolName }}</span>

      <span
        v-if="argumentPreview"
        class="hidden @sm/panel:inline font-mono text-[11px] text-base-content/40 truncate min-w-0"
      >{{ argumentPreview }}</span>

      <span class="grow"></span>

      <span
        v-if="lastDuration"
        class="hidden @lg/panel:inline text-[10px] text-base-content/40 tabular-nums shrink-0"
      >{{ lastDuration }}</span>

      <span
        v-if="totalsText"
        class="hidden @lg/panel:inline text-[11px] text-base-content/40 tabular-nums shrink-0"
      >{{ totalsText }}</span>

      <span
        v-if="errorText"
        class="hidden @lg/panel:inline text-[11px] text-error tabular-nums shrink-0"
      >{{ errorText }}</span>

      <i
        class="fa-solid fa-chevron-down text-[10px] text-base-content/40 shrink-0 transition-transform duration-150"
        :class="eventsOpen && 'rotate-180'"
        aria-hidden="true"
      ></i>
    </button>

    <!-- Processing details (side drawer) — only while the wall is open, so the
         strip never shows a control that has nothing to open. -->
    <button
      v-if="eventsOpen"
      type="button"
      class="px-2 border-l border-base-content/10 text-base-content/50 hover:text-base-content hover:bg-base-content/10 transition-colors duration-150"
      :class="drawerOpen && 'text-warning bg-warning/15'"
      aria-label="Processing details"
      title="Processing details"
      @click.stop="$emit('show-events-drawer')"
    >
      <i class="fa-solid fa-ellipsis"></i>
    </button>
  </div>
</template>

<script>
export default {
  props: ['message', 'eventsOpen', 'drawerOpen', 'panelId'],
  emits: ['toggle', 'show-events-drawer'],
  data() {
    return {
      // Request keys that read better without the `key=` prefix
      preferredKeys: ['path', 'file', 'file_path', 'pattern', 'query', 'command', 'cmd', 'url']
    }
  },
  computed: {
    toolEvents() {
      return this.message?.tool_events || []
    },
    lastToolEvent() {
      return this.toolEvents[this.toolEvents.length - 1] || null
    },
    isStreaming() {
      return !this.message?.done
    },
    // Status of the LAST execution. A still-streaming message with no tool yet
    // reports `running` so the strip appears with the run itself.
    lastStatus() {
      if (this.lastToolEvent?.status) return this.lastToolEvent.status
      return this.isStreaming ? 'running' : null
    },
    isRunning() {
      return this.lastStatus === 'running'
    },
    isFailed() {
      return this.lastStatus === 'error'
    },
    isCompleted() {
      return this.lastStatus === 'done'
    },
    toolName() {
      if (this.lastToolEvent?.tool) return this.lastToolEvent.tool
      return this.isStreaming ? 'Starting…' : 'No tool ran'
    },
    toolErrorCount() {
      return this.toolEvents.filter(event => event.status === 'error').length
    },
    errorText() {
      if (!this.toolErrorCount) return ''
      return `${this.toolErrorCount} error${this.toolErrorCount > 1 ? 's' : ''}`
    },
    // Duration of the whole run: lifecycle events own it, the sum of the tool
    // durations is only a fallback for messages recorded without them.
    toolRunDuration() {
      const lifecycleEvents = this.message?.lifecycle_events || []
      const fromLifecycle = lifecycleEvents.reduce((total, event) => total + (event.duration_ms || 0), 0)
      if (fromLifecycle) return fromLifecycle
      return this.toolEvents.reduce((total, event) => total + (event.duration_ms || 0), 0)
    },
    totalsText() {
      const parts = []
      if (this.toolEvents.length) {
        parts.push(`${this.toolEvents.length} tool${this.toolEvents.length > 1 ? 's' : ''}`)
      }
      if (this.toolRunDuration) parts.push(this.formatDuration(this.toolRunDuration))
      return parts.join(' · ')
    },
    lastDuration() {
      return this.formatDuration(this.lastToolEvent?.duration_ms)
    },
    // One-line preview of the most meaningful request argument
    argumentPreview() {
      const request = this.toolRequest(this.lastToolEvent)
      if (!request) return ''
      const [key, value] = Object.entries(request)[0] || []
      if (!key) return ''
      const isSimple = value === null || ['string', 'number', 'boolean'].includes(typeof value)
      const text = isSimple ? String(value ?? '') : this.stringifyValue(value)
      return this.preferredKeys.includes(key) ? text : `${key}=${text}`
    },
    // Full state in words — the visual status is never the only channel
    summaryTip() {
      if (!this.lastToolEvent) {
        return this.isStreaming
          ? 'Waiting for the first tool'
          : 'No tool ran for this message'
      }
      const statusWords = { running: 'Running', done: 'Done', error: 'Failed' }
      const parts = [statusWords[this.lastToolEvent.status] || 'Unknown', this.lastToolEvent.tool]
      if (this.lastToolEvent.duration_ms != null) {
        parts.push(this.formatDuration(this.lastToolEvent.duration_ms))
      }
      if (this.toolErrorCount) parts.push(this.errorText)
      return parts.join(' · ')
    },
    stripClass() {
      if (this.eventsOpen) return 'border-primary/40 bg-primary/10 hover:bg-primary/15'
      if (this.isFailed) return 'border-error/40 bg-base-200/60 hover:bg-base-200'
      return 'border-base-content/10 bg-base-200/50 hover:border-base-content/20 hover:bg-base-200/70'
    }
  },
  methods: {
    formatDuration(ms) {
      if (ms == null) return ''
      if (ms < 1000) return Math.round(ms) + ' ms'
      return (ms / 1000).toFixed(2) + ' s'
    },
    // Requests arrive parsed (objects) or serialized (JSON strings)
    toolRequest(toolEvent) {
      const request = toolEvent?.request
      if (!request) return null
      if (typeof request === 'string') {
        try {
          return JSON.parse(request)
        } catch {
          return { input: request }
        }
      }
      return typeof request === 'object' ? request : { input: request }
    },
    stringifyValue(value) {
      try {
        return JSON.stringify(value)
      } catch {
        return String(value)
      }
    }
  }
}
</script>