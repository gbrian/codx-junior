<template>
  <div
    v-if="show"
    class="modal modal-open z-50"
    role="dialog"
    aria-modal="true"
    aria-labelledby="console-script-confirm-title"
    aria-describedby="console-script-confirm-command"
  >
    <div class="modal-box max-w-lg">
      <!-- Header -->
      <div class="flex items-start gap-3 mb-4">
        <div class="p-2 rounded-lg bg-warning/15 text-warning shrink-0">
          <i class="fa-solid fa-terminal"></i>
        </div>
        <div class="min-w-0">
          <h3 id="console-script-confirm-title" class="font-bold text-lg leading-tight">
            Run console script?
          </h3>
          <p class="text-xs text-base-content/60 mt-1 truncate">{{ scriptName }}</p>
        </div>
      </div>

      <!-- Script description -->
      <p v-if="scriptDescription" class="text-sm text-base-content/70 mb-3">
        {{ scriptDescription }}
      </p>

      <!-- Exact command that will run -->
      <pre
        id="console-script-confirm-command"
        class="bg-base-300 rounded-lg p-3 text-xs font-mono overflow-auto max-h-40 whitespace-pre-wrap break-words"
      >{{ command }}</pre>

      <!-- Script metadata -->
      <div class="flex flex-wrap gap-2 mt-3">
        <span v-if="script && script.background" class="badge badge-sm badge-ghost gap-1">
          <i class="fa-solid fa-circle-play"></i> background
        </span>
        <span v-if="script && script.restart" class="badge badge-sm badge-ghost gap-1">
          <i class="fa-solid fa-power-off"></i> restart if stopped
        </span>
        <span class="badge badge-sm badge-warning gap-1">
          <i class="fa-solid fa-triangle-exclamation"></i> runs on the server
        </span>
      </div>

      <!-- Warning -->
      <p class="text-xs text-base-content/60 mt-3">
        The command runs on the codx-junior host, in the project working directory, with your
        permissions. It cannot be undone — check it before confirming.
      </p>

      <!-- Actions -->
      <div class="modal-action">
        <button
          ref="cancelButton"
          type="button"
          class="btn btn-sm btn-ghost"
          :disabled="busy"
          @click="onCancel"
        >
          Cancel
        </button>
        <button
          type="button"
          class="btn btn-sm btn-primary"
          :disabled="busy || !command"
          @click="onConfirm"
        >
          <span v-if="busy" class="loading loading-spinner loading-xs"></span>
          <i v-else class="fa-solid fa-play"></i>
          {{ busy ? 'Running…' : 'Run script' }}
        </button>
      </div>
    </div>

    <!-- Backdrop: click outside cancels -->
    <form method="dialog" class="modal-backdrop" @submit.prevent="onCancel">
      <button type="button" @click="onCancel" aria-label="Cancel"></button>
    </form>
  </div>
</template>

<script>
export default {
  props: {
    // Whether the dialog is visible
    show: { type: Boolean, default: false },
    // Console script ({ name, description, script, background, restart })
    script: { type: Object, default: null },
    // True while the command is being executed (locks the dialog)
    busy: { type: Boolean, default: false }
  },
  emits: ['confirm', 'cancel'],
  computed: {
    command() {
      if (!this.script) return ''
      return String(this.script.script || this.script.command || '').trim()
    },
    scriptName() {
      return this.script?.name || 'Unnamed script'
    },
    scriptDescription() {
      return this.script?.description || ''
    }
  },
  watch: {
    // Focus the safe action as soon as the dialog opens
    show(value) {
      if (value) {
        this.$nextTick(() => this.$refs.cancelButton?.focus())
      }
    }
  },
  mounted() {
    window.addEventListener('keydown', this.onKeydown)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    onKeydown(event) {
      if (!this.show) return
      if (event.key === 'Escape') {
        event.preventDefault()
        this.onCancel()
      }
    },
    onCancel() {
      if (this.busy) return
      this.$emit('cancel')
    },
    onConfirm() {
      if (this.busy || !this.command) return
      this.$emit('confirm', this.script)
    }
  }
}
</script>