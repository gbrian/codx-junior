<template>
  <div class="flex flex-wrap items-center gap-2">
    <div class="join">
      <button
        v-for="range in ranges"
        :key="range.value"
        @click="$storex.planning.setRangeFilter(range.value)"
        class="btn btn-sm join-item"
        :class="rangeFilter === range.value ? 'btn-primary' : 'btn-ghost'"
      >
        {{ range.label }}
      </button>
    </div>

    <div v-if="rangeFilter === 'custom'" class="flex items-center gap-1">
      <input
        type="date"
        :value="customFromDate"
        @change="$storex.planning.setCustomRange({ fromDate: $event.target.value, toDate: customToDate })"
        class="input input-sm input-bordered text-xs"
      />
      <span class="text-xs text-base-content/40">→</span>
      <input
        type="date"
        :value="customToDate"
        @change="$storex.planning.setCustomRange({ fromDate: customFromDate, toDate: $event.target.value })"
        class="input input-sm input-bordered text-xs"
      />
    </div>

    <span v-if="loading" class="loading loading-spinner loading-xs text-primary"></span>
  </div>
</template>

<script>
export default {
  name: 'PlanningRangeFilter',
  data() {
    return {
      ranges: [
        { label: 'Today', value: 'today' },
        { label: 'Last 7 days', value: 'week' },
        { label: 'Last 30 days', value: 'month' },
        { label: 'Custom', value: 'custom' }
      ]
    }
  },
  computed: {
    rangeFilter() {
      return this.$storex.planning.rangeFilter
    },
    customFromDate() {
      return this.$storex.planning.customFromDate
    },
    customToDate() {
      return this.$storex.planning.customToDate
    },
    loading() {
      return this.$storex.planning.loading
    }
  }
}
</script>