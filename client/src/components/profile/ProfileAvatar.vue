<script setup>
import Document from '../document/Document.vue';
</script>
<template>
  <div class="dropdown click"
    :title="profile?.name"
  >
    <div tabindex="0" class="avatar" v-if="profile">
      <div class="rounded-full bg-base-300" :class="avatarWidth">
        <img :src="avatarUrl" :alt="profile.name" />
      </div>
    </div>
    <div
      tabindex="0"
      class="dropdown-content bg-base-100 card card-sm bg-base-300/90 border-base-100 z-10 w-96 shadow-md">
      <div class="card-body text-xs">
        <div class="badge badge-primary">{{ profile.name }}</div>
        <p>{{ profile.description }}</p>
        <div>Tools: {{ profile.tools }}</div>
        <Document class="max-h-60 overflow-auto" :content="profile.content" />
        <slot></slot>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: ['profile', 'width'],
  computed: {
    avatarWidth() {
      let width = this.width
      if (!width) {
        width = 6
      }
      return `w-${width}`
    },
    avatarUrl() {
      // A generated avatar keeps the profile recognisable when it carries no
      // picture (same default the profile cards use), so an assignee whose
      // profile is still loading is never rendered as a broken image.
      return this.profile.avatar_url || this.profile.avatar ||
        `https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=400&d=robohash&r=${this.profile.name}`
    }
  }
}
</script>
