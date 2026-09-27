<script setup>
import DailyChart from './DailyChart.vue'
import Collapsible from '@/components/Collapsible.vue'
import PriceEditor from './PriceEditor.vue'
</script>

<template>
  <div class="metrics-dashboard bg-[#111111] h-full flex flex-col overflow-auto">
    <!-- Fixed Header -->
    <div class="sticky top-0 z-40 border-b border-white/5 bg-[#111111]/95 backdrop-blur-sm">
      <!-- Title Bar -->
      <div class="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-primary to-primary/80 flex items-center justify-center flex-shrink-0">
            <i class="fa-solid fa-chart-bar text-white text-sm"></i>
          </div>
          <h1 class="text-lg font-bold text-white">Analytics</h1>
        </div>

        <!-- Quick Actions -->
        <div class="flex items-center gap-2">
          <!-- Grouping selector -->
          <select
            v-model="grouping"
            class="px-2 py-1.5 bg-transparent border border-white/10 hover:border-white/20 rounded-lg text-xs text-white font-medium outline-none focus:border-primary/50 transition-colors cursor-pointer"
            @change="loadData"
          >
            <option value="minute" class="bg-[#1a1a1a]">Min</option>
            <option value="hour" class="bg-[#1a1a1a]">Hour</option>
            <option value="day" class="bg-[#1a1a1a]">Day</option>
          </select>

          <!-- Admin toggle -->
          <button
            v-if="$storex.users.isAdmin"
            @click="toggleAdminView"
            class="px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
            :class="isAdminView ? 'bg-primary/20 text-primary border border-primary/30 hover:bg-primary/30' : 'bg-white/5 text-white/70 border border-white/10 hover:bg-white/10'"
            title="Switch view mode"
          >
            <i class="fa-solid fa-shield-halved text-xs"></i>
          </button>

          <!-- Refresh button -->
          <button
            @click="loadData"
            :disabled="loading"
            class="px-2.5 py-1.5 bg-primary hover:bg-primary/90 disabled:bg-primary/50 disabled:cursor-not-allowed text-white rounded-lg text-xs font-medium transition-all flex items-center gap-1.5"
            title="Refresh data"
          >
            <i :class="['fa-solid fa-rotate-right', { 'animate-spin': loading }]" class="text-xs"></i>
          </button>
        </div>
      </div>

      <!-- Filter Bar (Compact) -->
      <div class="border-t border-white/5 bg-white/[0.02]">
        <div class="max-w-7xl mx-auto px-6 py-2 space-y-2">
          <!-- Row 1: Date Presets + Model + Auto-refresh -->
          <div class="flex items-center gap-2 flex-wrap">
            <!-- Date presets -->
            <div class="flex items-center gap-1">
              <button
                v-for="preset in datePresets"
                :key="preset.label"
                @click="applyPreset(preset)"
                class="px-2 py-1 text-xs font-medium rounded-lg transition-all duration-200 whitespace-nowrap"
                :class="activePreset === preset.label
                  ? 'bg-primary text-white'
                  : 'bg-white/5 text-white/70 hover:bg-white/10 border border-white/10'
                "
              >
                {{ preset.label }}
              </button>
            </div>

            <!-- Model filter -->
            <div class="w-px h-4 bg-white/10"></div>
            <select
              v-model="filters.model"
              class="px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-xs font-medium outline-none focus:border-primary/50 focus:bg-white/[0.08] transition-all cursor-pointer hover:border-white/20"
              @change="loadData"
              title="Filter by model"
            >
              <option value="" class="bg-[#1a1a1a]">All models</option>
              <option v-for="model in availableModels" :key="model" :value="model" class="bg-[#1a1a1a]">
                {{ model }}
              </option>
            </select>

            <!-- Auto-refresh -->
            <div class="w-px h-4 bg-white/10"></div>
            <select
              v-model="autoRefreshInterval"
              class="px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-xs text-white font-medium outline-none cursor-pointer hover:border-white/20 transition-colors"
              @change="setupAutoRefresh"
              title="Auto-refresh interval"
            >
              <option :value="null" class="bg-[#1a1a1a]">Off</option>
              <option :value="30" class="bg-[#1a1a1a]">30s</option>
              <option :value="60" class="bg-[#1a1a1a]">1m</option>
              <option :value="300" class="bg-[#1a1a1a]">5m</option>
              <option :value="900" class="bg-[#1a1a1a]">15m</option>
            </select>

            <div class="flex-1"></div>

            <!-- Advanced filters toggle -->
            <button
              @click="showAdvancedFilters = !showAdvancedFilters"
              class="px-2 py-1 text-xs font-medium rounded-lg text-white/50 hover:text-white hover:bg-white/5 border border-transparent hover:border-white/10 transition-all"
              title="Toggle advanced filters"
            >
              <i :class="['fa-solid fa-sliders', showAdvancedFilters ? 'text-primary' : '']" class="text-xs"></i>
            </button>

            <!-- Clear filters -->
            <button
              @click="clearFilters"
              class="px-2 py-1 text-xs font-medium rounded-lg text-white/50 hover:text-white hover:bg-white/5 border border-transparent hover:border-white/10 transition-all"
              title="Clear all filters"
            >
              <i class="fa-solid fa-xmark text-xs"></i>
            </button>
          </div>

          <!-- Advanced Filters (Collapsible) -->
          <div v-if="showAdvancedFilters" class="pt-2 border-t border-white/5 space-y-2">
            <!-- Date Range -->
            <div class="flex items-center gap-3 flex-wrap">
              <span class="text-xs text-white/40 font-medium">Date:</span>
              <input
                type="date"
                v-model="filters.startDate"
                class="px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-xs font-medium outline-none focus:border-primary/50 focus:bg-white/[0.08] transition-all"
                @change="applyCustomDates"
              />
              <span class="text-white/30 text-xs">→</span>
              <input
                type="date"
                v-model="filters.endDate"
                class="px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-xs font-medium outline-none focus:border-primary/50 focus:bg-white/[0.08] transition-all"
                @change="applyCustomDates"
              />
            </div>

            <!-- Admin Filters -->
            <template v-if="isAdminView">
              <div class="flex items-center gap-3 flex-wrap">
                <span class="text-xs text-white/40 font-medium">User:</span>
                <input
                  type="text"
                  v-model="filters.username"
                  placeholder="Search username..."
                  class="px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-xs placeholder:text-white/30 outline-none focus:border-primary/50 focus:bg-white/[0.08] transition-all"
                  @change="loadData"
                />
                <span class="text-xs text-white/40 font-medium">Project:</span>
                <input
                  type="text"
                  v-model="filters.projectName"
                  placeholder="Search project..."
                  class="px-2 py-1 bg-white/5 border border-white/10 rounded-lg text-white text-xs placeholder:text-white/30 outline-none focus:border-primary/50 focus:bg-white/[0.08] transition-all"
                  @change="loadData"
                />
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <!-- Scrollable Content -->
    <div class="flex-1 overflow-y-auto">
      <div class="max-w-7xl mx-auto px-6 py-6 space-y-6">
        <!-- Loading State -->
        <template v-if="loading">
          <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
            <div v-for="i in 7" :key="i" class="h-16 rounded-lg bg-white/5 border border-white/5 animate-pulse"></div>
          </div>
        </template>

        <!-- Dashboard Content -->
        <template v-else>
          <!-- KPI Cards Grid (Simplified) -->
          <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
            <div
              v-for="kpi in kpiCards"
              :key="kpi.label"
              class="group relative border border-white/10 rounded-lg p-3 hover:border-white/20 transition-all duration-200 cursor-help"
              :title="kpi.label + ': ' + kpi.sub"
            >
              <div class="flex flex-col items-center text-center gap-1.5">
                <div class="w-6 h-6 rounded flex items-center justify-center flex-shrink-0" :style="{ background: `${kpi.accentColor}15` }">
                  <i :class="[kpi.faIcon, 'text-xs']" :style="{ color: kpi.accentColor }"></i>
                </div>
                <p class="text-sm font-bold text-white leading-tight">
                  {{ kpi.value }}
                </p>
              </div>
            </div>
          </div>

          <!-- Charts Section -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <!-- Token Usage Chart -->
            <div class="border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-colors">
              <div class="px-4 py-3 border-b border-white/5 flex items-center gap-2">
                <i class="fa-solid fa-chart-line text-primary text-sm"></i>
                <h2 class="text-sm font-bold text-white">{{ groupingLabel }} Token Usage</h2>
              </div>
              <div class="p-4">
                <div v-if="dailyData.length === 0" class="flex flex-col items-center justify-center h-72 text-white/30">
                  <i class="fa-solid fa-chart-line text-4xl mb-2"></i>
                  <p class="text-xs font-medium">No data available</p>
                </div>
                <div v-else class="h-72">
                  <DailyChart :data="dailyData" :grouping="grouping" />
                </div>
              </div>
            </div>

            <!-- Model Usage Breakdown -->
            <div class="border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-colors">
              <div class="px-4 py-3 border-b border-white/5 flex items-center gap-2">
                <i class="fa-solid fa-microchip text-secondary text-sm"></i>
                <h2 class="text-sm font-bold text-white">Usage by Model</h2>
              </div>
              <div class="p-4">
                <div v-if="Object.keys(byModelData).length === 0" class="flex flex-col items-center justify-center h-72 text-white/30">
                  <i class="fa-solid fa-robot text-4xl mb-2"></i>
                  <p class="text-xs font-medium">No model data available</p>
                </div>
                <div v-else class="space-y-3 max-h-72 overflow-y-auto pr-2">
                  <div
                    v-for="[model, stats] in byModelDataSorted"
                    :key="model"
                    class="group"
                  >
                    <div class="flex items-center justify-between mb-1.5">
                      <span class="text-xs font-semibold text-white truncate" :title="model">{{ model }}</span>
                      <span class="text-xs text-white/50">{{ formatTokens(stats.total_tokens) }}</span>
                    </div>
                    <div class="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-gradient-to-r from-primary to-primary/60 transition-all duration-500"
                        :style="{ width: getModelPercentage(stats.total_tokens) + '%' }"
                      ></div>
                    </div>
                    <div class="flex gap-2 mt-1 flex-wrap text-xs">
                      <span class="text-success">
                        <i class="fa-solid fa-arrow-up text-xs mr-0.5"></i>{{ formatTokens(stats.input_tokens) }}
                      </span>
                      <span class="text-warning">
                        <i class="fa-solid fa-arrow-down text-xs mr-0.5"></i>{{ formatTokens(stats.output_tokens) }}
                      </span>
                      <span v-if="stats.total_cxjcoins != null" class="text-fuchsia-400 ml-auto">
                        🪙 {{ formatCoins(stats.total_cxjcoins) }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Admin Section -->
          <template v-if="isAdminView">
            <!-- User & Project Stats -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <!-- By User -->
              <div class="border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-colors">
                <div class="px-4 py-3 border-b border-white/5 flex items-center gap-2">
                  <i class="fa-solid fa-users text-accent text-sm"></i>
                  <h2 class="text-sm font-bold text-white">Usage by User</h2>
                </div>
                <div class="p-4">
                  <div v-if="Object.keys(byUserData).length === 0" class="flex flex-col items-center justify-center h-56 text-white/30">
                    <i class="fa-regular fa-user text-3xl mb-2"></i>
                    <p class="text-xs font-medium">No user data available</p>
                  </div>
                  <div v-else class="space-y-2 max-h-56 overflow-y-auto pr-2">
                    <div
                      v-for="(stats, username) in byUserData"
                      :key="username"
                      class="group"
                    >
                      <div class="flex items-center gap-2 mb-1.5">
                        <div class="w-6 h-6 rounded-full bg-gradient-to-br from-primary to-primary/60 flex items-center justify-center flex-shrink-0 text-xs font-bold text-white">
                          {{ username.charAt(0).toUpperCase() }}
                        </div>
                        <span class="text-xs font-semibold text-white flex-1 truncate">{{ username }}</span>
                        <span class="text-xs text-white/50">{{ formatTokens(stats.total_tokens) }}</span>
                      </div>
                      <div class="w-full h-1.5 bg-white/10 rounded-full overflow-hidden ml-8">
                        <div
                          class="h-full bg-gradient-to-r from-accent to-accent/60 transition-all duration-500"
                          :style="{ width: getUserPercentage(stats.total_tokens) + '%' }"
                        ></div>
                      </div>
                      <div class="flex gap-1.5 mt-1 ml-8 text-xs flex-wrap">
                        <span class="text-white/50">{{ stats.calls }} calls</span>
                        <span v-if="stats.total_cxjcoins != null" class="text-fuchsia-400">🪙 {{ formatCoins(stats.total_cxjcoins) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- By Project -->
              <div class="border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-colors">
                <div class="px-4 py-3 border-b border-white/5 flex items-center gap-2">
                  <i class="fa-solid fa-folder-open text-info text-sm"></i>
                  <h2 class="text-sm font-bold text-white">Usage by Project</h2>
                </div>
                <div class="p-4">
                  <div v-if="Object.keys(byProjectData).length === 0" class="flex flex-col items-center justify-center h-56 text-white/30">
                    <i class="fa-regular fa-folder text-3xl mb-2"></i>
                    <p class="text-xs font-medium">No project data available</p>
                  </div>
                  <div v-else class="space-y-2 max-h-56 overflow-y-auto pr-2">
                    <div
                      v-for="(stats, projectName) in byProjectData"
                      :key="projectName"
                      class="group"
                    >
                      <div class="flex items-center justify-between mb-1.5">
                        <span class="text-xs font-semibold text-white truncate" :title="projectName">{{ projectName }}</span>
                        <span class="text-xs text-white/50">{{ formatTokens(stats.total_tokens) }}</span>
                      </div>
                      <div class="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                          class="h-full bg-gradient-to-r from-info to-info/60 transition-all duration-500"
                          :style="{ width: getProjectPercentage(stats.total_tokens) + '%' }"
                        ></div>
                      </div>
                      <div class="flex gap-1.5 mt-1 text-xs flex-wrap">
                        <span class="text-white/50">{{ stats.calls }} calls</span>
                        <span v-if="stats.total_cxjcoins != null" class="text-fuchsia-400">🪙 {{ formatCoins(stats.total_cxjcoins) }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Model Performance Table -->
            <div class="border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-colors">
              <div class="px-4 py-3 border-b border-white/5 flex items-center gap-2">
                <i class="fa-solid fa-gauge-high text-warning text-sm"></i>
                <h2 class="text-sm font-bold text-white">Model Performance</h2>
              </div>
              <div class="p-4">
                <div v-if="Object.keys(byModelData).length === 0" class="text-center py-8 text-white/30">
                  <i class="fa-solid fa-robot text-3xl mb-2"></i>
                  <p class="text-xs font-medium">No model performance data available</p>
                </div>
                <div v-else class="overflow-x-auto">
                  <table class="w-full text-xs">
                    <thead>
                      <tr class="border-b border-white/10">
                        <th class="text-left px-3 py-2 text-white/70 font-semibold">Model</th>
                        <th class="text-right px-3 py-2 text-white/70 font-semibold">Calls</th>
                        <th class="text-right px-3 py-2 text-white/70 font-semibold">Total Tokens</th>
                        <th class="text-right px-3 py-2 text-white/70 font-semibold">Avg Duration</th>
                        <th class="text-right px-3 py-2 text-white/70 font-semibold">Tokens / sec</th>
                        <th class="text-right px-3 py-2 text-white/70 font-semibold">Cost (🪙)</th>
                        <th class="text-left px-3 py-2 text-white/70 font-semibold">Speed</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-white/10">
                      <tr
                        v-for="(stats, model) in modelPerformanceRows"
                        :key="model"
                        class="hover:bg-white/5 transition-colors"
                      >
                        <td class="px-3 py-2 font-medium text-white truncate max-w-24" :title="model">{{ model }}</td>
                        <td class="px-3 py-2 text-right text-white/50">{{ stats.calls }}</td>
                        <td class="px-3 py-2 text-right text-white font-medium">{{ formatTokens(stats.total_tokens) }}</td>
                        <td class="px-3 py-2 text-right font-mono text-white/70">
                          {{ stats.total_duration_seconds > 0 ? stats.total_duration_seconds.toFixed(2) + 's' : 'N/A' }}
                        </td>
                        <td class="px-3 py-2 text-right font-mono font-semibold" :class="getTokensPerSecColor(stats.tokens_per_second)">
                          {{ stats.tokens_per_second > 0 ? formatTokens(stats.tokens_per_second) + '/s' : 'N/A' }}
                        </td>
                        <td class="px-3 py-2 text-right text-fuchsia-400 font-semibold">
                          {{ stats.total_cxjcoins != null ? formatCoins(stats.total_cxjcoins) : '-' }}
                        </td>
                        <td class="px-3 py-2">
                          <div class="flex items-center gap-2">
                            <div class="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden min-w-16">
                              <div
                                class="h-full rounded-full transition-all duration-500"
                                :class="getSpeedBarColor(stats.tokens_per_second)"
                                :style="{ width: getSpeedPercentage(stats.tokens_per_second) + '%' }"
                              ></div>
                            </div>
                            <span class="text-xs text-white/50 w-6 text-right">
                              {{ getSpeedPercentage(stats.tokens_per_second) }}%
                            </span>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </template>

          <!-- Data Table -->
          <div class="border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-colors">
            <div class="px-4 py-3 border-b border-white/5 flex items-center justify-between">
              <div class="flex items-center gap-2">
                <i class="fa-solid fa-table text-primary text-sm"></i>
                <h2 class="text-sm font-bold text-white">Period Breakdown</h2>
              </div>
              <button
                @click="sortOrder = sortOrder === 'asc' ? 'desc' : 'asc'"
                class="px-2 py-1 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-white/70 text-xs font-medium transition-all flex items-center gap-1"
              >
                <i :class="sortOrder === 'asc' ? 'fa-solid fa-arrow-up-wide-short' : 'fa-solid fa-arrow-down-wide-short'" class="text-xs"></i>
              </button>
            </div>
            <div class="p-4">
              <div v-if="sortedDailyData.length === 0" class="text-center py-8 text-white/30">
                <i class="fa-solid fa-database text-3xl mb-2"></i>
                <p class="text-xs font-medium">No data available for the selected period</p>
              </div>
              <div v-else class="overflow-x-auto">
                <table class="w-full text-xs">
                  <thead>
                    <tr class="border-b border-white/10">
                      <th class="text-left px-3 py-2 text-white/70 font-semibold">
                        {{ grouping === 'minute' ? 'Time' : grouping === 'hour' ? 'Hour' : 'Date' }}
                      </th>
                      <th class="text-right px-3 py-2 text-white/70 font-semibold">Input</th>
                      <th class="text-right px-3 py-2 text-white/70 font-semibold">Output</th>
                      <th class="text-right px-3 py-2 text-white/70 font-semibold">Total</th>
                      <th class="text-right px-3 py-2 text-white/70 font-semibold">Calls</th>
                      <th class="text-right px-3 py-2 text-white/70 font-semibold">Avg Duration</th>
                      <th class="text-right px-3 py-2 text-white/70 font-semibold">Cost</th>
                      <th class="text-left px-3 py-2 text-white/70 font-semibold">Distribution</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-white/10">
                    <tr
                      v-for="row in sortedDailyData"
                      :key="row.period || row.date"
                      class="hover:bg-white/5 transition-colors group"
                    >
                      <td class="px-3 py-2 font-semibold text-white">{{ row.period || row.date }}</td>
                      <td class="px-3 py-2 text-right text-success">{{ formatTokens(row.input_tokens) }}</td>
                      <td class="px-3 py-2 text-right text-warning">{{ formatTokens(row.output_tokens) }}</td>
                      <td class="px-3 py-2 text-right font-semibold text-white">{{ formatTokens(row.total_tokens) }}</td>
                      <td class="px-3 py-2 text-right text-white/50">{{ row.calls }}</td>
                      <td class="px-3 py-2 text-right font-mono text-white/50">
                        {{ row.total_duration_seconds > 0 ? row.total_duration_seconds.toFixed(2) + 's' : '-' }}
                      </td>
                      <td class="px-3 py-2 text-right">
                        <div class="flex items-center justify-end gap-1.5">
                          <span class="text-xs font-semibold text-fuchsia-400">
                            {{ row.total_cxjcoins != null ? formatCoins(row.total_cxjcoins) : '-' }}
                          </span>
                          <button
                            v-if="isAdminView"
                            @click="openPriceEditorForDate(row.period || row.date)"
                            class="opacity-0 group-hover:opacity-100 transition-opacity px-1.5 py-0.5 text-fuchsia-400 hover:bg-fuchsia-400/10 rounded text-xs"
                            title="Edit prices"
                          >
                            <i class="fa-solid fa-pen-to-square text-xs"></i>
                          </button>
                        </div>
                      </td>
                      <td class="px-3 py-2">
                        <div class="flex h-1.5 rounded-full overflow-hidden bg-white/10 w-24">
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
                    <tr class="border-t-2 border-white/20 font-bold text-white bg-white/5">
                      <td class="px-3 py-2">Total</td>
                      <td class="px-3 py-2 text-right text-success">{{ formatTokens(totalStats.input_tokens) }}</td>
                      <td class="px-3 py-2 text-right text-warning">{{ formatTokens(totalStats.output_tokens) }}</td>
                      <td class="px-3 py-2 text-right">{{ formatTokens(totalStats.total_tokens) }}</td>
                      <td class="px-3 py-2 text-right text-white/50">{{ totalStats.calls }}</td>
                      <td class="px-3 py-2 text-right font-mono text-white/50">
                        {{ totalStats.total_duration_seconds > 0 ? totalStats.total_duration_seconds.toFixed(2) + 's' : '-' }}
                      </td>
                      <td class="px-3 py-2 text-right text-fuchsia-400">
                        {{ totalStats.total_cxjcoins != null ? formatCoins(totalStats.total_cxjcoins) : '-' }}
                      </td>
                      <td></td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>
          </div>

          <!-- Price Management (admin only) -->
          <template v-if="isAdminView">
            <div class="border border-white/10 rounded-lg overflow-hidden hover:border-white/20 transition-colors">
              <button
                @click="priceEditorOpen = !priceEditorOpen"
                class="w-full px-4 py-3 border-b border-white/5 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
              >
                <div class="flex items-center gap-2">
                  <i class="fa-solid fa-tags text-primary text-sm"></i>
                  <span class="font-semibold text-white text-sm">Price Management</span>
                  <span v-if="priceEditorDate" class="ml-2 px-2 py-1 bg-primary/20 border border-primary/30 text-primary text-xs font-medium rounded-lg">
                    <i class="fa-solid fa-calendar-day mr-1 text-xs"></i>
                    {{ priceEditorDate }}
                  </span>
                  <span v-if="priceEditorModel" class="ml-2 px-2 py-1 bg-secondary/20 border border-secondary/30 text-secondary text-xs font-medium rounded-lg">
                    <i class="fa-solid fa-microchip mr-1 text-xs"></i>
                    {{ priceEditorModel }}
                  </span>
                </div>
                <i :class="['fa-solid fa-chevron-down', priceEditorOpen ? 'rotate-180' : '']" class="text-white/40 transition-transform text-sm"></i>
              </button>
              <div v-if="priceEditorOpen" class="p-4 space-y-4 border-t border-white/5">
                <div class="flex flex-col sm:flex-row gap-3">
                  <div class="flex-1 space-y-1.5">
                    <label class="text-xs font-semibold text-white/70">Filter by Model</label>
                    <select
                      v-model="priceEditorModel"
                      class="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white text-xs font-medium outline-none focus:border-primary/50 focus:bg-white/[0.08] transition-all cursor-pointer hover:border-white/20"
                    >
                      <option :value="null" class="bg-[#1a1a1a]">All models</option>
                      <option v-for="model in availableModels" :key="model" :value="model" class="bg-[#1a1a1a]">
                        {{ model }}
                      </option>
                    </select>
                  </div>
                  <div class="flex items-end">
                    <button
                      @click="priceEditorModel = null"
                      class="px-2.5 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-white/70 text-xs font-medium transition-all"
                    >
                      <i class="fa-solid fa-times text-xs mr-1"></i>
                      Clear
                    </button>
                  </div>
                </div>
                <PriceEditor
                  :initial-start-date="priceEditorDate"
                  :initial-end-date="priceEditorDate"
                  :initial-model="priceEditorModel"
                  @metrics-changed="loadData"
                />
              </div>
            </div>
          </template>

          <!-- Error State -->
          <div v-if="error" class="border border-error/30 rounded-lg p-3 flex items-start gap-3">
            <i class="fa-solid fa-circle-exclamation text-error text-base flex-shrink-0 mt-0.5"></i>
            <div class="flex-1">
              <p class="text-xs font-semibold text-error mb-1">Error loading analytics</p>
              <p class="text-xs text-error/80">{{ error }}</p>
            </div>
            <button
              @click="error = null"
              class="flex-shrink-0 px-2 py-1 bg-error/10 hover:bg-error/20 text-error rounded-lg text-xs font-medium transition-all"
            >
              Dismiss
            </button>
          </div>
        </template>
      </div>
    </div>
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
      grouping: 'day',
      showAdvancedFilters: false,
      priceEditorOpen: false,
      priceEditorDate: null,
      priceEditorModel: null,
      autoRefreshInterval: null,
      autoRefreshTimer: null,
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
        calls: 0,
        total_duration_seconds: 0,
        total_cxjcoins: null
      },
      dailyData: [],
      byModelData: {},
      byUserData: {},
      byProjectData: {},
      datePresets: [
        { label: 'Today', type: 'today' },
        { label: '7d', days: 7 },
        { label: '30d', days: 30 },
        { label: '90d', days: 90 },
        { label: 'Month', type: 'thisMonth' },
        { label: 'All', type: 'allTime' }
      ]
    }
  },
  computed: {
    availableModels() {
      const models = new Set()
      Object.keys(this.byModelData).forEach(m => models.add(m))
      return Array.from(models).sort()
    },

    groupingLabel() {
      return {
        minute: 'Per-Minute',
        hour: 'Hourly',
        day: 'Daily'
      }[this.grouping] || 'Daily'
    },

    kpiCards() {
      const avgTokensPerCall = this.totalStats.calls > 0
        ? Math.round(this.totalStats.total_tokens / this.totalStats.calls)
        : 0
      const ratio = this.totalStats.total_tokens > 0
        ? ((this.totalStats.output_tokens / this.totalStats.total_tokens) * 100).toFixed(1)
        : 0
      const avgDur = this.totalStats.total_duration_seconds || 0
      const tokPerSec = avgDur > 0 ? Math.round(avgTokensPerCall / avgDur) : 0

      return [
        {
          label: 'Total Tokens',
          value: this.formatTokens(this.totalStats.total_tokens),
          sub: 'across selected period',
          faIcon: 'fa-solid fa-hashtag',
          accentColor: '#6366f1'
        },
        {
          label: 'Total Calls',
          value: this.formatNumber(this.totalStats.calls),
          sub: `avg ${this.formatTokens(avgTokensPerCall)} tokens/call`,
          faIcon: 'fa-solid fa-plug',
          accentColor: '#ec4899'
        },
        {
          label: 'Input Tokens',
          value: this.formatTokens(this.totalStats.input_tokens),
          sub: `${((this.totalStats.input_tokens / Math.max(this.totalStats.total_tokens, 1)) * 100).toFixed(1)}% of total`,
          faIcon: 'fa-solid fa-circle-arrow-up',
          accentColor: '#10b981'
        },
        {
          label: 'Output Tokens',
          value: this.formatTokens(this.totalStats.output_tokens),
          sub: `${ratio}% of total`,
          faIcon: 'fa-solid fa-circle-arrow-down',
          accentColor: '#f59e0b'
        },
        {
          label: 'Avg Duration',
          value: avgDur > 0 ? avgDur.toFixed(2) + 's' : 'N/A',
          sub: 'per LLM call',
          faIcon: 'fa-solid fa-stopwatch',
          accentColor: '#3b82f6'
        },
        {
          label: 'Tokens / sec',
          value: tokPerSec > 0 ? this.formatTokens(tokPerSec) + '/s' : 'N/A',
          sub: 'generation speed',
          faIcon: 'fa-solid fa-bolt',
          accentColor: '#ef4444'
        },
        {
          label: 'Total Cost',
          value: this.totalStats.total_cxjcoins != null ? this.formatCoins(this.totalStats.total_cxjcoins) : 'N/A',
          sub: 'cxjcoins spent',
          faIcon: 'fa-solid fa-coins',
          accentColor: '#a855f7'
        }
      ]
    },

    sortedDailyData() {
      return [...this.dailyData].sort((a, b) => {
        const aKey = a.period || a.date
        const bKey = b.period || b.date
        if (this.sortOrder === 'desc') return bKey > aKey ? 1 : -1
        return aKey > bKey ? 1 : -1
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
    },

    byModelDataSorted() {
      return Object.entries(this.byModelData).sort((a, b) => b[1].total_tokens - a[1].total_tokens)
    },

    modelPerformanceRows() {
      const rows = {}
      for (const [model, stats] of Object.entries(this.byModelData)) {
        const avgDur = stats.total_duration_seconds || 0
        const avgTokens = stats.calls > 0 ? stats.total_tokens / stats.calls : 0
        const tokensPerSecond = avgDur > 0 ? Math.round(avgTokens / avgDur) : 0
        rows[model] = { ...stats, total_duration_seconds: avgDur, tokens_per_second: tokensPerSecond }
      }
      return Object.fromEntries(
        Object.entries(rows).sort((a, b) => b[1].tokens_per_second - a[1].tokens_per_second)
      )
    },

    maxTokensPerSecond() {
      const values = Object.values(this.modelPerformanceRows).map(s => s.tokens_per_second)
      return Math.max(...values, 1)
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
      const todayStr = today.toISOString().split('T')[0]

      if (preset.type === 'today') {
        this.filters.startDate = todayStr
        this.filters.endDate = todayStr
      } else if (preset.type === 'allTime') {
        this.filters.startDate = '2024-01-01'
        this.filters.endDate = todayStr
      } else if (preset.type === 'thisMonth') {
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
        this.filters.startDate = firstDay.toISOString().split('T')[0]
        this.filters.endDate = todayStr
      } else {
        const past = new Date()
        past.setDate(today.getDate() - preset.days)
        this.filters.startDate = past.toISOString().split('T')[0]
        this.filters.endDate = todayStr
      }
      this.loadData()
    },

    applyCustomDates() {
      this.activePreset = null
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
      this.grouping = 'day'
      this.priceEditorModel = null
      this.showAdvancedFilters = false
      this.loadData()
    },

    setupAutoRefresh() {
      if (this.autoRefreshTimer) {
        clearInterval(this.autoRefreshTimer)
        this.autoRefreshTimer = null
      }
      if (!this.autoRefreshInterval) return
      this.autoRefreshTimer = setInterval(() => {
        this.loadData()
      }, this.autoRefreshInterval * 1000)
    },

    openPriceEditorForDate(date) {
      this.priceEditorDate = date
      this.priceEditorModel = null
      this.priceEditorOpen = true
      this.$nextTick(() => {
        const el = this.$el.querySelector('.border-white\\/10')
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
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
          projectName: this.filters.projectName || undefined,
          grouping: this.grouping
        }

        const adminFilters = this.isAdminView
          ? { ...baseFilters, username: this.filters.username || undefined }
          : baseFilters

        const [total, daily, byModel] = await Promise.all([
          analytics.total(adminFilters),
          analytics.daily(adminFilters),
          analytics.byModel(adminFilters)
        ])

        this.totalStats = total || {
          input_tokens: 0,
          output_tokens: 0,
          total_tokens: 0,
          calls: 0,
          total_duration_seconds: 0,
          total_cxjcoins: null
        }
        this.dailyData = Array.isArray(daily) ? daily : []
        this.byModelData = byModel || {}

        if (this.isAdminView && this.$storex.users.isAdmin) {
          const [byUser, byProject] = await Promise.all([
            this.$project.$api.analytics.admin.byUser(adminFilters),
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

    formatTokens(num) {
      if (!num) return '0'
      if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M'
      if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K'
      return num.toString()
    },

    formatNumber(num) {
      if (!num) return '0'
      if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + 'M'
      if (num >= 1_000) return (num / 1_000).toFixed(1) + 'K'
      return num.toString()
    },

    formatCoins(coins) {
      if (!coins && coins !== 0) return '-'
      if (coins >= 1_000_000) return '🪙 ' + (coins / 1_000_000).toFixed(2) + 'M'
      if (coins >= 1_000) return '🪙 ' + (coins / 1_000).toFixed(2) + 'K'
      return '🪙 ' + Number(coins).toFixed(2)
    },

    getModelPercentage(tokens) {
      return ((tokens / this.maxModelTokens) * 100).toFixed(1)
    },
    getUserPercentage(tokens) {
      return ((tokens / this.maxUserTokens) * 100).toFixed(1)
    },
    getProjectPercentage(tokens) {
      return ((tokens / this.maxProjectTokens) * 100).toFixed(1)
    },
    getSpeedPercentage(tokensPerSecond) {
      if (!tokensPerSecond || tokensPerSecond <= 0) return 0
      return Math.round((tokensPerSecond / this.maxTokensPerSecond) * 100)
    },
    getTokensPerSecColor(tps) {
      if (!tps || tps <= 0) return 'text-white/50'
      const pct = tps / this.maxTokensPerSecond
      if (pct >= 0.7) return 'text-success'
      if (pct >= 0.35) return 'text-warning'
      return 'text-error'
    },
    getSpeedBarColor(tps) {
      if (!tps || tps <= 0) return 'bg-white/20'
      const pct = tps / this.maxTokensPerSecond
      if (pct >= 0.7) return 'bg-success'
      if (pct >= 0.35) return 'bg-warning'
      return 'bg-error'
    }
  },

  mounted() {
    this.loadData()
  },

  beforeUnmount() {
    if (this.autoRefreshTimer) {
      clearInterval(this.autoRefreshTimer)
    }
  }
}
</script>