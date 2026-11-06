<script setup>
/**
 * Long-running task (orchestration run) strip shown by ChatView.
 *
 * `chat.run_id` is the run's process id. The bar renders the live status
 * pushed by the `codx-junior-orchestration` socket event and is the single
 * place where the user can start, pause and stop the process.
 */
</script>

<template>
  <div
    v-if="visible"
    class="flex flex-wrap items-center gap-2 rounded-xl border px-3 py-2 text-sm shadow-sm"
    :class="containerClass"
  >
    <!-- Status -->
    <span class="badge badge-sm gap-1.5 shrink-0" :class="statusBadgeClass">
      <i :class="statusIcon"></i>
      {{ statusLabel }}
    </span>

    <!-- Run name / process id -->
    <div class="min-w-0 flex items-center gap-2">
      <span class="font-semibold truncate max-w-56" :title="run?.name || chat?.name">
        {{ run?.name || chat?.name || 'Long-running task' }}
      </span>
      <span
        v-if="runId"
        class="text-[11px] font-mono text-base-content/50 hidden sm:inline"
        :title="`Process id: ${runId}`"
      >
        {{ shortRunId }}
      </span>
    </div>

    <!-- Progress / counts -->
    <div v-if="hasRun" class="flex items-center gap-2 min-w-40">
      <progress
        class="progress progress-primary w-24 h-2"
        :value="progress"
        max="100"
      ></progress>
      <span class="text-xs tabular-nums text-base-content/60">{{ progress }}%</span>
      <span
        v-if="counts.total"
        class="text-xs tabular-nums text-base-content/60"
        :title="`${counts.done || 0} done · ${counts.running || 0} running · ${counts.pending || 0} pending`"
      >
        {{ counts.done || 0 }}/{{ counts.total }}
      </span>
    </div>

    <!-- Budget -->
    <div v-if="hasRun" class="text-xs tabular-nums text-base-content/60">
      <span :title="'Spent / run budget (cxjcoins)'">{{ spentLabel }}</span>
    </div>

    <!-- Worker presence: a run cannot advance without the background process -->
    <span
      v-if="hasRun && workerAbsent"
      class="badge badge-warning badge-sm gap-1"
      title="The background worker is not running for this project. Start the API with CODX_JUNIOR_API_BACKGROUND=1."
    >
      <i class="fa-solid fa-triangle-exclamation"></i>
      worker off
    </span>

    <!-- Error -->
    <span
      v-if="error"
      class="text-xs text-error truncate max-w-72"
      :title="error"
    >
      {{ error }}
    </span>

    <!-- Controls -->
    <div class="ml-auto flex items-center gap-1.5 shrink-0">
      <button
        v-if="canStart"
        class="btn btn-xs btn-primary gap-1"
        :disabled="busy"
        :title="startTitle"
        @click="$emit('start')"
      >
        <i v-if="busy" class="fa-solid fa-spinner fa-spin"></i>
        <i v-else class="fa-solid fa-play"></i>
        Start
      </button>
      <button
        v-if="canPause"
        class="btn btn-xs btn-warning btn-outline gap-1"
        :disabled="busy"
        title="Pause: the in-flight turn finishes, then the worker stops advancing"
        @click="$emit('pause')"
      >
        <i v-if="busy" class="fa-solid fa-spinner fa-spin"></i>
        <i v-else class="fa-solid fa-pause"></i>
        Pause
      </button>
      <button
        v-if="canStop"
        class="btn btn-xs btn-error btn-outline gap-1"
        :disabled="busy"
        title="Stop: cancels the in-flight turns and publishes a stop report"
        @click="$emit('stop')"
      >
        <i v-if="busy" class="fa-solid fa-spinner fa-spin"></i>
        <i v-else class="fa-solid fa-stop"></i>
        Stop
      </button>
      <slot name="actions"></slot>
    </div>
  </div>
</template>

