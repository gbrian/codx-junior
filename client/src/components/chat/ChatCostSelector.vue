<script setup>
</script>

<template>
  <!-- ── Chip variant: compact coins chip + dropdown (chat header) ── -->
  <div v-if="variant === 'chip'" class="dropdown dropdown-end shrink-0">
    <button
      tabindex="0"
      role="button"
      class="btn btn-ghost btn-xs gap-1 rounded-md font-semibold tabular-nums focus:ring-2 focus:ring-primary/50"
      :class="budgetReached ? 'text-error' : 'text-amber-400'"
      :title="triggerTooltip"
      :aria-label="triggerTooltip"
    >
      <i class="fa-solid fa-coins text-xs"></i>
      <span>{{ formatCoins(cost || 0) }}</span>
      <template v-if="hasBudget">
        <span class="opacity-40">/</span>
        <span class="text-base-content/60">{{ formatCoins(estimationCost) }}</span>
      </template>
    </button>

    <div
      tabindex="0"
      class="dropdown-content z-[70] w-64 p-3 mt-1 bg-base-200 border border-base-100 rounded-box shadow-xl"
    >
      <div class="flex items-center gap-2 mb-2 text-xs font-semibold uppercase tracking-wider text-base-content/50">
        <i class="fa-solid fa-coins text-amber-400"></i>
        <span>{{ label }}</span>
        <span v-if="budgetReached" class="badge badge-error badge-xs ml-auto">Reached</span>
      </div>

      <div class="flex items-center justify-between text-xs mb-2">
        <span class="text-base-content/50">Spent</span>
        <span class="font-semibold tabular-nums text-amber-400">{{ formatCoins(cost || 0) }} cxj</span>
      </div>

      <label class="input input-sm input-bordered flex items-center gap-2 mb-2">
        <span class="text-xs text-base-content/40">Max</span>
        <input
          :value="workingCost ?? ''"
          type="number"
          min="0"
          step="0.1"
          placeholder="No limit"
          class="grow bg-transparent outline-none text-sm tabular-nums min-w-0"
          @input="onInput"
          @keydown.enter="saveCost"
          @keydown.esc="closeDropdown"
        />
        <span class="text-xs text-base-content/40">cxj</span>
      </label>

      <div class="flex flex-wrap gap-0.5 mb-2">
        <button
          v-for="preset in costPresets"
          :key="preset"
          type="button"
          class="btn btn-xs btn-ghost"
          @click.stop="applyPreset(preset)"
        >{{ preset }}</button>
        <button
          type="button"
          class="btn btn-xs btn-ghost text-error"
          @click.stop="clearCost"
        >No limit</button>
      </div>

      <p class="text-[10px] leading-snug text-base-content/40 mb-2">
        The agent stops once the accumulated cost reaches this budget.
      </p>

      <div class="flex justify-end gap-2">
        <button type="button" class="btn btn-xs btn-ghost" @click="closeDropdown">Cancel</button>
        <button type="button" class="btn btn-xs btn-primary" @click="saveCost">Save</button>
      </div>
    </div>
  </div>

  <!-- ── Field variant: inline editor for forms/modals ── -->
  <div v-else class="form-control">
    <label class="label py-1">
      <span class="label-text text-xs font-semibold uppercase tracking-wider text-base-content/50">{{ label }}</span>
      <span v-if="budgetReached" class="label-text-alt text-[10px] font-semibold text-error">Reached</span>
      <span v-else-if="hint" class="label-text-alt text-[10px] text-base-content/40">{{ hint }}</span>
    </label>
    <label class="input input-bordered input-sm flex items-center gap-2">
      <i class="fa-solid fa-coins text-amber-400 text-xs"></i>
      <input
        :value="workingCost ?? ''"
        type="number"
        min="0"
        step="0.1"
        placeholder="No limit"
        class="grow bg-transparent outline-none text-sm tabular-nums min-w-0"
        @input="onInput"
        @change="commitField"
        @keydown.enter="commitField"
      />
      <span class="text-xs text-base-content/40">cxj</span>
    </label>
    <div class="flex flex-wrap gap-1 mt-2">
      <button
        v-for="preset in costPresets"
        :key="preset"
        type="button"
        class="btn btn-xs btn-ghost"
        @click="applyPreset(preset)"
      >{{ preset }}</button>
      <button
        type="button"
        class="btn btn-xs btn-ghost text-error"
        @click="clearCost"
      >No limit</button>
    </div>
  </div>
