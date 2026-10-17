<template>
  <Teleport to="body">
    <div v-if="state.drawerOpen" class="fixed inset-0 z-[80] flex justify-end">
      <div class="absolute inset-0 bg-black/50" @click="closeDrawer"></div>

      <div class="relative w-full sm:max-w-xl h-full bg-base-100 border-l border-base-300 shadow-2xl flex flex-col">
        <!-- ── Header ───────────────────────────────────────────────────── -->
        <div class="shrink-0 px-4 py-3 border-b border-base-300 bg-base-200">
          <div class="flex items-start gap-2">
            <span class="inline-block w-2.5 h-2.5 rounded-full mt-1.5"
                  :class="dotClass(detail?.state)"></span>
            <div class="min-w-0 grow">
              <div class="font-bold truncate flex items-center gap-2">
                {{ detail?.name || state.selectedContainerId }}
                <span v-if="detail?.stack" class="badge badge-xs badge-ghost">{{ detail.stack }}</span>
              </div>
              <div class="text-xs opacity-50 font-mono truncate">{{ detail?.image }}</div>
            </div>
            <span class="badge badge-sm" :class="`badge-${stateTone(detail?.state)}`">
              {{ detail?.state || 'unknown' }}
            </span>
            <button class="btn btn-xs btn-ghost btn-square" @click="closeDrawer">
              <i class="fas fa-xmark"></i>
            </button>
          </div>

          <!-- quick actions -->
          <div class="flex flex-wrap gap-2 mt-2">
            <button v-if="detail?.state === 'running'" class="btn btn-xs btn-error btn-outline"
                    @click="askAction(detail, 'stop')">
              <i class="fas fa-stop"></i> Stop
            </button>
            <button v-else-if="detail?.state === 'paused'" class="btn btn-xs btn-success"
                    @click="askAction(detail, 'unpause')">
              <i class="fas fa-play"></i> Resume
            </button>
            <button v-else class="btn btn-xs btn-success" @click="askAction(detail, 'start')">
              <i class="fas fa-play"></i> Start
            </button>

            <button v-if="detail?.state === 'running'" class="btn btn-xs"
                    @click="askAction(detail, 'restart')">
              <i class="fas fa-rotate-right"></i> Restart
            </button>
            <button v-if="detail?.state === 'running'" class="btn btn-xs btn-ghost"
                    @click="askAction(detail, 'pause')">
              <i class="fas fa-pause"></i> Pause
            </button>

            <div class="flex-1"></div>
            <button class="btn btn-xs btn-ghost" @click="showJson(detail?.name, detail)">
              <i class="fas fa-code"></i> Inspect
            </button>
            <button class="btn btn-xs btn-ghost text-error" @click="askRemove(detail)">
              <i class="fas fa-trash-can"></i>
            </button>
          </div>
        </div>

        <!-- ── Tabs ─────────────────────────────────────────────────────── -->
        <div role="tablist" class="tabs tabs-boxed tabs-sm bg-base-200 mx-4 mt-3 shrink-0 flex-nowrap overflow-x-auto">
          <button v-for="t in DRAWER_TABS" :key="t.id" role="tab"
                  class="tab gap-1 whitespace-nowrap"
                  :class="{ 'tab-active': state.detailTab === t.id }"
                  @click="setDetailTab(t.id)">
            <i class="fas" :class="t.icon"></i>
            {{ t.label }}
          </button>
        </div>

        <!-- ── Body ─────────────────────────────────────────────────────── -->
        <div class="grow min-h-0 overflow-auto p-4 space-y-3">
          <!-- loading -->
          <div v-if="!detail" class="space-y-2">
            <div v-for="i in 5" :key="i" class="skeleton h-8 w-full"></div>
          </div>

          <!-- overview -->
          <template v-else-if="state.detailTab === 'overview'">
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

          <!-- logs -->
          <template v-else-if="state.detailTab === 'logs'">
            <div class="flex items-center gap-2">
              <span class="text-xs opacity-50">{{ state.logs.length }} lines</span>
              <div class="flex-1"></div>
              <button class="btn btn-xs btn-ghost" :disabled="state.logsLoading" @click="loadLogs()">
                <i class="fas fa-rotate-right" :class="{ 'animate-spin': state.logsLoading }"></i>
                Reload
              </button>
            </div>

            <div v-if="state.logsLoading && !state.logs.length" class="space-y-2">
              <div v-for="i in 8" :key="i" class="skeleton h-4 w-full"></div>
            </div>

            <pre v-else class="p-3 rounded-lg bg-base-300 text-[11px] leading-relaxed overflow-auto max-h-[60vh]"><template
              v-for="(line, i) in state.logs" :key="i"><span class="opacity-40">{{ fmtTime(line.ts) }}</span>  <span
              :class="logLevelClass(line.level)">{{ line.level }}</span>  {{ line.msg }}
</template></pre>
          </template>

          <!-- stats -->
          <template v-else-if="state.detailTab === 'stats'">
            <div v-if="state.statsLoading && !state.stats" class="space-y-2">
              <div v-for="i in 5" :key="i" class="skeleton h-8 w-full"></div>
            </div>

            <template v-else-if="state.stats">
              <div class="grid grid-cols-2 gap-2">
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
          <template v-else-if="state.detailTab === 'config'">
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
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
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
</script>
