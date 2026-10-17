<template>
  <div>
    <!-- ── Empty state ────────────────────────────────────────────────────── -->
    <div v-if="!filteredList.length" class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body items-center text-center py-12">
        <i class="fas fa-cube text-4xl opacity-30"></i>
        <h3 class="card-title mt-2">
          {{ hasContainers ? 'No containers match your filters' : 'No containers found' }}
        </h3>
        <p class="text-sm opacity-60">
          {{ hasContainers
            ? 'Try clearing the search box, the state or the stack filter.'
            : 'Containers running on this Docker host are listed here.' }}
        </p>
        <div v-if="hasContainers" class="card-actions mt-2">
          <button class="btn btn-sm btn-ghost" @click="clearFilters">
            <i class="fas fa-filter-circle-xmark"></i> Clear filters
          </button>
        </div>
      </div>
    </div>

    <!-- ── Container list ──────────────────────────────────────────────────
         ONE markup for every breakpoint: the table scrolls horizontally when
         the panel is narrow. Never gate it behind `hidden lg:block` — inside a
         dockview panel the breakpoint would hide the whole list. -->
    <div v-else class="card bg-base-200 border border-base-300 shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="table table-sm">
          <thead>
            <tr>
              <th>Container</th>
              <th class="w-56">State</th>
              <th class="text-right w-20">CPU</th>
              <th class="w-44">Memory</th>
              <th class="w-32">Ports</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in filteredList" :key="c.id"
                class="hover cursor-pointer"
                @click="openContainer(c.id)">
              <td>
                <div class="flex flex-col min-w-0">
                  <div class="flex items-center gap-2">
                    <i class="fas fa-cube text-xs opacity-40"></i>
                    <span class="font-semibold truncate">{{ c.name }}</span>
                    <span v-if="c.stack" class="badge badge-xs badge-ghost">{{ c.stack }}</span>
                    <span v-if="c.sysbox" class="badge badge-xs badge-outline">sysbox</span>
                  </div>
                  <span class="text-xs opacity-50 font-mono truncate">{{ c.image }}</span>
                </div>
              </td>

              <td>
                <div class="flex items-center gap-2">
                  <span class="inline-block w-2 h-2 rounded-full" :class="dotClass(c.state)"></span>
                  <span class="text-xs font-semibold">{{ c.state }}</span>
                  <span v-if="c.health" class="badge badge-xs" :class="`badge-${healthTone(c.health)}`">
                    {{ c.health }}
                  </span>
                </div>
                <span class="text-[11px] opacity-50">{{ stateLabel(c) }}</span>
              </td>

              <td class="text-right font-mono text-xs">
                {{ (c.cpu_pct || 0).toFixed(1) }}<span class="opacity-40">%</span>
              </td>

              <td>
                <div class="flex items-center justify-between text-xs">
                  <span class="font-mono">{{ fmtBytes(c.mem_used) }}</span>
                  <span class="opacity-40">/ {{ fmtBytes(c.mem_limit) }}</span>
                </div>
                <progress class="progress w-full h-1 mt-1"
                          :class="`progress-${tone(c.mem_pct, 85, 95)}`"
                          :value="c.mem_pct" max="100"></progress>
              </td>

              <td>
                <div class="flex flex-wrap gap-1">
                  <span v-for="(p, i) in publishedPorts(c)" :key="i"
                        class="badge badge-xs badge-outline font-mono">
                    :{{ p.host }}→{{ p.container }}
                  </span>
                  <span v-if="!publishedPorts(c).length" class="text-xs opacity-30">—</span>
                </div>
              </td>

              <td @click.stop>
                <div class="flex justify-end gap-1">
                  <button v-if="c.state === 'running'"
                          class="btn btn-xs btn-error btn-outline"
                          title="Stop" @click="askAction(c, 'stop')">
                    <i class="fas fa-stop"></i>
                  </button>
                  <button v-else-if="c.state === 'paused'"
                          class="btn btn-xs btn-success btn-outline"
                          title="Resume" @click="askAction(c, 'unpause')">
                    <i class="fas fa-play"></i>
                  </button>
                  <button v-else
                          class="btn btn-xs btn-success"
                          title="Start" @click="askAction(c, 'start')">
                    <i class="fas fa-play"></i>
                  </button>

                  <button v-if="c.state === 'running'" class="btn btn-xs"
                          title="Restart" @click="askAction(c, 'restart')">
                    <i class="fas fa-rotate-right"></i>
                  </button>
                  <button v-if="c.state === 'running'" class="btn btn-xs btn-ghost"
                          title="Pause" @click="askAction(c, 'pause')">
                    <i class="fas fa-pause"></i>
                  </button>

                  <button class="btn btn-xs btn-ghost" title="Logs" @click="openContainer(c.id)">
                    <i class="fas fa-file-lines"></i>
                  </button>
                  <button class="btn btn-xs btn-ghost" title="Inspect" @click="showJson(c.name, c)">
                    <i class="fas fa-code"></i>
                  </button>
                  <button class="btn btn-xs btn-ghost text-error" title="Remove" @click="askRemove(c)">
                    <i class="fas fa-trash-can"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  state, filteredList, setFilter, stateLabel, fmtBytes, tone,
  stateTone, dotClass, healthTone,
  openContainer, askAction, askRemove, showJson
} from './useInfra'

/** True when the host has containers at all (i.e. the empty state is filter-driven). */
const hasContainers = computed(() => state.containers.length > 0)

function clearFilters() {
  setFilter({ q: '', state: 'all', stack: 'all' })
}

/** Only the ports actually published on the host. */
function publishedPorts(container) {
  return (container.ports || []).filter(p => p.published && p.host)
}
</script>