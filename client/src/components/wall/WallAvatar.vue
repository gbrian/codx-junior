<script setup>
import { avatarClass } from './wallEvents'
</script>

<template>
  <div class="avatar tooltip shrink-0" :data-tip="account.name">
    <div
      class="rounded-full overflow-hidden grid place-items-center font-bold text-white shrink-0"
      :class="sizeClass"
    >
      <!-- Real avatar when available; the logo is used for the codx-junior bot
           and project icons. On load failure we fall back to initials. -->
      <img
        v-if="src"
        :src="src"
        :alt="account.name"
        class="w-full h-full object-cover"
        @error="failed = true"
      />
      <!-- Deterministic coloured circle with the account's initials. The span
           fills the whole circle (not just the text) so the avatar is always a
           visible, correctly-sized badge. -->
      <span v-else class="w-full h-full grid place-items-center" :class="avatarClass(seed)">
        {{ label }}
      </span>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    account: { type: Object, required: true },
    size: { type: Number, default: 10 }
  },
  data() {
    return { failed: false }
  },
  computed: {
    // Fixed size map (no dynamic `w-${n}` classes — Tailwind JIT can't see them)
    sizeClass() {
      return {
        5: 'w-5 h-5 text-[8px]',
        6: 'w-6 h-6 text-[9px]',
        8: 'w-8 h-8 text-xs',
        10: 'w-10 h-10 text-sm',
        12: 'w-12 h-12 text-base',
        14: 'w-14 h-14 text-lg'
      }[this.size] || 'w-10 h-10 text-sm'
    },
    seed() {
      return this.account.handle || this.account.name || this.account.id
    },
    src() {
      if (this.failed) return null
      const a = this.account?.avatar
      return (typeof a === 'string' && a.trim()) ? a : null
    },
    label() {
      // The bot normally renders the logo image; "AI" is only the error fallback.
      if (this.account.type === 'bot') return 'AI'
      const words = String(this.account.name || '').trim().split(/\s+/).filter(Boolean)
      if (!words.length) return '?'
      return words.length === 1
        ? words[0].slice(0, 2).toUpperCase()
        : (words[0][0] + words[1][0]).toUpperCase()
    }
  },
  watch: {
    account: {
      deep: true,
      handler() { this.failed = false }
    }
  }
}
</script>
