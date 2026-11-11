<script setup>
/**
 * Left pane of the harness diagnostic view: every harness task (an
 * orchestration run) of the project, searchable and filterable by status.
 *
 * Selecting a row emits `select` with the run id; the detail pane is owned by
 * the view, so the list stays a dumb, cheap component.
 */
import { computed, ref } from 'vue'
import { formatTime, runMeta } from './harnessStatus'

const props = defineProps({
  runs: { type: Array, default: () => [] },
  selectedRunId: { type: String, default: '' },
  loading: { type: Boolean, default: false }
})

const emit = defineEmits(['select', 'refresh'])

const STATUS_OPTIONS = [
  '',
  'running',
  'queued',
  'paused',
  'stalled',
  'completed',
  'failed',
  'stopped',
  'budget_exhausted'
]

const search = ref('')
const statusFilter = ref('')

const filtered = computed(() => {
  const term = search.value.trim().toLowerCase()
  return (props.runs || []).filter(run => {
    if (statusFilter.value && run.status !== statusFilter.value) return false
    if (!term) return true
    const haystack = `${run.name || ''} ${run.objective || ''} ${run.run_id || ''}`.toLowerCase()
    return haystack.includes(term)
  })
})

/** Number of plan steps (0 for a run whose plan is not written yet). */
function totalSteps(run) {
  return Number(run?.counts?.total || 0)
}

/** Number of steps already finished (done + skipped). */
function finishedSteps(run) {
  return Number(run?.counts?.done || 0) + Number(run?.counts?.skipped || 0)
}
</script>

<template>
  <section class="flex flex-col gap-2 min-h-0">
    <div class="flex items-center justify-between gap-2">
      <h2 class="font-semibold text-sm uppercase tracking-wide text-base-content/60">
        Harness tasks
        <span class="normal-case font-normal">({{ filtered.length }}<span v-if="filtered.length !== runs.length">/{{ runs.length }}</span>)</span>
      </h2>
      <button class="btn btn-xs btn-ghost" :disabled="loading" title="Refresh" @click="emit('refresh')">
        <i class="fa-solid fa-rotate" :class="{ 'animate-spin': loading }"></i>
      </button>
    </div>

    <div class="flex flex-col gap-1">
      <input
        v-model="search"
        type="search"
        class="input input-bordered input-xs w-full"
        placeholder="Search a task by name, objective or id…"
      />
      <select v-model="statusFilter" class="select select-bordered select-xs w-full">
        <option v-for="option in STATUS_OPTIONS" :key="option || 'all'" :value="option">
          {{ option ? runMeta(option).label : 'All statuses' }}
        </option>
      </select>
    </div>

    <div v-if="!filtered.length" class="text-sm text-base-content/50 bg-base-200 rounded-box p-3">
      <template v-if="runs.length">No run matches the filter.</template>
      <template v-else>
        No runs yet. Mention <code class="kbd kbd-xs">@codx-junior</code> in a chat and give it a task —
        every run and step will show up here.
      </template>
    </div>

    <ul v-else class="flex flex-col gap-1 overflow-y-auto max-h-[60vh] pr-1">
      <li v-for="run in filtered" :key="run.run_id">
        <button
          class="w-full text-left rounded-box border p-2 flex flex-col gap-1 transition-colors"
          :class="run.run_id === selectedRunId
            ? 'border-primary bg-primary/10'
            : 'border-base-300 bg-base-200 hover:bg-base-300'"
          @click="emit('select', run.run_id)"
        >
          <div class="flex items-center gap-1.5 min-w-0">
            <i :class="[runMeta(run.status).icon, runMeta(run.status).color]" class="text-xs shrink-0"></i>
            <span class="font-medium text-sm truncate" :title="run.name">{{ run.name || run.run_id }}</span>
            <span class="badge badge-xs shrink-0" :class="runMeta(run.status).badge">
              {{ runMeta(run.status).label }}
            </span>
          </div>
          <div v-if="run.objective" class="text-[11px] text-base-content/60 truncate" :title="run.objective">
            {{ run.objective }}
          </div>
          <div class="flex items-center gap-2 text-[11px] text-base-content/50">
            <progress class="progress progress-primary w-16 h-1.5" :value="run.progress || 0" max="100"></progress>
            <span class="tabular-nums">{{ run.progress || 0 }}%</span>
            <span v-if="totalSteps(run)" class="tabular-nums" :title="`${finishedSteps(run)} of ${totalSteps(run)} steps finished`">
              · {{ finishedSteps(run) }}/{{ totalSteps(run) }} steps
            </span>
            <span class="ml-auto truncate">{{ formatTime(run.updated_at) }}</span>
          </div>
        </button>
      </li>
    </ul>
  </section>
</template>
