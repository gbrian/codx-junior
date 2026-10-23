<script setup>
import { reactive, onMounted } from 'vue'
import { useSolopreneur } from './useSolopreneur'

const { state, t, goModule, saveAccount, toggleNotifications } = useSolopreneur()

const COUNTRIES = ['Spain', 'France', 'Germany', 'Portugal', 'Italy']
const form = reactive({ business: '', owner: '', email: '', country: 'Spain' })

function init() {
  form.business = state.user.business
  form.owner = state.user.owner
  form.email = state.user.email
  form.country = state.user.country
}

function submit() {
  saveAccount({ ...form })
}

onMounted(init)
</script>

<template>
  <div class="mx-auto w-full max-w-3xl flex flex-col gap-6">
    <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6 md:p-8">
      <h2 class="text-base font-semibold">{{ t('acc.title') }}</h2>
      <p class="text-sm text-base-content/50 mt-1.5">{{ t('acc.desc') }}</p>

      <form class="mt-6 flex flex-col gap-5" novalidate @submit.prevent="submit">
        <div class="flex flex-col gap-1.5">
          <label for="acc-business" class="text-xs font-semibold text-base-content/60">{{ t('acc.business') }}</label>
          <input
            id="acc-business"
            v-model="form.business"
            type="text"
            class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
            :aria-invalid="!!state.ui.errors.business"
          />
          <span v-if="state.ui.errors.business" class="text-xs text-error">{{ state.ui.errors.business }}</span>
        </div>

        <div class="flex flex-col gap-1.5">
          <label for="acc-owner" class="text-xs font-semibold text-base-content/60">{{ t('acc.owner') }}</label>
          <input
            id="acc-owner"
            v-model="form.owner"
            type="text"
            class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
            :aria-invalid="!!state.ui.errors.owner"
          />
          <span v-if="state.ui.errors.owner" class="text-xs text-error">{{ state.ui.errors.owner }}</span>
        </div>

        <div class="flex flex-col gap-1.5">
          <label for="acc-email" class="text-xs font-semibold text-base-content/60">{{ t('acc.email') }}</label>
          <input
            id="acc-email"
            v-model="form.email"
            type="email"
            class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
            :aria-invalid="!!state.ui.errors.email"
          />
          <span v-if="state.ui.errors.email" class="text-xs text-error">{{ state.ui.errors.email }}</span>
        </div>

        <div class="flex flex-col gap-1.5">
          <label for="acc-country" class="text-xs font-semibold text-base-content/60">{{ t('acc.country') }}</label>
          <select
            id="acc-country"
            v-model="form.country"
            class="h-11 rounded-xl border border-base-content/15 bg-base-100 px-4 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
          >
            <option v-for="c in COUNTRIES" :key="c" :value="c">{{ c }}</option>
          </select>
        </div>

        <div class="flex items-center justify-between gap-4 text-sm">
          <span class="text-base-content/50">{{ t('acc.plan') }}</span>
          <span class="font-semibold">{{ state.user.plan }}</span>
        </div>
        <div class="flex items-center justify-between gap-4 text-sm">
          <span class="text-base-content/50">{{ t('acc.signin') }}</span>
          <span class="font-semibold">{{ state.user.signIn }}</span>
        </div>

        <div class="flex flex-wrap gap-3 pt-1">
          <button
            type="submit"
            class="h-10 px-5 rounded-full bg-base-content text-base-100 text-sm font-semibold hover:opacity-90 transition"
          >{{ t('common.save') }}</button>
          <button
            type="button"
            class="h-10 px-5 rounded-full border border-base-content/20 bg-base-100 text-sm font-semibold hover:bg-base-200 transition"
            @click="goModule('summary')"
          >{{ t('common.cancel') }}</button>
        </div>
      </form>
    </section>

    <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6 md:p-8">
      <h2 class="text-base font-semibold">{{ t('acc.prefs') }}</h2>
      <div class="mt-5 flex items-center justify-between gap-4 text-sm">
        <span class="text-base-content/70">{{ t('acc.notify') }}</span>
        <button
          type="button"
          class="h-9 px-5 rounded-full border border-base-content/20 text-sm font-semibold hover:bg-base-200 transition"
          :aria-pressed="state.user.notifications"
          @click="toggleNotifications"
        >{{ state.user.notifications ? t('common.on') : t('common.off') }}</button>
      </div>
    </section>
  </div>
</template>