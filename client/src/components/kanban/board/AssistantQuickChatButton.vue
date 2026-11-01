<script setup>
</script>

<template>
  <!--
    Quick-chat entry point. The icon is the avatar of the profile that assists
    managers (ProjectManager), so the button reads as "talk to the assistant"
    instead of a generic chat bubble. Falls back to an icon when the profile
    has no avatar or cannot be loaded.
  -->
  <button
    type="button"
    class="btn btn-primary btn-sm gap-2"
    :title="title"
    :aria-label="title"
    @click="$emit('click', $event)"
  >
    <img
      v-if="avatarUrl"
      :src="avatarUrl"
      :alt="profileName"
      class="w-5 h-5 rounded-full object-cover bg-base-300 shrink-0"
    />
    <i v-else class="fa-solid fa-user-tie text-xs"></i>
    <span class="text-xs font-medium">{{ label }}</span>
  </button>
</template>

<script>
export default {
  name: 'AssistantQuickChatButton',
  props: {
    // Project whose profiles are used to resolve the assistant avatar
    project: { type: Object, default: null },
    // Profile that assists managers — its avatar becomes the button icon
    profileName: { type: String, default: 'ProjectManager' },
    label: { type: String, default: 'Quick chat' }
  },
  emits: ['click'],
  data() {
    return {
      profile: null,
      // Project the profile was resolved from (avoids refetching it)
      loadedProjectId: null
    }
  },
  created() {
    this.loadProfile()
  },
  computed: {
    avatarUrl() {
      return this.profile?.avatar_url || this.profile?.avatar || null
    },
    title() {
      const name = this.profile?.name || this.profileName
      return `Quick chat with ${name}`
    }
  },
  watch: {
    // Another project brings another ProjectManager profile
    project() {
      this.loadProfile()
    }
  },
  methods: {
    async loadProfile() {
      const project = this.project || this.$project
      if (!project?.project_id) return
      if (this.loadedProjectId === project.project_id) return
      this.loadedProjectId = project.project_id
      try {
        const api = project.$api || project.api
        const list = await api?.profiles?.list?.()
        this.profile = (list || []).find(profile => profile.name === this.profileName) || null
      } catch (error) {
        console.error('[AssistantQuickChatButton] Could not load the assistant profile:', error)
        this.profile = null
      }
    }
  }
}
</script>