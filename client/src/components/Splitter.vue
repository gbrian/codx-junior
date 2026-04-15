<script setup>
import StatuBar from './StatuBar.vue'
import DesktopView from '@/views/DesktopView.vue'
</script>

<template>
  <div class="flex">
    <div class="grow flex flex-col h-full overflow-hidden">
      <DesktopView class="h-full w-full" />
      <StatuBar />
    </div>
  </div>
</template>
<script>
export default {
  data() {
    return {
    }
  },
  computed: {
    zoom() {
      return this.$ui.activeApp && this.showCodxJunior ? 1.2 : 1
    },
    isHorizontal() {
      return this.$ui.appDivided === 'horizontal'
    },
    showCodxJunior() {
      return !!this.$ui.activeTab
    },
    showCodxJuniorFloating() {
      return !this.$ui.isMobile && this.$ui.floatingCodxJunior
    },
    showWorkspaces() {
      return this.$storex.projects.openedWorkspaces.length
    },
    showNavigationBar() {
      return !this.$ui.isMobile || !this.$projects.activeChat 
            || this.$ui.activeTab !== 'tasks'
            || this.$ui.activeApp
    }
  },
  mounted() {
  },
  watch: {
  },
  methods: {
    onDblclickCodxJunior() {
      console.log("onDblclickCodxJunior")
    }
  }
}
</script>