</template>

<script>
// Quick cost-budget presets (cxjcoins). Small values first so a single LLM
// iteration can be capped tightly, then a wider ladder for bigger tasks.
const COST_PRESETS = [0.1, 0.2, 0.3, 0.5, 1]

export default {
  name: 'ChatCostSelector',
  props: {
    // Accumulated cost already spent (cxjcoins). 0 for a chat that has not run yet.
    cost: { type: Number, default: 0 },
    // Current budget (Chat.estimation_cost). null / <= 0 means "no limit".
    estimationCost: { type: [Number, String], default: null },
    // 'chip'  → compact coin chip + dropdown (chat header)
    // 'field' → inline labelled editor (forms / modals)
    variant: { type: String, default: 'chip' },
    label: { type: String, default: 'Cost budget' },
    hint: { type: String, default: '' }
  },
  emits: ['cost-changed'],
  data() {
    return {
      // Draft value being edited before it is committed
      workingCost: null,
      costPresets: COST_PRESETS
    }
  },
  computed: {
    // A positive estimation_cost means the chat has a budget
    hasBudget() {
      return !!(this.estimationCost && Number(this.estimationCost) > 0)
    },
    // Budget consumed → surfaced in red
    budgetReached() {
      return this.hasBudget && (this.cost || 0) >= Number(this.estimationCost)
    },
    triggerTooltip() {
      const spent = this.formatCoins(this.cost || 0)
      if (this.hasBudget) {
        return `Cost: ${spent} of ${this.formatCoins(this.estimationCost)} cxj (click to edit budget)`
      }
      return `Cost: ${spent} cxj · no budget set (click to set)`
    }
  },
  watch: {
    estimationCost: {
      immediate: true,
      handler(val) {
        this.workingCost = (val === '' || val === null || val === undefined) ? null : Number(val)
      }
    }
  },
  methods: {
    // Keep the draft in sync while typing (no emit yet)
    onInput(event) {
      const raw = event.target.value
      this.workingCost = raw === '' ? null : Number(raw)
    },
    // Field variant commits on change / enter (no explicit Save button)
    commitField() {
      this.emitCost(this.workingCost)
    },
    saveCost() {
      this.emitCost(this.workingCost)
      this.closeDropdown()
    },
    applyPreset(preset) {
      this.workingCost = preset
      this.emitCost(preset)
      if (this.variant === 'chip') this.closeDropdown()
    },
    clearCost() {
      this.workingCost = null
      this.emitCost(null)
      if (this.variant === 'chip') this.closeDropdown()
    },
    emitCost(value) {
      this.$emit('cost-changed', this.normalizeCost(value))
    },
    // Normalize a draft to a positive number or null (no budget)
    normalizeCost(value) {
      const num = Number(value)
      if (value === '' || value === null || value === undefined || Number.isNaN(num) || num <= 0) {
        return null
      }
      return num
    },
    closeDropdown() {
      document.activeElement?.blur()
    },
    formatCoins(val) {
      if (val === null || val === undefined || val === '') return '0'
      const num = Number(val)
      if (Number.isNaN(num)) return '0'
      if (num >= 1_000_000) return (num / 1_000_000).toFixed(2) + 'M'
      if (num >= 1_000) return (num / 1_000).toFixed(2) + 'K'
      // Up to 2 decimals, no trailing zeros → 0.1, 1.5, 5
      return String(parseFloat(num.toFixed(2)))
    }
  }
}
</script>