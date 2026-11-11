<script setup>
/**
 * Flow of one harness task: the main task, its plan stages (one column per
 * dependency level) and the worker's next action.
 *
 * This is the "why is it stuck?" picture of the view: a card shows its step
 * status, how many attempts it consumed, and whether it is ready, blocked by a
 * failed dependency or waiting for its dependencies to finish.
 */
import { computed } from 'vue'
import {
  STEP_CHAT_STATUS_LABEL,
  SUCCESSFUL_STEP_STATUSES,
  formatTime,
  nextActionMeta,
  nextReasonLabel,
  runMeta,
  shortId,
  stepDuration,
  stepMeta
} from './harnessStatus'

const props = defineProps({
  run: { type: Object, default: null }
})

const emit = defineEmits(['open-chat'])

const steps = computed(() => props.run?.steps || [])

const stepsById = computed(() => {
  const index = {}
  steps.value.forEach(step => { index[step.id] = step })
  return index
})

/**
 * Dependency depth of a step (0 = no dependency).
 * Cycles cannot exist (the backend rejects them) but a guard keeps the UI safe.
 */
function depthOf(step, seen = new Set()) {
  const dependencies = step?.depends_on || []
  let depth = 0
  dependencies.forEach(dependencyId => {
    if (seen.has(dependencyId)) return
    seen.add(dependencyId)
    const parent = stepsById.value[dependencyId]
    if (!parent) return
    depth = Math.max(depth, depthOf(parent, seen) + 1)
  })
  return depth
}

/** One column per dependency level, steps sorted by creation. */
const stages = computed(() => {
  const byLevel = new Map()
  steps.value.forEach(step => {
    const level = depthOf(step)
    if (!byLevel.has(level)) byLevel.set(level, [])
    byLevel.get(level).push(step)
  })
  return [...byLevel.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([level, list]) => ({
      level,
      steps: list.sort((a, b) => String(a.created_at).localeCompare(String(b.created_at)))
    }))
})

/** True when every dependency of the step finished successfully. */
function isReady(step) {
  if (step.status !== 'pending') return false
  return (step.depends_on || []).every(id => {
    const dependency = stepsById.value[id]
    return !dependency || SUCCESSFUL_STEP_STATUSES.includes(dependency.status)
  })
}

/** True when a dependency failed/was blocked: the step can never run as is. */
function isBlocked(step) {
  if (step.status !== 'pending') return false
  return (step.depends_on || []).some(id => {
    const dependency = stepsById.value[id]
    return !!dependency && ['failed', 'blocked'].includes(dependency.status)
  })
}

function cardClass(step) {
  if (step.status === 'running') return 'border-primary/60 bg-primary/5'
  if (step.status === 'failed') return 'border-error/60 bg-error/5'
  if (step.status === 'blocked' || isBlocked(step)) return 'border-warning/60 bg-warning/5'
  if (SUCCESSFUL_STEP_STATUSES.includes(step.status)) return 'border-success/40 bg-success/5'
  return 'border-base-300'
}

function dependencyLabel(step) {
  return (step.depends_on || []).map(id => shortId(id, 6)).join(', ')
}

/** Workflow status mirrored on the step card (usually "doing" while running). */
function stepChatStatus(step) {
  if (!step?.chat_status) return ''
  return STEP_CHAT_STATUS_LABEL[step.chat_status] || step.chat_status
}

const meta = computed(() => runMeta(props.run?.status))
const nextAction = computed(() => props.run?.next_action || null)
const nextMeta = computed(() => nextActionMeta(nextAction.value?.action))
</script>

