<script setup>
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4">
    <!-- Header banner -->
    <div class="flex items-center gap-3 bg-gradient-to-r from-success/20 to-transparent rounded-xl px-4 py-3">
      <div class="avatar placeholder">
        <div class="bg-success text-success-content rounded-full w-10 h-10 flex items-center justify-center">
          <i class="fa-solid fa-wallet text-lg"></i>
        </div>
      </div>
      <div>
        <div class="font-bold text-base">{{ wallet.name || 'Wallet' }}</div>
        <div class="text-xs text-base-content/50">{{ wallet.wallet_id }}</div>
      </div>
      <div class="ml-auto flex gap-2">
        <span :class="wallet.enabled ? 'badge badge-success' : 'badge badge-error'" class="text-xs">
          <i :class="wallet.enabled ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'" class="mr-1"></i>
          {{ wallet.enabled ? 'Active' : 'Disabled' }}
        </span>
      </div>
    </div>

    <!-- Balance card -->
    <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg">
      <div class="text-xs font-bold uppercase tracking-widest text-success flex items-center gap-1">
        <i class="fa-solid fa-coins"></i> Balance
      </div>
      <div class="flex items-end gap-2">
        <span class="text-4xl font-bold text-success">{{ wallet.balance_cxjcoins?.toFixed(4) ?? '0.0000' }}</span>
        <span class="text-base-content/50 mb-1 text-sm">cxj coins</span>
      </div>
      <div class="flex gap-3">
        <div class="form-control flex-1">
          <label class="label py-1">
            <span class="label-text text-xs">Wallet Name</span>
          </label>
          <input class="input input-bordered input-sm" v-model="wallet.name" placeholder="Wallet name" />
        </div>
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs">Balance (cxj)</span>
          </label>
          <input
            type="number"
            step="0.0001"
            class="input input-bordered input-sm w-36"
            v-model.number="wallet.balance_cxjcoins"
            placeholder="0.0000"
          />
        </div>
        <div class="form-control">
          <label class="label py-1">
            <span class="label-text text-xs">Enabled</span>
          </label>
          <input type="checkbox" class="toggle toggle-sm toggle-success mt-2" v-model="wallet.enabled" />
        </div>
      </div>
    </div>

    <!-- Spending Limits -->
    <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg">
      <div class="text-xs font-bold uppercase tracking-widest text-warning flex items-center gap-1 justify-between">
        <span><i class="fa-solid fa-gauge-high mr-1"></i> Spending Limits</span>
        <button class="btn btn-xs btn-warning btn-outline" @click="addSpendingLimit">
          <i class="fa-solid fa-plus"></i> Add
        </button>
      </div>
      <div v-if="!wallet.spending_limits?.length" class="text-xs text-base-content-ERROR-40 italic text-center py-2">
        No spending limits configured
      </div>
      <!-- SpendingLimit fields: period, limit_cxjcoins, current_spent, period_start -->
      <div
        v-for="(limit, index) in wallet.spending_limits"
        :key="index"
        class="flex items-center gap-2 bg-base-300 rounded-lg p-2"
      >
        <div class="form-control flex-1">
          <label class="label py-0">
            <span class="label-text text-xs">Period</span>
          </label>
          <select class="select select-bordered select-xs" v-model="limit.period">
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>
        <div class="form-control flex-1">
          <label class="label py-0">
            <!-- Backend field: limit_cxjcoins (max allowed per period) -->
            <span class="label-text text-xs">Max (cxj)</span>
          </label>
          <input
            type="number"
            class="input input-bordered input-xs"
            v-model.number="limit.limit_cxjcoins"
            step="0.01"
            placeholder="0.00"
          />
        </div>
        <div class="form-control flex-1">
          <label class="label py-0">
            <!-- Backend field: current_spent (read-only info) -->
            <span class="label-text text-xs">Spent</span>
          </label>
          <input
            type="number"
            class="input input-bordered input-xs opacity-60"
            :value="limit.current_spent?.toFixed(4) ?? '0.0000'"
            readonly
          />
        </div>
        <button class="btn btn-error btn-xs mt-4" @click="removeSpendingLimit(index)">
          <i class="fa-solid fa-trash-can"></i>
        </button>
      </div>
    </div>

    <!-- Transactions -->
    <div class="flex flex-col gap-3 p-3 bg-base-200 rounded-lg flex-1">
      <div class="text-xs font-bold uppercase tracking-widest text-info flex items-center gap-1">
        <i class="fa-solid fa-arrow-right-arrow-left mr-1"></i> Transactions
        <span class="badge badge-info badge-xs ml-1">{{ wallet.transactions?.length || 0 }}</span>
      </div>
      <div v-if="!wallet.transactions?.length" class="text-xs text-base-content-ERROR-40 italic text-center py-4">
        No transactions yet
      </div>
      <div v-else class="flex flex-col gap-1 max-h-48 overflow-y-auto">
        <!--
          WalletTransaction fields:
            transaction_id, timestamp, amount_cxjcoins, description, usage, balance_after
        -->
        <div
          v-for="tx in wallet.transactions"
          :key="tx.transaction_id"
          class="flex items-center justify-between bg-base-300 rounded-lg px-3 py-2 text-xs"
        >
          <div class="flex items-center gap-2">
            <i
              :class="tx.amount_cxjcoins >= 0 ? 'fa-solid fa-arrow-down text-success' : 'fa-solid fa-arrow-up text-error'"
            ></i>
            <span class="text-base-content/70">{{ tx.description || 'Transaction' }}</span>
          </div>
          <div class="flex items-center gap-3">
            <span :class="tx.amount_cxjcoins >= 0 ? 'text-success font-bold' : 'text-error font-bold'">
              {{ tx.amount_cxjcoins >= 0 ? '+' : '' }}{{ tx.amount_cxjcoins?.toFixed(4) }} cxj
            </span>
            <span class="text-base-content-ERROR-40 text-xs">bal: {{ tx.balance_after?.toFixed(4) }}</span>
            <!-- Backend field: timestamp (not created_at) -->
            <span class="text-base-content-ERROR-40">{{ formatDate(tx.timestamp) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['wallet'],
  methods: {
    addSpendingLimit() {
      if (!this.wallet.spending_limits) this.wallet.spending_limits = []
      // SpendingLimit fields: period, limit_cxjcoins, current_spent, period_start
      this.wallet.spending_limits.push({ period: 'monthly', limit_cxjcoins: 0, current_spent: 0 })
    },
    removeSpendingLimit(index) {
      this.wallet.spending_limits.splice(index, 1)
    },
    formatDate(dateStr) {
      if (!dateStr) return ''
      return new Date(dateStr).toLocaleDateString()
    }
  }
}
</script>