<script setup>
</script>

<template>
  <div class="bg-base-200 rounded-lg border border-slate-400 bg-base-200 drop-shadow flex flex-col">
    <!-- Header toggle -->
    <div
      class="flex items-center gap-2 p-2 cursor-pointer select-none"
      @click="isOpen = !isOpen"
    >
      <!-- Optional icon slot -->
      <slot name="icon">
        <i class="fa-solid fa-chevron-right text-xs opacity-60"></i>
      </slot>

      <!-- Title slot -->
      <span class="text-sm font-medium">
        <slot name="title">Toggle</slot>
      </span>

      <!-- Summary slot — shown when collapsed, e.g. active filter chips -->
      <div class="flex gap-1 flex-wrap grow">
        <slot name="summary"></slot>
      </div>

      <!-- Actions slot — buttons always visible in header -->
      <slot name="actions"></slot>

      <!-- Chevron indicator -->
      <i
        class="fa-solid text-xs opacity-50"
        :class="isOpen ? 'fa-chevron-up' : 'fa-chevron-down'"
      ></i>
    </div>

    <!-- Collapsible body -->
    <div
      v-show="isOpen"
      class="border-t border-base-300 grow"
    >
      <slot></slot>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    // Control initial open state
    defaultOpen: { type: Boolean, default: false },
    // Allow parent to control open state via v-model
    modelValue: { type: Boolean, default: null }
  },
  emits: ['update:modelValue'],
  data() {
    return {
      internalOpen: this.defaultOpen
    }
  },
  computed: {
    // Support both controlled (v-model) and uncontrolled mode
    isOpen: {
      get() {
        return this.modelValue !== null ? this.modelValue : this.internalOpen
      },
      set(val) {
        this.internalOpen = val
        this.$emit('update:modelValue', val)
      }
    }
  }
}
</script>