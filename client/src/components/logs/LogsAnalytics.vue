<script setup>
</script>

<template>
  <div class="space-y-4">
    <!-- Row 1: Models / Providers / Projects -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <!-- Top Models -->
      <div class="card bg-base-100 shadow">
        <div class="card-body p-4">
          <h3 class="font-bold text-sm flex items-center gap-2 mb-3">
            <i class="fa-solid fa-microchip text-primary"></i>Top Models
          </h3>
          <div v-if="topModels.length === 0" class="text-center py-6 text-base-content/40 text-xs">No data</div>
          <div v-else class="space-y-2">
            <div v-for="m in topModels" :key="m.name" class="flex items-center gap-2">
              <span class="text-xs truncate flex-1 font-mono" :title="m.name">{{ m.name }}</span>
              <div class="w-24 bg-base-200 rounded-full h-2">
                <div class="h-2 rounded-full bg-primary" :style="{ width: m.pct + '%' }"></div>
              </div>
              <span class="text-xs text-base-content/50 w-8 text-right">{{ m.count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Top Providers -->
      <div class="card bg-base-100 shadow">
        <div class="card-body p-4">
          <h3 class="font-bold text-sm flex items-center gap-2 mb-3">
            <i class="fa-solid fa-plug text-secondary"></i>Top Providers
          </h3>
          <div v-if="topProviders.length === 0" class="text-center py-6 text-base-content/40 text-xs">No data</div>
          <div v-else class="space-y-2">
            <div v-for="p in topProviders" :key="p.name" class="flex items-center gap-2">
              <span class="text-xs truncate flex-1" :title="p.name">{{ p.name }}</span>
              <div class="w-24 bg-base-200 rounded-full h-2">
                <div class="h-2 rounded-full bg-secondary" :style="{ width: p.pct + '%' }"></div>
              </div>
              <span class="text-xs text-base-content/50 w-8 text-right">{{ p.count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Top Projects (field is "project" from RawAILogger) -->
      <div class="card bg-base-100 shadow">
        <div class="card-body p-4">
          <h3 class="font-bold text-sm flex items-center gap-2 mb-3">
            <i class="fa-solid fa-folder text-accent"></i>Top Projects
          </h3>
          <div v-if="topProjects.length === 0" class="text-center py-6 text-base-content/40 text-xs">No data</div>
          <div v-else class="space-y-2">
            <div v-for="p in topProjects" :key="p.name" class="flex items-center gap-2">
              <span class="text-xs truncate flex-1" :title="p.name">{{ p.name || '(no project)' }}</span>
              <div class="w-24 bg-base-200 rounded-full h-2">
                <div class="h-2 rounded-full bg-accent" :style="{ width: p.pct + '%' }"></div>
              </div>
              <span class="text-xs text-base-content/50 w-8 text-right">{{ p.count }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Row 2: Request/Response ratio + Avg duration by model + Tags -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <!-- Direction breakdown -->
      <div class="card bg-base-100 shadow">
        <div class="card-body p-4">
          <h3 class="font-bold text-sm flex items-center gap-2 mb-3">
            <i class="fa-solid fa-arrows-up-down text-info"></i>Direction Split
          </h3>
          <div class="flex items-center gap-4">
            <div class="radial-progress text-success" :style="`--value:${requestPct}; --size:5rem`">
              <span class="text-xs font-bold">{{ requestPct }}%</span>
            </div>
            <div class="space-y-1 text-xs">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-success inline-block"></span>
                <span>Requests: <strong>{{ directionCounts.request }}</strong></span>
              </div>
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-warning inline-block"></span>
                <span>Responses: <strong>{{ directionCounts.response }}</strong></span>
              </div>
              <div v-if="directionCounts.other" class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full bg-ghost inline-block"></span>
                <span>Other: <strong>{{ directionCounts.other }}</strong></span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Avg duration by model -->
      <div class="card bg-base-100 shadow">
        <div class="card-body p-4">
          <h3 class="font-bold text-sm flex items-center gap-2 mb-3">
            <i class="fa-solid fa-stopwatch text-warning"></i>Avg Duration / Model
          </h3>
          <div v-if="durationByModel.length === 0" class="text-center py-6 text-base-content/40 text-xs">No data</div>
          <div v-else class="space-y-2">
            <div v-for="m in durationByModel" :key="m.name" class="flex items-center gap-2">
              <span class="text-xs truncate flex-1 font-mono" :title="m.name">{{ m.name }}</span>
              <div class="w-24 bg-base-200 rounded-full h-2">
                <div class="h-2 rounded-full bg-warning" :style="{ width: m.pct + '%' }"></div>
              </div>
              <span class="text-xs text-base-content/50 w-12 text-right font-mono">{{ m.avg.toFixed(1) }}s</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Top tags -->
      <div class="card bg-base-100 shadow">
        <div class="card-body p-4">
          <h3 class="font-bold text-sm flex items-center gap-2 mb-3">
            <i class="fa-solid fa-tags text-fuchsia-400"></i>Top Tags
          </h3>
          <div v-if="topTags.length === 0" class="text-center py-6 text-base-content/40 text-xs">No tags</div>
          <div v-else class="flex flex-wrap gap-1">
            <span
              v-for="tag in topTags"
              :key="tag.name"
              class="badge badge-sm gap-1"
              :style="`opacity: ${0.4 + 0.6 * (tag.pct / 100)}`"
            >
              {{ tag.name }}
              <span class="text-xs font-semibold">{{ tag.count }}</span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LogsAnalytics',
  props: {
    logs: { type: Array, default: () => [] }
  },
  computed: {
    topModels() { return this.topNByCount(this.logs, 'model', 6) },
    topProviders() { return this.topNByCount(this.logs, 'provider', 6) },
    // Backend uses "project" field (not project_name)
    topProjects() { return this.topNByCount(this.logs, 'project', 6) },

    directionCounts() {
      const c = { request: 0, response: 0, other: 0 }
      for (const l of this.logs) {
        if (l.direction === 'request') c.request++
        else if (l.direction === 'response') c.response++
        else c.other++
      }
      return c
    },
    requestPct() {
      const total = this.logs.length
      if (!total) return 0
      return Math.round((this.directionCounts.request / total) * 100)
    },

    durationByModel() {
      const map = {}
      for (const l of this.logs) {
        if (!l.model || l.duration_seconds == null) continue
        if (!map[l.model]) map[l.model] = { total: 0, count: 0 }
        map[l.model].total += l.duration_seconds
        map[l.model].count++
      }
      const sorted = Object.entries(map)
        .map(([name, v]) => ({ name, avg: v.total / v.count }))
        .sort((a, b) => b.avg - a.avg)
        .slice(0, 5)
      const maxAvg = sorted[0]?.avg || 1
      return sorted.map(m => ({ ...m, pct: Math.round((m.avg / maxAvg) * 100) }))
    },

    topTags() {
      const map = {}
      for (const l of this.logs) {
        if (!l.tags) continue
        // Tags are stored as comma-separated string
        l.tags.split(',').map(t => t.trim()).filter(Boolean).forEach(tag => {
          map[tag] = (map[tag] || 0) + 1
        })
      }
      const sorted = Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, 20)
      const maxCount = sorted[0]?.[1] || 1
      return sorted.map(([name, count]) => ({ name, count, pct: Math.round((count / maxCount) * 100) }))
    }
  },
  methods: {
    /** Count occurrences of a field value, return top N with percentages */
    topNByCount(items, groupKey, n) {
      const map = {}
      for (const item of items) {
        const k = item[groupKey] || '(unknown)'
        map[k] = (map[k] || 0) + 1
      }
      const sorted = Object.entries(map).sort((a, b) => b[1] - a[1]).slice(0, n)
      const maxCount = sorted[0]?.[1] || 1
      return sorted.map(([name, count]) => ({ name, count, pct: Math.round((count / maxCount) * 100) }))
    }
  }
}
</script>