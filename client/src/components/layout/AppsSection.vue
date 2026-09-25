<script setup>
import NavItem from './NavItem.vue'
</script>

<template>
  <div class="px-2 py-3 shrink-0 border-b border-white/5">
    <button
      v-if="!isCollapsed && !isMobileExpanded"
      class="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-white/60 hover:text-white/80 transition-colors"
      @click="primaryNavExpanded = !primaryNavExpanded"
      title="Toggle Primary Navigation"
    >
      <span>APPS</span>
      <i :class="primaryNavExpanded ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'" class="text-xs"></i>
    </button>
    <div v-if="primaryNavExpanded || isCollapsed || isMobileExpanded" class="flex flex-col gap-1">
      <NavItem
        icon="fas fa-plus"
        label="New"
        :is-collapsed="isCollapsed && !isMobileExpanded"
        :is-primary="true"
        @click="handleNavigateToNewChat"
      />

      <NavItem
        icon="fas fa-list-check"
        label="Task Manager"
        :is-collapsed="isCollapsed && !isMobileExpanded"
        @click="handleNavigateToKanban"
      />

      <NavItem
        icon="fas fa-messages"
        label="Messenger"
        :is-collapsed="isCollapsed && !isMobileExpanded"
        @click="handleNavigateToMessenger"
      />

      <NavItem
        icon="fas fa-folder-open"
        label="File Explorer"
        :is-collapsed="isCollapsed && !isMobileExpanded"
        @click="handleNavigateToFileExplorer"
      />

      <NavItem
        icon="fas fa-graduation-cap"
        label="Wiki"
        :is-collapsed="isCollapsed && !isMobileExpanded"
        @click="handleNavigateToWiki"
      />

      <NavItem
        icon="fas fa-chevron-down"
        label="More"
        :is-collapsed="isCollapsed && !isMobileExpanded"
        :expandable="true"
        :expanded="moreExpanded"
        @click="handleMoreClick"
      />
    </div>
  </div>
</template>

<script>
export default {
  props: {
    isCollapsed: { type: Boolean, default: false },
    isMobileExpanded: { type: Boolean, default: false },
    moreExpanded: { type: Boolean, default: false }
  },
  emits: ['update:moreExpanded', 'close'],
  data() {
    return {
      primaryNavExpanded: true
    }
  },
  methods: {
    handleMoreClick() {
      if (this.isCollapsed && !this.isMobileExpanded) {
        this.toggleCollapse()
      } else {
        this.$emit('update:moreExpanded', !this.moreExpanded)
      }
    },
    handleNavigateToNewChat() {
      this.$storex.$router.$navigation.apps.openHome()
      this.$emit('close')
    },
    handleNavigateToKanban() {
      this.$storex.$router.$navigation.apps.openKanban()
      this.$emit('close')
    },
    handleNavigateToMessenger() {
      this.$storex.$router.$navigation.apps.openMessenger()
      this.$emit('close')
    },
    handleNavigateToFileExplorer() {
      this.$storex.$router.$navigation.apps.openFileExplorer()
      this.$emit('close')
    },
    handleNavigateToWiki() {
      this.$storex.$router.$navigation.apps.openWiki()
      this.$emit('close')
    },
    toggleCollapse() {
      this.$emit('toggle-collapse')
    }
  }
}
</script>