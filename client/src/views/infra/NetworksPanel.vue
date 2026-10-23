<template>
  <div>
    <!-- ── Empty state ────────────────────────────────────────────────────── -->
    <div v-if="!filteredList.length" class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body items-center text-center py-12">
        <i class="fas fa-network-wired text-4xl opacity-30"></i>
        <h3 class="card-title mt-2">
          {{ hasNetworks ? 'No networks match your filters' : 'No networks found' }}
        </h3>
        <p class="text-sm opacity-60">
          {{ hasNetworks
            ? 'Try clearing the search box.'
            : 'Bridge, host and overlay networks on this host are listed here.' }}
        </p>
        <div v-if="hasNetworks" class="card-actions mt-2">
          <button class="btn btn-sm btn-ghost" @click="clearFilters">
            <i class="fas fa-filter-circle-xmark"></i> Clear filters
          </button>
        </div>
      </div>
    </div>

    <!-- ── Narrow panel (< 42rem / 672px): one card per network ───────────── -->
    <div v-else-if="layout.compact" class="space-y-2">
      <article v-for="n in filteredList" :key="`card-${n.id}`"
               class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <div class="flex items-start gap-2 min-w-0">
            <i class="fas fa-network-wired text-xs opacity-40 mt-1 shrink-0"></i>
            <div class="min-w-0 grow">
              <div class="flex items-center gap-1.5 min-w-0">
                <span class="font-mono text-xs font-semibold truncate">{{ n.name }}</span>
                <span v-if="n.internal" class="badge badge-xs badge-warning badge-outline shrink-0">internal</span>
              </div>
              <div class="text-[11px] opacity-50">
                {{ n.driver }} · {{ n.scope }} · <span class="font-mono">{{ n.subnet }}</span>
              </div>
            </div>
            <span class="badge badge-xs shrink-0"
                  :class="n.containers?.length ? 'badge-success badge-outline' : 'badge-ghost'">
              {{ n.containers?.length || 0 }}
            </span>
          </div>

          <div v-if="n.containers?.length" class="flex flex-wrap gap-1">
            <span v-for="c in n.containers" :key="c" class="badge badge-xs badge-ghost font-mono">{{ c }}</span>
          </div>

          <div class="flex items-center justify-end gap-1.5 pt-2 border-t border-base-300">
            <button class="btn btn-sm btn-ghost" @click="showJson(n.name, n)">
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
              <th class="w-20">Scope</th>
              <th class="w-36">Subnet</th>
              <th class="w-24 text-center">Internal</th>
              <th class="w-28 text-center">Containers</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="n in filteredList" :key="n.id" class="hover">
              <td>
                <div class="flex items-center gap-2 min-w-0">
                  <i class="fas fa-network-wired text-xs opacity-40"></i>
                  <span class="font-mono text-xs truncate">{{ n.name }}</span>
                </div>
                <div v-if="n.containers?.length" class="flex flex-wrap gap-1 mt-1">
                  <span v-for="c in n.containers" :key="c" class="badge badge-xs badge-ghost font-mono">{{ c }}</span>
                </div>
              </td>
              <td class="text-xs">{{ n.driver }}</td>
              <td class="text-xs opacity-70">{{ n.scope }}</td>
              <td class="font-mono text-xs">{{ n.subnet }}</td>
              <td class="text-center">
                <span class="badge badge-xs" :class="n.internal ? 'badge-warning badge-outline' : 'badge-ghost'">
                  {{ n.internal ? 'yes' : 'no' }}
                </span>
              </td>
              <td class="text-center">
                <span class="badge badge-xs" :class="n.containers?.length ? 'badge-success badge-outline' : 'badge-ghost'">
                  {{ n.containers?.length || 0 }}
                </span>
              </td>
              <td>
                <div class="flex justify-end gap-1">
                  <button class="btn btn-xs btn-ghost" title="Inspect" @click="showJson(n.name, n)">
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
import { state, filteredList, setFilter, showJson } from './useInfra'
import { layout } from './useInfraLayout'

/** True when the host has networks at all (i.e. the empty state is filter-driven). */
const hasNetworks = computed(() => state.networks.length > 0)

function clearFilters() {
  setFilter({ q: '' })
}
</script>