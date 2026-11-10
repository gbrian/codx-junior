<script setup>
import Markdown from '../Markdown.vue'
</script>

<template>
  <!-- ── Floating tools panel ──
       Sticks right under the chat entry header (`top-[27px]`, which mirrors the
       header height: 24px row + pb-1.5 + border − mt-1 → 33px at @lg/panel), so
       the run detail stays visible while the message body scrolls.
       Opaque surface + shadow: it must not let content show through while stuck.
       The one-line run summary lives OUTSIDE this panel (see
       <ChatEntryToolSummary>), so the wall starts directly with the executions
       and no line is spent twice on the same information. -->
  <div
    :id="panelId"
    class="sticky top-[27px] @lg/panel:top-[33px] z-10 flex flex-col max-h-[60vh] rounded-lg border border-base-300/70 bg-base-100 shadow-sm overflow-hidden"
  >

    <!-- Scrollable wall: a long run never outgrows the viewport -->
    <div class="min-h-0 overflow-y-auto">

      <!-- ── Tool executions (wall) ──
           Each execution is one row of a continuous feed: status accent on the
           left, tool identity on the first line and its arguments underneath, so
           the run can be followed without opening any row. -->
      <div v-if="toolEvents.length" class="divide-y divide-base-300/40">
        <div
          v-for="tool in tools"
          :key="tool.event.tool_call_id || ('tool-' + tool.index)"
          class="px-2.5 py-1.5 border-l-2 transition-colors duration-150 hover:bg-base-200/60"
          :class="accentClass(tool.event.status)"
        >
          <!-- Headline: which tool ran and how it went.
               No status badge: the icon (spinner / check / cross) plus the left
               accent already tell the outcome; the status word lives in the
               tooltip so the state is never conveyed by color alone. -->
          <button
            class="w-full flex items-center gap-2 text-left min-w-0"
            :aria-expanded="isToolOpen(tool.index) ? 'true' : 'false'"
            :title="(isToolOpen(tool.index) ? 'Hide details' : 'Show details') + ' · ' + (tool.event.status || 'unknown')"
            @click="toggleTool(tool.index)"
          >
            <span class="w-4 shrink-0 text-right text-[10px] tabular-nums text-base-content/30">{{ tool.index + 1 }}</span>

            <!-- Status indicator -->
            <span class="w-3.5 flex justify-center shrink-0">
              <span
                v-if="tool.event.status === 'running'"
                class="loading loading-spinner loading-xs text-info"
              ></span>
              <i v-else-if="tool.event.status === 'done'" class="fa-solid fa-circle-check text-success text-xs"></i>
              <i v-else-if="tool.event.status === 'error'" class="fa-solid fa-circle-xmark text-error text-xs"></i>
              <i v-else class="fa-solid fa-circle text-base-content/30 text-xs"></i>
            </span>

            <span class="font-mono text-xs font-semibold text-base-content truncate">{{ tool.event.tool }}</span>

            <span v-if="tool.event.duration_ms != null" class="text-[10px] text-base-content/40 tabular-nums shrink-0">
              {{ formatDuration(tool.event.duration_ms) }}
            </span>

            <span v-if="tool.time" class="hidden @lg/panel:inline text-[10px] text-base-content/30 tabular-nums shrink-0">
              {{ tool.time }}
            </span>

            <span class="grow"></span>

            <span v-if="tool.args.length" class="text-[10px] text-base-content/30 tabular-nums shrink-0">
              {{ tool.args.length }} args
            </span>

            <i
              class="fa-solid fa-chevron-down text-[10px] text-base-content/40 shrink-0 transition-transform duration-150"
              :class="isToolOpen(tool.index) && 'rotate-180'"
            ></i>
          </button>

          <!-- Arguments at a glance — the params are part of the summary -->
          <div
            v-if="tool.visibleArgs.length"
            class="mt-1 ml-[26px] grid grid-cols-[minmax(4.5rem,7rem)_1fr] gap-x-3 gap-y-0.5 items-baseline"
          >
            <template v-for="arg in tool.visibleArgs" :key="arg.key">
              <span class="text-[10px] font-medium uppercase tracking-wide text-base-content/40 truncate" :title="arg.key">
                {{ arg.key }}
              </span>
              <span class="font-mono text-[11px] text-base-content/60 truncate" :title="arg.full">
                {{ arg.display }}
              </span>
            </template>
          </div>
          <p v-if="tool.hiddenArgs" class="mt-0.5 ml-[26px] text-[10px] text-base-content/30">
            +{{ tool.hiddenArgs }} more argument{{ tool.hiddenArgs > 1 ? 's' : '' }}
          </p>

          <!-- Errors belong to the summary: no need to expand to know what failed -->
          <div
            v-if="tool.event.status === 'error' && tool.event.error"
            class="mt-1 ml-[26px] flex items-start gap-1 text-[11px] text-error"
          >
            <i class="fa-solid fa-triangle-exclamation text-[10px] mt-0.5 shrink-0"></i>
            <span class="line-clamp-2 break-all" :title="tool.event.error">{{ tool.event.error }}</span>
          </div>

          <!-- ── Tool details ── -->
          <div v-if="isToolOpen(tool.index)" class="mt-2 pl-[26px] space-y-2">
            <!-- Arguments -->
            <div v-if="hasRequest(tool.event)">
              <p class="text-[10px] uppercase tracking-wide text-base-content/40 mb-1">Arguments</p>
              <pre class="text-[11px] leading-snug bg-base-300/40 rounded-md p-2 overflow-auto max-h-40">{{ formatRequest(tool.event.request) }}</pre>
            </div>

            <!-- Result preview -->
            <div v-if="tool.event.response">
              <p class="text-[10px] uppercase tracking-wide text-base-content/40 mb-1">Result</p>
              <pre class="text-[11px] leading-snug bg-base-300/40 rounded-md p-2 overflow-auto max-h-40">{{ tool.event.response }}</pre>
            </div>

            <!-- Error -->
            <div v-if="tool.event.error" class="alert alert-error text-xs py-1.5 px-3">
              <i class="fa-solid fa-triangle-exclamation"></i>
              <span>{{ tool.event.error }}</span>
            </div>

            <!-- User-facing output (kept OUT of the message body — opt-in) -->
            <div v-if="tool.event.output">
              <button class="btn btn-xs btn-ghost gap-1" @click="toggleOutput(tool.index)">
                <i class="fa-solid fa-eye"></i>
                {{ isOutputOpen(tool.index) ? 'Hide output' : 'Show output' }}
              </button>
              <div
                v-if="isOutputOpen(tool.index)"
                class="mt-1 rounded-md border border-base-300/50 bg-base-100/40 p-2 max-h-96 overflow-auto"
              >
                <Markdown :text="tool.event.output"></Markdown>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ── Run lifecycle ── -->
      <ul v-if="lifecycleEvents.length" class="divide-y divide-base-300/40 border-t border-base-300/40">
        <li
          v-for="(runEvent, index) in lifecycleEvents"
          :key="runEvent.run_id || ('run-' + index)"
          class="px-3 py-1.5 flex items-center gap-2 text-[11px]"
        >
          <i class="fa-solid fa-circle-play text-info text-[10px] shrink-0"></i>
          <span class="font-mono text-base-content/50 truncate">{{ shortRunId(runEvent.run_id) }}</span>
          <span class="badge badge-xs" :class="statusBadgeClass(runEvent.status)">{{ runEvent.status }}</span>
          <span v-if="runEvent.duration_ms != null" class="text-[10px] text-base-content/40 tabular-nums">
            {{ formatDuration(runEvent.duration_ms) }}
          </span>
          <span v-if="runEvent.error" class="text-error truncate">{{ runEvent.error }}</span>
        </li>
      </ul>

      <!-- ── Empty state ── -->
      <div v-if="!toolEvents.length && !lifecycleEvents.length" class="px-3 py-2 text-[11px] text-base-content/40">
        No events recorded for this message.
      </div>
    </div>
  </div>
