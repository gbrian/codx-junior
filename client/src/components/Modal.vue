<script setup>
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center">
    <!-- Backdrop -->
    <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="close && $emit('close')"></div>

    <!-- Modal Box -->
    <div
      v-bind="$attrs"
      class="relative z-10 bg-base-100 rounded-2xl shadow-2xl border border-base-300 w-full max-w-lg max-h-[90vh] flex flex-col mx-4 animate-fade-in"
    >
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-base-300">
        <slot name="title">
          <span class="text-lg font-semibold text-base-content"></span>
        </slot>
        <button
          v-if="close"
          class="btn btn-ghost btn-sm btn-circle text-base-content/60 hover:text-error transition-colors"
          @click="$emit('close')"
        >
          <i class="fa-solid fa-xmark text-lg"></i>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-6 py-4">
        <slot></slot>
      </div>

      <!-- Footer -->
      <div v-if="$slots.footer" class="px-6 py-4 border-t border-base-300 flex justify-end gap-2">
        <slot name="footer"></slot>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  inheritAttrs: false,
  props: ['close', 'scope'],
  mounted() {
    // Attach to the provided scope element, or fall back to the root App element
    const target = this.scope || this.$root.$el
    target.appendChild(this.$el)
  },
  beforeUnmount() {
    // Clean up when modal is destroyed
    if (this.$el.parentNode) {
      this.$el.parentNode.removeChild(this.$el)
    }
  }
}
</script>