<script>
const STATUS = {
  running: {
    label: 'Running',
    icon: 'fa-solid fa-arrows-spin fa-spin',
    badge: 'badge-primary',
    container: 'border-primary/30 bg-primary/5'
  },
  queued: {
    label: 'Queued',
    icon: 'fa-regular fa-clock',
    badge: 'badge-info',
    container: 'border-info/30 bg-info/5'
  },
  paused: {
    label: 'Paused',
    icon: 'fa-solid fa-pause',
    badge: 'badge-warning',
    container: 'border-warning/30 bg-warning/5'
  },
  stalled: {
    label: 'Stalled',
    icon: 'fa-solid fa-triangle-exclamation',
    badge: 'badge-warning',
    container: 'border-warning/30 bg-warning/5'
  },
  completed: {
    label: 'Completed',
    icon: 'fa-solid fa-circle-check',
    badge: 'badge-success',
    container: 'border-success/30 bg-success/5'
  },
  stopped: {
    label: 'Stopped',
    icon: 'fa-solid fa-circle-stop',
    badge: 'badge-error',
    container: 'border-error/30 bg-error/5'
  },
  failed: {
    label: 'Failed',
    icon: 'fa-solid fa-circle-xmark',
    badge: 'badge-error',
    container: 'border-error/30 bg-error/5'
  },
  budget_exhausted: {
    label: 'Budget exhausted',
    icon: 'fa-solid fa-coins',
    badge: 'badge-error',
    container: 'border-error/30 bg-error/5'
  },
  idle: {
    label: 'Agent mode',
    icon: 'fa-solid fa-robot',
    badge: 'badge-ghost',
    container: 'border-base-300 bg-base-200/40'
  }
}

const STARTABLE = ['paused', 'stalled', 'queued', 'stopped', 'failed']
const PAUSABLE = ['running', 'queued']
const TERMINAL = ['completed', 'stopped', 'failed', 'budget_exhausted']

export default {
  props: {
    chat: { type: Object, required: true },
    run: { type: Object, default: null },
    busy: { type: Boolean, default: false },
    error: { type: String, default: '' }
  },
  emits: ['start', 'pause', 'stop'],
  computed: {
    isAgentMode() {
      return this.chat?.mode === 'agent'
    },
    runId() {
      return this.run?.run_id || this.chat?.run_id || null
    },
    hasRun() {
      return !!this.runId
    },
    // Agent mode without a registered process still shows the bar so the user
    // can start the run (e.g. a task created from the board's agent mode).
    visible() {
      return this.hasRun || this.isAgentMode
    },
    status() {
      if (!this.hasRun) return 'idle'
      return this.run?.status || this.chat?.run_status || 'queued'
    },
    statusConfig() {
      return STATUS[this.status] || STATUS.queued
    },
    statusLabel() {
      return this.statusConfig.label
    },
    statusIcon() {
      return this.statusConfig.icon
    },
    statusBadgeClass() {
      return this.statusConfig.badge
    },
    containerClass() {
      return this.statusConfig.container
    },
    progress() {
      const value = this.run?.progress ?? this.chat?.progress ?? 0
      return Math.max(0, Math.min(100, Math.round(Number(value) || 0)))
    },
    counts() {
      return this.run?.counts || {}
    },
    spentLabel() {
      const spent = Number(this.run?.spent_cxjcoins || this.chat?.cost || 0)
      const budget = Number(this.run?.budget_cxjcoins || 0)
      if (budget > 0) {
        return `${spent.toFixed(2)} / ${budget.toFixed(2)}`
      }
      return spent > 0 ? spent.toFixed(2) : ''
    },
    workerAbsent() {
      return this.hasRun && this.run?.worker?.present === false
    },
    canStart() {
      if (!this.hasRun) return this.isAgentMode
      return STARTABLE.includes(this.status)
    },
    canPause() {
      return this.hasRun && PAUSABLE.includes(this.status)
    },
    canStop() {
      return this.hasRun && !TERMINAL.includes(this.status)
    },
    startTitle() {
      if (!this.hasRun) return 'Start the long-running task for this agent chat'
      if (this.status === 'paused' || this.status === 'stalled') return 'Resume the run'
      if (this.status === 'stopped' || this.status === 'failed') return 'Reopen the run and continue its plan'
      return 'Start the run'
    },
    shortRunId() {
      const id = String(this.runId || '')
      return id.length > 12 ? `${id.slice(0, 8)}…` : id
    }
  }
}
</script>