</template>

<script>
export default {
  // `panelId` is the id the tool summary strip points at with aria-controls
  props: ['message', 'panelId'],
  data() {
    return {
      openTools: {},
      openOutputs: {},
      // Arguments rendered in the summary row before the "+N more" hint
      maxSummaryArgs: 3
    }
  },
  computed: {
    toolEvents() {
      return this.message?.tool_events || []
    },
    lifecycleEvents() {
      return this.message?.lifecycle_events || []
    },
    // Rows of the wall, resolved once per render (index, args, time)
    tools() {
      return this.toolEvents.map((event, index) => {
        const args = this.toolArgs(event)
        return {
          index,
          event,
          args,
          visibleArgs: args.slice(0, this.maxSummaryArgs),
          hiddenArgs: Math.max(args.length - this.maxSummaryArgs, 0),
          time: this.eventTime(event)
        }
      })
    }
  },
  methods: {
    statusBadgeClass(status) {
      if (status === 'running') return 'badge-info'
      if (status === 'done') return 'badge-success'
      if (status === 'error') return 'badge-error'
      return 'badge-ghost'
    },
    // Left accent of a wall row — always paired with the status icon, never alone
    accentClass(status) {
      if (status === 'running') return 'border-info/60'
      if (status === 'done') return 'border-success/50'
      if (status === 'error') return 'border-error/70'
      return 'border-base-content/15'
    },
    formatDuration(ms) {
      if (ms == null) return ''
      if (ms < 1000) return Math.round(ms) + ' ms'
      return (ms / 1000).toFixed(2) + ' s'
    },
    formatRequest(request) {
      if (!request || Object.keys(request).length === 0) return '{}'
      try {
        return JSON.stringify(request, null, 2)
      } catch {
        return String(request)
      }
    },
    hasRequest(toolEvent) {
      return toolEvent.request && Object.keys(toolEvent.request).length > 0
    },
    shortRunId(runId) {
      return runId ? String(runId).slice(0, 8) : '—'
    },
    // Tool arguments as flat { key, full, display } entries for the summary grid
    toolArgs(toolEvent) {
      const request = this.toolRequest(toolEvent)
      if (!request) return []
      return Object.entries(request).map(([key, value]) => {
        const isSimple = value === null || ['string', 'number', 'boolean'].includes(typeof value)
        const full = isSimple ? String(value) : this.stringifyValue(value)
        return { key, full, display: this.truncateValue(full) }
      })
    },
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
    truncateValue(value) {
      const text = String(value ?? '').replace(/\s+/g, ' ').trim()
      return text.length > 72 ? text.slice(0, 71) + '…' : text
    },
    stringifyValue(value) {
      try {
        return JSON.stringify(value)
      } catch {
        return String(value)
      }
    },
    // Wall rows show the wall-clock time of the execution when the backend provides it
    eventTime(event) {
      const timestamp = event?.started_at || event?.created_at || event?.timestamp
      if (!timestamp) return null
      const date = new Date(timestamp)
      if (isNaN(date.getTime())) return null
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    },
    isToolOpen(index) {
      return !!this.openTools[index]
    },
    toggleTool(index) {
      this.openTools[index] = !this.openTools[index]
    },
    isOutputOpen(index) {
      return !!this.openOutputs[index]
    },
    toggleOutput(index) {
      this.openOutputs[index] = !this.openOutputs[index]
    }
  }
}
</script>