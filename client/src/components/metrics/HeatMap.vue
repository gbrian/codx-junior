<script setup>
import moment from 'moment';
import { CalendarHeatmap } from 'vue3-calendar-heatmap'
</script>
<template>
  <div class="group">
    <calendar-heatmap dark-mode :round="5" :values="data" :end-date="moment().format('YYYY-MM-DD')" />
    <div class="opacity-0 group-hover:opacity-100 text-[8px] flex gap-2 justify-end">
      <span>{{ months }}</span>
    </div>
  </div>
</template>

<script>
export default {
  props: ['data'],
  computed: {
    total() {
      return this.data.reduce((acc, v) => acc + v.count, 0)
    },
    months() {
      const m = v => v.date.split("-").slice(0,2).join("-") + "-01"
      const s = (a, b) => (a || 0) + 1
      const months = this.data.reduce((acc, v) => ({ ...acc, [m(v)]: s(acc[m(v)], v.count) }), {})
      return Object.keys(months).map(m => [moment(m).format("MMM"), months[m]].join(": ")).join(" ")
    }
  }
}
</script>
<style>
.vch__legend {
  display: none;
}
</style>