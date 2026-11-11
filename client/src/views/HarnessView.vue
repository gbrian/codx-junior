<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { $storex } from '@/store'

// The project-scoped API instance carries the codx_path of the active project
// (the harness endpoints are project scoped).
const api = computed(() => $storex.projects.activeProject?.$api || $storex.api)

const status = ref(null)
const runs = ref([])
const audit = ref([])
const auditOffset = ref(0)
const auditEvent = ref('')
const auditTotal = ref(null)
const loading = ref(false)
const error = ref('')
const loadingAudit = ref(false)

const AUDIT_EVENTS = [
  { value: '', label: 'All events' },
  { value: 'task_requested', label: 'task_requested' },
  { value: 'run_event', label: 'run_event (run lifecycle)' },
  { value: 'notification_sent', label: 'notification_sent' },
  { value: 'worker_stalled', label: 'worker_stalled' },
  { value: 'worker_restarted', label: 'worker_restarted' },
  { value: 'worker_recovered', label: 'worker_recovered' }
]

const RUN_STATUS_CLASSES = {
  queued: 'badge-ghost',
  running: 'badge-info',
  paused: 'badge-warning',
  completed: 'badge-success',
  stopped: 'badge-ghost',
  failed: 'badge-error',
  budget_exhausted: 'badge-error',
  stalled: 'badge-warning'
}

let refreshTimer = null

async function refresh() {
  const client = api.value
  if (!client) return
  loading.value = true
  error.value = ''
  try {
    const [statusData, runsData] = await Promise.all([
      client.harness.status(),
      client.orchestration.list()
    ])
    status.value = statusData
    runs.value = runsData || []
  } catch (ex) {
    error.value = ex?.response?.data?.detail || ex?.message || String(ex)
  } finally {
    loading.value = false
  }
}

async function loadAudit(reset = true) {
  const client = api.value
  if (!client) return
  loadingAudit.value = true
  try {
    const offset = reset ? 0 : auditOffset.value
    const data = await client.harness.audit({
      limit: 50,
      offset,
      ...(auditEvent.value ? { event: auditEvent.value } : {})
    })
    audit.value = reset ? data.entries || [] : [...audit.value, ...(data.entries || [])]
    auditOffset.value = offset + (data.entries || []).length
    auditTotal.value = data.exists ? null : 0
  } catch (ex) {
    // The audit load failure must not hide the rest of the view.
    console.warn('Harness audit load failed', ex)
  } finally {
    loadingAudit.value = false
  }
}

function openRunTask(run) {
  if (!run?.main_chat_id) return
  $storex.ui.openChat({ id: run.main_chat_id })
}

function formatTime(value) {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value)
  return date.toLocaleString()
}

function auditText(entry) {
  if (entry.event === 'task_requested') {
    return `@codx-junior requested by ${entry.user || '?'} in chat ${entry.chat_id || '?'}`
  }
  if (entry.event === 'run_event') {
    const runEvent = entry.run_event || ''
    const extra = runEvent === 'step_finished' ? ` step ${entry.step_id || '?'}`
      : runEvent === 'step_started' ? ` step ${entry.step_id || '?'}`
        : ''
    return `${runEvent} · run ${entry.run_id || '?'}${extra} · ${entry.message || ''}`
  }
  if (entry.event === 'notification_sent') {
    return `user notified · run ${entry.run_id || '?'} (${entry.status || ''})`
  }
  if (entry.event === 'worker_stalled') {
    return `worker stalled · project ${entry.project || '?'} · ${entry.active_runs?.length || 0} active run(s)`
  }
  if (entry.event === 'worker_restarted') {
    return `worker restarted · ${entry.method || ''} · ${entry.project || ''}`
  }
  if (entry.event === 'worker_recovered') {
    return `worker recovered · pid ${entry.pid ?? '?'}`
  }
  return JSON.stringify(entry)
}

