<template>
  <!-- ── Responsive shell ────────────────────────────────────────────────────
       This view is rendered inside a RESIZABLE dockview panel, so "mobile"
       must mean "this panel is narrow", not "the browser window is narrow".
       The panel width is measured by `observePanelWidth()` (see
       useInfraLayout.js) and every layout decision below reads `layout.*`. -->
  <div ref="rootEl" class="infra-view w-full h-full overflow-auto pb-28"
       :class="layout.compact ? 'p-4' : 'p-6'">
    <!-- ── Header ───────────────────────────────────────────────────────── -->
    <div class="flex flex-wrap items-start gap-3 mb-4">
      <div class="min-w-0">
        <h1 class="text-2xl font-bold leading-tight flex items-center gap-2">
          <i class="fas fa-server text-primary"></i>
          Infrastructure
        </h1>
        <p class="text-sm opacity-60 mt-0.5">
          Every container deployed on your Docker host — state, resources, ports and logs.
        </p>
      </div>
      <div class="flex-1"></div>

      <div class="flex flex-wrap items-center gap-2">
        <label class="sr-only" for="host-select">Host</label>
        <select id="host-select" class="select select-bordered select-sm"
                :class="layout.compact ? 'grow w-full' : 'w-56'"
                :value="state.hostId" @change="onHostChange">
          <option v-for="h in state.hosts" :key="h.id" :value="h.id">
            {{ h.is_local ? '🐳' : '🛰️' }} {{ h.name }}
          </option>
        </select>

        <label class="label cursor-pointer gap-2 py-0">
          <span class="label-text text-xs">Live</span>
          <input type="checkbox" class="toggle toggle-sm toggle-primary"
                 :checked="state.autoRefresh" @change="toggleLive($event.target.checked)" />
        </label>

        <button class="btn btn-sm" @click="reloadAll">
          <i class="fas fa-arrows-rotate"></i> Refresh
        </button>
        <button class="btn btn-sm btn-primary" @click="openRunModal()">
          <i class="fas fa-plus"></i> Run container
        </button>
      </div>
    </div>

    <!-- ── Host KPI strip ───────────────────────────────────────────────── -->
    <div v-if="state.summary" class="stats w-full bg-base-200 border border-base-300 shadow-sm mb-4"
         :class="layout.compact ? 'stats-vertical' : 'stats-horizontal'">
      <div class="stat">
        <div class="stat-title">CPU · {{ state.summary.cpu_cores }} cores</div>
        <div class="stat-value text-2xl">{{ state.summary.cpu_pct }}<span class="text-base opacity-50">%</span></div>
        <div class="stat-desc">
          <progress class="progress w-full"
                    :class="meterClass(tone(state.summary.cpu_pct, 85, 65))"
                    :value="Math.min(100, state.summary.cpu_pct)" max="100"></progress>
        </div>
      </div>

      <div class="stat">
        <div class="stat-title">Memory</div>
        <div class="stat-value text-2xl">{{ memPct }}<span class="text-base opacity-50">%</span></div>
        <div class="stat-desc">
          <progress class="progress w-full"
                    :class="meterClass(tone(memPct, 85, 65))"
                    :value="memPct" max="100"></progress>
          <span class="block mt-1 opacity-70">{{ fmtBytes(state.summary.mem_used) }} / {{ fmtBytes(state.summary.mem_total) }}</span>
        </div>
      </div>

      <div class="stat">
        <div class="stat-title">Disk</div>
        <div class="stat-value text-2xl">{{ diskPct }}<span class="text-base opacity-50">%</span></div>
        <div class="stat-desc">
          <progress class="progress w-full"
                    :class="meterClass(tone(diskPct, 85, 70))"
                    :value="diskPct" max="100"></progress>
          <span class="block mt-1 opacity-70">{{ fmtBytes(state.summary.disk_used) }} / {{ fmtBytes(state.summary.disk_total) }}</span>
        </div>
      </div>

      <div class="stat">
        <div class="stat-title">Containers</div>
        <div class="stat-value text-2xl">{{ counts.running }}<span class="text-base opacity-50">/{{ counts.total }}</span></div>
        <div class="stat-desc flex flex-wrap gap-1 mt-1">
          <span class="badge badge-sm badge-success badge-outline">{{ counts.running }} up</span>
          <span class="badge badge-sm badge-outline">{{ counts.stopped }} stopped</span>
          <span v-if="counts.paused" class="badge badge-sm badge-info badge-outline">{{ counts.paused }} paused</span>
          <span v-if="counts.restarting" class="badge badge-sm badge-warning badge-outline">{{ counts.restarting }} restarting</span>
          <span v-if="counts.unhealthy" class="badge badge-sm badge-error badge-outline">{{ counts.unhealthy }} unhealthy</span>
        </div>
      </div>

      <div class="stat">
        <div class="stat-title">Images</div>
        <div class="stat-value text-2xl">{{ counts.images }}</div>
        <div class="stat-desc">Engine {{ state.summary.engine }}</div>
      </div>

      <div class="stat">
        <div class="stat-title">Volumes · Networks</div>
        <div class="stat-value text-2xl">{{ counts.volumes }}<span class="text-base opacity-50"> · {{ counts.networks }}</span></div>
        <div class="stat-desc">{{ state.summary.host.name }}</div>
      </div>
    </div>

    <div v-else-if="state.status === 'loading'" class="grid gap-3 mb-4"
         :class="layout.compact ? 'grid-cols-2' : 'grid-cols-6'">
      <div v-for="i in 6" :key="i" class="skeleton h-24 w-full"></div>
    </div>

    <!-- last updated -->
    <div class="text-xs opacity-50 mb-3 flex items-center gap-2">
      <i class="fas fa-clock"></i>
      <span>{{ state.lastUpdated ? 'Updated ' + fmtTime(state.lastUpdated.toISOString()) : 'Not loaded' }}</span>
    </div>

    <!-- ── Tabs ─────────────────────────────────────────────────────────── -->
    <div role="tablist" class="tabs tabs-boxed bg-base-200 w-full flex-wrap justify-start">
      <button v-for="t in TABS" :key="t.id" role="tab"
              class="tab gap-2" :class="{ 'tab-active': state.route === t.id }"
              @click="setRoute(t.id)">
        <i class="fas" :class="t.icon"></i>
        {{ t.label }}
        <span class="badge badge-sm" :class="state.route === t.id ? 'badge-primary' : 'badge-ghost'">{{ tabCount(t.id) }}</span>
      </button>
    </div>

    <!-- ── Content ──────────────────────────────────────────────────────── -->
    <div class="mt-4">
      <!-- error -->
      <div v-if="state.status === 'error'" class="card bg-base-200 border border-base-300">
        <div class="card-body items-center text-center py-12">
          <i class="fas fa-triangle-exclamation text-error text-4xl"></i>
          <h3 class="card-title mt-2">Could not reach the Docker daemon</h3>
          <p class="opacity-60 text-sm max-w-md">{{ state.error }}</p>
          <div class="card-actions mt-2">
            <button class="btn btn-primary btn-sm" @click="loadAll()"><i class="fas fa-rotate-right"></i> Retry</button>
          </div>
        </div>
      </div>

      <template v-else>
        <!-- filters (each control takes its own row in a narrow panel).
             Maintenance carries its own toolbar + search-less review list, so
             the shared container/image/volume filters would only be noise. -->
        <div v-if="state.route !== 'maintenance'" class="flex flex-wrap items-center gap-2 mb-3">
          <label class="input input-bordered input-sm flex items-center gap-2"
                 :class="layout.compact ? 'w-full' : 'flex-1 min-w-56 max-w-96'">
            <i class="fas fa-magnifying-glass opacity-50"></i>
            <input type="text" class="grow min-w-0" :placeholder="searchPlaceholder"
                   :value="state.filters.q" @input="setFilter({ q: $event.target.value })" />
          </label>

          <select v-if="state.route === 'containers'" class="select select-bordered select-sm"
                  :class="layout.compact ? 'grow' : 'w-40'"
                  :value="state.filters.state" @change="setFilter({ state: $event.target.value })">
            <option value="all">All states</option>
            <option value="running">Running</option>
            <option value="exited">Exited</option>
            <option value="restarting">Restarting</option>
            <option value="paused">Paused</option>
            <option value="unhealthy">Unhealthy</option>
          </select>

          <select v-if="state.route === 'containers' || state.route === 'stacks'"
                  class="select select-bordered select-sm"
                  :class="layout.compact ? 'grow' : 'w-40'"
                  :value="state.filters.stack" @change="setFilter({ stack: $event.target.value })">
            <option value="all">All stacks</option>
            <option v-for="s in state.stacks" :key="s.name" :value="s.name">{{ s.name }}</option>
          </select>

          <select v-if="['containers', 'images', 'volumes'].includes(state.route)"
                  class="select select-bordered select-sm"
                  :class="layout.compact ? 'grow' : 'w-36'"
                  :value="state.filters.sort" @change="setFilter({ sort: $event.target.value })">
            <option value="name">Sort: Name</option>
            <option value="cpu">Sort: CPU %</option>
            <option value="mem">Sort: Memory</option>
            <option value="created">Sort: Created</option>
          </select>

          <div class="flex-1"></div>
          <span class="text-xs opacity-50">{{ filteredList.length }} item(s)</span>
        </div>

        <!-- loading skeleton -->
        <div v-if="state.status === 'loading' || state.status === 'idle'" class="card bg-base-200 border border-base-300 p-4 space-y-3">
          <div v-for="i in 6" :key="i" class="skeleton h-10 w-full"></div>
        </div>

        <!-- panels -->
        <template v-else>
          <ContainersPanel v-if="state.route === 'containers'" />
          <StacksPanel v-else-if="state.route === 'stacks'" />
          <ImagesPanel v-else-if="state.route === 'images'" />
          <VolumesPanel v-else-if="state.route === 'volumes'" />
          <NetworksPanel v-else-if="state.route === 'networks'" />
          <EventsPanel v-else-if="state.route === 'events'" />
          <MaintenancePanel v-else-if="state.route === 'maintenance'" />
        </template>
      </template>
    </div>

    <!-- ── Container detail drawer ──────────────────────────────────────── -->
    <ContainerDrawer />

    <!-- ── Modals ─────────────────────────────────────────────────────────
         Teleported to <body>: full-window overlays, so they stay viewport
         based on purpose. -->
    <Teleport to="body">
      <!-- confirm -->
      <div v-if="state.modal && state.modal.type === 'confirm'" class="modal modal-open">
        <div class="modal-box">
          <h3 class="font-bold text-lg flex items-center gap-2">
            <i class="fas fa-triangle-exclamation" :class="state.modal.danger ? 'text-error' : 'text-primary'"></i>
            {{ state.modal.title }}
          </h3>
          <p class="py-3 text-sm opacity-80" v-html="state.modal.html"></p>
          <div class="modal-action">
            <button class="btn btn-sm btn-ghost" @click="state.modal = null">Cancel</button>
            <button class="btn btn-sm" :class="state.modal.danger ? 'btn-error' : 'btn-primary'"
                    @click="state.modal.onConfirm && state.modal.onConfirm()">
              {{ state.modal.confirmText }}
            </button>
          </div>
        </div>
        <div class="modal-backdrop" @click="state.modal = null"></div>
      </div>

      <!-- json inspect -->
      <div v-if="state.modal && state.modal.type === 'json'" class="modal modal-open">
        <div class="modal-box max-w-3xl">
          <h3 class="font-bold flex items-center gap-2"><i class="fas fa-code"></i> {{ state.modal.title }}</h3>
          <pre class="my-3 p-3 rounded-lg bg-base-300 text-xs overflow-auto max-h-[60vh]">{{ state.modal.json }}</pre>
          <div class="modal-action">
            <button class="btn btn-sm btn-ghost" @click="state.modal = null">Close</button>
          </div>
        </div>
        <div class="modal-backdrop" @click="state.modal = null"></div>
      </div>

      <!-- run container -->
      <div v-if="state.modal && state.modal.type === 'run'" class="modal modal-open">
        <div class="modal-box">
          <h3 class="font-bold text-lg flex items-center gap-2"><i class="fas fa-play"></i> Run a new container</h3>
          <div class="py-3 space-y-3 max-h-[60vh] overflow-auto">
            <div>
              <label class="label-text text-xs" for="run-name">Container name *</label>
              <input id="run-name" class="input input-bordered input-sm w-full"
                     :class="{ 'input-error': state.modal.errors.name }"
                     placeholder="e.g. my-worker"
                     :value="state.modal.form.name"
                     @input="updateRunField('name', $event.target.value)" />
              <p v-if="state.modal.errors.name" class="text-error text-xs mt-1">{{ state.modal.errors.name }}</p>
            </div>
            <div>
              <label class="label-text text-xs" for="run-image">Image *</label>
              <input id="run-image" class="input input-bordered input-sm w-full"
                     :class="{ 'input-error': state.modal.errors.image }"
                     placeholder="e.g. redis:7-alpine"
                     :value="state.modal.form.image"
                     @input="updateRunField('image', $event.target.value)" />
              <p v-if="state.modal.errors.image" class="text-error text-xs mt-1">{{ state.modal.errors.image }}</p>
            </div>
            <div>
              <label class="label-text text-xs" for="run-ports">Port mappings</label>
              <input id="run-ports" class="input input-bordered input-sm w-full"
                     placeholder="8001:8001, 9000:9000"
                     :value="state.modal.form.ports"
                     @input="updateRunField('ports', $event.target.value)" />
              <p class="text-xs opacity-50 mt-1">Comma separated host:container mappings</p>
            </div>
            <div>
              <label class="label-text text-xs" for="run-env">Environment variables</label>
              <input id="run-env" class="input input-bordered input-sm w-full"
                     placeholder="NODE_ENV=production, PORT=3000"
                     :value="state.modal.form.env"
                     @input="updateRunField('env', $event.target.value)" />
            </div>
            <div>
              <label class="label-text text-xs" for="run-cmd">Command (optional)</label>
              <input id="run-cmd" class="input input-bordered input-sm w-full"
                     placeholder="node server.js"
                     :value="state.modal.form.cmd"
                     @input="updateRunField('cmd', $event.target.value)" />
            </div>
          </div>
          <div class="modal-action">
            <button class="btn btn-sm btn-ghost" @click="state.modal = null">Cancel</button>
            <button class="btn btn-sm btn-primary" :disabled="state.modal.submitting" @click="submitRun()">
              <span v-if="state.modal.submitting" class="loading loading-spinner loading-xs"></span>
              <i v-else class="fas fa-play"></i>
              {{ state.modal.submitting ? 'Starting…' : 'Run container' }}
            </button>
          </div>
        </div>
        <div class="modal-backdrop" @click="state.modal = null"></div>
      </div>
    </Teleport>

    <!-- ── Toasts ───────────────────────────────────────────────────────── -->
    <div class="toast toast-end toast-top z-[90]">
      <div v-for="t in state.toasts" :key="t.id"
           class="alert shadow-lg" :class="toastClass(t.kind)">
        <i class="fas" :class="toastIcon(t.kind)"></i>
        <span class="text-sm">{{ t.text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import {
  useInfra, TABS, fmtTime, fmtBytes, tone
} from './useInfra'
import { layout, observePanelWidth } from './useInfraLayout'
import ContainersPanel from './ContainersPanel.vue'
import ContainerDrawer from './ContainerDrawer.vue'
import StacksPanel from './StacksPanel.vue'
import ImagesPanel from './ImagesPanel.vue'
import VolumesPanel from './VolumesPanel.vue'
import NetworksPanel from './NetworksPanel.vue'
import EventsPanel from './EventsPanel.vue'
import MaintenancePanel from './MaintenancePanel.vue'

const {
  state, filteredList, tabCount,
  loadHosts, loadAll, setRoute, setHost, setFilter,
  openRunModal, submitRun, updateRunField,
  toggleLive
} = useInfra()

/* ── panel width tracking (this view lives in a resizable dockview panel) ─── */
const rootEl = ref(null)
let disposeLayout = null

/* ── derived ──────────────────────────────────────────────────────────────── */
const counts = computed(() => state.summary?.counts || {
  total: 0, running: 0, stopped: 0, paused: 0, restarting: 0, unhealthy: 0, images: 0, volumes: 0, networks: 0
})

const memPct = computed(() => {
  const s = state.summary
  return s ? Math.round((s.mem_used / s.mem_total) * 100) : 0
})
const diskPct = computed(() => {
  const s = state.summary
  return s ? Math.round((s.disk_used / s.disk_total) * 100) : 0
})

const searchPlaceholder = computed(() => ({
  containers: 'Search by name, image, service, stack…',
  stacks: 'Search stacks…',
  images: 'Search repository or tag…',
  volumes: 'Search volumes…',
  networks: 'Search networks…',
  events: 'Filter events by actor…'
}[state.route] || 'Search…'))

/* ── helpers ──────────────────────────────────────────────────────────────── */
function onHostChange (e) { setHost(e.target.value) }
function reloadAll () { loadAll() }

function meterClass (toneName) {
  return { success: 'progress-success', warning: 'progress-warning', error: 'progress-error' }[toneName] || 'progress-primary'
}
function toastClass (kind) {
  return { success: 'alert-success', error: 'alert-error', warning: 'alert-warning' }[kind] || 'alert-info'
}
function toastIcon (kind) {
  return {
    success: 'fa-circle-check',
    error: 'fa-circle-xmark',
    warning: 'fa-triangle-exclamation'
  }[kind] || 'fa-circle-info'
}

/* ── lifecycle ────────────────────────────────────────────────────────────── */
onMounted(async () => {
  disposeLayout = observePanelWidth(rootEl.value)
  await loadHosts()
  await loadAll()
})
onBeforeUnmount(() => {
  if (disposeLayout) {
    disposeLayout()
    disposeLayout = null
  }
  // stop polling when the view unmounts
  if (state.autoRefresh) toggleLive(false)
})
</script>