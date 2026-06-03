<script setup>
import Document from '../document/Document.vue';
</script>
<template>
  <div class="dropdown click">
    <div tabindex="0" class="avatar" v-if="profile">
      <div class="rounded-full bg-base-300" :class="avatarWidth">
        <img :src="avatarUrl" />
      </div>
    </div>
    <div
      tabindex="0"
      class="dropdown-content card card-sm bg-base-300/90 border-base-300 z-10 w-96 shadow-md">
      <div class="card-body text-xs">
        <div class="badge badge-primary">{{ profile.name }}</div>
        <p>{{ profile.description }}</p>
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
      return this.profile.avatar_url || this.profile.avatar
    }
  }
}
</script>