<script setup>
import { API } from '@/api/api'
</script>

<template>
  <div class="w-full flex flex-col gap-6 p-4">
    <h2 class="text-lg font-bold">Price Management</h2>

    <div v-if="loading" class="flex items-center gap-2 text-base-content/60">
      <span class="loading loading-spinner loading-sm"></span>
      Loading pricing data...
    </div>

    <div v-for="provider in providers" :key="provider.name" class="card bg-base-200 shadow">
      <div class="card-body gap-4">

        <!-- Provider row -->
        <div class="flex flex-wrap items-center gap-4">
          <span class="font-bold text-base flex-1">{{ provider.name }}</span>
          <label class="flex items-center gap-2 text-sm">
            Input /1K
            <input
              type="number"
              step="0.01"
              class="input input-sm input-bordered w-24"
              v-model.number="provider.input_k_tokens_cxjcoins"
            />
          </label>
          <label class="flex items-center gap-2 text-sm">
            Output /1K
            <input
              type="number"
              step="0.01"
              class="input input-sm input-bordered w-24"
              v-model.number="provider.output_k_tokens_cxjcoins"
            />
          </label>
          <button
            class="btn btn-sm btn-primary"
            :disabled="savingProvider === provider.name"
            @click="saveProvider(provider)"
          >
            <span v-if="savingProvider === provider.name" class="loading loading-spinner loading-xs"></span>
            Save Provider
          </button>
        </div>

        <div class="divider my-0"></div>

        <!-- Model rows -->
        <div
          v-for="model in provider.models"
          :key="model.name"
          class="flex flex-wrap items-center gap-4 pl-4"
        >
          <span class="flex-1 text-sm font-medium">{{ model.name }}</span>
          <label class="flex items-center gap-2 text-sm">
            Input /1K
            <input
              type="number"
              step="0.01"
              class="input input-sm input-bordered w-24"
              v-model.number="model.input_k_tokens_cxjcoins"
            />
          </label>
          <label class="flex items-center gap-2 text-sm">
            Output /1K
            <input
              type="number"
              step="0.01"
              class="input input-sm input-bordered w-24"
              v-model.number="model.output_k_tokens_cxjcoins"
            />
          </label>
          <button
            class="btn btn-sm btn-secondary"
            :disabled="savingModel === `${provider.name}/${model.name}`"
            @click="saveModel(provider, model)"
          >
            <span
              v-if="savingModel === `${provider.name}/${model.name}`"
              class="loading loading-spinner loading-xs"
            ></span>
            Save
          </button>
          <!-- Recalculate using the date range passed from the dashboard -->
          <button
            class="btn btn-sm btn-warning"
            :disabled="recalcRunning === `${provider.name}/${model.name}`"
            :title="recalcDateLabel"
            @click="runRecalculate(provider, model)"
          >
            <span
              v-if="recalcRunning === `${provider.name}/${model.name}`"
              class="loading loading-spinner loading-xs"
            ></span>
            <i v-else class="fa-solid fa-rotate text-xs"></i>
            Recalculate
            <span v-if="recalcDateLabel" class="badge badge-xs badge-ghost ml-1">{{ recalcDateLabel }}</span>
          </button>
        </div>

      </div>
    </div>

    <!-- Toast -->
    <div v-if="toast" class="toast toast-end">
      <div :class="['alert', toast.type === 'error' ? 'alert-error' : 'alert-success']">
        <span>{{ toast.message }}</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    initialStartDate: { type: String, default: null },
    initialEndDate:   { type: String, default: null },
  },
  emits: ['metrics-changed'],
  data() {
    return {
      providers: [],
      loading: false,
      savingProvider: null,
      savingModel: null,
      recalcRunning: null,
      toast: null,
    }
  },
  computed: {
    recalcDateLabel() {
      if (!this.initialStartDate) return null
      if (this.initialStartDate === this.initialEndDate) return this.initialStartDate
      return `${this.initialStartDate} → ${this.initialEndDate}`
    },
  },
  async mounted() {
    await this.loadPricing()
  },
  methods: {
    async loadPricing() {
      this.loading = true
      try {
        this.providers = await API.analytics.admin.pricing.list()
      } catch (e) {
        this.showToast('Failed to load pricing data', 'error')
      } finally {
        this.loading = false
      }
    },

    async saveProvider(provider) {
      this.savingProvider = provider.name
      try {
        await API.analytics.admin.pricing.updateProvider(provider.name, {
          input_k_tokens_cxjcoins: provider.input_k_tokens_cxjcoins,
          output_k_tokens_cxjcoins: provider.output_k_tokens_cxjcoins,
        })
        this.showToast(`Provider "${provider.name}" pricing saved`)
        // Notify dashboard to reload metrics after price update
        this.$emit('metrics-changed')
      } catch (e) {
        this.showToast('Failed to save provider pricing', 'error')
      } finally {
        this.savingProvider = null
      }
    },

    async saveModel(provider, model) {
      this.savingModel = `${provider.name}/${model.name}`
      try {
        await API.analytics.admin.pricing.updateModel(provider.name, model.name, {
          input_k_tokens_cxjcoins: model.input_k_tokens_cxjcoins,
          output_k_tokens_cxjcoins: model.output_k_tokens_cxjcoins,
        })
        this.showToast(`Model "${model.name}" pricing saved`)
        // Notify dashboard to reload metrics after price update
        this.$emit('metrics-changed')
      } catch (e) {
        this.showToast('Failed to save model pricing', 'error')
      } finally {
        this.savingModel = null
      }
    },

    async runRecalculate(provider, model) {
      const key = `${provider.name}/${model.name}`
      this.recalcRunning = key
      try {
        await API.analytics.admin.pricing.recalculate({
          provider: provider.name,
          model: model.name,
          startDate: this.initialStartDate,
          endDate: this.initialEndDate,
          inputPrice: model.input_k_tokens_cxjcoins,
          outputPrice: model.output_k_tokens_cxjcoins,
        })
        this.showToast(`Recalculated "${model.name}" for ${this.recalcDateLabel}`)
        // Notify dashboard to reload metrics after recalculation
        this.$emit('metrics-changed')
      } catch (e) {
        this.showToast('Recalculation failed', 'error')
      } finally {
        this.recalcRunning = null
      }
    },

    showToast(message, type = 'success') {
      this.toast = { message, type }
      setTimeout(() => { this.toast = null }, 3000)
    },
  },
}
</script>