onMounted(() => {
  refresh()
  loadAudit()
  refreshTimer = setInterval(() => {
    refresh()
    loadAudit()
  }, 10000)
})

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<template>
  <div class="h-full overflow-y-auto p-4 flex flex-col gap-4">
    <!-- Header -->
    <div class="flex items-center justify-between gap-2 flex-wrap">
      <div>
        <div class="text-lg font-semibold flex items-center gap-2">
          <i class="fa-solid fa-bolt text-primary"></i>
          codx-junior Harness
        </div>
        <div class="text-xs text-base-content/60">
          Every request, run, step and completion registered by the
          <code class="kbd kbd-xs">@codx-junior</code> profile — navigable and audited.
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span
          v-if="status"
          class="badge gap-1"
          :class="status.worker_running ? 'badge-success' : 'badge-error'"
        >
          <i :class="status.worker_running ? 'fa-solid fa-circle-check' : 'fa-solid fa-triangle-exclamation'"></i>
          worker {{ status.worker_running ? 'running' : 'off' }}
        </span>
        <button class="btn btn-sm" :disabled="loading" @click="refresh">
          <i class="fa-solid fa-rotate" :class="{ 'animate-spin': loading }"></i>
          Refresh
        </button>
      </div>
    </div>

    <div v-if="error" class="alert alert-error text-sm">
      <i class="fa-solid fa-triangle-exclamation"></i>
      {{ error }}
    </div>

    <!-- Worker / watchdog strip -->
    <div v-if="status" class="grid grid-cols-2 md:grid-cols-4 gap-2">
      <div class="stat bg-base-200 rounded-box p-3">
        <div class="stat-title text-xs">Active runs</div>
        <div class="stat-value text-xl">{{ status.active_run_count }}</div>
      </div>
      <div class="stat bg-base-200 rounded-box p-3">
        <div class="stat-title text-xs">Worker heartbeat</div>
        <div class="stat-value text-sm pt-1">
          {{ status.worker?.age_seconds != null ? `${Math.round(status.worker.age_seconds)}s ago` : 'never' }}
        </div>
      </div>
      <div class="stat bg-base-200 rounded-box p-3">
        <div class="stat-title text-xs">Watchdog</div>
        <div class="stat-value text-sm pt-1">
          {{ status.watchdog?.running ? 'watching' : (status.watchdog?.enabled ? 'not running' : 'disabled') }}
        </div>
      </div>
      <div class="stat bg-base-200 rounded-box p-3">
        <div class="stat-title text-xs">Watchdog restarts</div>
        <div class="stat-value text-sm pt-1">{{ status.watchdog?.restarts ?? 0 }}</div>
      </div>
    </div>

    <!-- Runs -->
    <section class="flex flex-col gap-2">
      <div class="flex items-center justify-between">
        <h2 class="font-semibold text-sm uppercase tracking-wide text-base-content/60">
          Runs <span class="normal-case font-normal">({{ runs.length }})</span>
        </h2>
      </div>
      <div v-if="!runs.length" class="text-sm text-base-content/50 bg-base-200 rounded-box p-4">
        No runs yet. Mention <code class="kbd kbd-xs">@codx-junior</code> in a chat and give it a task —
        every run and step will show up here.
      </div>
      <div v-else class="overflow-x-auto bg-base-200 rounded-box">
        <table class="table table-sm">
          <thead>
            <tr>
              <th>Run</th>
              <th>Status</th>
              <th>Progress</th>
              <th>Board / Sprint</th>
              <th>Budget</th>
              <th>Updated</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="run in runs" :key="run.run_id">
              <td class="max-w-xs">
                <div class="font-medium truncate" :title="run.name">{{ run.name }}</div>
                <div class="text-xs text-base-content/50 truncate" :title="run.objective">{{ run.objective }}</div>
              </td>
              <td>
                <span class="badge badge-sm" :class="RUN_STATUS_CLASSES[run.status] || 'badge-ghost'">
                  {{ run.status }}
                </span>
              </td>
              <td>
                <div class="w-28">
                  <progress
                    class="progress progress-primary w-full"
                    :value="run.progress || 0"
                    max="100"
                  ></progress>
                  <div class="text-[10px] text-base-content/50">{{ run.progress || 0 }}%</div>
                </div>
              </td>
              <td class="text-xs">{{ run.board }}<span v-if="run.sprint"> / {{ run.sprint }}</span></td>
              <td class="text-xs">
                <span v-if="run.budget_cxjcoins">
                  {{ Number(run.spent_cxjcoins || 0).toFixed(2) }} / {{ Number(run.budget_cxjcoins).toFixed(2) }}
                </span>
                <span v-else>—</span>
              </td>
              <td class="text-xs">{{ formatTime(run.updated_at) }}</td>
              <td>
                <button
                  class="btn btn-xs btn-outline"
                  :disabled="!run.main_chat_id"
                  @click="openRunTask(run)"
                >
                  Open task
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Audit journal -->
    <section class="flex flex-col gap-2 pb-4">
      <div class="flex items-center justify-between gap-2 flex-wrap">
        <h2 class="font-semibold text-sm uppercase tracking-wide text-base-content/60">Audit journal</h2>
        <select v-model="auditEvent" class="select select-bordered select-xs" @change="loadAudit()">
          <option v-for="option in AUDIT_EVENTS" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </div>
      <div v-if="!audit.length" class="text-sm text-base-content/50 bg-base-200 rounded-box p-4">
        No audited events yet.
      </div>
      <div v-else class="flex flex-col gap-1 bg-base-200 rounded-box p-2 max-h-96 overflow-y-auto">
        <div
          v-for="(entry, index) in audit"
          :key="`${entry.ts}-${index}`"
          class="flex items-start gap-2 text-sm px-2 py-1 rounded hover:bg-base-300"
        >
          <span class="badge badge-xs badge-outline shrink-0 mt-0.5">{{ entry.event }}</span>
          <span class="text-xs shrink-0 text-base-content/50 mt-0.5">{{ formatTime(entry.ts) }}</span>
          <span class="text-xs break-all">{{ auditText(entry) }}</span>
        </div>
        <button
          v-if="audit.length >= 50"
          class="btn btn-xs btn-ghost"
          :disabled="loadingAudit"
          @click="loadAudit(false)"
        >
          <i v-if="loadingAudit" class="fa-solid fa-spinner animate-spin"></i>
          Load more
        </button>
      </div>
    </section>
  </div>
</template>
