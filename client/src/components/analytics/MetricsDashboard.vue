<script setup>
import DailyChart from './DailyChart.vue'
</script>

<template>
  <div class="metrics-dashboard bg-base-200 p-4 overflow-auto">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
      <div class="flex items-center gap-3">
        <i class="fa-solid fa-chart-bar text-primary text-3xl"></i>
        <h1 class="text-2xl font-bold text-base-content">Analytics Dashboard</h1>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <button
          class="btn btn-sm btn-outline"
          :class="{ 'btn-active': isAdminView }"
          v-if="$storex.users.isAdmin"
          @click="toggleAdminView"
        >
          <i class="fa-solid fa-shield-halved text-sm"></i>
          Admin View
        </button>
        <button class="btn btn-sm btn-primary" @click="loadData" :disabled="loading">
          <i class="fa-solid fa-rotate-right text-sm" :class="{ 'animate-spin': loading }"></i>
          Refresh
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="card bg-base-100 shadow mb-6">
      <div class="card-body py-3 px-4">
        <div class="flex flex-wrap items-center gap-4">
          <div class="flex items-center gap-2">
            <i class="fa-regular fa-calendar-days text-base-content/60 text-sm"></i>
            <span class="text-sm font-medium text-base-content/70">Date Range</span>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <div class="flex items-center gap-1">
              <label class="text-xs text-base-content/60">From</label>
              <input
                type="date"
                v-model="filters.startDate"
                class="input input-bordered input-sm w-36"
                @change="loadData"
              />
            </div>
            <div class="flex items-center gap-1">
              <label class="text-xs text-base-content/60">To</label>
              <input
                type="date"
                v-model="filters.endDate"
                class="input input-bordered input-sm w-36"
                @change="loadData"
              />
            </div>
          </div>

          <!-- Quick date presets -->
          <div class="flex flex-wrap gap-1">
            <button
              v-for="preset in datePresets"
              :key="preset.label"
              class="btn btn-xs"
              :class="activePreset === preset.label ? 'btn-primary' : 'btn-ghost'"
              @click="applyPreset(preset)"
            >
              {{ preset.label }}
            </button>
          </div>

          <!-- Admin filters -->
          <template v-if="isAdminView">
            <div class="flex items-center gap-1">
              <label class="text-xs text-base-content/60">User</label>
              <input
                type="text"
                v-model="filters.username"
                placeholder="All users"
                class="input input-bordered input-sm w-32"
                @change="loadData"
              />
            </div>
          </template>

          <!-- Model filter -->
          <div class="flex items-center gap-1">
            <label class="text-xs text-base-content/60">Model</label>
            <select
              v-model="filters.model"
              class="select select-bordered select-sm w-40"
              @change="loadData"
            >
              <option value="">All models</option>
              <option v-for="model in availableModels" :key="model" :value="model">
                {{ model }}
              </option>
            </select>
          </div>

          <button class="btn btn-xs btn-ghost" @click="clearFilters">
            <i class="fa-solid fa-filter-circle-xmark text-xs"></i>
            Clear
          </button>
        </div>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div v-for="i in 4" :key="i" class="card bg-base-100 shadow">
          <div class="card-body p-4 animate-pulse">
            <div class="h-4 bg-base-300 rounded w-1/2 mb-3"></div>
            <div class="h-8 bg-base-300 rounded w-3/4"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Dashboard content -->
    <template v-else>
      <!-- KPI Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div
          v-for="kpi in kpiCards"
          :key="kpi.label"
          class="card bg-base-100 shadow hover:shadow-lg transition-shadow"
        >
          <div class="card-body p-4">
            <div class="flex items-start justify-between">
              <div>
                <p class="text-xs font-medium text-base-content/60 uppercase tracking-wider">
                  {{ kpi.label }}
                </p>
                <p class="text-2xl font-bold mt-1" :class="kpi.color">
                  {{ kpi.value }}
                </p>
                <p v-if="kpi.sub" class="text-xs text-base-content/50 mt-1">{{ kpi.sub }}</p>
              </div>
              <div class="p-2 rounded-lg" :class="kpi.bgColor">
                <i :class="[kpi.faIcon, kpi.color]"></i>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <!-- Daily Usage Chart -->
        <div class="card bg-base-100 shadow">
          <div class="card-body p-4">
            <h2 class="card-title text-base mb-4 flex items-center gap-2">
              <i class="fa-solid fa-chart-line text-primary"></i>
              Daily Token Usage
            </h2>
            <div v-if="dailyData.length === 0" class="flex items-center justify-center h-48 text-base-content/40">
              <div class="text-center">
                <i class="fa-solid fa-chart-line text-5xl"></i>
                <p class="mt-2 text-sm">No daily data available</p>
              </div>
            </div>
            <div v-else class="relative h-48">
              <DailyChart :data="dailyData" />
            </div>
          </div>
        </div>

        <!-- Model Breakdown -->
        <div class="card bg-base-100 shadow">
          <div class="card-body p-4">
            <h2 class="card-title text-base mb-4 flex items-center gap-2">
              <i class="fa-solid fa-microchip text-secondary"></i>
              Usage by Model
            </h2>
            <div v-if="Object.keys(byModelData).length === 0" class="flex items-center justify-center h-48 text-base-content/40">
              <div class="text-center">
                <i class="fa-solid fa-robot text-5xl"></i>
                <p class="mt-2 text-sm">No model data available</p>
              </div>
            </div>
            <div v-else class="space-y-3 overflow-y-auto max-h-48">
              <div
                v-for="(stats, model) in byModelData"
                :key="model"
                class="flex items-center gap-3"
              >
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between mb-1">
                    <span class="text-xs font-medium truncate" :title="model">{{ model }}</span>
                    <span class="text-xs text-base-content/60 ml-2">
                      {{ formatNumber(stats.total_tokens) }} tokens
                    </span>
                  </div>
                  <div class="w-full bg-base-200 rounded-full h-2">
                    <div
                      class="h-2 rounded-full bg-primary transition-all duration-500"
                      :style="{ width: getModelPercentage(stats.total_tokens) + '%' }"
                    ></div>
                  </div>
                  <div class="flex gap-2 mt-1">
                    <span class="text-xs text-success">↑ {{ formatNumber(stats.input_tokens) }} in</span>
                    <span class="text-xs text-warning">↓ {{ formatNumber(stats.output_tokens) }} out</span>
                    <span class="text-xs text-base-content/50">{{ stats.calls }} calls</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Admin-only rows -->
      <template v-if="isAdminView">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <!-- By User -->
          <div class="card bg-base-100 shadow">
            <div class="card-body p-4">
              <h2 class="card-title text-base mb-4 flex items-center gap-2">
                <i class="fa-solid fa-users text-accent"></i>
                Usage by User
              </h2>
              <div v-if="Object.keys(byUserData).length === 0" class="flex items-center justify-center h-48 text-base-content/40">
                <div class="text-center">
                  <i class="fa-regular fa-user text-5xl"></i>
                  <p class="mt-2 text-sm">No user data available</p>
                </div>
              </div>
              <div v-else class="space-y-3 overflow-y-auto max-h-48">
                <div
                  v-for="(stats, username) in byUserData"
                  :key="username"
                  class="flex items-center gap-3"
                >
                  <div class="avatar placeholder">
                    <div class="bg-neutral text-neutral-content rounded-full w-7">
                      <span class="text-xs">{{ username.charAt(0).toUpperCase() }}</span>
                    </div>
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between mb-1">
                      <span class="text-xs font-medium truncate">{{ username }}</span>
                      <span class="text-xs text-base-content/60">
                        {{ formatNumber(stats.total_tokens) }} tokens
                      </span>
                    </div>
                    <div class="w-full bg-base-200 rounded-full h-2">
                      <div
                        class="h-2 rounded-full bg-accent transition-all duration-500"
                        :style="{ width: getUserPercentage(stats.total_tokens) + '%' }"
                      ></div>
                    </div>
                    <div class="flex gap-2 mt-1">
                      <span class="text-xs text-base-content/50">{{ stats.calls }} calls</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- By Project -->
          <div class="card bg-base-100 shadow">
            <div class="card-body p-4">
              <h2 class="card-title text-base mb-4 flex items-center gap-2">
                <i class="fa-solid fa-folder-open text-info"></i>
                Usage by Project
              </h2>
              <div v-if="Object.keys(byProjectData).length === 0" class="flex items-center justify-center h-48 text-base-content/40">
                <div class="text-center">
                  <i class="fa-regular fa-folder text-5xl"></i>
                  <p class="mt-2 text-sm">No project data available</p>
                </div>
              </div>
              <div v-else class="space-y-3 overflow-y-auto max-h-48">
                <div
                  v-for="(stats, projectName) in byProjectData"
                  :key="projectName"
                  class="flex items-center gap-3"
                >
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between mb-1">
                      <span class="text-xs font-medium truncate" :title="projectName">
                        {{ projectName }}
                      </span>
                      <span class="text-xs text-base-content/60">
                        {{ formatNumber(stats.total_tokens) }} tokens
                      </span>
                    </div>
                    <div class="w-full bg-base-200 rounded-full h-2">
                      <div
                        class="h-2 rounded-full bg-info transition-all duration-500"
                        :style="{ width: getProjectPercentage(stats.total_tokens) + '%' }"
                      ></div>
                    </div>
                    <div class="flex gap-2 mt-1">
                      <span class="text-xs text-base-content/50">{{ stats.calls }} calls</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- Daily Data Table -->
      <div class="card bg-base-100 shadow">
        <div class="card-body p-4">
          <div class="flex items-center justify-between mb-4">
            <h2 class="card-title text-base flex items-center gap-2">
              <i class="fa-solid fa-table text-primary"></i>
              Daily Breakdown
            </h2>
            <div class="flex items-center gap-2">
              <button
                class="btn btn-xs btn-ghost"
                @click="sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'"
              >
                <i :class="sortOrder === 'asc' ? 'fa-solid fa-arrow-up-wide-short' : 'fa-solid fa-arrow-down-wide-short'" class="text-xs"></i>
                {{ sortOrder === 'asc' ? 'Oldest first' : 'Newest first' }}
              </button>
            </div>
          </div>

          <div v-if="sortedDailyData.length === 0" class="text-center py-8 text-base-content/40">
            <i class="fa-solid fa-database text-5xl"></i>
            <p class="mt-2 text-sm">No data available for the selected period</p>
          </div>

          <div v-else class="overflow-x-auto">
            <table class="table table-sm w-full">
              <thead>
                <tr class="text-xs">
                  <th>Date</th>
                  <th class="text-right">Input Tokens</th>
                  <th class="text-right">Output Tokens</th>
                  <th class="text-right">Total Tokens</th>
                  <th class="text-right">Calls</th>
                  <th>Distribution</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in sortedDailyData"
                  :key="row.date"
                  class="hover text-sm"
                >
                  <td class="font-medium">{{ row.date }}</td>
                  <td class="text-right text-success">{{ formatNumber(row.input_tokens) }}</td>
                  <td class="text-right text-warning">{{ formatNumber(row.output_tokens) }}</td>
                  <td class="text-right font-semibold">{{ formatNumber(row.total_tokens) }}</td>
                  <td class="text-right text-base-content/60">{{ row.calls }}</td>
                  <td class="min-w-24">
                    <div class="flex h-2 rounded-full overflow-hidden bg-base-200 w-24">
                      <div
                        class="bg-success"
                        :style="{ width: (row.input_tokens / row.total_tokens * 100) + '%' }"
                      ></div>
                      <div
                        class="bg-warning"
                        :style="{ width: (row.output_tokens / row.total_tokens * 100) + '%' }"
                      ></div>
                    </div>
                  </td>
                </tr>
              </tbody>
              <tfoot>
                <tr class="font-bold text-sm border-t-2 border-base-300">
                  <td>Total</td>
                  <td class="text-right text-success">{{ formatNumber(totalStats.input_tokens) }}</td>
                  <td class="text-right text-warning">{{ formatNumber(totalStats.output_tokens) }}</td>
                  <td class="text-right">{{ formatNumber(totalStats.total_tokens) }}</td>
                  <td class="text-right text-base-content/60">{{ totalStats.calls }}</td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>

      <!-- Error state -->
      <div v-if="error" class="alert alert-error mt-4">
        <i class="fa-solid fa-circle-exclamation"></i>
        <span>{{ error }}</span>
        <button class="btn btn-sm btn-ghost" @click="error = null">Dismiss</button>
      </div>
    </template>
  </div>
