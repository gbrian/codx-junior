<template>
  <div class="">
    <h2 class="text-xl font-bold">{{ title }} Metrics</h2>
    <div class="h-60 overflow-auto">
      <table class="table w-full text-left">
        <thead>
          <tr>
            <th>{{ subtitle }}</th>
            <th class="text-left" colspan="3">Time (ms)</th>
          </tr>
          <tr class="text-xs">
            <th class="px-4 py-2"></th>
            <th class="px-4 py-2">min</th>
            <th class="px-4 py-2">max</th>
            <th class="px-4 py-2">avg</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(metrics) in requestMetrics" :key="path">
            <td class="px-4 py-2">{{ metrics.path }}</td>
            <td class="px-4 py-2">{{ metrics.min.toFixed(3) }}</td>
            <td class="px-4 py-2">{{ metrics.max.toFixed(3) }}</td>
            <td class="px-4 py-2">{{ metrics.avg.toFixed(3) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
export default {
  props: ['title', 'subtitle', 'logs'],
  data() {
    return {
    }
  },
  computed: {
    requestMetrics() {
      const metricsMap = {}
      this.logs.forEach(log => {
        const { 
          path, time_taken: time
        } = log
        
        if (!metricsMap[path]) {
          metricsMap[path] = { times: [] }
        }
        if (time) {
          metricsMap[path].times.push(time)
        }
      })

      // Calculate min, max, and avg for each path
      const result = []
      for (const [path, { times }] of Object.entries(metricsMap)) {
        const min = Math.min(...times)
        const max = Math.max(...times)
        const avg = times.reduce((a, b) => a + b, 0) / times.length
        result.push({ path, min, max, avg })
      }

      return result.sort((a, b) => a.avg > b.avg ? -1: 1)
    },
  },
  methods: {
  }
}
</script>