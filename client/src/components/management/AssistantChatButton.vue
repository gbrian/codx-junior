<script setup>
import { computed } from 'vue'
import { useAssistantProfile } from '@/views/management/useAssistantProfile'
</script>

<template>
  <!--
    Entry point of the assistant chat. The icon is the avatar of the profile
    that assists managers (ProjectManager), so the control reads as "talk to the
    manager's assistant" instead of a generic chat bubble.

    Variants:
      • icon  — header action (32px square, daisyUI btn)
      • fab   — floating action (48px round, primary gradient)
      • label — button with the assistant name next to the avatar
  -->
  <button
    type="button"
    :class="buttonClass"
    :title="title"
    :aria-label="title"
    @click="$emit('click', $event)"
  >
    <img
      v-if="avatarUrl"
      :src="avatarUrl"
      :alt="name"
      class="rounded-full object-cover bg-base-300 shrink-0"
      :class="imageClass"
    />
    <i v-else class="fa-solid fa-user-tie shrink-0" :class="fallbackClass"></i>

    <span v-if="variant === 'label'" class="text-xs font-medium truncate">{{ label }}</span>
  </button>
</template>

<script>
export default {
  name: 'AssistantChatButton',
  props: {
    // Project the assistant belongs to (live store project or `{ id }` row)
    project: { type: Object, default: null },
    // Profile that assists managers — its avatar is the button icon
    profileName: { type: String, default: 'ProjectManager' },
    // icon | fab | label
    variant: { type: String, default: 'icon' },
    // Visible text of the `label` variant
    label: { type: String, default: 'Assistant' }
  },
  emits: ['click'],
  computed: {
    assistant() {
      return useAssistantProfile(() => this.project, this.profileName)
    },
    avatarUrl() {
      return this.assistant.avatarUrl.value
    },
    name() {
      return this.assistant.name.value
    },
    title() {
      return `Chat with ${this.name}`
    },
    buttonClass() {
      const base = 'grid place-items-center transition-all duration-150 ' +
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary/60 focus-visible:ring-offset-1'
      if (this.variant === 'fab') {
        return `${base} w-12 h-12 rounded-full shadow-lg hover:shadow-xl hover:brightness-110 ` +
          'bg-gradient-to-br from-primary to-secondary'
      }
      if (this.variant === 'label') {
        return 'btn btn-primary btn-sm gap-2'
      }
      return 'btn btn-ghost btn-sm btn-square'
    },
    imageClass() {
      if (this.variant === 'fab') return 'w-9 h-9'
      if (this.variant === 'label') return 'w-5 h-5'
      return 'w-6 h-6'
    },
    fallbackClass() {
      if (this.variant === 'fab') return 'text-lg text-base-100'
      return 'text-sm text-primary'
    }
  }
}
</script>