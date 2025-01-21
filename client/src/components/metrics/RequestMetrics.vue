<template>
  <div class="collapse bg-base-200">
    <input type="checkbox" />
    <div class="collapse-title text-xl font-medium">
      <h2 class="text-xl font-bold">{{ title }} Metrics</h2>
    </div>
    <div class="collapse-content">
      <table class="table w-full text-left">
        <thead>
          <tr>
            <th>{{ subtitle }}</th>
            <th class="text-left" colspan="3">Time (s)</th>
          </tr>
          <tr class="text-xs">
            <th class="px-4 py-2"></th>
            <th class="px-4 py-2">min</th>
            <th class="px-4 py-2">max</th>
            <th class="px-4 py-2">avg</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="metrics in requestMetrics" :key="metrics.path">
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
  props: {
    title: {
      type: String,
      required: true
    },
    subtitle: {
      type: String,
      required: true
    },
    logs: {
      type: Array,
      required: true
    }
  },
  computed: {
    requestMetrics() {
      const metricsMap = {}
      
      // Organizing logs into metrics map based on the path
      this.logs.forEach(log => {
        const { path, time_taken: time } = log
        
        if (!metricsMap[path]) {
          metricsMap[path] = { times: [] }
        }
        if (isFinite(time) && !isNaN(time) && time > 0) {
          metricsMap[path].times.push(time)
        }
      })

      // Calculating min, max, and avg times for each path
      const result = []
      for (const [path, { times }] of Object.entries(metricsMap)) {
        if (times.length) {
          const min = Math.min(...times)
          const max = Math.max(...times)
          const avg = times.reduce((a, b) => a + b, 0) / times.length
          result.push({ path, min, max, avg })
        }
      }

      // Sorting results based on average time
      return result.sort((a, b) => a.avg > b.avg ? -1 : 1)
    },
  }
}
</script>