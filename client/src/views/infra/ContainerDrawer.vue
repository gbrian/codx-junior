<template>
  <!-- ── Container detail overlay ────────────────────────────────────────────
       Centered MODAL (it used to be a right-hand drawer). Reading logs needs
       width and height, which a side panel can't give inside a dockview panel.
       Teleported to <body> so the overlay is sized by the viewport, not by the
       resizable panel it was opened from. -->
  <Teleport to="body">
    <div v-if="state.drawerOpen" class="fixed inset-0 z-[80] flex items-center justify-center p-2 sm:p-4">
      <!-- backdrop -->
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeDrawer"></div>

      <!-- dialog -->
      <div ref="dialogEl" role="dialog" aria-modal="true" tabindex="-1"
           :aria-label="`Container detail: ${detail?.name || state.selectedContainerId || ''}`"
           class="relative z-10 flex flex-col w-full max-w-6xl h-[92vh] bg-base-100 border border-base-300 rounded-xl shadow-2xl overflow-hidden outline-none">

        <!-- ── Header ─────────────────────────────────────────────────────── -->
        <header class="shrink-0 px-4 py-3 border-b border-base-300 bg-base-200">
          <div class="flex items-start gap-2">
            <span class="inline-block w-2.5 h-2.5 rounded-full mt-2"
                  :class="dotClass(detail?.state)"></span>
            <div class="min-w-0 grow">
              <div class="text-lg font-bold leading-tight truncate flex items-center gap-2">
                {{ detail?.name || state.selectedContainerId }}
                <span v-if="detail?.stack" class="badge badge-sm badge-ghost">{{ detail.stack }}</span>
                <span v-if="detail?.sysbox" class="badge badge-sm badge-outline">sysbox</span>
              </div>
              <div class="text-xs opacity-50 font-mono truncate">{{ detail?.image || '—' }}</div>
            </div>
            <span class="badge badge-sm shrink-0" :class="`badge-${stateTone(detail?.state)}`">
              {{ detail?.state || 'unknown' }}
            </span>
            <button class="btn btn-sm btn-ghost btn-square shrink-0"
                    aria-label="Close container detail" title="Close (Esc)" @click="closeDrawer">
              <i class="fas fa-xmark"></i>
            </button>
          </div>

          <!-- quick actions -->
          <div class="flex flex-wrap items-center gap-2 mt-2">
            <button v-if="detail?.state === 'running'" class="btn btn-sm btn-error btn-outline"
                    @click="askAction(detail, 'stop')">
              <i class="fas fa-stop"></i> Stop
            </button>
            <button v-else-if="detail?.state === 'paused'" class="btn btn-sm btn-success"
                    @click="askAction(detail, 'unpause')">
              <i class="fas fa-play"></i> Resume
            </button>
            <button v-else class="btn btn-sm btn-success" @click="askAction(detail, 'start')">
              <i class="fas fa-play"></i> Start
            </button>

            <button v-if="detail?.state === 'running'" class="btn btn-sm"
                    @click="askAction(detail, 'restart')">
              <i class="fas fa-rotate-right"></i> Restart
            </button>
            <button v-if="detail?.state === 'running'" class="btn btn-sm btn-ghost"
                    @click="askAction(detail, 'pause')">
              <i class="fas fa-pause"></i> Pause
            </button>

            <div class="flex-1"></div>
            <button class="btn btn-sm btn-ghost" @click="showJson(detail?.name, detail)">
              <i class="fas fa-code"></i> Inspect
            </button>
            <button class="btn btn-sm btn-ghost text-error" title="Remove container"
                    aria-label="Remove container" @click="askRemove(detail)">
              <i class="fas fa-trash-can"></i>
            </button>
          </div>
        </header>

        <!-- ── Tabs ───────────────────────────────────────────────────────── -->
        <div ref="tabStripEl" role="tablist"
             class="shrink-0 tabs tabs-boxed tabs-sm bg-base-200 mx-4 mt-3 flex-nowrap overflow-x-auto">
          <button v-for="t in DRAWER_TABS" :key="t.id" role="tab"
                  class="tab gap-1 whitespace-nowrap"
                  :aria-selected="state.detailTab === t.id"
                  :class="{ 'tab-active': state.detailTab === t.id }"
                  @click="setDetailTab(t.id)">
            <i class="fas" :class="t.icon"></i>
            {{ t.label }}
            <span v-if="t.id === 'logs' && state.logs.length" class="badge badge-xs badge-ghost">
              {{ state.logs.length }}
            </span>
          </button>
        </div>

        <!-- ── Body ───────────────────────────────────────────────────────── -->
        <div class="grow min-h-0 flex flex-col">

          <!-- loading -->
          <div v-if="!detail" class="grow min-h-0 overflow-auto p-4 space-y-2">
            <div v-for="i in 8" :key="i" class="skeleton h-8 w-full"></div>
          </div>

          <!-- ── logs: owns the whole remaining height ──────────────────── -->
          <template v-else-if="state.detailTab === 'logs'">
            <div class="shrink-0 flex flex-wrap items-center gap-2 px-4 py-2 border-b border-base-300">
              <span class="text-xs opacity-50">{{ state.logs.length }} lines</span>

              <label class="sr-only" for="log-tail">Log tail size</label>
              <select id="log-tail" class="select select-bordered select-xs"
                      :value="tailSize" @change="onTailChange">
                <option :value="100">tail 100</option>
                <option :value="200">tail 200</option>
                <option :value="500">tail 500</option>
                <option :value="1000">tail 1000</option>
              </select>

              <div class="flex-1"></div>

              <label class="label cursor-pointer gap-2 py-0">
                <span class="label-text text-xs">Follow</span>
                <input type="checkbox" class="toggle toggle-xs toggle-primary" v-model="follow" />
              </label>

              <button class="btn btn-xs btn-ghost" :disabled="state.logsLoading" @click="reloadLogs">
                <i class="fas fa-rotate-right" :class="{ 'animate-spin': state.logsLoading }"></i>
                Reload
              </button>
            </div>

            <div ref="logEl" class="grow min-h-0 overflow-auto bg-base-300/60">
              <div v-if="state.logsLoading && !state.logs.length" class="p-4 space-y-2">
                <div v-for="i in 10" :key="i" class="skeleton h-4 w-full"></div>
              </div>

              <p v-else-if="!state.logs.length" class="p-8 text-center text-xs opacity-50">
                No log lines were returned for this container.
              </p>

              <table v-else class="table table-xs font-mono text-[11px]">
                <tbody>
                  <tr v-for="(line, i) in state.logs" :key="i" class="hover:bg-base-100/60">
                    <td class="whitespace-nowrap opacity-40 align-top w-20">{{ fmtTime(line.ts) }}</td>
                    <td class="whitespace-nowrap align-top w-14">
                      <span :class="logLevelClass(line.level)">{{ line.level }}</span>
                    </td>
                    <td class="whitespace-pre-wrap break-all">{{ line.msg }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>

          <!-- ── overview / stats / config scroll normally ──────────────── -->
          <div v-else class="grow min-h-0 overflow-auto p-4 space-y-3">

            <!-- overview -->
            <template v-if="state.detailTab === 'overview'">
              <div class="grid grid-cols-2 gap-2">
                <div class="stat bg-base-200 rounded-lg p-3">
                  <div class="stat-title text-xs">CPU</div>
                  <div class="stat-value text-xl">{{ (detail.cpu_pct || 0).toFixed(1) }}%</div>
                </div>
                <div class="stat bg-base-200 rounded-lg p-3">
                  <div class="stat-title text-xs">Memory</div>
                  <div class="stat-value text-xl">{{ fmtBytes(detail.mem_used) }}</div>
                  <div class="stat-desc">of {{ fmtBytes(detail.mem_limit) }}</div>
                </div>
              </div>

              <div class="flex items-center gap-2">
                <progress class="progress grow"
                          :class="`progress-${tone(detail.mem_pct, 85, 95)}`"
                          :value="detail.mem_pct" max="100"></progress>
                <span class="text-xs opacity-60">{{ detail.mem_pct || 0 }}%</span>
              </div>

              <div class="overflow-x-auto">
                <table class="table table-xs">
                  <tbody>
                    <tr><th class="w-32 opacity-60">ID</th><td class="font-mono text-xs">{{ detail.id }}</td></tr>
                    <tr><th class="opacity-60">Image</th><td class="font-mono text-xs">{{ detail.image }}</td></tr>
                    <tr><th class="opacity-60">State</th><td>{{ stateLabel(detail) }}</td></tr>
                    <tr><th class="opacity-60">Health</th>
                      <td>
                        <span v-if="detail.health" class="badge badge-xs" :class="`badge-${healthTone(detail.health)}`">
                          {{ detail.health }}
                        </span>
                        <span v-else class="opacity-40">—</span>
                      </td>
                    </tr>
                    <tr><th class="opacity-60">Uptime</th><td>{{ fmtUptime(detail.uptime_seconds) }}</td></tr>
                    <tr><th class="opacity-60">Created</th><td>{{ fmtTime(detail.created) }}</td></tr>
                    <tr><th class="opacity-60">Started</th><td>{{ fmtTime(detail.started_at) }}</td></tr>
                    <tr><th class="opacity-60">Restarts</th><td>{{ detail.restart_count ?? 0 }}</td></tr>
                    <tr><th class="opacity-60">Policy</th><td>{{ detail.restart_policy || '—' }}</td></tr>
                    <tr><th class="opacity-60">PIDs</th><td>{{ detail.pids ?? '—' }}</td></tr>
                    <tr><th class="opacity-60">Network</th>
                      <td class="font-mono text-xs">
                        ↓ {{ fmtBytes(detail.net_rx) }} · ↑ {{ fmtBytes(detail.net_tx) }}
                      </td>
                    </tr>
                    <tr><th class="opacity-60">Block I/O</th>
                      <td class="font-mono text-xs">
                        R {{ fmtBytes(detail.block_read) }} · W {{ fmtBytes(detail.block_write) }}
                      </td>
                    </tr>
                    <tr v-if="detail.stack"><th class="opacity-60">Compose</th>
                      <td>{{ detail.stack }} / {{ detail.service }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <!-- ports -->
              <div>
                <h4 class="font-semibold text-sm mb-1">Ports</h4>
                <div v-if="detail.ports?.length" class="flex flex-wrap gap-1">
                  <span v-for="(p, i) in detail.ports" :key="i" class="badge badge-sm badge-outline font-mono">
                    {{ p.host ? `:${p.host}→` : '' }}{{ p.container }}/{{ p.proto }}
                  </span>
                </div>
                <p v-else class="text-xs opacity-40">No ports exposed</p>
              </div>

              <!-- mounts -->
              <div>
                <h4 class="font-semibold text-sm mb-1">Mounts</h4>
                <ul v-if="detail.mounts?.length" class="space-y-1">
                  <li v-for="(m, i) in detail.mounts" :key="i" class="text-xs">
                    <span class="badge badge-xs badge-ghost">{{ m.type }}</span>
                    <span class="font-mono break-all">{{ m.source }}</span>
                    <i class="fas fa-arrow-right text-[10px] opacity-40 mx-1"></i>
                    <span class="font-mono break-all">{{ m.destination }}</span>
                    <span class="opacity-40">({{ m.mode }})</span>
                  </li>
                </ul>
                <p v-else class="text-xs opacity-40">No mounts</p>
              </div>

              <!-- networks -->
              <div>
                <h4 class="font-semibold text-sm mb-1">Networks</h4>
                <ul v-if="detail.networks?.length" class="space-y-1">
                  <li v-for="(n, i) in detail.networks" :key="i" class="text-xs font-mono">
                    {{ n.name }} <span class="opacity-40">{{ n.ip }}</span>
                  </li>
                </ul>
                <p v-else class="text-xs opacity-40">Not attached</p>
              </div>

              <!-- healthcheck -->
              <div v-if="detail.healthcheck">
                <h4 class="font-semibold text-sm mb-1">Healthcheck</h4>
                <pre class="p-2 rounded-lg bg-base-300 text-xs overflow-auto">{{ detail.healthcheck }}</pre>
              </div>
            </template>

            <!-- stats -->
            <template v-else-if="state.detailTab === 'stats'">
              <div v-if="state.statsLoading && !state.stats" class="space-y-2">
                <div v-for="i in 5" :key="i" class="skeleton h-8 w-full"></div>
              </div>

              <template v-else-if="state.stats">
                <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <div class="stat bg-base-200 rounded-lg p-3">
                    <div class="stat-title text-xs">CPU now</div>
                    <div class="stat-value text-xl">{{ (state.stats.current?.cpu_pct || 0).toFixed(1) }}%</div>
                  </div>
                  <div class="stat bg-base-200 rounded-lg p-3">
                    <div class="stat-title text-xs">Memory now</div>
                    <div class="stat-value text-xl">{{ fmtBytes(state.stats.current?.mem_used) }}</div>
                  </div>
                  <div class="stat bg-base-200 rounded-lg p-3">
                    <div class="stat-title text-xs">Net RX</div>
                    <div class="stat-value text-lg">{{ fmtBytes(state.stats.current?.net_rx) }}</div>
                  </div>
                  <div class="stat bg-base-200 rounded-lg p-3">
                    <div class="stat-title text-xs">Net TX</div>
                    <div class="stat-value text-lg">{{ fmtBytes(state.stats.current?.net_tx) }}</div>
                  </div>
                </div>

                <div>
                  <h4 class="font-semibold text-sm mb-1">CPU history</h4>
                  <div class="flex items-end gap-0.5 h-24 p-2 rounded-lg bg-base-200">
                    <div v-for="(s, i) in state.stats.series" :key="`cpu-${i}`"
                         class="bg-primary/70 grow rounded-t"
                         :style="{ height: barHeight(s.cpu, maxCpu) }"
                         :title="`${s.cpu}%`"></div>
                  </div>
                </div>

                <div>
                  <h4 class="font-semibold text-sm mb-1">Memory history</h4>
                  <div class="flex items-end gap-0.5 h-24 p-2 rounded-lg bg-base-200">
                    <div v-for="(s, i) in state.stats.series" :key="`mem-${i}`"
                         class="bg-secondary/70 grow rounded-t"
                         :style="{ height: barHeight(s.mem, maxMem) }"
                         :title="fmtBytes(s.mem)"></div>
                  </div>
                </div>
              </template>

              <p v-else class="text-xs opacity-40">No stats available</p>
            </template>

            <!-- env & labels -->
            <template v-else>
              <div>
                <h4 class="font-semibold text-sm mb-1">Environment</h4>
                <div v-if="detail.env?.length" class="overflow-x-auto">
                  <table class="table table-xs">
                    <tbody>
                      <tr v-for="(e, i) in detail.env" :key="i">
                        <th class="font-mono text-xs w-48">{{ e.k }}</th>
                        <td class="font-mono text-xs break-all">{{ e.v }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p v-else class="text-xs opacity-40">No environment variables</p>
              </div>

              <div>
                <h4 class="font-semibold text-sm mb-1">Command</h4>
                <pre class="p-2 rounded-lg bg-base-300 text-xs overflow-auto">{{ commandLine }}</pre>
              </div>

              <div>
                <h4 class="font-semibold text-sm mb-1">Labels</h4>
                <div v-if="Object.keys(detail.labels || {}).length" class="overflow-x-auto">
                  <table class="table table-xs">
                    <tbody>
                      <tr v-for="(v, k) in detail.labels" :key="k">
                        <th class="font-mono text-xs">{{ k }}</th>
                        <td class="font-mono text-xs break-all">{{ v }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <p v-else class="text-xs opacity-40">No labels</p>
              </div>
            </template>
          </div>
        </div>

        <!-- ── Footer ─────────────────────────────────────────────────────── -->
        <footer class="shrink-0 px-4 py-2 border-t border-base-300 bg-base-200 flex flex-wrap items-center gap-3 text-xs">
          <span class="font-mono opacity-50">{{ shortId }}</span>
          <span v-if="detail" class="opacity-50">Uptime {{ fmtUptime(detail.uptime_seconds) }}</span>
          <div class="flex-1"></div>
          <button class="btn btn-sm btn-ghost" @click="closeDrawer">Close</button>
        </footer>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  state, closeDrawer, setDetailTab, loadLogs,
  askAction, askRemove, showJson,
  fmtBytes, fmtTime, fmtUptime, tone,
  stateTone, dotClass, healthTone, stateLabel
} from './useInfra'

const DRAWER_TABS = [
  { id: 'overview', label: 'Overview', icon: 'fa-circle-info' },
  { id: 'logs', label: 'Logs', icon: 'fa-file-lines' },
  { id: 'stats', label: 'Stats', icon: 'fa-chart-area' },
  { id: 'config', label: 'Env & labels', icon: 'fa-sliders' }
]

const detail = computed(() => state.detail)

/* ── log pane state ───────────────────────────────────────────────────────── */
const tailSize = ref(200)
const follow = ref(true)

const maxCpu = computed(() => {
  const series = state.stats?.series || []
  return Math.max(10, ...series.map(s => s.cpu || 0))
})
const maxMem = computed(() => {
  const series = state.stats?.series || []
  return Math.max(1, ...series.map(s => s.mem || 0))
})

const commandLine = computed(() => {
  if (!detail.value) return '—'
  return [detail.value.entrypoint, ...(detail.value.cmd || [])]
    .filter(Boolean)
    .join(' ') || '—'
})

const shortId = computed(() => {
  const id = detail.value?.short || detail.value?.id || state.selectedContainerId || ''
  return String(id).slice(0, 12) || '—'
})

function barHeight(value, max) {
  const pct = Math.max(2, Math.min(100, ((value || 0) / (max || 1)) * 100))
  return `${pct}%`
}

function logLevelClass(level) {
  return {
    ERROR: 'text-error font-semibold',
    WARN: 'text-warning',
    DEBUG: 'text-info/70'
  }[level] || 'text-success'
}

/* ── focus / scroll plumbing ──────────────────────────────────────────────── */
const dialogEl = ref(null)
const tabStripEl = ref(null)
const logEl = ref(null)

/** Keeps the active tab visible inside the horizontally scrollable strip. */
async function revealActiveTab() {
  await nextTick()
  const active = tabStripEl.value?.querySelector('.tab-active')
  if (active) active.scrollIntoView({ block: 'nearest', inline: 'nearest' })
}

async function scrollLogsToBottom() {
  if (!follow.value) return
  await nextTick()
  const el = logEl.value
  if (el) el.scrollTop = el.scrollHeight
}

async function reloadLogs() {
  await loadLogs(tailSize.value)
  scrollLogsToBottom()
}

function onTailChange(event) {
  tailSize.value = Number(event.target.value) || 200
  reloadLogs()
}

function onKeydown(event) {
  if (event.key === 'Escape' && state.drawerOpen) {
    // The detail overlay is the topmost layer: consume the key.
    event.stopPropagation()
    closeDrawer()
  }
}

/* ── lifecycle / watchers ─────────────────────────────────────────────────── */
onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

watch(() => state.drawerOpen, async (open) => {
  if (!open) return
  await nextTick()
  dialogEl.value?.focus()
  revealActiveTab()
  scrollLogsToBottom()
})

watch(() => state.detailTab, () => revealActiveTab())

// New log lines arrive as a fresh array; keep following the tail.
watch(() => state.logs, () => scrollLogsToBottom())
</script>