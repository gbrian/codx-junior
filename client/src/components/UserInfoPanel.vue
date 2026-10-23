<script setup>
import MetricRow from './MetricRow.vue'
</script>

<template>
  <div class="flex flex-col gap-3">
    <!-- Header: user info + close -->
    <div class="flex items-center gap-3">
      <div class="avatar placeholder relative">
        <div class="w-10 rounded-full bg-neutral text-neutral-content overflow-hidden">
          <img v-if="user?.avatar" :src="user.avatar" :alt="user?.userName" class="w-full h-full object-cover" />
          <span v-else class="text-base">{{ userInitial }}</span>
        </div>
      </div>
      <div class="min-w-0 flex-1">
        <div class="font-semibold truncate">{{ user?.userName }}</div>
        <div class="text-xs opacity-60 truncate">{{ user?.role }}</div>
      </div>
      <button class="btn btn-ghost btn-xs shrink-0" @click="$emit('close')" title="Close">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>

    <!-- Connection status -->
    <div class="flex items-center gap-2 text-xs">
      <span
        class="inline-block w-2 h-2 rounded-full"
        :class="$storex.session.connected ? 'bg-success' : 'bg-error'"
      ></span>
      <span :class="$storex.session.connected ? 'text-success/80' : 'text-error'">
        {{ $storex.session.connected ? 'API connected' : 'API offline' }}
      </span>
    </div>

    <!-- Daily limit alert banner -->
    <div
      v-if="dailyLimitStatus"
      class="flex items-center gap-2 rounded-lg px-2.5 py-2 text-[11px] font-semibold"
      :class="dailyLimitStatus === 'exceeded' ? 'bg-error/20 text-error border border-error/40' : 'bg-warning/20 text-warning border border-warning/40'"
    >
      <i
        class="fa-solid fa-triangle-exclamation"
        :class="dailyLimitStatus === 'exceeded' ? 'animate-pulse' : ''"
      ></i>
      <span v-if="dailyLimitStatus === 'exceeded'">
        Daily limit reached! ({{ formatCoins(todayCoins) }}/{{ formatCoins(dailyLimit) }} cxj)
      </span>
      <span v-else>
        Approaching daily limit — {{ (dailySpendRatio * 100).toFixed(0) }}% used
      </span>
    </div>

    <!-- Wallet card -->
    <div v-if="wallet" class="rounded-xl bg-base-100/60 p-3 flex flex-col gap-2">
      <div class="flex items-center justify-between text-xs opacity-70">
        <span><i class="fa-solid fa-wallet text-success mr-1"></i>Wallet</span>
        <span
          :class="wallet.enabled ? 'text-success' : 'text-error'"
          class="text-[10px] font-semibold uppercase"
        >
          {{ wallet.enabled ? 'Active' : 'Disabled' }}
        </span>
      </div>
      <div class="text-xl font-bold text-success font-mono leading-none">
        {{ formatCoins(wallet.balance_cxjcoins) }}
        <span class="text-xs font-normal opacity-60">cxj</span>
      </div>
      <template v-if="dailyLimit">
        <div class="flex justify-between text-[11px] opacity-60">
          <span>Daily limit</span>
          <span>{{ (dailySpendRatio * 100).toFixed(0) }}%</span>
        </div>
        <div class="w-full h-1.5 bg-base-300 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all"
            :class="dailySpendRatio >= 1 ? 'bg-error' : dailySpendRatio >= 0.8 ? 'bg-warning' : 'bg-success'"
            :style="{ width: Math.min(dailySpendRatio * 100, 100) + '%' }"
          ></div>
        </div>
      </template>
    </div>

    <!-- Spending limits -->
    <div v-if="wallet?.spending_limits?.length" class="flex flex-col gap-1.5">
      <div class="flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide opacity-50">
        <i class="fa-solid fa-gauge-high"></i> Spending Limits
      </div>
      <div
        v-for="(limit, i) in wallet.spending_limits"
        :key="i"
        class="flex flex-col bg-base-100/60 rounded-lg px-2.5 py-2 text-xs gap-1.5"
      >
        <div class="flex items-center justify-between">
          <span class="capitalize font-semibold opacity-80 flex items-center gap-1">
            {{ limit.period }}
            <i
              v-if="limit.period === 'daily' && dailyLimitStatus"
              class="fa-solid fa-triangle-exclamation"
              :class="dailyLimitStatus === 'exceeded' ? 'text-error animate-pulse' : 'text-warning'"
            ></i>
          </span>
          <span
            :class="spendRatio(limit) > 0.8 ? 'text-error' : 'text-warning'"
            class="font-mono"
          >
            {{ formatCoins(getLimitSpent(limit)) }} / {{ formatCoins(limit.limit_cxjcoins) }}
          </span>
        </div>
        <div class="w-full h-1.5 bg-base-300 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all"
            :class="spendRatio(limit) > 0.8 ? 'bg-error' : 'bg-warning'"
            :style="{ width: Math.min(spendRatio(limit) * 100, 100) + '%' }"
          ></div>
        </div>
        <div class="flex items-center gap-3 opacity-60">
          <span v-if="limit.period === 'daily'" class="flex items-center gap-1">
            <i class="fa-solid fa-sun text-warning"></i>
            Today: <span class="font-mono text-warning">{{ formatCoins(todayCoins) }}</span>
          </span>
          <span v-if="limit.period === 'monthly'" class="flex items-center gap-1">
            <i class="fa-solid fa-calendar text-info"></i>
            Month: <span class="font-mono text-info">{{ formatCoins(monthCoins) }}</span>
          </span>
          <span class="ml-auto">{{ (spendRatio(limit) * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>

    <!-- Recent transactions (last 3) -->
    <div v-if="recentTransactions.length" class="flex flex-col gap-1.5">
      <div class="flex items-center gap-1 text-[11px] font-bold uppercase tracking-wide opacity-50">
        <i class="fa-solid fa-arrow-right-arrow-left"></i> Recent Transactions
      </div>
      <div
        v-for="tx in recentTransactions"
        :key="tx.transaction_id"
        class="flex items-center justify-between bg-base-100/60 rounded-lg px-2.5 py-1.5 text-xs"
      >
        <span class="opacity-60 truncate max-w-24">{{ tx.description || 'Transaction' }}</span>
        <div class="flex items-center gap-2">
          <span
            :class="tx.amount_cxjcoins >= 0 ? 'text-success' : 'text-error'"
            class="font-mono font-bold"
          >
            {{ tx.amount_cxjcoins >= 0 ? '+' : '' }}{{ formatCoins(tx.amount_cxjcoins) }}
          </span>
          <span class="opacity-40">{{ formatDate(tx.timestamp) }}</span>
        </div>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex justify-center py-2">
      <span class="loading loading-spinner loading-sm"></span>
    </div>

    <template v-else-if="metrics">
      <!-- Today metrics -->
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold uppercase tracking-wide opacity-50">Today</span>
          <span class="flex items-center gap-1 text-xs font-bold text-warning font-mono">
            <i class="fa-solid fa-coins"></i>{{ formatCoins(metrics.today.total_cxjcoins) }}
          </span>
        </div>
        <div class="grid grid-cols-2 gap-1 text-xs">
          <MetricRow label="Calls" :value="metrics.today.calls" />
          <MetricRow label="Tokens" :value="formatTokens(metrics.today.total_tokens)" />
          <MetricRow label="Input" :value="formatTokens(metrics.today.input_tokens)" />
          <MetricRow label="Output" :value="formatTokens(metrics.today.output_tokens)" />
          <MetricRow label="Duration" :value="formatDuration(metrics.today.total_duration_seconds)" />
        </div>
      </div>

      <!-- Current month metrics -->
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold uppercase tracking-wide opacity-50">
            This Month
            <span class="font-normal normal-case opacity-60 ml-1">
              {{ metrics.current_month.start_date }} → {{ metrics.current_month.end_date }}
            </span>
          </span>
          <span class="flex items-center gap-1 text-xs font-bold text-warning font-mono">
            <i class="fa-solid fa-coins"></i>{{ formatCoins(metrics.current_month.total_cxjcoins) }}
          </span>
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

    <div v-else class="text-xs opacity-50 text-center py-2">No metrics available</div>

    <!-- Actions (pinned to the bottom) -->
    <div class="mt-auto flex flex-col gap-2 pt-1">
      <button
        class="btn btn-xs btn-outline w-full justify-start gap-2"
        @click="openAccountSettings"
      >
        <i class="fa-solid fa-user-gear"></i>
        Account settings
      </button>
      <button
        class="btn btn-xs btn-outline btn-error w-full justify-start gap-2"
        @click="logout"
      >
        <i class="fa-solid fa-right-from-bracket"></i>
        Logout
      </button>
    </div>
  </div>
</template>

<script>
import MetricRow from './MetricRow.vue'

export default {
  components: { MetricRow },
  emits: ['close'],
  data() {
    return {
      loading: false
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
  },
  methods: {
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
    openAccountSettings() {
      this.$emit('close')
      this.$ui.setActiveTab('account')
    },
    async logout() {
      this.$emit('close')
      await this.$storex.users.logout()
    }
  }
}
</script>