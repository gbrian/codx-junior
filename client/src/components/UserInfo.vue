<script setup>
import MetricRow from './MetricRow.vue'
</script>

<template>
  <div class="relative">
    <!-- Slot for custom trigger (default: compact status bar) -->
    <slot name="trigger" :toggle-panel="togglePanel" :daily-limit-status="dailyLimitStatus" :today-coins="todayCoins" :user="user" :wallet="wallet">
      <div
        class="flex items-center gap-1 cursor-pointer hover:bg-base-200 rounded px-1 py-0.5"
        @click="togglePanel"
      >
        <!-- Avatar with warning indicator -->
        <div class="avatar placeholder relative">
          <div
            class="w-6 h-6 rounded-full text-neutral-content overflow-hidden"
            :class="dailyLimitStatus === 'exceeded' ? 'bg-error ring-2 ring-error ring-offset-1' : dailyLimitStatus === 'warning' ? 'bg-warning ring-2 ring-warning ring-offset-1' : 'bg-neutral'"
          >
            <img v-if="user?.avatar" :src="user.avatar" :alt="user?.userName" class="w-full h-full object-cover" />
            <span v-else class="text-xs">{{ userInitial }}</span>
          </div>
          <!-- Warning badge on avatar -->
          <span
            v-if="dailyLimitStatus"
            class="absolute -top-1 -right-1 w-3 h-3 rounded-full flex items-center justify-center text-white z-10"
            :class="dailyLimitStatus === 'exceeded' ? 'bg-error' : 'bg-warning'"
            :title="dailyLimitStatus === 'exceeded' ? 'Daily limit exceeded!' : 'Approaching daily limit'"
          >
            <i class="fa-solid fa-exclamation text-[6px]"></i>
          </span>
        </div>

        <!-- Compact: today's coins + wallet balance -->
        <div
          v-if="todayCoins != null"
          class="text-xs font-mono hidden sm:flex items-center gap-0.5"
          :class="dailyLimitStatus === 'exceeded' ? 'text-error' : dailyLimitStatus === 'warning' ? 'text-warning' : 'text-warning'"
        >
          <i
            class="fa-solid fa-coins"
            :class="dailyLimitStatus === 'exceeded' ? 'text-error animate-bounce' : dailyLimitStatus === 'warning' ? 'text-warning' : 'text-yellow-500'"
          ></i>
          <span>{{ formatCoins(todayCoins) }}</span>
          <span class="opacity-60">cxj</span>
          <!-- Inline exceeded label -->
          <span v-if="dailyLimitStatus === 'exceeded'" class="text-error font-bold ml-1 animate-pulse">LIMIT!</span>
        </div>
        <div v-if="wallet" class="text-xs text-success font-mono hidden sm:flex items-center gap-0.5 ml-1">
          <i class="fa-solid fa-wallet text-success"></i>
          <span>{{ formatCoins(wallet.balance_cxjcoins) }}</span>
        </div>
      </div>
    </slot>

    <!-- Detailed panel overlay -->
    <div
      v-if="showPanel"
      class="absolute left-0 bottom-8 z-50 w-96 bg-base-200 border border-base-300 rounded-lg shadow-xl p-4 flex flex-col gap-3"
    >
      <!-- Header: user info -->
      <div class="flex items-center gap-3">
        <div class="avatar placeholder relative">
          <div class="w-12 h-12 rounded-full bg-neutral text-neutral-content overflow-hidden">
            <img v-if="user?.avatar" :src="user.avatar" :alt="user?.userName" class="w-full h-full object-cover" />
            <span v-else class="text-lg">{{ userInitial }}</span>
          </div>
        </div>
        <div>
          <div class="font-semibold text-base-content">{{ user?.userName }}</div>
          <div class="text-xs text-base-content opacity-60">{{ user?.role }}</div>
        </div>
        <button class="btn btn-xs btn-ghost ml-auto" @click="showPanel = false">✕</button>
      </div>

      <!-- Daily limit alert banner -->
      <div
        v-if="dailyLimitStatus"
        class="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold"
        :class="dailyLimitStatus === 'exceeded' ? 'bg-error/20 text-error border border-error/40' : 'bg-warning/20 text-warning border border-warning/40'"
      >
        <i
          class="fa-solid fa-triangle-exclamation text-base"
          :class="dailyLimitStatus === 'exceeded' ? 'animate-pulse' : ''"
        ></i>
        <span v-if="dailyLimitStatus === 'exceeded'">
          Daily spending limit reached! ({{ formatCoins(todayCoins) }} / {{ formatCoins(dailyLimit) }} cxj)
        </span>
        <span v-else>
          Approaching daily limit — {{ (dailySpendRatio * 100).toFixed(0) }}% used
          ({{ formatCoins(todayCoins) }} / {{ formatCoins(dailyLimit) }} cxj)
        </span>
      </div>

      <div class="divider my-0"></div>

      <!-- Wallet section -->
      <div v-if="wallet" class="flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <div class="text-xs font-bold text-base-content opacity-70 uppercase flex items-center gap-1">
            <i class="fa-solid fa-wallet text-success"></i> Wallet
            <span class="text-xs font-normal normal-case opacity-50 ml-1">{{ wallet.wallet_id }}</span>
          </div>
          <span :class="wallet.enabled ? 'badge badge-success' : 'badge badge-error'" class="badge-xs text-xs">
            {{ wallet.enabled ? 'Active' : 'Disabled' }}
          </span>
        </div>
        <!-- Balance highlight -->
        <div class="flex items-end gap-2 bg-base-100 rounded-lg px-3 py-2">
          <i class="fa-solid fa-coins text-success mb-0.5"></i>
          <span class="text-2xl font-bold text-success font-mono">{{ formatCoins(wallet.balance_cxjcoins) }}</span>
          <span class="text-xs text-base-content opacity-50 mb-1">cxj coins</span>
          <span class="ml-auto text-xs text-base-content opacity-60 font-semibold">{{ wallet.name }}</span>
        </div>
        <!-- Spending limits summary -->
        <div v-if="wallet.spending_limits?.length" class="flex flex-col gap-1">
          <div class="text-xs font-bold text-warning opacity-80 uppercase flex items-center gap-1">
            <i class="fa-solid fa-gauge-high"></i> Spending Limits
          </div>
          <div
            v-for="(limit, i) in wallet.spending_limits"
            :key="i"
            class="flex flex-col bg-base-100 rounded px-2 py-1.5 text-xs gap-1"
          >
            <!-- Period label + badge -->
            <div class="flex items-center justify-between">
              <span class="capitalize font-semibold opacity-80 flex items-center gap-1">
                {{ limit.period }}
                <!-- Warning icon next to daily period if limit hit -->
                <i
                  v-if="limit.period === 'daily' && dailyLimitStatus"
                  class="fa-solid fa-triangle-exclamation"
                  :class="dailyLimitStatus === 'exceeded' ? 'text-error animate-pulse' : 'text-warning'"
                ></i>
              </span>
              <span
                :class="spendRatio(limit) > 0.8 ? 'badge-error' : 'badge-warning'"
                class="badge badge-xs font-mono"
              >
                {{ formatCoins(getLimitSpent(limit)) }} / {{ formatCoins(limit.limit_cxjcoins) }} cxj
              </span>
            </div>
            <!-- Progress bar -->
            <div class="w-full h-1.5 bg-base-300 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all"
                :class="spendRatio(limit) > 0.8 ? 'bg-error' : 'bg-warning'"
                :style="{ width: Math.min(spendRatio(limit) * 100, 100) + '%' }"
              ></div>
            </div>
            <!-- Breakdown: today vs month -->
            <div class="flex items-center gap-3 opacity-60 mt-0.5">
              <span v-if="limit.period === 'daily'" class="flex items-center gap-1">
                <i class="fa-solid fa-sun text-yellow-400"></i>
                Today: <span class="font-mono text-warning ml-1">{{ formatCoins(todayCoins) }}</span>
              </span>
              <span v-if="limit.period === 'monthly'" class="flex items-center gap-1">
                <i class="fa-solid fa-calendar text-blue-400"></i>
                Month: <span class="font-mono text-info ml-1">{{ formatCoins(monthCoins) }}</span>
              </span>
              <span class="ml-auto">
                {{ (spendRatio(limit) * 100).toFixed(0) }}% used
              </span>
            </div>
          </div>
        </div>
        <!-- Recent transactions (last 3) -->
        <div v-if="recentTransactions.length" class="flex flex-col gap-1">
          <div class="text-xs font-bold text-info opacity-80 uppercase flex items-center gap-1">
            <i class="fa-solid fa-arrow-right-arrow-left"></i> Recent Transactions
          </div>
          <div
            v-for="tx in recentTransactions"
            :key="tx.transaction_id"
            class="flex items-center justify-between bg-base-100 rounded px-2 py-1 text-xs"
          >
            <span class="opacity-60 truncate max-w-32">{{ tx.description || 'Transaction' }}</span>
            <div class="flex items-center gap-2">
              <span :class="tx.amount_cxjcoins >= 0 ? 'text-success font-bold' : 'text-error font-bold'" class="font-mono">
                {{ tx.amount_cxjcoins >= 0 ? '+' : '' }}{{ formatCoins(tx.amount_cxjcoins) }}
              </span>
              <span class="opacity-40">{{ formatDate(tx.timestamp) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="divider my-0"></div>

      <!-- Loading state -->
      <div v-if="loading" class="flex justify-center py-2">
        <span class="loading loading-spinner loading-sm"></span>
      </div>

      <template v-else-if="metrics">
        <!-- Today metrics -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <div class="text-xs font-bold text-base-content opacity-70 uppercase">Today</div>
            <div class="flex items-center gap-1 text-sm font-bold text-yellow-500 font-mono">
              <i class="fa-solid fa-coins text-yellow-500 mr-1"></i>
              {{ formatCoins(metrics.today.total_cxjcoins) }}
              <span class="text-xs font-normal opacity-60">cxj</span>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-1 text-xs">
            <MetricRow label="Calls" :value="metrics.today.calls" />
            <MetricRow label="Tokens" :value="formatTokens(metrics.today.total_tokens)" />
            <MetricRow label="Input" :value="formatTokens(metrics.today.input_tokens)" />
            <MetricRow label="Output" :value="formatTokens(metrics.today.output_tokens)" />
            <MetricRow label="Duration" :value="formatDuration(metrics.today.total_duration_seconds)" />
          </div>
        </div>

        <div class="divider my-0"></div>

        <!-- Current month metrics -->
        <div>
          <div class="flex items-center justify-between mb-1">
            <div class="text-xs font-bold text-base-content opacity-70 uppercase">
              This Month
              <span class="font-normal normal-case opacity-60 ml-1">
                {{ metrics.current_month.start_date }} → {{ metrics.current_month.end_date }}
              </span>
            </div>
            <div class="flex items-center gap-1 text-sm font-bold text-yellow-500 font-mono">
              <i class="fa-solid fa-coins text-yellow-500 mr-1"></i>
              {{ formatCoins(metrics.current_month.total_cxjcoins) }}
              <span class="text-xs font-normal opacity-60">cxj</span>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-1 text-xs">
            <MetricRow label="Calls" :value="metrics.current_month.calls" />
            <MetricRow label="Tokens" :value="formatTokens(metrics.current_month.total_tokens)" />
            <MetricRow label="Input" :value="formatTokens(metrics.current_month.input_tokens)" />
            <MetricRow label="Output" :value="formatTokens(metrics.current_month.output_tokens)" />
            <MetricRow label="Duration" :value="formatDuration(metrics.current_month.total_duration_seconds)" />
          </div>
        </div>
      </template>

      <div v-else class="text-xs text-base-content opacity-50 text-center py-2">No metrics available</div>

      <!-- Logout -->
      <div class="divider my-0"></div>
      <button class="btn btn-xs btn-outline btn-error w-full" @click="logout">Logout</button>
    </div>

    <!-- Backdrop to close panel -->
    <div v-if="showPanel" class="fixed inset-0 z-40" @click="showPanel = false"></div>
  </div>
</template>

<script>
import MetricRow from './MetricRow.vue'

export default {
  components: { MetricRow },
  data() {
    return {
      showPanel: false,
      loading: false,
      intervalId: null
    }
  },
  computed: {
    user() {
      return this.$storex.users.user
    },
    metrics() {
      return this.$storex.users.metrics
    },
    wallet() {
      return this.user?.wallet ?? null
    },
    recentTransactions() {
      const txs = this.wallet?.transactions
      if (!txs?.length) return []
      return [...txs]
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
        .slice(0, 3)
    },
    todayCoins() {
      return this.metrics?.today?.total_cxjcoins ?? null
    },
    monthCoins() {
      return this.metrics?.current_month?.total_cxjcoins ?? null
    },
    userInitial() {
      return (this.user?.userName || '?')[0].toUpperCase()
    },
    dailyLimitConfig() {
      return this.wallet?.spending_limits?.find(l => l.period === 'daily') ?? null
    },
    dailyLimit() {
      return this.dailyLimitConfig?.limit_cxjcoins ?? null
    },
    dailySpendRatio() {
      if (!this.dailyLimit || this.todayCoins == null) return 0
      return this.todayCoins / this.dailyLimit
    },
    dailyLimitStatus() {
      if (!this.dailyLimit || this.todayCoins == null) return null
      if (this.dailySpendRatio >= 1) return 'exceeded'
      if (this.dailySpendRatio >= 0.8) return 'warning'
      return null
    }
  },
  mounted() {
    this.fetchMetrics()
    this.intervalId = setInterval(() => this.fetchMetrics(), 30000)
  },
  unmounted() {
    clearInterval(this.intervalId)
  },
  methods: {
    async togglePanel() {
      this.showPanel = !this.showPanel
      if (this.showPanel) {
        await this.fetchMetrics()
      }
    },
    async fetchMetrics() {
      this.loading = true
      try {
        await this.$storex.users.loadMetrics()
      } catch(ex) {
        console.error("Error calling get user metrics", ex)
      } finally {
        this.loading = false
      }
    },
    getLimitSpent(limit) {
      if (limit.period === 'daily' && this.todayCoins != null) return this.todayCoins
      if (limit.period === 'monthly' && this.monthCoins != null) return this.monthCoins
      return limit.current_spent || 0
    },
    spendRatio(limit) {
      if (!limit.limit_cxjcoins) return 0
      return this.getLimitSpent(limit) / limit.limit_cxjcoins
    },
    formatCoins(val) {
      return val != null ? Number(val).toFixed(2) : '-'
    },
    formatTokens(val) {
      if (val == null) return '-'
      if (val >= 1_000_000) return (val / 1_000_000).toFixed(1) + 'M'
      if (val >= 1_000) return (val / 1_000).toFixed(1) + 'K'
      return val
    },
    formatDuration(seconds) {
      if (seconds == null) return '-'
      const h = Math.floor(seconds / 3600)
      const m = Math.floor((seconds % 3600) / 60)
      const s = Math.floor(seconds % 60)
      if (h > 0) return `${h}h ${m}m`
      if (m > 0) return `${m}m ${s}s`
      return `${s}s`
    },
    formatDate(dateStr) {
      if (!dateStr) return ''
      return new Date(dateStr).toLocaleDateString()
    },
    async logout() {
      this.showPanel = false
      await this.$storex.users.logout()
    }
  }
}
</script>