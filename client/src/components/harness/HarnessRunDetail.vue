<script setup>
/**
 * Diagnosis of one harness task: header (status, budget, worker, controls) and
 * four tabs — the flow of the plan, every associated task card, the run
 * timeline and the last delivery/stop report.
 *
 * Everything comes from `GET /api/orchestration/{run_id}`, which is the source
 * of truth of a run: plan, step results, next action and worker presence.
 */
import { computed, ref, watch } from 'vue'
import HarnessStepFlow from './HarnessStepFlow.vue'
import HarnessTaskTable from './HarnessTaskTable.vue'
import HarnessTimeline from './HarnessTimeline.vue'
import {
  TERMINAL_RUN_STATUSES,
  formatTime,
  runMeta,
  shortId
} from './harnessStatus'

const props = defineProps({
  run: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['open-chat', 'refresh', 'control'])

const TABS = [
  { id: 'flow', label: 'Flow', icon: 'fa-solid fa-diagram-project' },
  { id: 'tasks', label: 'Tasks', icon: 'fa-solid fa-list-check' },
  { id: 'timeline', label: 'Timeline', icon: 'fa-solid fa-clock-rotate-left' },
  { id: 'report', label: 'Report', icon: 'fa-solid fa-file-lines' }
]

const STARTABLE = ['paused', 'stalled', 'queued', 'stopped', 'failed']
const PAUSABLE = ['running', 'queued']

const tab = ref('flow')

// A different task always opens on its flow.
watch(() => props.run?.run_id, () => { tab.value = 'flow' })

const meta = computed(() => runMeta(props.run?.status))
const counts = computed(() => props.run?.counts || {})
const progress = computed(() => Math.max(0, Math.min(100, Math.round(Number(props.run?.progress || 0)))))
const workerPresent = computed(() => props.run?.worker?.present !== false)
const budgetLabel = computed(() => {
  const budget = Number(props.run?.budget_cxjcoins || 0)
  const spent = Number(props.run?.spent_cxjcoins || 0)
  if (budget > 0) return `${spent.toFixed(2)} / ${budget.toFixed(2)} cxjcoins`
  return spent > 0 ? `${spent.toFixed(2)} cxjcoins spent` : 'no budget'
})
const canStart = computed(() => !!props.run && STARTABLE.includes(props.run.status))
const canPause = computed(() => !!props.run && PAUSABLE.includes(props.run.status))
const canStop = computed(() => !!props.run && !TERMINAL_RUN_STATUSES.includes(props.run.status))

function control(action) {
  if (!props.run) return
  emit('control', { action, runId: props.run.run_id })
}
</script>

<template>
  <section class="flex flex-col gap-3 min-w-0">
    <div v-if="error" class="alert alert-error text-sm">
      <i class="fa-solid fa-triangle-exclamation"></i>
      {{ error }}
    </div>

    <div v-if="!run" class="flex flex-col items-center gap-2 py-12 text-base-content/40">
      <i class="fa-solid fa-bolt text-4xl"></i>
      <span class="text-sm">Select a harness task on the left to diagnose it.</span>
    </div>

    <template v-else>
      <!-- Header -->
      <header class="rounded-box bg-base-200 p-3 flex flex-col gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <span class="badge badge-sm gap-1" :class="meta.badge">
            <i :class="meta.icon"></i>
            {{ meta.label }}
          </span>
          <h2 class="font-semibold text-base truncate" :title="run.name">{{ run.name || 'Harness task' }}</h2>
          <code class="text-[11px] text-base-content/40" :title="run.run_id">{{ shortId(run.run_id, 8) }}</code>
          <span
            v-if="!workerPresent"
            class="badge badge-sm badge-warning gap-1"
            title="No background worker is running for this project: the run cannot advance."
          >
            <i class="fa-solid fa-triangle-exclamation"></i>
            worker off
          </span>
          <button class="btn btn-xs btn-ghost ml-auto" :disabled="loading" @click="emit('refresh')">
            <i class="fa-solid fa-rotate" :class="{ 'animate-spin': loading }"></i>
            Refresh
          </button>
          <button
            v-if="canStart"
            class="btn btn-xs btn-primary"
            :disabled="busy"
            title="Start / resume / reopen the run"
            @click="control('start')"
          >
            <i class="fa-solid fa-play"></i> Start
          </button>
          <button
            v-if="canPause"
            class="btn btn-xs btn-warning btn-outline"
            :disabled="busy"
            title="The in-flight turn finishes, then the worker stops advancing"
            @click="control('pause')"
          >
            <i class="fa-solid fa-pause"></i> Pause
          </button>
          <button
            v-if="canStop"
            class="btn btn-xs btn-error btn-outline"
            :disabled="busy"
            title="Stop the run and cancel its in-flight turns"
            @click="control('stop')"
          >
            <i class="fa-solid fa-stop"></i> Stop
          </button>
        </div>

        <p v-if="run.objective" class="text-xs text-base-content/70 line-clamp-3" :title="run.objective">
          {{ run.objective }}
        </p>

        <div class="flex flex-wrap items-center gap-3 text-[11px] text-base-content/60">
          <span class="flex items-center gap-1 min-w-40">
            <progress class="progress progress-primary w-24 h-2" :value="progress" max="100"></progress>
            <span class="tabular-nums">{{ progress }}%</span>
          </span>
          <span class="tabular-nums" :title="'Steps done / total'">
            <i class="fa-solid fa-list-check"></i>
            {{ counts.done || 0 }}/{{ counts.total || 0 }}
            <span v-if="counts.failed" class="text-error">· {{ counts.failed }} failed</span>
            <span v-if="counts.blocked" class="text-warning">· {{ counts.blocked }} blocked</span>
            <span v-if="counts.running" class="text-primary">· {{ counts.running }} running</span>
            <span v-if="counts.pending" class="text-base-content/40">· {{ counts.pending }} pending</span>
          </span>
          <span><i class="fa-solid fa-coins"></i> {{ budgetLabel }}</span>
          <span v-if="run.rounds"><i class="fa-solid fa-repeat"></i> {{ run.rounds }} round(s)</span>
          <span v-if="run.config?.board"><i class="fa-solid fa-table-columns"></i> {{ run.config.board }}</span>
          <span v-if="run.config?.sprint"><i class="fa-solid fa-person-running"></i> {{ run.config.sprint }}</span>
          <span class="ml-auto">updated {{ formatTime(run.updated_at) }}</span>
        </div>

        <div
          v-if="run.last_error"
          class="alert alert-error alert-soft text-xs py-1.5 flex items-start gap-2"
        >
          <i class="fa-solid fa-circle-exclamation mt-0.5"></i>
          <span class="break-words">{{ run.last_error }}</span>
        </div>
      </header>

      <!-- Tabs -->
      <div role="tablist" class="tabs tabs-boxed tabs-xs w-fit">
        <button
          v-for="item in TABS"
          :key="item.id"
          role="tab"
          class="tab gap-1"
          :class="{ 'tab-active': tab === item.id }"
          @click="tab = item.id"
        >
          <i :class="item.icon"></i>
          {{ item.label }}
        </button>
      </div>

      <HarnessStepFlow v-if="tab === 'flow'" :run="run" @open-chat="emit('open-chat', $event)" />
      <HarnessTaskTable v-else-if="tab === 'tasks'" :run="run" @open-chat="emit('open-chat', $event)" />
      <HarnessTimeline v-else-if="tab === 'timeline'" :run="run" />
      <div v-else class="flex flex-col gap-2">
        <div v-if="run.stop_reason" class="text-xs text-base-content/60">
          stop reason: <span class="text-base-content">{{ run.stop_reason }}</span>
        </div>
        <pre
          v-if="run.last_report"
          class="bg-base-200 rounded-box p-3 text-xs whitespace-pre-wrap break-words max-h-[32rem] overflow-y-auto"
        >{{ run.last_report }}</pre>
        <div v-else class="text-sm text-base-content/50 bg-base-200 rounded-box p-4">
          No delivery report yet — it is published when the run completes, stops or exhausts its budget.
        </div>
      </div>
    </template>
  </section>
</template>
