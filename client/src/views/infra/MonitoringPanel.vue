<script setup>
import MonitoringChart from './MonitoringChart.vue'
</script>

<template>
  <div class="space-y-4">
    <!-- ── Collector status ─────────────────────────────────────────────────
         These charts are NOT a server-side history: every refresh appends one
         point to a client buffer (see useInfraMonitor.js). This row is the
         honest explanation of what the window contains and how fresh it is. -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs opacity-60">
      <span class="inline-flex items-center gap-1.5">
        <i class="fas fa-wave-square" :class="live ? 'text-success animate-pulse' : 'opacity-40'"></i>
        {{ live ? 'Sampling every ' + interval + 's' : 'Sampling paused' }}
      </span>
      <span><i class="fas fa-clock mr-1"></i>{{ windowLabel }}</span>
      <span v-if="lastSample"><i class="fas fa-rotate-right mr-1"></i>{{ fmtTime(lastSample.t) }}</span>
      <div class="flex-1"></div>
      <button class="btn btn-xs btn-ghost" :disabled="!samples.length"
              title="Discard the samples collected so far" @click="onClear">
        <i class="fas fa-eraser"></i> Clear
      </button>
    </div>

    <!-- ── Window aggregates ────────────────────────────────────────────────
         The live snapshot strip already sits above the tabs; these tiles add
         the one thing it cannot show: the trend inside the sampled window. -->
    <div class="grid gap-3" :class="layout.compact ? 'grid-cols-2' : 'grid-cols-3 xl:grid-cols-6'">
      <div v-for="kpi in kpis" :key="kpi.id" class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-1">
          <div class="flex items-center justify-between gap-1">
            <span class="text-[11px] font-medium uppercase tracking-wide opacity-60 truncate">{{ kpi.label }}</span>
            <i class="fas text-xs" :class="[kpi.icon, toneText(kpi.tone)]"></i>
          </div>
          <div class="text-xl font-bold leading-none">
            {{ kpi.value }}<span v-if="kpi.unit" class="text-xs opacity-50 ml-0.5">{{ kpi.unit }}</span>
          </div>
          <progress v-if="kpi.bar !== null" class="progress w-full h-1.5 mt-1"
                    :class="meterClass(kpi.tone)" :value="kpi.bar" max="100"></progress>
          <div class="text-[11px] opacity-50 truncate" :title="kpi.sub">{{ kpi.sub }}</div>
        </div>
      </div>
    </div>

    <!-- ── Host load: the primary signal, full width ────────────────────── -->
    <div class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body p-3 gap-2">
        <div class="flex items-center justify-between gap-2">
          <h3 class="text-sm font-semibold flex items-center gap-2">
            <i class="fas fa-gauge-high text-primary"></i> Host load
          </h3>
          <span class="text-[11px] opacity-50">{{ samples.length }} pts</span>
        </div>
        <div class="h-56">
          <MonitoringChart :samples="samples" :metrics="loadMetrics" :max-y="100"
                           unit="%" y-title="Usage %" />
        </div>
      </div>
    </div>

    <!-- ── Containers / resources over the window ───────────────────────── -->
    <div class="grid gap-3" :class="layout.compact ? 'grid-cols-1' : 'grid-cols-2'">
      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <h3 class="text-sm font-semibold flex items-center gap-2">
            <i class="fas fa-cubes text-success"></i> Containers by state
          </h3>
          <div class="h-48">
            <MonitoringChart :samples="samples" :metrics="stateMetrics" y-title="Containers" />
          </div>
        </div>
      </div>

      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <h3 class="text-sm font-semibold flex items-center gap-2">
            <i class="fas fa-hard-drive text-info"></i> Docker resources
          </h3>
          <div class="h-48">
            <MonitoringChart :samples="samples" :metrics="resourceMetrics" y-title="Count" />
          </div>
        </div>
      </div>
    </div>

    <!-- ── Problems + busiest containers ────────────────────────────────── -->
    <div class="grid gap-3" :class="layout.compact ? 'grid-cols-1' : 'grid-cols-2'">
      <!-- Rule based, from the live snapshot: each rule is something an
           operator wants to know BEFORE opening the per-resource tabs. -->
      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-center gap-2">
            <h3 class="text-sm font-semibold flex items-center gap-2">
              <i class="fas" :class="issues.length ? 'fa-triangle-exclamation text-warning' : 'fa-circle-check text-success'"></i>
              Possible problems
            </h3>
            <span v-if="issues.length" class="badge badge-sm badge-warning">{{ issues.length }}</span>
          </div>

          <p v-if="!issues.length" class="text-sm opacity-60">
            Nothing looks wrong — CPU, memory and disk are within range and every container reports healthy.
          </p>

          <ul v-else class="space-y-1.5">
            <li v-for="issue in issues" :key="issue.id"
                class="flex items-start gap-2 rounded-lg px-2 py-1.5" :class="rowClass(issue.tone)">
              <i class="fas mt-0.5 shrink-0" :class="[issue.icon, toneText(issue.tone)]"></i>
              <div class="min-w-0">
                <div class="text-sm font-medium">{{ issue.title }}</div>
                <div class="text-xs opacity-70 break-words">{{ issue.detail }}</div>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <div class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-center justify-between gap-2">
            <h3 class="text-sm font-semibold flex items-center gap-2">
              <i class="fas fa-fire text-error"></i> Busiest containers
            </h3>
            <span class="text-[11px] opacity-50">CPU now</span>
          </div>

          <p v-if="!topContainers.length" class="text-sm opacity-60">
            No running container reports CPU usage right now.
          </p>

          <ul v-else class="space-y-2.5">
            <li v-for="c in topContainers" :key="c.id">
              <div class="flex items-center justify-between gap-2 text-xs mb-1">
                <button class="font-mono truncate text-left min-w-0 hover:text-primary"
                        :title="'Open ' + c.name" @click="openContainer(c.id)">
                  {{ c.name }}
                </button>
                <span class="shrink-0 opacity-60 font-mono">{{ fmtNum(c.cpu_pct) }}% · {{ fmtBytes(c.mem_used) }}</span>
              </div>
              <progress class="progress w-full h-1.5"
                        :class="meterClass(tone(c.cpu_pct, 75, 90))"
                        :value="Math.min(100, Number(c.cpu_pct) || 0)" max="100"></progress>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { monitoring, clearSamples, MONITORING_MAX_SAMPLES } from './useInfraMonitor'
