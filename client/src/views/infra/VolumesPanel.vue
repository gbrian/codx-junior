<template>
  <div>
    <!-- ── Empty state ────────────────────────────────────────────────────── -->
    <div v-if="!filteredList.length" class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body items-center text-center py-12">
        <i class="fas fa-database text-4xl opacity-30"></i>
        <h3 class="card-title mt-2">
          {{ hasVolumes ? 'No volumes match your filters' : 'No volumes found' }}
        </h3>
        <p class="text-sm opacity-60">
          {{ hasVolumes
            ? 'Try clearing the search box.'
            : 'Named and anonymous volumes on this host are listed here.' }}
        </p>
        <div v-if="hasVolumes" class="card-actions mt-2">
          <button class="btn btn-sm btn-ghost" @click="clearFilters">
            <i class="fas fa-filter-circle-xmark"></i> Clear filters
          </button>
        </div>
      </div>
    </div>

    <!-- ── Narrow panel (< 42rem / 672px): one card per volume ────────────── -->
    <div v-else-if="layout.compact" class="space-y-2">
      <article v-for="v in filteredList" :key="`card-${v.name}`"
               class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-start gap-2 min-w-0">
            <i class="fas fa-database text-xs opacity-40 mt-1 shrink-0"></i>
            <div class="min-w-0 grow">
              <div class="flex items-center gap-1.5 min-w-0">
                <span class="font-mono text-xs font-semibold truncate">{{ v.name }}</span>
                <span v-if="v.anonymous" class="badge badge-xs badge-ghost shrink-0">anonymous</span>
              </div>
              <div class="text-[11px] opacity-40 font-mono break-all">{{ v.mountpoint }}</div>
            </div>
            <span class="badge badge-xs shrink-0"
                  :class="v.in_use ? 'badge-success badge-outline' : 'badge-ghost'">
              {{ v.in_use ? 'in use' : 'unused' }}
            </span>
          </div>

          <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px]">
            <span><span class="opacity-50">Driver</span> <span class="font-mono">{{ v.driver }}</span></span>
            <span><span class="opacity-50">Size</span> <span class="font-mono">{{ fmtBytes(v.size) }}</span></span>
            <span v-if="v.stack" class="badge badge-xs badge-ghost">{{ v.stack }}</span>
          </div>

          <div class="flex items-center justify-end gap-1.5 pt-2 border-t border-base-300">
            <button class="btn btn-sm btn-ghost" @click="showJson(v.name, v)">
              <i class="fas fa-code"></i> Inspect
            </button>
          </div>
        </div>
      </article>
    </div>

    <!-- ── Wide panel (>= 42rem / 672px): list rows ───────────────────────── -->
    <div v-else class="card bg-base-200 border border-base-300 shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="table table-sm">
          <thead>
            <tr>
              <th>Name</th>
              <th class="w-24">Driver</th>
              <th class="w-28 text-right">Size</th>
              <th class="w-24">Stack</th>
              <th class="w-24 text-center">In use</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="v in filteredList" :key="v.name" class="hover">
              <td>
                <div class="flex flex-col min-w-0">
                  <div class="flex items-center gap-2">
                    <i class="fas fa-database text-xs opacity-40"></i>
                    <span class="font-mono text-xs truncate">{{ v.name }}</span>
                    <span v-if="v.anonymous" class="badge badge-xs badge-ghost">anonymous</span>
                  </div>
                  <span class="text-[11px] opacity-40 font-mono truncate">{{ v.mountpoint }}</span>
                </div>
              </td>
              <td class="text-xs">{{ v.driver }}</td>
              <td class="text-right font-mono text-xs">{{ fmtBytes(v.size) }}</td>
              <td class="text-xs">
                <span v-if="v.stack" class="badge badge-xs badge-ghost">{{ v.stack }}</span>
                <span v-else class="opacity-30">—</span>
              </td>
              <td class="text-center">
                <span class="badge badge-xs" :class="v.in_use ? 'badge-success badge-outline' : 'badge-ghost'">
                  {{ v.in_use ? 'yes' : 'no' }}
                </span>
              </td>
              <td>
                <div class="flex justify-end gap-1">
                  <button class="btn btn-xs btn-ghost" title="Inspect" @click="showJson(v.name, v)">
                    <i class="fas fa-code"></i>
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
import { state, filteredList, setFilter, fmtBytes, showJson } from './useInfra'
import { layout } from './useInfraLayout'

/** True when the host has volumes at all (i.e. the empty state is filter-driven). */
const hasVolumes = computed(() => state.volumes.length > 0)

function clearFilters() {
  setFilter({ q: '' })
}
</script>