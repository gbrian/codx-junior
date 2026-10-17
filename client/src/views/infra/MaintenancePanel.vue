<template>
  <div class="space-y-3">
    <!-- ── Toolbar: threshold, rescan and quick prune actions ─────────────── -->
    <div class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body p-3 gap-3">
        <div class="flex flex-wrap items-start gap-2">
          <div class="min-w-0 grow">
            <h2 class="font-bold flex items-center gap-2">
              <i class="fas fa-broom text-primary"></i>
              Cleanup candidates
            </h2>
            <p class="text-xs opacity-60 mt-0.5">
              Detected from the current host snapshot:
              <span class="font-semibold">{{ report.totalItems }} item(s)</span>
              <template v-if="report.reclaimable">
                · <span class="font-semibold">~{{ fmtBytes(report.reclaimable) }}</span> reclaimable
              </template>
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <label class="flex items-center gap-2 text-xs">
              <span class="opacity-60">Older than</span>
              <select class="select select-bordered select-xs"
                      :value="state.maintenanceOlderThanDays" @change="onAgeChange">
                <option :value="0">Any age</option>
                <option :value="7">7 days</option>
                <option :value="30">30 days</option>
                <option :value="90">90 days</option>
              </select>
            </label>

            <button class="btn btn-sm btn-ghost" :disabled="rescanning" @click="rescan">
              <i class="fas fa-arrows-rotate" :class="{ 'animate-spin': rescanning }"></i>
              Rescan
            </button>
          </div>
        </div>

        <!-- Quick prune actions. The column count follows the PANEL width
             (`layout.*`), never the viewport: this view lives in a dockview
             panel that can be resized independently of the window. -->
        <div class="grid gap-2"
             :class="layout.compact ? 'grid-cols-1' : layout.twoCol ? 'grid-cols-3' : 'grid-cols-2'">
          <button v-for="p in PRUNE_TARGETS" :key="p.id"
                  class="btn btn-sm h-auto justify-start gap-2 py-2 text-left"
                  :class="p.danger ? 'btn-outline btn-error' : 'btn-outline'"
                  :disabled="!!state.maintenanceBusy"
                  :title="p.desc"
                  @click="askPrune(p.id)">
            <span v-if="state.maintenanceBusy === p.id" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fas" :class="p.icon"></i>
            <span class="flex flex-col">
              <span class="text-xs font-semibold">{{ p.label }}</span>
              <span class="text-[10px] font-normal opacity-60">{{ p.desc }}</span>
            </span>
          </button>
        </div>

        <div role="note" class="alert alert-warning py-2">
          <i class="fas fa-triangle-exclamation text-sm"></i>
          <span class="text-xs">
            Deletion is permanent. Pruning volumes destroys data that is not backed up.
          </span>
        </div>
      </div>
    </div>

    <!-- ── Nothing to do ─────────────────────────────────────────────────── -->
    <div v-if="!report.totalItems" class="card bg-base-200 border border-base-300 shadow-sm">
      <div class="card-body items-center text-center py-12">
        <i class="fas fa-circle-check text-4xl text-success opacity-60"></i>
        <h3 class="card-title mt-2">Nothing to clean up</h3>
        <p class="text-sm opacity-60 max-w-md">
          No unused images, volumes or networks and no stale containers were found
          with this age threshold.
        </p>
        <div v-if="report.olderThanDays > 0" class="card-actions mt-2">
          <button class="btn btn-sm btn-ghost" @click="setMaintenanceAge(0)">
            <i class="fas fa-clock-rotate-left"></i> Include every age
          </button>
        </div>
      </div>
    </div>

    <!-- ── One card per resource class ───────────────────────────────────── -->
    <template v-else>
      <section v-for="group in visibleGroups" :key="group.id"
               class="card bg-base-200 border border-base-300 shadow-sm">
        <div class="card-body p-3 gap-2">
          <!-- group header -->
          <div class="flex flex-wrap items-start gap-2">
            <i class="fas mt-0.5" :class="[group.icon, 'text-primary']"></i>
            <div class="min-w-0 grow">
              <div class="flex flex-wrap items-center gap-2">
                <h3 class="font-semibold text-sm">{{ group.label }}</h3>
                <span class="badge badge-sm badge-ghost">{{ group.items.length }}</span>
                <span v-if="group.size" class="text-xs opacity-50 font-mono">~{{ fmtBytes(group.size) }}</span>
              </div>
              <p class="text-[11px] opacity-50">{{ group.hint }}</p>
            </div>

            <div class="flex items-center gap-2 shrink-0">
              <label class="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" class="checkbox checkbox-xs"
                       :checked="allSelected(group)"
                       :aria-label="`Select every ${group.label.toLowerCase()}`"
                       @change="toggleAll(group)" />
                <span class="text-[11px] opacity-60">Select all</span>
              </label>
              <button class="btn btn-xs btn-error btn-outline"
                      :disabled="!selectedItems(group).length || !!state.maintenanceBusy"
                      @click="askRemoveCandidates(group, selectedItems(group))">
                <i class="fas fa-trash-can"></i>
                Remove {{ selectedItems(group).length || '' }}
              </button>
            </div>
          </div>

          <!-- group rows -->
          <ul class="rounded-lg bg-base-300/30 divide-y divide-base-300">
            <li v-for="item in group.items" :key="item.key"
                class="flex items-start gap-2 px-2 py-1.5">
              <input type="checkbox" class="checkbox checkbox-xs mt-1 shrink-0"
                     :checked="isSelected(group.id, item.key)"
                     :aria-label="`Select ${item.name}`"
                     @change="toggleItem(group.id, item.key)" />

              <div class="min-w-0 grow">
                <div class="flex items-center gap-1.5 min-w-0">
                  <span class="font-mono text-xs truncate" :title="item.name">{{ item.name }}</span>
                  <span v-if="item.state" class="badge badge-xs shrink-0" :class="badgeClass(group.id, item)">
                    {{ item.state }}
                  </span>
                </div>
                <div class="text-[11px] opacity-40 font-mono truncate" :title="item.subtitle">
                  {{ item.subtitle }}
                </div>
              </div>

              <div class="shrink-0 text-right">
                <div class="font-mono text-[11px]">{{ item.size ? fmtBytes(item.size) : '—' }}</div>
                <div class="text-[10px] opacity-40">
                  {{ item.ageDays != null ? `${item.ageDays}d old` : 'age unknown' }}
                </div>
              </div>

              <button class="btn btn-xs btn-ghost btn-square text-error shrink-0"
                      :title="`Remove ${item.name}`" :aria-label="`Remove ${item.name}`"
                      :disabled="!!state.maintenanceBusy"
                      @click="askRemoveCandidates(group, [item])">
                <i class="fas fa-trash-can"></i>
              </button>
            </li>
          </ul>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import {
  state, maintenanceReport, PRUNE_TARGETS, setMaintenanceAge, setFilter,
  askPrune, askRemoveCandidates, loadAll, fmtBytes
} from './useInfra'
import { layout } from './useInfraLayout'

