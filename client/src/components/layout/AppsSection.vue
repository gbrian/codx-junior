<script setup>
import NavItem from './NavItem.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
import ViewModeToggle from './ViewModeToggle.vue';
</script>

<template>
  <div class="px-2 py-3 shrink-0 border-b border-base-content/5">
    <div class="flex gap-2 pb-1">  
      
      <!-- Project selector -->
      <ProjectDetailt 
        v-if="!isCollapsed"
        @click.stop=""
        :options="{ folders: true, showIcon: true }"
        @select="$storex.projects.activeProjectChanged($event)"
      />
      <ViewModeToggle v-if="!isCollapsed"
       />
          
    </div>
    <button
      v-if="!isCollapsed"
      class="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-base-content/60 hover:text-base-content/80 transition-colors"
      @click="primaryNavExpanded = !primaryNavExpanded"
      title="Toggle Primary Navigation"
    >
      APPS
      <i :class="primaryNavExpanded ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'" class="text-xs"></i>
    </button>
    <div v-if="primaryNavExpanded || isCollapsed" class="flex flex-col gap-1">
      
      <NavItem
        icon="fas fa-plus"
        label="New"
        :is-collapsed="isCollapsed"
        :is-primary="true"
        @click="handleNavigateToNewChat"
      />

      <NavItem
        icon="fas fa-list-check"
        label="Task Manager"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToKanban"
      />

      <NavItem
        icon="fas fa-diagram-project"
        label="Planning"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToPlanning"
      />

      <NavItem
        icon="fa-regular fa-comments"
        label="Messenger"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToMessenger"
      />

      <NavItem
        icon="fas fa-video"
        label="Meet"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToMeet"
      />

      <NavItem
        icon="fas fa-folder-open"
        label="File Explorer"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToFileExplorer"
      />

      <NavItem
        icon="fas fa-graduation-cap"
        label="Wiki"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToWiki"
      />

    </div>
  </div>
</template>

<script>
export default {
  props: {
    isCollapsed: { type: Boolean, default: false },
    moreExpanded: { type: Boolean, default: false }
  },
  emits: ['update:moreExpanded', 'close'],
  data() {
    return {
      primaryNavExpanded: true
    }
  },
  methods: {
    handleNavigateToNewChat() {
      if (this.$router.$navigation.isDesktopMode) {
        this.$service.chat.newQuickChat()
      } else {
        this.$storex.$router.$navigation.apps.openHome()
      }
      this.$emit('close')
    },
    handleNavigateToKanban() {
      this.$ui.setActiveTab('tasks')
      this.$emit('close')
    },
    handleNavigateToPlanning() {
      this.$ui.openPlanning()
      this.$emit('close')
    },
    handleNavigateToMessenger() {
      this.$ui.setActiveTab('messenger')
      this.$emit('close')
    },
    handleNavigateToMeet() {
      this.$ui.openMeet()
      this.$emit('close')
    },
    handleNavigateToFileExplorer() {
      this.$ui.setActiveTab('file-explorer')
      this.$emit('close')
    },
    handleNavigateToWiki() {
      this.$ui.setActiveTab('wiki')
      this.$emit('close')
    },
    toggleCollapse() {
      this.$emit('toggle-collapse')
    }
  }
}
</script>