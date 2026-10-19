<script setup>
import { useSolopreneur } from './useSolopreneur'

const { state, t, money, shortDate, openModal, PLANS, CREDIT_PACKS } = useSolopreneur()
</script>

<template>
  <div class="mx-auto w-full max-w-4xl flex flex-col gap-6">
    <!-- Wallet card -->
    <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6 md:p-8">
      <h2 class="text-base font-semibold">{{ t('wal.title') }}</h2>
      <p class="text-sm text-base-content/50 mt-1.5">{{ t('wal.desc') }}</p>

      <div class="flex items-baseline gap-2.5 mt-4">
        <strong class="text-4xl font-semibold tracking-tight leading-none">{{ state.wallet.credits }}</strong>
        <span class="text-sm font-medium">{{ t('wal.credits') }}</span>
      </div>

      <dl class="mt-5 flex flex-col gap-4">
        <div class="flex items-center justify-between gap-4 text-sm">
          <dt class="text-base-content/50">{{ t('wal.plan') }}</dt>
          <dd class="font-semibold">{{ state.wallet.plan }}</dd>
        </div>
        <div class="flex items-center justify-between gap-4 text-sm">
          <dt class="text-base-content/50">{{ t('wal.billing') }}</dt>
          <dd class="font-semibold">{{ state.wallet.billing }}</dd>
        </div>
        <div class="flex items-center justify-between gap-4 text-sm">
          <dt class="text-base-content/50">{{ t('wal.invoice') }}</dt>
          <dd class="font-semibold text-right">{{ money(state.wallet.invoice) }} · {{ t('wal.due') }} {{ shortDate(state.wallet.due) }}</dd>
        </div>
      </dl>

      <p class="text-[11px] text-base-content/40 mt-4">{{ t('wal.vat') }}</p>

      <div class="flex flex-wrap gap-3 mt-5">
        <button type="button" class="h-10 px-5 rounded-full border border-base-content/20 bg-base-100 text-sm font-semibold hover:bg-base-200 transition" @click="openModal('credits')">
          {{ t('wal.add') }}
        </button>
        <button type="button" class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition" @click="openModal('plan')">
          {{ t('wal.change') }}
        </button>
      </div>
    </section>

    <!-- Plans -->
    <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6 md:p-8">
      <h2 class="text-base font-semibold">{{ t('wal.plans') }}</h2>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-5">
        <div v-for="p in PLANS" :key="p.id" class="border border-base-content/10 rounded-xl p-5">
          <h3 class="text-base font-semibold">{{ p.name }}</h3>
          <p class="text-sm text-base-content/50 mt-1">{{ p.note }}</p>
          <p class="text-lg font-semibold mt-3">{{ money(p.price) }}</p>
          <button
            type="button"
            class="mt-3 h-9 px-4 rounded-full text-sm font-semibold transition"
            :class="state.wallet.plan === p.name
              ? 'border border-base-content/20 bg-base-100 text-base-content/50 cursor-default'
              : 'bg-base-content text-base-100 hover:opacity-90'"
            :disabled="state.wallet.plan === p.name"
            @click="openModal('plan')"
          >{{ state.wallet.plan === p.name ? t('wal.current') : t('wal.choose') }}</button>
        </div>
      </div>
    </section>

    <!-- Invoices -->
    <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6 md:p-8">
      <h2 class="text-base font-semibold">{{ t('wal.invoices') }}</h2>
      <div v-if="state.invoices.length" class="mt-4 overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-[11px] uppercase tracking-wide text-base-content/40">
              <th class="pb-2 font-semibold">Date</th>
              <th class="pb-2 font-semibold">Description</th>
              <th class="pb-2 font-semibold">Amount</th>
              <th class="pb-2 font-semibold text-right">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="inv in state.invoices" :key="inv.id" class="border-t border-base-content/10">
              <td class="py-3">{{ shortDate(inv.date) }}</td>
              <td class="py-3">{{ inv.desc }}</td>
              <td class="py-3">{{ money(inv.amount) }}</td>
              <td class="py-3 text-right">{{ inv.status }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="mt-4 py-10 text-center text-sm text-base-content/50 bg-base-200 rounded-xl">—</div>

      <div class="mt-5 flex flex-wrap gap-3">
        <button
          v-for="pack in CREDIT_PACKS"
          :key="pack.id"
          type="button"
          class="h-9 px-4 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition"
          @click="openModal('credits')"
        >+{{ pack.credits }} · {{ money(pack.price) }}</button>
      </div>
    </section>
  </div>
</template>