<template>
  <div class="repo-branch-list flex flex-col h-full w-full overflow-hidden">
    <!-- Filter -->
    <div v-if="showFilter" class="px-2 py-1.5 border-b border-base-content/10 shrink-0">
      <div class="relative">
        <i class="fa-solid fa-magnifying-glass absolute left-2 top-1/2 -translate-y-1/2 text-[10px] opacity-40"></i>
        <input
          :value="filter"
          type="text"
          :placeholder="filterPlaceholder"
          class="input input-xs input-bordered w-full pl-6"
          :aria-label="filterPlaceholder"
          @input="$emit('update:filter', $event.target.value)"
        />
      </div>
    </div>

    <!-- Branch list -->
    <div class="grow overflow-y-auto min-h-0">
      <div v-if="loading && !displayBranches.length" class="p-3 text-xs opacity-50">
        Loading branches...
      </div>
      <div v-else-if="!filteredBranches.length" class="p-3 text-xs opacity-50">
        {{ branches.length ? 'No branches match the filter' : emptyLabel }}
      </div>
      <button
        v-for="branch in filteredBranches"
        :key="branch"
        class="w-full flex items-center gap-2 px-3 py-1.5 text-left text-xs transition-colors"
        :class="[
          isSelected(branch) ? 'bg-primary/15 text-primary' : 'hover:bg-base-200',
          isCurrent(branch) ? 'font-semibold' : ''
        ]"
        :title="branch === 'local' ? 'local (uncommitted working tree)' : branch"
        @click="$emit('select', branch)"
        @contextmenu.prevent.stop="$emit('contextmenu', $event, branch)"
      >
        <i
          class="fa-solid shrink-0"
          :class="branch === 'local'
            ? 'fa-laptop-file text-warning'
            : isCurrent(branch)
              ? 'fa-circle-check text-success'
              : 'fa-code-branch opacity-50'"
        ></i>
        <span class="truncate grow min-w-0">{{ branch === 'local' ? 'local (working tree)' : branch }}</span>
        <span
          v-if="countFor(branch)"
          class="badge badge-xs badge-ghost shrink-0"
        >{{ countFor(branch) }}</span>
        <span v-if="branch === 'local'" class="badge badge-xs badge-warning badge-outline shrink-0">local</span>
      </button>
    </div>
  </div>
</template>

<script>
/**
 * Branch list shared by the Repository tab and the Review branch selector.
 *
 * Repository uses it as the sidebar list (current branch, commit counts and
 * context-menu actions). Review uses the exact same visual list for its source
 * and target pickers, so both screens show branches the same way.
 */
export default {
  name: 'RepoBranchList',
  props: {
    branches: { type: Array, default: () => [] },
    currentBranch: { type: String, default: '' },
    selectedBranch: { type: String, default: '' },
    loading: { type: Boolean, default: false },
    filter: { type: String, default: '' },
    /** branch name -> number of commits in the repo tree */
    counts: { type: Object, default: () => ({}) },
    /** Offer the `local` sentinel (uncommitted working tree) */
    includeLocal: { type: Boolean, default: false },
    showFilter: { type: Boolean, default: true },
    filterPlaceholder: { type: String, default: 'Filter branches...' },
    emptyLabel: { type: String, default: 'No branches' }
  },
  emits: ['select', 'contextmenu', 'update:filter'],
  computed: {
    displayBranches() {
      const list = (this.branches || []).filter(Boolean)
      if (!this.includeLocal || list.includes('local')) return list
      return ['local', ...list]
    },
    filteredBranches() {
      const filter = (this.filter || '').trim().toLowerCase()
      if (!filter) return this.displayBranches
      return this.displayBranches.filter(branch => branch.toLowerCase().includes(filter))
    }
  },
  methods: {
    sameBranch(a, b) {
      const clean = value => String(value || '').replace(/^refs\/heads\//, '').replace(/^\* /, '').trim()
      return !!a && !!b && clean(a) === clean(b)
    },
    isCurrent(branch) {
      return this.sameBranch(branch, this.currentBranch)
    },
    isSelected(branch) {
      return this.sameBranch(branch, this.selectedBranch)
    },
    countFor(branch) {
      return this.counts?.[branch] || 0
    }
  }
}
</script>
