<script setup>
</script>

<template>
  <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
    <div
      v-for="kpi in kpis"
      :key="kpi.label"
      class="card bg-base-100 shadow hover:shadow-md transition-shadow"
    >
      <div class="card-body p-3">
        <div class="flex items-start justify-between">
          <div class="min-w-0">
            <p class="text-xs font-medium text-base-content/50 uppercase tracking-wide truncate">
              {{ kpi.label }}
            </p>
            <p class="text-xl font-bold mt-0.5 truncate" :class="kpi.color">{{ kpi.value }}</p>
            <p v-if="kpi.sub" class="text-xs text-base-content-ERROR-40 mt-0.5 truncate">{{ kpi.sub }}</p>
          </div>
          <div class="p-1.5 rounded-lg shrink-0" :class="kpi.bgColor">
            <i :class="[kpi.icon, kpi.color, 'text-sm']"></i>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LogsLiveMetrics',
  props: {
    logs: { type: Array, default: () => [] },
    total: { type: Number, default: 0 }
  },
  computed: {
    // Aggregate from LogEntry fields produced by _build_log_entry in the backend
    stats() {
      const s = {
        total: this.total,
        requests: 0,
        responses: 0,
        errors: 0,
        totalDuration: 0,
        durationCount: 0,
        models: new Set(),
        providers: new Set(),
        users: new Set(),
        sessions: new Set(),
      }
      for (const l of this.logs) {
        if (l.direction === 'request') s.requests++
        if (l.direction === 'response') s.responses++
        // duration_seconds is the raw field from RawAILogger
        if (l.duration_seconds != null) { s.totalDuration += l.duration_seconds; s.durationCount++ }
        if (l.model) s.models.add(l.model)
        if (l.provider) s.providers.add(l.provider)
        if (l.username) s.users.add(l.username)
        if (l.session_id) s.sessions.add(l.session_id)
      }
      return s
    },

    kpis() {
      const s = this.stats
      const avgDur = s.durationCount ? (s.totalDuration / s.durationCount) : 0
      return [
        {
          label: 'Total Logs',
          value: this.fmtNum(s.total),
          sub: `${this.logs.length} loaded`,
          icon: 'fa-solid fa-list',
          color: 'text-primary',
          bgColor: 'bg-primary/10'
        },
        {
          label: 'Requests',
          value: this.fmtNum(s.requests),
          sub: 'outgoing',
          icon: 'fa-solid fa-arrow-up',
          color: 'text-success',
          bgColor: 'bg-success/10'
        },
        {
          label: 'Responses',
          value: this.fmtNum(s.responses),
          sub: 'completed',
          icon: 'fa-solid fa-arrow-down',
          color: 'text-warning',
          bgColor: 'bg-warning/10'
        },
        {
          label: 'Sessions',
          value: s.sessions.size.toString(),
          sub: 'unique',
          icon: 'fa-solid fa-comments',
          color: 'text-secondary',
          bgColor: 'bg-secondary/10'
        },
        {
          label: 'Avg Duration',
          value: s.durationCount ? avgDur.toFixed(2) + 's' : 'N/A',
          sub: 'per response',
          icon: 'fa-solid fa-stopwatch',
          color: 'text-info',
          bgColor: 'bg-info/10'
        },
        {
          label: 'Models',
          value: s.models.size.toString(),
          sub: Array.from(s.models).slice(0, 2).join(', ') || '—',
          icon: 'fa-solid fa-microchip',
          color: 'text-accent',
          bgColor: 'bg-accent/10'
        },
        {
          label: 'Providers',
          value: s.providers.size.toString(),
          sub: Array.from(s.providers).slice(0, 2).join(', ') || '—',
          icon: 'fa-solid fa-plug',
          color: 'text-fuchsia-400',
          bgColor: 'bg-fuchsia-400/10'
        },
        {
          label: 'Users',
          value: s.users.size.toString(),
          sub: 'active',
          icon: 'fa-solid fa-users',
          color: 'text-error',
          bgColor: 'bg-error/10'
        },
      ]
    }
  },
  methods: {
    fmtNum(n) {
      if (!n) return '0'
      if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
      if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
      return n.toString()
    }
  }
}
</script>