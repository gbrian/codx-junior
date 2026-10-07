<script setup>
import Selector from './Selector.vue'
</script>

<template>
  <Selector
    :items="formattedModels"
    :selected-items="selectedModelItem"
    label="Model"
    icon="fa-solid fa-brain"
    :single="true"
    :allow-deselect="true"
    :enable-tag-filter="true"
    :empty-label="'default'"
    @select="onModelSelected"
    @open="loadModels"
  >
    <!-- Custom model card rendering (V1 — Grid Card) -->
    <template #default="{ item, selected }">
      <div
        class="group relative flex flex-col gap-2 p-3 rounded-xl border text-left cursor-pointer transition-all duration-150 w-full min-w-0"
        :class="selected
          ? 'border-transparent bg-primary/10'
          : 'border-base-content/10 bg-base-200/40 hover:bg-base-200 hover:border-base-content/25'"
        :title="item.price ? item.price.tooltip : (item.description || 'No pricing available')"
      >
        <!-- Header: icon · name / provider · selection check -->
        <div class="flex items-center gap-2 min-w-0">
          <span
            class="w-8 h-8 rounded-lg grid place-items-center shrink-0"
            :class="selected ? 'bg-primary text-primary-content' : 'bg-base-300 text-base-content/70'"
          >
            <i class="fa-solid fa-brain text-xs" aria-hidden="true"></i>
          </span>
          <span class="flex flex-col min-w-0 flex-1">
            <span class="text-sm font-semibold truncate leading-tight">{{ item.name }}</span>
            <span class="text-[11px] text-base-content/45 truncate leading-tight">{{ item.description }}</span>
          </span>
          <i
            v-if="selected"
            class="fa-solid fa-circle-check text-success text-sm shrink-0"
            aria-hidden="true"
          ></i>
        </div>

        <!-- Price row: 5-coin cost rating + approximate per-request cost -->
        <div class="flex items-center justify-between gap-2 pt-2 border-t border-base-content/5">
          <span
            class="inline-flex items-center gap-0.5 pointer-events-none select-none"
            role="img"
            :aria-label="item.price ? item.price.ariaLabel : 'No pricing data'"
          >
            <i
              v-for="n in 5"
              :key="n"
              class="fa-solid fa-coins text-[11px]"
              :class="coinClass(item.price, n)"
              aria-hidden="true"
            ></i>
          </span>
          <span
            v-if="item.price"
            class="text-[11px] font-mono text-base-content/60 truncate"
          >
            ~{{ item.price.estimateLabel }}
          </span>
          <span v-else class="text-[11px] text-base-content/30">no price</span>
        </div>

        <!-- Tags row: task capabilities (image, vision, coding, design, ...) -->
        <div
          v-if="item.tags && item.tags.length"
          class="flex flex-wrap gap-1"
          aria-label="Model tags"
        >
          <span
            v-for="tag in item.tags"
            :key="tag"
            class="badge badge-xs badge-ghost gap-1 text-[10px] text-base-content/70"
          >
            <i class="fa-solid fa-tag text-[8px]" aria-hidden="true"></i>
            {{ tag }}
          </span>
        </div>
      </div>
    </template>
  </Selector>
</template>

<script>
// Rough token budget for one "standard request", used to approximate per-request cost.
// (Prices are stored per 1K tokens, so 1000 tokens ≈ ×1.)
const STANDARD_REQUEST = { input: 1000, output: 1000 }

// Filled-coin count per tier (1 = cheapest, 5 = most expensive)
const TIER_LEVEL = {
  'very cheap': 1,
  'cheap': 2,
  'moderate': 3,
  'expensive': 4,
  'very expensive': 5,
  unknown: 0
}

