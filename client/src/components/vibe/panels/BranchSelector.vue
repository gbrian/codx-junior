<script setup>
import { ref } from 'vue'
</script>

<template>
  <div class="shrink-0 border-b border-base-content/10 px-2 py-2 bg-base-200/30">
    <div class="flex items-center gap-2 text-xs min-w-0">
      <!-- Current branch dropdown -->
      <div class="flex items-center gap-1 min-w-0">
        <i class="fa-solid fa-code-branch text-success text-[10px] shrink-0"></i>
        <div class="dropdown dropdown-bottom relative">
          <button
            tabindex="0"
            :disabled="loading"
            class="btn btn-xs btn-bordered truncate tlr font-mono text-ellipsis overflow-hidden justify-start"
            :title="currentBranch"
          >
            {{ currentBranch }}
            <i class="fa-solid fa-chevron-down text-[8px] ml-auto"></i>
          </button>
          <div
            tabindex="0"
            class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-[300px] max-h-60 overflow-y-auto"
          >
            <!-- Filter input -->
            <input
              type="text"
              placeholder="Filter branches..."
              class="input input-xs input-bordered w-full mb-2"
              v-model="currentBranchFilter"
              @keydown.stop
            />

            <!-- Filtered branches -->
            <button
              v-for="b in filteredCurrentBranches"
              :key="`current-${b}`"
              :class="{ 'bg-success/20': currentBranch === b }"
              class="btn btn-xs btn-ghost justify-start font-mono w-full text-left"
              @click="onCurrentBranchChange(b)"
              :title="b"
            >
              <i v-if="currentBranch === b" class="fa-solid fa-check text-success text-[10px]"></i>
              <span class="truncate">{{ b }}</span>
            </button>

            <!-- Empty state -->
            <div v-if="!filteredCurrentBranches.length" class="p-2 text-center text-base-content/40 text-xs">
              No branches found
            </div>
          </div>
        </div>
      </div>

      <!-- Compare arrow -->
      <div class="flex items-center gap-1 text-base-content/40 shrink-0">
        <i class="fa-solid fa-arrow-right text-[10px]"></i>
        <i class="fa-solid fa-angles-right text-[10px]"></i>
      </div>

      <!-- Compare branch dropdown -->
      <div class="dropdown dropdown-bottom relative">
        <button
          tabindex="0"
          :disabled="loading"
          class="btn btn-xs btn-bordered  truncate tlr font-mono text-warning text-ellipsis overflow-hidden justify-start"
          :title="compareBranch"
        >
          {{ compareBranch }}
          <i class="fa-solid fa-chevron-down text-[8px] ml-auto"></i>
        </button>
        <div
          tabindex="0"
          class="dropdown-content z-[1] menu p-2 shadow bg-base-100 rounded-box w-[300px] max-h-60 overflow-y-auto"
        >
          <!-- Filter input -->
          <input
            type="text"
            placeholder="Filter branches..."
            class="input input-xs input-bordered w-full mb-2"
            v-model="compareBranchFilter"
            @keydown.stop
          />

          <!-- Filtered branches -->
          <button
            v-for="b in filteredCompareBranches"
            :key="`compare-${b}`"
            :class="{ 'bg-warning/20': compareBranch === b }"
            class="btn btn-xs btn-ghost justify-start font-mono w-full text-left"
            @click="onCompareBranchChange(b)"
            :title="b"
          >
            <i v-if="compareBranch === b" class="fa-solid fa-check text-warning text-[10px]"></i>
            <span class="truncate">{{ b }}</span>
          </button>

          <!-- Empty state -->
          <div v-if="!filteredCompareBranches.length" class="p-2 text-center text-base-content/40 text-xs">
            No branches found
          </div>
        </div>
      </div>

      <!-- Loading indicator -->
      <div v-if="loading" class="ml-auto shrink-0">
        <i class="fa-solid fa-spinner text-[10px] animate-spin text-base-content/40"></i>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    project: { type: Object, required: true },
    currentBranch: { type: String, default: 'main' },
    compareBranch: { type: String, default: 'local' },
    availableBranches: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false }
  },
  emits: ['branch-changed', 'compare-branch-changed'],
  data() {
    return {
      currentBranchFilter: '',
      compareBranchFilter: ''
    }
  },
  computed: {
    filteredCurrentBranches() {
      return this.filterBranches(this.availableBranches, this.currentBranchFilter)
    },

    filteredCompareBranches() {
      const allOptions = ['local', ...this.availableBranches]
      return this.filterBranches(allOptions, this.compareBranchFilter)
    }
  },
  watch: {
    currentBranch() {
      this.currentBranchFilter = ''
    },
    compareBranch() {
      this.compareBranchFilter = ''
    }
  },
  methods: {
    filterBranches(branches, filter) {
      if (!filter.trim()) return branches
      const lowerFilter = filter.toLowerCase()
      return branches.filter(b => b.toLowerCase().includes(lowerFilter))
    },

    onCurrentBranchChange(branch) {
      this.$emit('branch-changed', branch)
    },

    onCompareBranchChange(branch) {
      this.$emit('compare-branch-changed', branch)
    },

  }
}
</script>