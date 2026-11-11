<script setup>
/**
 * Timeline of one harness run: the durable `RunEvent` log written by the
 * runtime (`run_created`, `plan_updated`, `step_dispatched`, `step_finished`,
 * `report`, ...), newest first.
 *
 * The append-only audit journal of the whole project is shown by the view
 * itself (it also carries worker supervision events), so this component only
 * renders what belongs to the selected run.
 */
import { computed, ref } from 'vue'
import { formatTime, shortId } from './harnessStatus'

const props = defineProps({
  run: { type: Object, default: null }
})

const EVENT_CLASSES = {
  run_created: 'badge-info',
  run_started: 'badge-primary',
  plan_updated: 'badge-secondary',
  step_dispatched: 'badge-primary',
  step_started: 'badge-primary',
  step_finished: 'badge-success',
  step_retried: 'badge-warning',
  report: 'badge-success',
  completed: 'badge-success',
  failed: 'badge-error',
  stopped: 'badge-error',
  error: 'badge-error'
}

const showData = ref(false)

/** Newest first; the run keeps at most the last 200 events. */
const events = computed(() => {
  const list = props.run?.events || []
  return [...list].reverse()
})

function eventClass(type) {
  return EVENT_CLASSES[type] || 'badge-ghost'
}

/** Compact, human-readable detail of an event payload. */
function dataText(event) {
  const data = event?.data || {}
  const parts = Object.entries(data)
    .filter(([, value]) => value !== null && value !== undefined && value !== '')
    .map(([key, value]) => {
      const text = typeof value === 'object' ? JSON.stringify(value) : String(value)
      return `${key}=${text.length > 80 ? `${text.slice(0, 80)}…` : text}`
    })
  return parts.join(' · ')
}
</script>

<template>
  <div v-if="!run" class="text-sm text-base-content/50 bg-base-200 rounded-box p-4">
    Select a harness task to see its timeline.
  </div>

  <div v-else class="flex flex-col gap-2">
    <div class="flex items-center gap-2 text-xs text-base-content/60">
      <span class="badge badge-sm badge-ghost">run {{ shortId(run.run_id, 8) }}</span>
      <span>{{ events.length }} event(s)</span>
      <label class="ml-auto flex items-center gap-1 cursor-pointer">
        <input v-model="showData" type="checkbox" class="checkbox checkbox-xs" />
        show payload
      </label>
    </div>

    <div v-if="!events.length" class="text-sm text-base-content/50 bg-base-200 rounded-box p-4">
      No events recorded yet.
    </div>

    <div v-else class="flex flex-col gap-1 bg-base-200 rounded-box p-2 max-h-[32rem] overflow-y-auto">
      <div
        v-for="(event, index) in events"
        :key="`${event.at}-${index}`"
        class="flex items-start gap-2 text-sm px-2 py-1 rounded hover:bg-base-300"
      >
        <span class="badge badge-xs shrink-0 mt-0.5" :class="eventClass(event.type)">
          {{ event.type || 'event' }}
        </span>
        <span class="text-xs shrink-0 text-base-content/50 mt-0.5">{{ formatTime(event.at) }}</span>
        <div class="min-w-0">
          <div class="text-xs break-words">{{ event.message }}</div>
          <div
            v-if="showData && dataText(event)"
            class="font-mono text-[10px] text-base-content/40 break-all"
          >
            {{ dataText(event) }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
