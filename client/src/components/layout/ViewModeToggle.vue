<script setup>
</script>

<template>
  <button class="btn tooltip tooltip-right"
    :data-tip="isDesktopMode ? 'Chat mode' : 'Desktop mode'"
    @click.stop="handleToggleViewMode">
    <i v-if="isDesktopMode" class="click fa-regular fa-window-maximize"></i>
    <i v-else class="click fa-solid fa-table-columns"></i>
  </button>
</template>

<script>
export default {
  computed: {
    isDesktopMode() {
      return this.$storex.$router.$navigation.isDesktopMode
    }
  },
  methods: {
    handleToggleViewMode() {
      if (this.isDesktopMode) {
        this.$storex.$router.$navigation.apps.openHome()
      } else {
        this.$storex.$router.$navigation.apps.openDesktop()
      }
    }
  }
}
</script>