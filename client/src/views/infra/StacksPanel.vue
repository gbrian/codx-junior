<template>
  <div>
    <div v-if="!filteredList.length" class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body items-center text-center py-12">
        <i class="fas fa-layer-group text-4xl opacity-30"></i>
        <h3 class="card-title mt-2">No compose stacks found</h3>
        <p class="text-sm opacity-60">Containers started with docker compose are grouped here.</p>
      </div>
    </div>

    <div v-else class="grid grid-cols-1 xl:grid-cols-2 gap-3">
      <div v-for="s in filteredList" :key="s.name" class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-start gap-2">
            <i class="fas fa-layer-group text-primary mt-1"></i>
            <div class="min-w-0 grow">
              <div class="font-bold truncate">{{ s.name }}</div>
              <div class="text-[11px] opacity-50 font-mono truncate">{{ s.path }}</div>
            </div>
            <span class="badge badge-sm" :class="statusBadge(s.status)">{{ s.status }}</span>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-xs opacity-60">{{ s.running }}/{{ s.total }} services running</span>
            <progress class="progress grow h-1"
                      :class="s.running === s.total ? 'progress-success' : s.running ? 'progress-warning' : 'progress-error'"
                      :value="s.total ? (s.running / s.total) * 100 : 0" max="100"></progress>
          </div>

          <div class="overflow-x-auto">
            <table class="table table-xs">
              <tbody>
                <tr v-for="svc in s.services" :key="svc.id">
                  <td class="w-6">
                    <span class="inline-block w-2 h-2 rounded-full" :class="dotClass(svc.state)"></span>
                  </td>
                  <td class="font-mono text-xs">{{ svc.service || svc.name }}</td>
                  <td class="text-xs opacity-60">{{ svc.name }}</td>
                  <td class="text-xs">
                    <span class="badge badge-xs" :class="`badge-${stateTone(svc.state)}`">{{ svc.state }}</span>
                    <span v-if="svc.health" class="badge badge-xs ml-1" :class="`badge-${healthTone(svc.health)}`">
                      {{ svc.health }}
                    </span>
                  </td>
                  <td class="text-right">
                    <button class="btn btn-xs btn-ghost" title="Details" @click="openContainer(svc.id)">
                      <i class="fas fa-chevron-right"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="card-actions justify-end">
            <button class="btn btn-xs btn-ghost" @click="showJson(s.name, s)">
              <i class="fas fa-code"></i> Inspect
            </button>
            <button class="btn btn-xs" @click="filterContainers(s.name)">
              <i class="fas fa-cube"></i> Containers
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  filteredList, stateTone, dotClass, healthTone,
  openContainer, showJson, setRoute, setFilter
} from './useInfra'

function statusBadge(status) {
  return {
    running: 'badge-success',
    degraded: 'badge-warning',
    stopped: 'badge-error'
  }[status] || 'badge-ghost'
}

function filterContainers(stack) {
  setFilter({ stack, q: '' })
  setRoute('containers')
}
</script>
