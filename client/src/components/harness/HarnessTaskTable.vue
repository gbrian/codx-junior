<script setup>
/**
 * Every task associated with a harness run: the main task plus one card per
 * plan step, with the board/column each card lives in, its workflow status,
 * the worker turns it consumed and its cost.
 *
 * This is the "all tasks associated" answer of the diagnostic view: a step
 * that never got a card (`chat_id` empty) is visible too, because that is one
 * of the usual reasons a run stalls.
 */
import { computed } from 'vue'
import {
  STEP_CHAT_STATUS_LABEL,
  formatCost,
  formatTime,
  runMeta,
  stepDuration,
  stepMeta
} from './harnessStatus'

const props = defineProps({
  run: { type: Object, default: null }
})

const emit = defineEmits(['open-chat'])

/** Main task + step cards, in plan order. */
const rows = computed(() => {
  const run = props.run
  if (!run) return []
  const meta = runMeta(run.status)
  const main = {
    key: 'main-task',
    kind: 'main',
    title: run.name || '(unnamed harness task)',
    chatId: run.main_chat_id,
    chatStatus: '',
    statusLabel: meta.label,
    statusBadge: meta.badge,
    statusIcon: meta.icon,
    profile: (run.config?.supervisor_profiles || []).map(name => `@${name}`).join(' '),
    board: run.config?.board || '—',
    column: 'main task',
    attempts: run.rounds ?? 0,
    cost: formatCost(run.spent_cxjcoins),
    duration: '—',
    updated: run.updated_at
  }
  const steps = (run.steps || []).map((step, index) => {
    const stepStatus = stepMeta(step.status)
    return {
      key: step.id,
      kind: 'step',
      index: index + 1,
      title: step.title,
      chatId: step.chat_id,
      chatStatus: STEP_CHAT_STATUS_LABEL[step.chat_status] || step.chat_status || '—',
      statusLabel: stepStatus.label,
      statusBadge: stepStatus.badge,
      statusIcon: stepStatus.icon,
      profile: step.profile ? `@${step.profile}` : '—',
      board: step.board || '—',
      column: step.column || '—',
      attempts: step.attempts || 0,
      cost: formatCost(step.result?.cost_cxjcoins),
      duration: stepDuration(step),
      updated: step.updated_at
    }
  })
  return [main, ...steps]
})

const missingCards = computed(() => (props.run?.steps || []).filter(step => !step.chat_id).length)
</script>

<template>
  <div v-if="!run" class="text-sm text-base-content/50 bg-base-200 rounded-box p-4">
    Select a harness task to see its associated tasks.
  </div>

  <div v-else class="flex flex-col gap-2">
    <div class="flex flex-wrap items-center gap-2 text-xs text-base-content/60">
      <span class="badge badge-sm badge-ghost">{{ rows.length }} task(s)</span>
      <span v-if="run.config?.board">board <strong class="text-base-content">{{ run.config.board }}</strong></span>
      <span v-if="run.config?.sprint">sprint <strong class="text-base-content">{{ run.config.sprint }}</strong></span>
      <span
        v-if="missingCards"
        class="badge badge-sm badge-warning gap-1"
        :title="`${missingCards} step(s) have no task card yet`"
      >
        <i class="fa-solid fa-triangle-exclamation"></i>
        {{ missingCards }} step(s) without a card
      </span>
    </div>

    <div class="overflow-x-auto bg-base-200 rounded-box">
      <table class="table table-xs">
        <thead>
          <tr>
            <th class="w-6">#</th>
            <th>Task</th>
            <th>Step status</th>
            <th>Chat status</th>
            <th>Board / column</th>
            <th>Profile</th>
            <th class="text-right">Turns</th>
            <th class="text-right">Cost</th>
            <th class="text-right">Duration</th>
            <th>Updated</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.key" :class="row.kind === 'main' ? 'bg-primary/5' : ''">
            <td class="text-base-content/40">
              <i v-if="row.kind === 'main'" class="fa-solid fa-bolt text-primary" title="Main task"></i>
              <span v-else>{{ row.index }}</span>
            </td>
            <td class="max-w-72">
              <div class="font-medium truncate" :title="row.title">{{ row.title }}</div>
              <div class="font-mono text-[10px] text-base-content/40 truncate" :title="row.chatId">
                {{ row.chatId || 'no task card' }}
              </div>
            </td>
            <td>
              <span class="badge badge-xs gap-1" :class="row.statusBadge">
                <i :class="row.statusIcon"></i>
                {{ row.statusLabel }}
              </span>
            </td>
            <td class="text-[11px]">{{ row.chatStatus || '—' }}</td>
            <td class="text-[11px]">
              {{ row.board }}
              <span v-if="row.column && row.column !== '—'" class="text-base-content/50"> / {{ row.column }}</span>
            </td>
            <td class="text-[11px]">{{ row.profile || '—' }}</td>
            <td class="text-right text-[11px] tabular-nums">{{ row.attempts }}</td>
            <td class="text-right text-[11px] tabular-nums">{{ row.cost }}</td>
            <td class="text-right text-[11px] tabular-nums">{{ row.duration }}</td>
            <td class="text-[11px]">{{ formatTime(row.updated) }}</td>
            <td>
              <button
                class="btn btn-xs btn-outline"
                :disabled="!row.chatId"
                @click="emit('open-chat', row.chatId)"
              >
                Open
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
