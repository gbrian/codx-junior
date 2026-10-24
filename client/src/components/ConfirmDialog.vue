<script setup>
</script>

<template>
  <modal close @close="$emit('cancel')">
    <!-- ── Header ───────────────────────────────────────────────────────── -->
    <template #header>
      <div class="flex items-center gap-2 min-w-0">
        <i class="fa-solid text-sm shrink-0" :class="[icon, iconClass]"></i>
        <h2 class="text-sm md:text-base font-semibold truncate">{{ title }}</h2>
      </div>
    </template>

    <!-- ── Body ─────────────────────────────────────────────────────────── -->
    <div class="flex flex-col gap-3 md:min-w-[20rem] md:max-w-md">
      <p v-if="message" class="text-sm text-base-content/80 leading-relaxed break-words">
        {{ message }}
      </p>

      <ul
        v-if="visibleDetails.length"
        class="flex flex-col gap-0.5 max-h-40 overflow-auto rounded-lg border border-base-content/10 bg-base-100/60 p-2"
      >
        <li
          v-for="detail in visibleDetails"
          :key="detail"
          class="font-mono text-[11px] truncate text-base-content/70"
          :title="detail"
        >{{ detail }}</li>
        <li v-if="hiddenCount" class="text-[11px] text-base-content/50">
          + {{ hiddenCount }} more
        </li>
      </ul>

      <p v-if="hint" class="text-[11px] text-base-content/50 leading-tight">{{ hint }}</p>
    </div>

    <!-- ── Actions ──────────────────────────────────────────────────────── -->
    <template #footer>
      <button
        ref="cancelButton"
        class="btn btn-sm btn-ghost"
        :disabled="busy"
        @click="$emit('cancel')"
      >
        Cancel
      </button>
      <button
        class="btn btn-sm gap-1"
        :class="confirmClass"
        :disabled="busy"
        @click="$emit('confirm')"
      >
        <i v-if="busy" class="fa-solid fa-spinner animate-spin"></i>
        <i v-else-if="confirmIcon" class="fa-solid" :class="confirmIcon"></i>
        {{ confirmLabel }}
      </button>
    </template>
  </modal>
</template>

<script>
export default {
  name: 'ConfirmDialog',
  props: {
    // Dialog heading
    title: { type: String, default: 'Confirm' },
    // Question or explanation shown above the details
    message: { type: String, default: '' },
    // Optional list of affected items (file paths, branches...)
    details: { type: Array, default: () => [] },
    // Optional consequence warning, rendered under the details
    hint: { type: String, default: '' },
    // Header icon: font-awesome class and its color utility
    icon: { type: String, default: 'fa-triangle-exclamation' },
    iconClass: { type: String, default: 'text-warning' },
    // Confirm button label, icon and daisyUI style (btn-error for destructive)
    confirmLabel: { type: String, default: 'Confirm' },
    confirmIcon: { type: String, default: '' },
    confirmClass: { type: String, default: 'btn-primary' },
    // Operation running: both buttons are disabled and a spinner is shown
    busy: { type: Boolean, default: false },
    // Maximum number of details rendered before collapsing into "+ n more"
    maxDetails: { type: Number, default: 8 }
  },
  emits: ['confirm', 'cancel'],
  computed: {
    visibleDetails() {
      return (this.details || []).slice(0, this.maxDetails)
    },
    hiddenCount() {
      return Math.max((this.details || []).length - this.maxDetails, 0)
    }
  },
  mounted() {
    // Destructive actions: the safe option holds the initial focus
    this.$nextTick(() => this.$refs.cancelButton?.focus())
  }
}
</script>