export default {
  props: {
    selectedModel: String,
    models: { type: Array, default: () => [] }
  },
  emits: ['model-changed'],
  data() {
    return {
      loadedModels: [],
      providers: []
    }
  },
  async created() {
    await this.loadModels()
  },
  computed: {
    // Logarithmic cost range across the loaded models — log scale keeps budget
    // models genuinely "cheap" even when a premium outlier is present.
    costRange() {
      const costs = (this.loadedModels || [])
        .map(model => this.getPriceInfo(model))
        .filter(price => price && price.cost != null && price.cost > 0)
        .map(price => price.cost)
      if (!costs.length) return { minLog: null, maxLog: null }
      const logs = costs.map(c => Math.log10(c))
      return { minLog: Math.min(...logs), maxLog: Math.max(...logs) }
    },
    formattedModels() {
      const range = this.costRange
      return (this.loadedModels || []).map(model => {
        const price = this.getPriceInfo(model)
        if (price) {
          price.tier = this.getPriceTier(price.cost, range)
          price.level = TIER_LEVEL[price.tier] ?? 0
          price.estimateLabel = this.formatCost(price.cost, price.currency)
          price.ariaLabel = `${price.tier} cost, about ${price.estimateLabel} per request`
          price.tooltip = this.buildPriceTooltip(model, price)
        }
        return {
          name: model.name,
          description: model.ai_model || model.description,
          avatar: null,
          tags: model.tags || [],
          price
        }
      })
    },
    selectedModelItem() {
      if (!this.selectedModel) return []
      const model = this.formattedModels.find(m => m.name === this.selectedModel)
      return model ? [model] : []
    }
  },
  methods: {
    // Selector emits the selected item (single mode) or null when cleared
    onModelSelected(selection) {
      const item = Array.isArray(selection) ? selection[0] : selection
      this.$emit('model-changed', item ? item.name : null)
    },

    async loadModels() {
      const [models, providers] = await Promise.all([
        this.$storex.api.projects.ai.models.list(),
        this.$storex.api.settings.global.section('ai_providers').catch(() => [])
      ])
      this.loadedModels = models || []
      this.providers = providers || []
    },

    // Resolve pricing (priority: model cxj → provider price list $)
    getPriceInfo(model) {
      if (!model) return null
      const input = model.input_k_tokens_cxjcoins
      const output = model.output_k_tokens_cxjcoins
      const perK = model.k_tokens_cxjcoins

      let price = null
      // 1) Model-level input/output pricing (cxj)
      if (input != null || output != null) {
        price = { input, output, currency: 'cxj' }
      // 2) Model-level single price per 1K tokens (cxj)
      } else if (perK != null) {
        price = { input: perK, output: perK, currency: 'cxj' }
      } else {
        // 3) Provider price list fallback ($ per 1K tokens)
        const entry = this.getProviderPrice(model)
        if (entry) {
          price = {
            input: entry.input_price_per_1k_tokens,
            output: entry.output_price_per_1k_tokens,
            currency: '$'
          }
        }
      }
      if (!price) return null

      price.cost = this.estimateCost(price)
      return price.cost == null ? null : price
    },

    getProviderPrice(model) {
      if (!model?.ai_provider || !this.providers?.length) return null
      const provider = this.providers.find(p => p.name === model.ai_provider)
      if (!provider?.price_list?.length) return null
      const lookupName = model.ai_model || model.name
      return provider.price_list.find(entry => entry.model_name === lookupName) || null
    },

    // Approximate cost of a standard request from per-1K input & output rates
    estimateCost(price) {
      const i = price.input != null ? Number(price.input) : null
      const o = price.output != null ? Number(price.output) : null
      if (i == null && o == null) return null
      return (i || 0) * (STANDARD_REQUEST.input / 1000) +
             (o || 0) * (STANDARD_REQUEST.output / 1000)
    },

    // Bucket the estimated cost into 5 tiers (relative, log scale)
    getPriceTier(cost, range) {
      if (cost == null) return 'unknown'
      if (cost <= 0) return 'very cheap'
      if (range.minLog == null || range.maxLog == null) return 'unknown'
      const span = range.maxLog - range.minLog
      if (span === 0) return 'moderate'
      const ratio = (Math.log10(cost) - range.minLog) / span
      if (ratio <= 0.2) return 'very cheap'
      if (ratio <= 0.4) return 'cheap'
      if (ratio <= 0.6) return 'moderate'
      if (ratio <= 0.8) return 'expensive'
      return 'very expensive'
    },

    // Lit coins use the primary color; unlit coins stay dimmed.
    // 1 coin = very cheap · 3 = moderate · 5 = very expensive.
    coinClass(price, n) {
      if (!price || !price.level || n > price.level) return 'text-base-content/15'
      return 'text-primary'
    },

    // Compact per-request cost label (e.g. "$0.013", "4 cxj")
    formatCost(value, currency) {
      if (value == null || !isFinite(value)) return '—'
      const num = Number(value.toPrecision(value >= 1 ? 3 : 2)).toString()
      return currency === '$' ? `$${num}` : `${num} cxj`
    },

    // Raw per-1K rate for the tooltip
    formatRate(value) {
      if (value == null) return '—'
      const num = Number(value)
      return isFinite(num) ? String(num) : '—'
    },

    buildPriceTooltip(model, price) {
      const unit = price.currency === '$' ? 'USD' : 'cxj'
      const rate = `↓${this.formatRate(price.input)} / ↑${this.formatRate(price.output)} ${unit} per 1K tokens`
      const est = `≈ ${price.estimateLabel} per standard request (${STANDARD_REQUEST.input / 1000}K in + ${STANDARD_REQUEST.output / 1000}K out)`
      return `${model.name} — ${rate} · ${est}`
    }
  }
}
</script>