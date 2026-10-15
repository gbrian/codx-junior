<script setup>
import { avatarUrl } from './config'
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="$emit('close')"></div>

    <div
      class="relative card bg-base-100 border border-base-content/10 shadow-2xl w-full max-w-md max-h-[92vh] overflow-y-auto"
      role="dialog"
      aria-modal="true"
      :aria-label="`Add members to ${team.name}`"
    >
      <div class="card-body gap-4">
        <div class="flex items-center justify-between">
          <h2 class="card-title text-lg min-w-0">
            <span class="truncate">Add members to {{ team.name }}</span>
          </h2>
          <button type="button" class="btn btn-ghost btn-sm btn-square" aria-label="Close" @click="$emit('close')">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>

        <p class="text-[11px] text-base-content/50 -mt-2">
          Pick the project members to add. Selected members keep the teams they already belong to.
        </p>

        <template v-if="available.length">
          <!-- Free-text filter for names + "Unassigned" filter option -->
          <div class="flex items-center gap-3">
            <div class="relative flex-1 min-w-0">
              <input
                v-model="search"
                type="text"
                class="input input-sm input-bordered w-full pl-8"
                placeholder="Filter members…"
                aria-label="Filter members by name"
              />
              <i class="fa-solid fa-magnifying-glass absolute left-2.5 top-1/2 -translate-y-1/2 text-base-content/40 text-xs"></i>
              <button
                v-if="search"
                type="button"
                class="btn btn-ghost btn-xs btn-square btn-circle absolute right-1 top-1/2 -translate-y-1/2"
                aria-label="Clear filter"
                @click="search = ''"
              >
                <i class="fa-solid fa-xmark text-xs"></i>
              </button>
            </div>

            <!-- Unassigned filter: only members that belong to no team -->
            <label
              class="flex items-center gap-1.5 cursor-pointer select-none shrink-0"
              :title="unassignedOnly ? 'Showing unassigned members only' : 'Show only members that are in no team'"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-xs checkbox-info"
                v-model="unassignedOnly"
                aria-label="Show unassigned members only"
              />
              <span class="text-xs text-base-content/60">Unassigned</span>
            </label>
          </div>

          <!-- Available members (not yet in this team), sorted A→Z -->
          <div v-if="filteredAvailable.length" class="flex flex-col gap-1 max-h-72 overflow-y-auto pr-1">
            <label
              v-for="m in filteredAvailable"
              :key="m.name"
              class="flex items-center gap-3 p-2 rounded-lg cursor-pointer hover:bg-base-200 transition-colors"
            >
              <input
                type="checkbox"
                class="checkbox checkbox-sm"
                :value="m.name"
                v-model="selected"
              />
              <div class="avatar shrink-0">
                <div class="w-7 rounded-full">
                  <img :src="avatarUrl(m)" :alt="m.name" />
                </div>
              </div>
              <span class="text-sm truncate flex-1">{{ m.name }}</span>
            </label>
          </div>

          <!-- No match for the current filters -->
          <div v-else class="flex flex-col items-center gap-2 py-8 text-center text-base-content/50">
            <i class="fa-solid fa-magnifying-glass text-2xl"></i>
            <p class="text-sm">
              No members match {{ unassignedOnly ? 'these filters' : `“${search}”` }}.
            </p>
          </div>
        </template>

        <div v-else class="flex flex-col items-center gap-2 py-8 text-center text-base-content/50">
          <i class="fa-solid fa-user-check text-2xl"></i>
          <p class="text-sm">All project members are already in this team.</p>
        </div>

        <div class="card-actions justify-end">
          <button type="button" class="btn btn-sm btn-ghost" @click="$emit('close')">Cancel</button>
          <button
            type="button"
            class="btn btn-sm btn-primary"
            :disabled="saving || !selected.length"
            @click="submit"
          >
            <span v-if="saving" class="loading loading-spinner loading-xs"></span>
            <i v-else class="fa-solid fa-plus"></i>
            Add{{ selected.length ? ` (${selected.length})` : '' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AddMembersToTeamDialog',
  props: {
    /** The team to add members to. */
    team: { type: Object, required: true },
    /** Every team in the project — used to detect unassigned members. */
    teams: { type: Array, default: () => [] },
    /** Every project member (profiles). */
    members: { type: Array, default: () => [] },
    saving: { type: Boolean, default: false }
  },
  emits: ['add', 'close'],
  data() {
    return {
      selected: [],
      search: '',
      // When true, only members that belong to no team are listed.
      unassignedOnly: false
    }
  },
  computed: {
    /** Every member name that already belongs to at least one team. */
    assignedNames() {
      const names = new Set()
      ;(this.teams || []).forEach(team => {
        (team?.profiles || []).forEach(name => names.add(name))
      })
      return names
    },
    /** Members that are NOT already part of this team, sorted alphabetically. */
    available() {
      const current = new Set(this.team?.profiles || [])
      return (this.members || [])
        .filter(m => m?.name && !current.has(m.name))
        .filter(m => !this.unassignedOnly || !this.assignedNames.has(m.name))
        .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
    },
    /** `available` narrowed by the free-text filter. */
    filteredAvailable() {
      const q = (this.search || '').trim().toLowerCase()
      if (!q) return this.available
      return this.available.filter(m => (m.name || '').toLowerCase().includes(q))
    }
  },
  mounted() {
    window.addEventListener('keydown', this.onKeydown)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    avatarUrl,
    onKeydown(event) {
      if (event.key === 'Escape') this.$emit('close')
    },
    submit() {
      if (!this.selected.length || this.saving) return
      this.$emit('add', { teamId: this.team.id, profiles: [...this.selected] })
    }
  }
}
</script>

<!-- Made with ❤️ by codx-junior -->