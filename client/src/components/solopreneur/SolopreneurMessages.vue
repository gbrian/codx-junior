<script setup>
import { ref, watch, nextTick } from 'vue'
import { useSolopreneur } from './useSolopreneur'

const { state, t, sendMessage } = useSolopreneur()
const draft = ref('')
const threadRef = ref(null)

function submit() {
  const value = draft.value.trim()
  if (!value) return
  draft.value = ''
  sendMessage(value)
}

function scrollToBottom() {
  nextTick(() => {
    const el = threadRef.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

watch(() => state.messages.length, scrollToBottom)
watch(() => state.ui.typing, scrollToBottom)
</script>

<template>
  <section class="bg-base-100 border border-base-content/10 rounded-2xl shadow-sm p-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-base font-semibold">{{ t('ms.title') }}</h2>
        <p class="text-sm text-base-content/50 mt-1.5 max-w-prose">{{ t('ms.desc') }}</p>
      </div>
      <span class="inline-flex items-center gap-2 text-xs font-semibold text-success whitespace-nowrap">
        <span class="w-1.5 h-1.5 rounded-full bg-success" aria-hidden="true"></span>
        {{ t('ms.online') }}
      </span>
    </div>

    <!-- Thread -->
    <div ref="threadRef" class="mt-5 flex flex-col gap-5 overflow-y-auto pr-1 min-h-[360px]">
      <div
        v-for="m in state.messages"
        :key="m.id"
        class="flex items-start gap-3"
        :class="m.from === 'me' ? 'justify-end' : ''"
      >
        <span
          v-if="m.from !== 'me'"
          class="w-9 h-9 rounded-full shrink-0 grid place-items-center text-[11px] font-bold text-white bg-codx-primary"
          aria-hidden="true"
        >AI</span>

        <div class="flex flex-col gap-1.5 max-w-[80%] min-w-0" :class="m.from === 'me' ? 'items-end' : ''">
          <span class="text-[10px] font-semibold tracking-widest text-base-content/40">
            {{ m.from === 'me' ? t('ms.you') : t('ms.ai') }}
          </span>
          <div
            class="rounded-2xl px-4 py-3 text-sm leading-relaxed"
            :class="m.from === 'me' ? 'bg-base-content text-base-100' : 'bg-base-200 text-base-content'"
          >{{ m.text }}</div>
          <time class="text-[11px] text-base-content/40">{{ m.time }}</time>
        </div>

        <span
          v-if="m.from === 'me'"
          class="w-9 h-9 rounded-full shrink-0 grid place-items-center text-[11px] font-bold text-white bg-codx-secondary"
          aria-hidden="true"
        >{{ state.user.initials }}</span>
      </div>

      <!-- Typing indicator -->
      <div v-if="state.ui.typing" class="flex items-start gap-3">
        <span class="w-9 h-9 rounded-full shrink-0 grid place-items-center text-[11px] font-bold text-white bg-codx-primary" aria-hidden="true">AI</span>
        <div class="flex flex-col gap-1.5">
          <span class="text-[10px] font-semibold tracking-widest text-base-content/40">{{ t('ms.ai') }}</span>
          <div class="rounded-2xl px-4 py-3 bg-base-200 inline-flex items-center gap-1" role="status" :aria-label="t('ms.typing')">
            <span class="w-1.5 h-1.5 rounded-full bg-base-content/40 animate-pulse"></span>
            <span class="w-1.5 h-1.5 rounded-full bg-base-content/40 animate-pulse" style="animation-delay:.15s"></span>
            <span class="w-1.5 h-1.5 rounded-full bg-base-content/40 animate-pulse" style="animation-delay:.3s"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Composer -->
    <form class="mt-6 flex items-center gap-3" @submit.prevent="submit">
      <label class="sr-only" for="solo-composer">{{ t('ms.ph') }}</label>
      <input
        id="solo-composer"
        v-model="draft"
        type="text"
        autocomplete="off"
        :placeholder="t('ms.ph')"
        class="flex-1 min-w-0 h-12 rounded-full border border-base-content/15 bg-base-100 px-5 text-sm outline-none focus:border-codx-primary focus:ring-2 focus:ring-codx-primary/20"
      />
      <button
        type="submit"
        class="h-12 px-7 rounded-full bg-codx-primary text-white text-sm font-semibold hover:opacity-90 active:scale-95 transition"
      >
        {{ t('ms.send') }}
      </button>
    </form>
  </section>
</template>