import { state, fmtBytes, fmtTime, tone, openContainer } from './useInfra'
import { layout } from './useInfraLayout'

/**
 * Infrastructure → Monitoring.
 *
 * Three time series over the client-side sample buffer, plus the diagnostics
 * an operator actually opens this tab for:
 *
 *   • window aggregates (now / peak / avg) — the live KPI strip above the tabs
 *     only ever shows the CURRENT value, never the trend;
 *   • "Possible problems" — deterministic rules (thresholds, healthchecks,
 *     restart loops) so nothing here is a guess;
 *   • "Busiest containers" — the usual culprit, one click away from its
 *     detail drawer.
 *
 * Presentation only: the polling cadence and the buffer belong to
 * useInfraMonitor.js, so this component can be mounted/unmounted freely.
 */
export default {
  name: 'MonitoringPanel',
  computed: {
    samples() {
      return monitoring.samples
    },
    live() {
      return monitoring.live
    },
    interval() {
      return monitoring.interval
    },
    summary() {
      return state.summary
    },
    containers() {
      return state.containers
    },
    counts() {
      return state.summary?.counts || {}
    },
    lastSample() {
      const list = monitoring.samples
      return list[list.length - 1] || null
    },
    memPct() {
      const s = state.summary
      if (!s || !s.mem_total) return 0
      return Math.round((s.mem_used / s.mem_total) * 100)
    },
    diskPct() {
      const s = state.summary
      if (!s || !s.disk_total) return 0
      return Math.round((s.disk_used / s.disk_total) * 100)
    },
    /** What the buffer actually covers: "42 / 120 samples · 3 min window". */
    windowLabel() {
      const count = monitoring.samples.length
      if (!count) return 'Waiting for the first sample'
      const seconds = Math.round(count * (Number(monitoring.interval) || 0))
      const span = seconds < 60 ? seconds + 's' : Math.round(seconds / 60) + ' min'
      return count + ' / ' + MONITORING_MAX_SAMPLES + ' samples · ' + span + ' window'
    },

    /* ── KPI tiles ───────────────────────────────────────────────────────── */
    kpis() {
      const last = this.lastSample
      const s = this.summary
      const cpu = last ? last.cpu : this.fmtNum(s?.cpu_pct)
      const mem = last ? last.mem : this.memPct
      const disk = last ? last.disk : this.diskPct
      const running = last ? last.running : (this.counts.running || 0)
      const total = last ? last.total : (this.counts.total || 0)
      const unhealthy = last ? last.unhealthy : (this.counts.unhealthy || 0)
      const restarting = last ? last.restarting : (this.counts.restarting || 0)

      return [
        {
          id: 'cpu',
          label: 'CPU',
          value: this.fmtNum(cpu),
          unit: '%',
          icon: 'fa-microchip',
          tone: tone(cpu, 75, 90),
          bar: Math.min(100, cpu),
          sub: 'peak ' + this.fmtNum(this.peak('cpu')) + '% · avg ' + this.fmtNum(this.avg('cpu')) + '%'
        },
        {
          id: 'mem',
          label: 'Memory',
          value: this.fmtNum(mem),
          unit: '%',
          icon: 'fa-memory',
          tone: tone(mem, 80, 90),
          bar: Math.min(100, mem),
          sub: fmtBytes(s?.mem_used) + ' / ' + fmtBytes(s?.mem_total)
        },
        {
          id: 'disk',
          label: 'Disk',
          value: this.fmtNum(disk),
          unit: '%',
          icon: 'fa-hard-drive',
          tone: tone(disk, 80, 90),
          bar: Math.min(100, disk),
          sub: fmtBytes(s?.disk_used) + ' / ' + fmtBytes(s?.disk_total)
        },
        {
          id: 'running',
          label: 'Containers up',
          value: running,
          unit: '/' + total,
          icon: 'fa-cubes',
          tone: running ? 'success' : 'warning',
          bar: null,
          sub: 'peak ' + this.peak('running') + ' in window'
        },
        {
          id: 'unhealthy',
          label: 'Unhealthy',
          value: unhealthy,
          icon: 'fa-heart-pulse',
          tone: unhealthy ? 'error' : 'success',
          bar: null,
          sub: unhealthy ? 'See the list beside' : 'All healthchecks passing'
        },
        {
          id: 'restarting',
          label: 'Restarting',
          value: restarting,
          icon: 'fa-rotate',
          tone: restarting ? 'warning' : 'success',
          bar: null,
          sub: 'peak ' + this.peak('restarting') + ' in window'
        }
      ]
    },

    /* ── Diagnostics ─────────────────────────────────────────────────────── */
    issues() {
      const list = []
      const last = this.lastSample
      const s = this.summary
      const containers = this.containers

      const cpu = last ? last.cpu : this.fmtNum(s?.cpu_pct)
      if (cpu >= 90) {
        list.push({
          id: 'cpu', tone: 'error', icon: 'fa-microchip',
          title: 'Host CPU at ' + this.fmtNum(cpu) + '%',
          detail: 'The host is saturated — containers will queue requests and may time out.'
        })
      } else if (cpu >= 80) {
        list.push({
          id: 'cpu', tone: 'warning', icon: 'fa-microchip',
          title: 'Host CPU at ' + this.fmtNum(cpu) + '%',
          detail: 'Sustained load. Check the busiest containers.'
        })
      }

      const mem = last ? last.mem : this.memPct
      if (mem >= 90) {
        list.push({
          id: 'mem', tone: 'error', icon: 'fa-memory',
          title: 'Memory at ' + this.fmtNum(mem) + '%',
          detail: 'Almost no headroom left — the OOM killer may terminate containers.'
        })
      } else if (mem >= 80) {
        list.push({
          id: 'mem', tone: 'warning', icon: 'fa-memory',
          title: 'Memory at ' + this.fmtNum(mem) + '%',
          detail: 'Memory pressure building up on the host.'
        })
      }

      const disk = last ? last.disk : this.diskPct
      if (disk >= 90) {
        list.push({
          id: 'disk', tone: 'error', icon: 'fa-hard-drive',
          title: 'Disk at ' + this.fmtNum(disk) + '%',
          detail: 'Image pulls and volume writes will start failing.'
        })
      } else if (disk >= 80) {
        list.push({
          id: 'disk', tone: 'warning', icon: 'fa-hard-drive',
          title: 'Disk at ' + this.fmtNum(disk) + '%',
          detail: 'Consider pruning unused images and volumes from Maintenance.'
        })
      }

      const unhealthy = containers.filter(c => c.health === 'unhealthy')
      if (unhealthy.length) {
        list.push({
          id: 'unhealthy', tone: 'error', icon: 'fa-heart-pulse',
          title: unhealthy.length + (unhealthy.length === 1 ? ' container is unhealthy' : ' containers are unhealthy'),
          detail: this.names(unhealthy)
        })
      }

      // A restart count that high means the container is crash-looping, whether
      // it is currently up or not.
      const loops = containers.filter(c => Number(c.restart_count) >= 5)
      if (loops.length) {
        const worst = loops.reduce((max, c) => Math.max(max, Number(c.restart_count) || 0), 0)
        list.push({
          id: 'restarts', tone: 'warning', icon: 'fa-rotate',
          title: loops.length + ' container(s) restarted repeatedly',
          detail: this.names(loops) + ' · up to ' + worst + ' restarts'
        })
      }

      const restarting = containers.filter(c => c.state === 'restarting')
      if (restarting.length) {
        list.push({
          id: 'restarting', tone: 'warning', icon: 'fa-arrows-rotate',
          title: restarting.length + ' container(s) stuck restarting',
          detail: this.names(restarting)
        })
      }

      const stopped = containers.filter(c => ['exited', 'dead'].includes(c.state))
      if (stopped.length) {
        list.push({
          id: 'stopped', tone: 'info', icon: 'fa-circle-pause',
          title: stopped.length + ' stopped container(s)',
          detail: 'They pin their images and keep a writable layer. Prune them from Maintenance.'
        })
      }

      const order = { error: 0, warning: 1, info: 2 }
      return list.sort((a, b) => order[a.tone] - order[b.tone])
    },

    topContainers() {
      return this.containers
        .filter(c => c.state === 'running')
        .slice()
        .sort((a, b) => (Number(b.cpu_pct) || 0) - (Number(a.cpu_pct) || 0))
        .slice(0, 5)
    },

    /* ── Chart series (same palette as the analytics charts) ─────────────── */
    loadMetrics() {
      return [
        { key: 'cpu', label: 'CPU', color: '#6366f1', fill: true },
        { key: 'mem', label: 'Memory', color: '#10b981', fill: true },
        { key: 'disk', label: 'Disk', color: '#f59e0b' }
      ]
    },
    stateMetrics() {
      return [
        { key: 'running', label: 'Running', color: '#10b981', fill: true },
        { key: 'restarting', label: 'Restarting', color: '#f59e0b' },
        { key: 'unhealthy', label: 'Unhealthy', color: '#ef4444' },
        { key: 'stopped', label: 'Stopped', color: '#6b7280' }
      ]
    },
    resourceMetrics() {
      return [
        { key: 'images', label: 'Images', color: '#3b82f6' },
        { key: 'volumes', label: 'Volumes', color: '#8b5cf6' },
        { key: 'networks', label: 'Networks', color: '#9ca3af' }
      ]
    }
  },
  methods: {
    fmtBytes,
    fmtTime,
    tone,
    openContainer,

    /** One decimal, no trailing ".0" (charts and tiles must agree). */
    fmtNum(value) {
      const num = Math.round((Number(value) || 0) * 10) / 10
      return Number.isInteger(num) ? String(num) : num.toFixed(1)
    },

    /** Highest value of `key` across the sample buffer. */
    peak(key) {
      const values = this.samples.map(sample => Number(sample[key]) || 0)
      return values.length ? Math.max(...values) : 0
    },

    /** Mean value of `key` across the sample buffer (one decimal). */
    avg(key) {
      const values = this.samples.map(sample => Number(sample[key]) || 0)
      if (!values.length) return 0
      const total = values.reduce((sum, value) => sum + value, 0)
      return Math.round((total / values.length) * 10) / 10
    },

    /** "a, b, c +2 more" — keeps the diagnostics lines readable. */
    names(list) {
      const names = list.map(item => item.name || item.id).filter(Boolean)
      const head = names.slice(0, 3).join(', ')
      return names.length > 3 ? head + ' +' + (names.length - 3) + ' more' : head
    },

    toneText(toneName) {
      return {
        success: 'text-success',
        warning: 'text-warning',
        error: 'text-error',
        info: 'text-info'
      }[toneName] || 'opacity-40'
    },
    rowClass(toneName) {
      return {
        success: 'bg-success/10',
        warning: 'bg-warning/10',
        error: 'bg-error/10',
        info: 'bg-info/10'
      }[toneName] || 'bg-base-300'
    },
    meterClass(toneName) {
      return {
        success: 'progress-success',
        warning: 'progress-warning',
        error: 'progress-error'
      }[toneName] || 'progress-primary'
    },

    onClear() {
      clearSamples()
    }
  }
}
</script>