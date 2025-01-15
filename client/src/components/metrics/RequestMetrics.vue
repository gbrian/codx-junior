<template>
  <div class="p-6">
    <h2 class="text-xl font-bold mb-4">Request Metrics</h2>
    <table class="table-auto w-full text-left border-collapse">
      <thead>
        <tr>
          <th class="px-4 py-2 border-b">Request Path</th>
          <th class="px-4 py-2 border-b">Min Time (ms)</th>
          <th class="px-4 py-2 border-b">Max Time (ms)</th>
          <th class="px-4 py-2 border-b">Avg Time (ms)</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(metrics, path) in requestMetrics" :key="path">
          <td class="px-4 py-2 border-b">{{ path }}</td>
          <td class="px-4 py-2 border-b">{{ metrics.min.toFixed(3) }}</td>
          <td class="px-4 py-2 border-b">{{ metrics.max.toFixed(3) }}</td>
          <td class="px-4 py-2 border-b">{{ metrics.avg.toFixed(3) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  data() {
    return {
      logs: [
        "[2025-01-14 18:18:26,384] INFO [codx.junior.app:156] Request https://0.0.0.0:9984/api/logs?codx_path=%2Fshared%2Fapp-ng-mro%2F.vscode%2F.codx - 0.0020394325256347656 ms"
      ]
    }
  },
  computed: {
    requestMetrics() {
      const metricsMap = {}
      
      // Parse logs to extract path and time
      this.logs.forEach(log => {
        const parsed = this.parseLog(log)
        if (parsed) {
          const { path, time } = parsed
          if (!metricsMap[path]) {
            metricsMap[path] = { times: [] }
          }
          metricsMap[path].times.push(time)
        }
      })

      // Calculate min, max, and avg for each path
      const result = {}
      for (const [path, { times }] of Object.entries(metricsMap)) {
        const min = Math.min(...times)
        const max = Math.max(...times)
        const avg = times.reduce((a, b) => a + b, 0) / times.length
        result[path] = { min, max, avg }
      }

      return result
    }
  },
  methods: {
    parseLog(log) {
      const regex = /Request (https?:\/\/[^\s]+) - (\d+\.\d+) ms/
      const match = log.match(regex)
      if (match) {
        return { path: match[1], time: parseFloat(match[2]) }
      }
      return null
    }
  }
}
</script>