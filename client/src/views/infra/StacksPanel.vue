<template>
  <div>
    <div v-if="!filteredList.length" class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body items-center text-center py-12">
        <i class="fas fa-layer-group text-4xl opacity-30"></i>
        <h3 class="card-title mt-2">No compose stacks found</h3>
        <p class="text-sm opacity-60">Containers started with docker compose are grouped here.</p>
      </div>
    </div>

    <!-- Two columns only when the PANEL is wide enough for two readable cards
         (`layout.twoCol`, >= 56rem / 896px). -->
    <div v-else class="grid gap-3" :class="layout.twoCol ? 'grid-cols-2' : 'grid-cols-1'">
      <div v-for="s in filteredList" :key="s.name" class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-start gap-2">
            <i class="fas fa-layer-group text-primary mt-1"></i>
            <div class="min-w-0 grow">
              <div class="font-bold truncate">{{ s.name }}</div>
              <div class="text-[11px] opacity-50 font-mono truncate">{{ s.path }}</div>
            </div>
            <!-- A compose command is running on this stack: `up`, `build` and
                 `down` are long enough that the card must say so. -->
            <span v-if="stackActionBusy(s.name)" class="loading loading-spinner loading-xs mt-1 shrink-0"
                  title="A compose command is running"></span>
            <span class="badge badge-sm" :class="statusBadge(s.status)">{{ s.status }}</span>
          </div>

          <div class="flex items-center gap-2">
            <span class="text-xs opacity-60">{{ s.running }}/{{ s.total }} services running</span>
            <progress class="progress grow h-1"
                      :class="s.running === s.total ? 'progress-success' : s.running ? 'progress-warning' : 'progress-error'"
                      :value="s.total ? (s.running / s.total) * 100 : 0" max="100"></progress>
          </div>

          <!-- Services: compact rows, readable at any panel width -->
          <ul class="space-y-1">
            <li v-for="svc in s.services" :key="svc.id"
                class="flex items-center gap-2 rounded-lg bg-base-300/40 px-2 py-1.5">
              <span class="inline-block w-2 h-2 rounded-full shrink-0" :class="dotClass(svc.state)"></span>
              <span class="font-mono text-xs truncate grow">{{ svc.service || svc.name }}</span>
              <span class="badge badge-xs shrink-0" :class="`badge-${stateTone(svc.state)}`">{{ svc.state }}</span>
              <span v-if="svc.health" class="badge badge-xs shrink-0" :class="`badge-${healthTone(svc.health)}`">
                {{ svc.health }}
              </span>
              <button class="btn btn-xs btn-ghost btn-square shrink-0"
                      title="Details" aria-label="Details" @click="openContainer(svc.id)">
                <i class="fas fa-chevron-right"></i>
              </button>
            </li>
          </ul>

          <!-- ── Compose commands ──────────────────────────────────────────
               Same vocabulary as the container rows: ONE labelled primary
               action that matches the current state (`up` when stopped, `stop`
               when running), then square icon buttons for the rest.
               Every button is disabled while a command runs on this stack and
               stops the click locally (the card has no row click today, but the
               pattern keeps the actions safe if one is ever added). -->
          <div class="flex flex-wrap items-center gap-1.5 pt-2 border-t border-base-300">
            <button v-if="s.running" class="btn btn-xs btn-error btn-outline grow"
                    :disabled="stackActionBusy(s.name)"
                    title="Stop every service"
                    @click.stop="askStackAction(s, 'stop')">
              <i class="fas fa-stop"></i> Stop
            </button>
            <button v-else class="btn btn-xs btn-success grow"
                    :disabled="stackActionBusy(s.name)"
                    title="Run docker compose up -d"
                    @click.stop="askStackAction(s, 'up')">
              <i class="fas fa-play"></i> Start
            </button>

            <button v-if="s.running" class="btn btn-xs btn-square"
                    title="Restart every service" aria-label="Restart every service"
                    :disabled="stackActionBusy(s.name)"
                    @click.stop="askStackAction(s, 'restart')">
              <i class="fas fa-rotate-right" :class="{ 'animate-spin': stackActionBusy(s.name, 'restart') }"></i>
            </button>

            <!-- build / pull need no confirmation: they are idempotent, so the
                 icon only reports the command through its own animation. -->
            <button class="btn btn-xs btn-square btn-ghost"
                    title="Build images" aria-label="Build images"
                    :disabled="stackActionBusy(s.name)"
                    @click.stop="askStackAction(s, 'build')">
              <i class="fas fa-hammer" :class="{ 'animate-pulse': stackActionBusy(s.name, 'build') }"></i>
            </button>
            <button class="btn btn-xs btn-square btn-ghost"
                    title="Pull images" aria-label="Pull images"
                    :disabled="stackActionBusy(s.name)"
                    @click.stop="askStackAction(s, 'pull')">
              <i class="fas fa-download" :class="{ 'animate-pulse': stackActionBusy(s.name, 'pull') }"></i>
            </button>

            <button class="btn btn-xs btn-square btn-ghost"
                    title="Compose logs (all services)" aria-label="Compose logs"
                    @click.stop="openStackLogs(s)">
              <i class="fas fa-file-lines"></i>
            </button>

            <button class="btn btn-xs btn-square btn-ghost text-error"
                    title="Compose down (removes containers)"
                    aria-label="Compose down"
                    :disabled="stackActionBusy(s.name)"
                    @click.stop="askStackAction(s, 'down')">
              <i class="fas fa-power-off" :class="{ 'animate-pulse': stackActionBusy(s.name, 'down') }"></i>
            </button>
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
import { askStackAction, openStackLogs, stackActionBusy } from './useInfraStacks'
import { layout } from './useInfraLayout'

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