</template>

<script>
export default {
  name: 'MetricsDashboard',
  data() {
    const today = new Date()
    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(today.getDate() - 30)

    return {
      loading: false,
      error: null,
      isAdminView: false,
      sortOrder: 'desc',
      activePreset: '30d',
      filters: {
        startDate: thirtyDaysAgo.toISOString().split('T')[0],
        endDate: today.toISOString().split('T')[0],
        username: '',
        model: '',
        projectName: ''
      },
      totalStats: {
        input_tokens: 0,
        output_tokens: 0,
        total_tokens: 0,
        calls: 0
      },
      dailyData: [],
      byModelData: {},
      byUserData: {},
      byProjectData: {},
      datePresets: [
        { label: '7d', days: 7 },
        { label: '30d', days: 30 },
        { label: '90d', days: 90 },
        { label: 'This month', type: 'thisMonth' },
        { label: 'All time', type: 'allTime' }
      ]
    }
  },
  computed: {
    availableModels() {
      const models = new Set()
      Object.keys(this.byModelData).forEach(m => models.add(m))
      return Array.from(models).sort()
    },
    kpiCards() {
      const avgTokensPerCall = this.totalStats.calls > 0
        ? Math.round(this.totalStats.total_tokens / this.totalStats.calls)
        : 0
      const ratio = this.totalStats.total_tokens > 0
        ? ((this.totalStats.output_tokens / this.totalStats.total_tokens) * 100).toFixed(1)
        : 0

      return [
        {
          label: 'Total Tokens',
          value: this.formatNumber(this.totalStats.total_tokens),
          sub: 'across selected period',
          faIcon: 'fa-solid fa-hashtag',
          color: 'text-primary',
          bgColor: 'bg-primary/10'
        },
        {
          label: 'Total Calls',
          value: this.formatNumber(this.totalStats.calls),
          sub: `avg ${this.formatNumber(avgTokensPerCall)} tokens/call`,
          faIcon: 'fa-solid fa-plug',
          color: 'text-secondary',
          bgColor: 'bg-secondary/10'
        },
        {
          label: 'Input Tokens',
          value: this.formatNumber(this.totalStats.input_tokens),
          sub: `${((this.totalStats.input_tokens / Math.max(this.totalStats.total_tokens, 1)) * 100).toFixed(1)}% of total`,
          faIcon: 'fa-solid fa-circle-arrow-up',
          color: 'text-success',
          bgColor: 'bg-success/10'
        },
        {
          label: 'Output Tokens',
          value: this.formatNumber(this.totalStats.output_tokens),
          sub: `${ratio}% of total`,
          faIcon: 'fa-solid fa-circle-arrow-down',
          color: 'text-warning',
          bgColor: 'bg-warning/10'
        }
      ]
    },
    sortedDailyData() {
      return [...this.dailyData].sort((a, b) => {
        if (this.sortOrder === 'desc') return b.date > a.date ? 1 : -1
        return a.date > b.date ? 1 : -1
      })
    },
    maxModelTokens() {
      return Math.max(...Object.values(this.byModelData).map(s => s.total_tokens), 1)
    },
    maxUserTokens() {
      return Math.max(...Object.values(this.byUserData).map(s => s.total_tokens), 1)
    },
    maxProjectTokens() {
      return Math.max(...Object.values(this.byProjectData).map(s => s.total_tokens), 1)
    }
  },
  methods: {
    toggleAdminView() {
      this.isAdminView = !this.isAdminView
      this.loadData()
    },
    applyPreset(preset) {
      this.activePreset = preset.label
      const today = new Date()
      const end = today.toISOString().split('T')[0]

      if (preset.type === 'allTime') {
        this.filters.startDate = '2024-01-01'
        this.filters.endDate = end
      } else if (preset.type === 'thisMonth') {
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
        this.filters.startDate = firstDay.toISOString().split('T')[0]
        this.filters.endDate = end
      } else {
        const past = new Date()
        past.setDate(today.getDate() - preset.days)
        this.filters.startDate = past.toISOString().split('T')[0]
        this.filters.endDate = end
      }
      this.loadData()
    },
    clearFilters() {
      const today = new Date()
      const thirtyDaysAgo = new Date()
      thirtyDaysAgo.setDate(today.getDate() - 30)
      this.filters = {
        startDate: thirtyDaysAgo.toISOString().split('T')[0],
        endDate: today.toISOString().split('T')[0],
        username: '',
        model: '',
        projectName: ''
      }
      this.activePreset = '30d'
      this.loadData()
    },
    async loadData() {
      this.loading = true
      this.error = null
      try {
        const analytics = this.isAdminView && this.$storex.users.isAdmin
          ? this.$project.$api.analytics.admin
          : this.$project.$api.analytics

        const baseFilters = {
          startDate: this.filters.startDate,
          endDate: this.filters.endDate,
          model: this.filters.model || undefined,
          projectName: this.filters.projectName || undefined
        }

        const adminFilters = this.isAdminView
          ? { ...baseFilters, username: this.filters.username || undefined }
          : baseFilters

        const [total, daily, byModel] = await Promise.all([
          analytics.total(adminFilters),
          analytics.daily(adminFilters),
          analytics.byModel(adminFilters)
        ])

        this.totalStats = total || { input_tokens: 0, output_tokens: 0, total_tokens: 0, calls: 0 }
        this.dailyData = Array.isArray(daily) ? daily : []
        this.byModelData = byModel || {}

        if (this.isAdminView && this.$storex.users.isAdmin) {
          const [byUser, byProject] = await Promise.all([
            this.$project.$api.analytics.admin.byUser(baseFilters),
            this.$project.$api.analytics.admin.byProject(adminFilters)
          ])
          this.byUserData = byUser || {}
          this.byProjectData = byProject || {}
        }
      } catch (err) {
        console.error('Failed to load analytics:', err)
        this.error = 'Failed to load analytics data. Please try again.'
      } finally {
        this.loading = false
      }
    },
    formatNumber(num) {
      if (!num) return '0'
      if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M'
      if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K'
      return num.toString()
    },
    getModelPercentage(tokens) {
      return ((tokens / this.maxModelTokens) * 100).toFixed(1)
    },
    getUserPercentage(tokens) {
      return ((tokens / this.maxUserTokens) * 100).toFixed(1)
    },
    getProjectPercentage(tokens) {
      return ((tokens / this.maxProjectTokens) * 100).toFixed(1)
    }
  },
  mounted() {
    this.loadData()
  }
}
</script>