const report = maintenanceReport
const rescanning = ref(false)

/**
 * Checkbox selection is a pure view concern: it must not leak into the shared
 * store (other panels would then see stale keys). Keys are kept per group
 * because ids are only unique inside a group.
 */
const selection = reactive({})

const visibleGroups = computed(() => report.value.groups.filter(g => g.items.length))

function onAgeChange(event) {
  setMaintenanceAge(event?.target?.value)
}

async function rescan() {
  rescanning.value = true
  try {
    await loadAll()
  } finally {
    rescanning.value = false
  }
}

function isSelected(groupId, key) {
  return (selection[groupId] || []).includes(key)
}

function toggleItem(groupId, key) {
  const list = selection[groupId] || (selection[groupId] = [])
  const ix = list.indexOf(key)
  if (ix >= 0) list.splice(ix, 1)
  else list.push(key)
}

function selectedItems(group) {
  return group.items.filter(item => isSelected(group.id, item.key))
}

function allSelected(group) {
  return group.items.length > 0 && selectedItems(group).length === group.items.length
}

function toggleAll(group) {
  selection[group.id] = allSelected(group) ? [] : group.items.map(item => item.key)
}

function badgeClass(groupId, item) {
  if (groupId === 'images') return item.state === 'dangling' ? 'badge-warning badge-outline' : 'badge-ghost'
  if (groupId === 'containers') return item.state === 'dead' ? 'badge-error badge-outline' : 'badge-ghost'
  return 'badge-ghost'
}
</script>