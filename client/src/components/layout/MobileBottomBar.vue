<script setup>
</script>

<template>
  <nav
    class="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around bg-base-300 border-t border-base-content/10 px-2 py-2 safe-area-bottom"
  >
    <button
      class="flex flex-col items-center gap-1 px-3 py-2 text-base-content/50 hover: transition-colors"
      @click="$emit('show-menu')"
    >
      <i class="fas fa-ellipsis text-lg"></i>
      <span class="text-[10px]">More</span>
    </button>

    <button
      class="flex flex-col items-center gap-1 px-3 py-2 text-base-content/50 hover: transition-colors"
      @click="handleNavigateToNewChat"
    >
      <i class="fas fa-plus text-lg"></i>
      <span class="text-[10px]">New</span>
    </button>

    <button
      class="flex flex-col items-center gap-1 px-3 py-2 text-base-content/50 hover: transition-colors"
      @click="handleNavigateToKanban"
    >
      <i class="fas fa-list-check text-lg"></i>
      <span class="text-[10px]">Task Manager</span>
    </button>

    <button
      class="flex flex-col items-center gap-1 px-3 py-2 text-base-content/50 hover: transition-colors"
      @click="handleNavigateToFileExplorer"
    >
      <i class="fas fa-folder-open text-lg"></i>
      <span class="text-[10px]">Files</span>
    </button>

  </nav>
</template>

<script>
export default {
  props: {
    userName: { type: String, default: 'User' }
  },
  emits: ['show-menu'],
  methods: {
    handleNavigateToNewChat() {
      this.$storex.$router.$navigation.apps.openHome()
    },
    handleNavigateToKanban() {
      this.$storex.$router.$navigation.apps.openKanban()
    },
    handleNavigateToFileExplorer() {
      this.$storex.$router.$navigation.apps.openFileExplorer()
    }
  }
}
</script>