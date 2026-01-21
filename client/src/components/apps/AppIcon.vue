<template>
  <i :class="app.icon" v-if="isAwesome"></i>
  <img class="-mt-1 w-6 h-6 rounded-full" :src="imageUrl" v-else />

</template>
<script>
export default {
  props: ['app'],
  computed: {
    isAwesome() {
      return this.app.icon?.includes("fa")
    },
    imageUrl() {
      const path = this.app.path?.split("#")[0]
      const sep = this.app.path?.endsWith("/") ? "": "/"
      return this.app.icon || `${path}${sep}favicon.ico`
    }
  }
}
</script>