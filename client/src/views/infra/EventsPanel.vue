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
          <li v-for="(e, i) in filteredList" :key="`${e.ts}-${i}`"
              class="flex items-center gap-3 px-3 py-2 text-sm">
            <span class="w-5 text-center">
              <i class="fas" :class="typeIcon(e.type)" :title="e.type"></i>
            </span>
            <span class="font-mono text-xs opacity-50 w-20 shrink-0">{{ fmtTime(e.ts) }}</span>
            <span class="badge badge-sm shrink-0" :class="actionBadge(e.action)">{{ e.action }}</span>
            <span class="font-mono text-xs truncate grow">{{ e.actor }}</span>
            <span class="text-[11px] opacity-40 hidden sm:inline">{{ e.type }}</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { filteredList, fmtTime } from './useInfra'

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
