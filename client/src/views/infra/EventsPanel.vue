<template>
  <div>
    <div v-if="!filteredList.length" class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body items-center text-center py-12">
        <i class="fas fa-bolt text-4xl opacity-30"></i>
        <h3 class="card-title mt-2">No recent events</h3>
        <p class="text-sm opacity-60">Daemon events (create, start, die, pull…) are streamed here.</p>
      </div>
    </div>

    <div v-else class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body p-0">
        <ul class="divide-y divide-base-300">
          <!-- Two-line block in a narrow panel, single row when the panel is
               wide enough (`layout.inline`, >= 36rem / 576px). -->
          <li v-for="(e, i) in filteredList" :key="`${e.ts}-${i}`"
              class="flex px-3 py-2.5 text-sm"
              :class="layout.inline ? 'items-center gap-3' : 'items-start gap-2'">
            <span class="w-5 shrink-0 text-center" :class="layout.inline ? '' : 'pt-0.5'">
              <i class="fas" :class="typeIcon(e.type)" :title="e.type"></i>
            </span>

            <div class="min-w-0 grow" :class="layout.inline ? 'flex items-center gap-3' : ''">
              <div class="flex items-center gap-2 min-w-0">
                <span class="badge badge-sm shrink-0" :class="actionBadge(e.action)">{{ e.action }}</span>
                <span class="font-mono text-xs truncate">{{ e.actor }}</span>
              </div>
              <div class="flex items-center gap-2 text-[11px] opacity-50"
                   :class="layout.inline ? 'ml-auto shrink-0' : 'mt-0.5'">
                <span class="font-mono">{{ fmtTime(e.ts) }}</span>
                <span v-if="layout.inline">{{ e.type }}</span>
              </div>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { filteredList, fmtTime } from './useInfra'
import { layout } from './useInfraLayout'

function typeIcon(type) {
  return {
    container: 'fa-cube text-primary',
    image: 'fa-hard-drive text-info',
    volume: 'fa-database text-secondary',
    network: 'fa-network-wired text-accent',
    health_status: 'fa-heart-pulse text-warning'
  }[type] || 'fa-circle-dot opacity-40'
}

function actionBadge(action) {
  return {
    start: 'badge-success',
    create: 'badge-success badge-outline',
    restart: 'badge-warning',
    die: 'badge-error',
    kill: 'badge-error',
    destroy: 'badge-error badge-outline',
    unhealthy: 'badge-warning',
    pull: 'badge-info'
  }[action] || 'badge-ghost'
}
</script>