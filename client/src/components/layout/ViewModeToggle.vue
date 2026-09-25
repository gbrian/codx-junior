<script setup>
</script>

<template>
  <div class="flex cursor-pointer gap-2 items-center rounded-full border py-1 px-2"
    @click.stop="handleToggleViewMode"
  >
    <span class=" tooltip" data-tip="Swicth to simple view">
      <i :class="isDesktopMode && 'opacity-50'"
        class="click fa-regular fa-window-maximize">
      </i>
    </span>
    <span class="tooltip" data-tip="Swicth to tabs view">
      <i :class="!isDesktopMode && 'opacity-50'"
        class="click fa-solid fa-table-columns">
      </i>
    </span>
  </div>
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