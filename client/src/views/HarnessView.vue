<script setup>
/**
 * Harness diagnostic view.
 *
 * A harness task *is* a codx-junior orchestration run: the main task (a chat)
 * plus one child task card per plan step. This view answers, for one task:
 *
 * - what is the flow of the plan (stages, dependencies, next action),
 * - which tasks are associated and where they live on the board,
 * - what happened (run timeline + append-only audit journal),
 * - what the delivery/stop report says,
 * - and whether the project has a worker able to advance it at all.
 *
 * Read-only except for the run controls (start / pause / stop); the data comes
 * from `GET /api/orchestration` and `GET /api/harness/*`.
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { $storex } from '@/store'
import HarnessRunList from '@/components/harness/HarnessRunList.vue'
import HarnessRunDetail from '@/components/harness/HarnessRunDetail.vue'
import { formatTime } from '@/components/harness/harnessStatus'

// The project-scoped API instance carries the codx_path of the active project
// (the harness endpoints are project scoped).
const api = computed(() => $storex.projects.activeProject?.$api || $storex.api)

const status = ref(null)
const runs = ref([])
const selectedRunId = ref('')
const run = ref(null)
const runLoading = ref(false)
const runError = ref('')
const controlBusy = ref(false)

const audit = ref([])
const auditOffset = ref(0)
const auditEvent = ref('')
const auditScope = ref('run')
const loadingAudit = ref(false)

const loading = ref(false)
const error = ref('')
const live = ref(true)

const AUDIT_EVENTS = [
  { value: '', label: 'All events' },
  { value: 'task_requested', label: 'task_requested' },
  { value: 'run_event', label: 'run_event (run lifecycle)' },
  { value: 'notification_sent', label: 'notification_sent' },
  { value: 'worker_stalled', label: 'worker_stalled' },
  { value: 'worker_restarted', label: 'worker_restarted' },
  { value: 'worker_recovered', label: 'worker_recovered' },
  { value: 'error', label: 'error' }
]

let refreshTimer = null

function errorMessage(ex) {
  return ex?.response?.data?.detail || ex?.message || String(ex)
}

/** Load the run list and the harness health of the project. */
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
    // `GET /api/orchestration` answers `{ runs: [...] }`.
    runs.value = Array.isArray(runsData) ? runsData : (runsData?.runs || [])
    if (!selectedRunId.value && runs.value.length) {
      selectedRunId.value = runs.value[0].run_id
    }
    if (selectedRunId.value) {
      await loadRun(selectedRunId.value)
    }
  } catch (ex) {
    error.value = errorMessage(ex)
  } finally {
    loading.value = false
  }
}

/** Load the full detail (plan, step results, next action, worker). */
async function loadRun(runId) {
  const client = api.value
  if (!client || !runId) {
    run.value = null
    return
  }
  runLoading.value = true
  runError.value = ''
  try {
    run.value = await client.orchestration.get(runId)
  } catch (ex) {
    run.value = null
    runError.value = errorMessage(ex)
  } finally {
    runLoading.value = false
  }
}

async function selectRun(runId) {
  if (!runId || runId === selectedRunId.value) return
  selectedRunId.value = runId
  await loadRun(runId)
  await loadAudit(true)
}

/** Read the append-only audit journal (optionally scoped to the run). */
async function loadAudit(reset = true) {
  const client = api.value
  if (!client) return
  loadingAudit.value = true
  try {
    const offset = reset ? 0 : auditOffset.value
    const params = { limit: 50, offset }
    if (auditEvent.value) params.event = auditEvent.value
    if (auditScope.value === 'run' && selectedRunId.value) params.run_id = selectedRunId.value
    const data = await client.harness.audit(params)
    const entries = data.entries || []
    audit.value = reset ? entries : [...audit.value, ...entries]
    auditOffset.value = offset + entries.length
  } catch (ex) {
    // The audit failure must not hide the rest of the view.
    console.warn('Harness audit load failed', ex)
  } finally {
    loadingAudit.value = false
  }
}

/** Run controls (start / pause / stop) emitted by the detail pane. */
async function onControl({ action, runId }) {
  const client = api.value
  if (!client || !runId) return
  controlBusy.value = true
  error.value = ''
  try {
    if (action === 'start') await client.orchestration.start(runId)
    else if (action === 'pause') await client.orchestration.pause(runId, 'paused from the harness view')
    else if (action === 'stop') await client.orchestration.stop(runId, 'stopped from the harness view')
    await loadRun(runId)
    await loadAudit(true)
  } catch (ex) {
    error.value = errorMessage(ex)
  } finally {
    controlBusy.value = false
  }
}

function openTask(chatId) {
  if (!chatId) return
  $storex.ui.openChat({ id: chatId })
}

/** One-line human summary of an audit entry. */
function auditText(entry) {
  if (entry.event === 'task_requested') {
    return `@codx-junior requested by ${entry.user || '?'} in chat ${entry.chat_id || '?'}`
  }
  if (entry.event === 'run_event') {
    const runEvent = entry.run_event || ''
    const extra = ['step_finished', 'step_started', 'step_dispatched', 'step_retried'].includes(runEvent)
      ? ` step ${entry.step_id || '?'}`
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
  if (entry.event === 'error') {
    return `${entry.message || entry.error || JSON.stringify(entry)}`
  }
  return JSON.stringify(entry)
}

function reloadAuditScope() {
  loadAudit(true)
}

onMounted(() => {
  refresh()
  loadAudit()
  refreshTimer = setInterval(() => {
    if (!live.value) return
    refresh()
    loadAudit(true)
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
          Diagnose any harness task: its flow, every associated task card, the timeline and the
          audited work of the <code class="kbd kbd-xs">@codx-junior</code> profile.
        </div>
      </div>
      <div class="flex items-center gap-2">
        <label class="label cursor-pointer gap-1 py-0">
          <input v-model="live" type="checkbox" class="toggle toggle-xs" />
          <span class="label-text text-xs">live</span>
        </label>
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

    <!-- Runs + diagnosis -->
    <div class="grid grid-cols-1 xl:grid-cols-[20rem_minmax(0,1fr)] gap-3 items-start">
      <HarnessRunList
        :runs="runs"
        :selected-run-id="selectedRunId"
        :loading="loading"
        @select="selectRun"
        @refresh="refresh"
      />
      <HarnessRunDetail
        :run="run"
        :loading="runLoading"
        :error="runError"
        :busy="controlBusy"
        @open-chat="openTask"
        @refresh="loadRun(selectedRunId)"
        @control="onControl"
      />
    </div>

    <!-- Audit journal -->
    <section class="flex flex-col gap-2 pb-4">
      <div class="flex items-center justify-between gap-2 flex-wrap">
        <h2 class="font-semibold text-sm uppercase tracking-wide text-base-content/60">Audit journal</h2>
        <div class="flex items-center gap-2">
          <select v-model="auditScope" class="select select-bordered select-xs" @change="reloadAuditScope">
            <option value="run">This task</option>
            <option value="all">Whole project</option>
          </select>
          <select v-model="auditEvent" class="select select-bordered select-xs" @change="loadAudit()">
            <option v-for="option in AUDIT_EVENTS" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </div>
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
