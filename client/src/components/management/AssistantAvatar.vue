<script setup>
import { computed } from 'vue'
import { useAssistantProfile } from '@/views/management/useAssistantProfile'
</script>

<template>
  <!--
    Identity of the assistant that answers: the avatar of the profile that
    assists managers (ProjectManager). Falls back to a role icon when the
    profile has no image, so the element never collapses to an empty box.
  -->
  <span
    class="rounded-full grid place-items-center overflow-hidden shrink-0 bg-base-300 border border-base-content/10"
    :class="sizeClass"
    :title="name"
  >
    <img v-if="avatarUrl" :src="avatarUrl" :alt="name" class="w-full h-full object-cover" />
    <i v-else class="fa-solid fa-user-tie text-primary" :class="iconClass"></i>
  </span>
</template>

<script>
export default {
  name: 'AssistantAvatar',
  props: {
    // Project the assistant belongs to (live store project or `{ id }` row)
    project: { type: Object, default: null },
    // Profile that assists managers — its avatar is the assistant identity
    profileName: { type: String, default: 'ProjectManager' },
    // xs | sm | md | lg
    size: { type: String, default: 'sm' }
  },
  computed: {
    sizeClass() {
      return {
        xs: 'w-5 h-5',
        sm: 'w-7 h-7',
        md: 'w-9 h-9',
        lg: 'w-12 h-12'
      }[this.size] || 'w-7 h-7'
    },
    iconClass() {
      return {
        xs: 'text-[9px]',
        sm: 'text-[11px]',
        md: 'text-sm',
        lg: 'text-lg'
      }[this.size] || 'text-[11px]'
    }
  },
  methods: {
    // The profile is resolved in setup so it is shared with the button that
    // opens the chat (same cache, same avatar, one request per project).
    bindAssistant() {
      const { avatarUrl, name, loading } = useAssistantProfile(
        () => this.project,
        this.profileName
      )
      this.assistantAvatar = avatarUrl
      this.assistantName = name
      this.assistantLoading = loading
    }
  },
  data() {
    return {
      assistantAvatar: null,
      assistantName: this.profileName,
      assistantLoading: false
    }
  },
  created() {
    this.bindAssistant()
  },
  watch: {
    profileName() {
      this.bindAssistant()
    }
  }
}
</script>