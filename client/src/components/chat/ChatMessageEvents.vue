<script setup>
import Markdown from '../Markdown.vue'
</script>

<template>
  <div class="rounded-lg border border-base-300/70 bg-base-200/40 overflow-hidden">

    <!-- ── Summary strip ── -->
    <div class="flex items-center gap-2 px-3 py-1.5 text-[11px] text-base-content/60 bg-base-200/60">
      <i class="fa-solid fa-wrench text-info"></i>
      <span class="font-semibold tracking-wide uppercase">Tools &amp; Events</span>
      <span class="grow"></span>
      <span v-if="toolEvents.length" class="badge badge-xs badge-ghost gap-1">
        <i class="fa-solid fa-wrench text-[9px]"></i>{{ toolEvents.length }}
      </span>
      <span v-if="lifecycleEvents.length" class="badge badge-xs badge-ghost gap-1">
        <i class="fa-solid fa-play text-[9px]"></i>{{ lifecycleEvents.length }}
      </span>
    </div>

    <!-- ── Tool executions ── -->
    <ul v-if="toolEvents.length" class="divide-y divide-base-300/40">
      <li
        v-for="(toolEvent, index) in toolEvents"
        :key="toolEvent.tool_call_id || ('tool-' + index)"
        class="px-3 py-2"
      >
        <button
          class="w-full flex items-center gap-2 text-left"
          @click="toggleTool(index)"
        >
          <!-- Status indicator -->
          <span class="w-3.5 flex justify-center shrink-0">
            <span
              v-if="toolEvent.status === 'running'"
              class="loading loading-spinner loading-xs text-info"
            ></span>
            <i v-else-if="toolEvent.status === 'done'" class="fa-solid fa-circle-check text-success text-xs"></i>
            <i v-else-if="toolEvent.status === 'error'" class="fa-solid fa-circle-xmark text-error text-xs"></i>
            <i v-else class="fa-solid fa-circle text-base-content/30 text-xs"></i>
          </span>

          <span class="font-mono text-xs text-base-content truncate">{{ toolEvent.tool }}</span>

          <span class="badge badge-xs" :class="statusBadgeClass(toolEvent.status)">{{ toolEvent.status }}</span>

          <span v-if="toolEvent.duration_ms != null" class="text-[10px] text-base-content/40 tabular-nums">
            {{ formatDuration(toolEvent.duration_ms) }}
          </span>

          <span class="grow"></span>

          <i
            class="fa-solid fa-chevron-down text-[10px] text-base-content/40 transition-transform duration-150"
            :class="isToolOpen(index) && 'rotate-180'"
          ></i>
        </button>

        <!-- ── Tool details ── -->
        <div v-if="isToolOpen(index)" class="mt-2 pl-[22px] space-y-2">
          <!-- Arguments -->
          <div v-if="hasRequest(toolEvent)">
            <p class="text-[10px] uppercase tracking-wide text-base-content/40 mb-1">Arguments</p>
            <pre class="text-[11px] leading-snug bg-base-300/40 rounded-md p-2 overflow-auto max-h-40">{{ formatRequest(toolEvent.request) }}</pre>
          </div>

          <!-- Result preview -->
          <div v-if="toolEvent.response">
            <p class="text-[10px] uppercase tracking-wide text-base-content/40 mb-1">Result</p>
            <pre class="text-[11px] leading-snug bg-base-300/40 rounded-md p-2 overflow-auto max-h-40">{{ toolEvent.response }}</pre>
          </div>

          <!-- Error -->
          <div v-if="toolEvent.error" class="alert alert-error text-xs py-1.5 px-3">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span>{{ toolEvent.error }}</span>
          </div>

          <!-- User-facing output (kept OUT of the message body — opt-in) -->
          <div v-if="toolEvent.output">
            <button class="btn btn-xs btn-ghost gap-1" @click="toggleOutput(index)">
              <i class="fa-solid fa-eye"></i>
              {{ isOutputOpen(index) ? 'Hide output' : 'Show output' }}
            </button>
            <div
              v-if="isOutputOpen(index)"
              class="mt-1 rounded-md border border-base-300/50 bg-base-100/40 p-2 max-h-96 overflow-auto"
            >
              <Markdown :text="toolEvent.output"></Markdown>
            </div>
          </div>
        </div>
      </li>
    </ul>

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
</template>

<script>
export default {
  props: ['message'],
  data() {
    return {
      openTools: {},
      openOutputs: {}
    }
  },
  computed: {
    toolEvents() {
      return this.message?.tool_events || []
    },
    lifecycleEvents() {
      return this.message?.lifecycle_events || []
    }
  },
  methods: {
    statusBadgeClass(status) {
      if (status === 'running') return 'badge-info'
      if (status === 'done') return 'badge-success'
      if (status === 'error') return 'badge-error'
      return 'badge-ghost'
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