<template>
  <div v-if="!run" class="text-sm text-base-content/50 bg-base-200 rounded-box p-4">
    Select a harness task to see its flow.
  </div>

  <div v-else class="flex flex-col gap-3">
    <!-- The harness task itself (the run's main task) -->
    <div class="rounded-xl border border-primary/30 bg-primary/5 p-3 flex flex-wrap items-center gap-2">
      <i class="fa-solid fa-bolt text-primary"></i>
      <div class="min-w-0 flex-1">
        <div class="text-sm font-semibold truncate" :title="run.name">{{ run.name || 'Harness task' }}</div>
        <div v-if="run.objective" class="text-xs text-base-content/60 line-clamp-2" :title="run.objective">
          {{ run.objective }}
        </div>
      </div>
      <span class="badge badge-sm gap-1" :class="meta.badge">
        <i :class="meta.icon"></i>
        {{ meta.label }}
      </span>
      <span class="badge badge-sm badge-ghost" :title="`Run id ${run.run_id}`">
        {{ shortId(run.run_id, 8) }}
      </span>
      <button
        v-if="run.main_chat_id"
        class="btn btn-xs btn-outline"
        title="Open the main task conversation"
        @click="emit('open-chat', run.main_chat_id)"
      >
        <i class="fa-solid fa-arrow-up-right-from-square"></i>
        Main task
      </button>
    </div>

    <div v-if="!steps.length" class="text-sm text-base-content/50 bg-base-200 rounded-box p-4">
      <i class="fa-solid fa-diagram-project mr-1"></i>
      This run has no plan yet — the supervisor writes it on its next round.
    </div>

    <!-- Plan stages -->
    <div v-else class="flex items-start gap-2 overflow-x-auto pb-2">
      <template v-for="(stage, index) in stages" :key="stage.level">
        <div class="flex items-center self-center text-base-content/30" v-if="index > 0">
          <i class="fa-solid fa-arrow-right-long"></i>
        </div>
        <div class="flex flex-col gap-2 min-w-56 max-w-64">
          <div class="text-[11px] uppercase tracking-wide text-base-content/50">
            Stage {{ stage.level + 1 }}
            <span class="normal-case">({{ stage.steps.length }})</span>
          </div>
          <div
            v-for="step in stage.steps"
            :key="step.id"
            class="rounded-lg border bg-base-200 p-2 flex flex-col gap-1"
            :class="cardClass(step)"
          >
            <div class="flex items-start gap-1.5 min-w-0">
              <i :class="[stepMeta(step.status).icon, stepMeta(step.status).color]" class="text-xs mt-0.5 shrink-0"></i>
              <span class="text-xs font-medium leading-tight" :title="step.title">{{ step.title }}</span>
            </div>

            <div class="flex flex-wrap items-center gap-1">
              <span class="badge badge-xs" :class="stepMeta(step.status).badge">{{ stepMeta(step.status).label }}</span>
              <span v-if="step.profile" class="badge badge-xs badge-outline">@{{ step.profile }}</span>
              <span v-if="step.attempts" class="badge badge-xs badge-ghost" title="Worker turns consumed">
                try {{ step.attempts }}
              </span>
              <span v-if="isReady(step)" class="badge badge-xs badge-info" title="Every dependency finished">
                ready
              </span>
              <span v-if="isBlocked(step)" class="badge badge-xs badge-warning" title="A dependency failed">
                blocked by dependency
              </span>
              <span v-if="step.priority === 'high'" class="badge badge-xs badge-error">high</span>
            </div>

            <div v-if="step.depends_on?.length" class="text-[10px] text-base-content/40" :title="step.depends_on.join(', ')">
              <i class="fa-solid fa-turn-up"></i> after {{ dependencyLabel(step) }}
            </div>

            <div class="text-[10px] text-base-content/50 line-clamp-2" :title="step.objective">
              {{ step.objective }}
            </div>

            <div v-if="step.error || step.result?.error" class="text-[10px] text-error line-clamp-2" :title="step.error || step.result?.error">
              <i class="fa-solid fa-triangle-exclamation"></i>
              {{ step.error || step.result.error }}
            </div>

            <div class="flex items-center justify-between gap-1 text-[10px] text-base-content/40">
              <span>{{ stepChatStatus(step) }}</span>
              <span>{{ stepDuration(step) }}</span>
            </div>

            <button
              v-if="step.chat_id"
              class="btn btn-xs btn-ghost justify-start px-1"
              title="Open the task card conversation of this step"
              @click="emit('open-chat', step.chat_id)"
            >
              <i class="fa-solid fa-up-right-from-square"></i>
              Open task
            </button>
          </div>
        </div>
      </template>
    </div>

    <!-- What the worker will do next -->
    <div v-if="nextAction" class="rounded-box bg-base-200 p-3 flex flex-wrap items-center gap-2 text-xs">
      <span class="badge badge-sm badge-neutral gap-1">
        <i :class="nextMeta.icon"></i>
        {{ nextMeta.label }}
      </span>
      <span class="text-base-content/70">{{ nextReasonLabel(nextAction.reason) }}</span>
      <span v-if="nextAction.steps?.length" class="font-mono text-[11px] text-base-content/50">
        {{ nextAction.steps.map(id => shortId(id, 6)).join(', ') }}
      </span>
      <span class="ml-auto text-base-content/40">updated {{ formatTime(run.updated_at) }}</span>
    </div>
  </div>
</template>
