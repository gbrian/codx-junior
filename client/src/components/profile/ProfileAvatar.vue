<template>
  <div class="dropdown dropdown-hover">
    <div tabindex="0" role="button" class="">
      <div class="avatar" v-if="profile">
        <div class="rounded-full" :class="avatarWidth">
          <img :src="profile.avatar" />
        </div>
      </div>
    </div>
    <div
      tabindex="0"
      class="dropdown-content card card-sm bg-base-300/90 border-base-300 z-10 w-96 shadow-md">
      <div class="card-body text-xs">
        <div class="badge badge-primary">{{ profile.name }}</div>
        <p>{{ profile.description }}</p>
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
      return `w-${width} h-${width}`
    }
  }
}
</script>