<script setup>
import { onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  actions: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue', 'select'])

function close() {
  emit('update:modelValue', false)
}

function run(action) {
  if (!action || action.disabled) return
  emit('select', action)
  close()
}

// Lock the underlying screen while the sheet is open so a swipe scrolls the
// sheet's own content instead of the page behind it.
watch(
  () => props.modelValue,
  open => {
    document.documentElement.classList.toggle('mobile-sheet-open', !!open)
  }
)

onBeforeUnmount(() => {
  document.documentElement.classList.remove('mobile-sheet-open')
})
</script>

<template>
  <Teleport to="body">
    <Transition name="mobile-sheet">
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[120] flex flex-col justify-end"
        role="dialog"
        aria-modal="true"
        :aria-label="title || 'Actions'"
        @keydown.esc="close"
      >
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="close"></div>

        <div class="mobile-sheet-panel relative mx-auto w-full max-w-xl overflow-hidden rounded-t-3xl border border-base-content/10 bg-base-100 shadow-2xl">
          <div class="flex justify-center pt-2.5">
            <span class="h-1 w-10 rounded-full bg-base-content/20" aria-hidden="true"></span>
          </div>

          <div v-if="title" class="px-5 pb-1 pt-3">
            <h2 class="text-base font-bold leading-tight text-base-content">{{ title }}</h2>
            <p v-if="subtitle" class="mt-0.5 text-xs text-base-content/50">{{ subtitle }}</p>
          </div>

          <div class="max-h-[65vh] overflow-y-auto overscroll-contain px-2 py-2">
            <button
              v-for="action in actions"
              :key="action.key || action.label"
              type="button"
              class="flex w-full items-center gap-3 rounded-2xl px-3 py-3 text-left transition-colors active:bg-base-content/10 disabled:opacity-40"
              :class="action.danger ? 'text-error' : 'text-base-content'"
              :disabled="action.disabled"
              @click="run(action)"
            >
              <span
                class="grid h-10 w-10 shrink-0 place-items-center rounded-xl"
                :class="action.danger ? 'bg-error/15 text-error' : (action.toneClass || 'bg-base-content/10 text-base-content/70')"
              >
                <i :class="action.icon || 'fa-solid fa-circle'" aria-hidden="true"></i>
              </span>
              <span class="min-w-0 flex-1">
                <span class="block text-sm font-semibold leading-tight">{{ action.label }}</span>
                <span v-if="action.description" class="mt-0.5 block truncate text-[11px] text-base-content/45">
                  {{ action.description }}
                </span>
              </span>
              <i v-if="action.badge" class="text-[10px] text-base-content/40">{{ action.badge }}</i>
              <i v-else class="fa-solid fa-chevron-right text-[10px] text-base-content/25" aria-hidden="true"></i>
            </button>
          </div>

          <div class="safe-area-bottom px-3 pb-2 pt-1">
            <button type="button" class="btn btn-ghost btn-block h-11 justify-center text-sm" @click="close">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
