<script setup>
import NavItem from './NavItem.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
import ViewModeToggle from './ViewModeToggle.vue'
import PinnedProjectsSwitcher from './PinnedProjectsSwitcher.vue';
import { isMultiInstance } from '@/config/apps'
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
        @open="$emit('overlay-open')"
        @close="$emit('overlay-close')"
      />

      <!-- Pin / unpin the active project (quick switcher) -->
      <button
        v-if="!isCollapsed"
        class="btn tooltip tooltip-right"
        :class="isActiveProjectPinned ? 'click text-primary' : 'click text-base-content/50'"
        :data-tip="isActiveProjectPinned ? 'Unpin project' : 'Pin project'"
        :aria-pressed="isActiveProjectPinned"
        aria-label="Pin project"
        @click.stop="togglePinCurrentProject"
      >
        <i class="fa-solid fa-thumbtack text-xs"></i>
      </button>

      <ViewModeToggle v-if="!isCollapsed"
       />
          
    </div>

    <!-- Pinned projects quick switcher (icons only while the rail is collapsed) -->
    <PinnedProjectsSwitcher :is-collapsed="isCollapsed" />

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
        icon="fas fa-folder-plus"
        label="New Project"
        :is-collapsed="isCollapsed"
        @click="handleNewProject"
      />

      <NavItem
        icon="fas fa-clock-rotate-left"
        label="Activity"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToActivity"
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
        icon="fas fa-people-group"
        label="Team"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToTeam"
      />

      <NavItem
        icon="fas fa-folder-open"
        label="File Explorer"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToFileExplorer"
      />

      <NavItem
        icon="fas fa-code-branch"
        label="Git"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToGitView"
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
  emits: ['update:moreExpanded', 'close', 'overlay-open', 'overlay-close'],
  data() {
    return {
      primaryNavExpanded: true
    }
  },
  computed: {
    // True when the active project is in the UI store's pinned list
    isActiveProjectPinned() {
      return this.$storex.ui.isActiveProjectPinned
    }
  },
  methods: {
    // Single entry point for opening an app from this menu.
    // On desktop a multi-instance app (declared in config/apps.js) opens a NEW
    // tab each time so several instances can coexist — e.g. the Task Manager,
    // where each tab is a board. Every other case keeps the original behaviour:
    // setActiveTab focuses/creates the single desktop panel, or switches to the
    // app's own route in single/mobile mode.
    openApp(appKey) {
      if (this.$ui.isDesktopMode && isMultiInstance(appKey)) {
        // newInstance tells showApp to skip its per-key de-duplication and
        // create a brand-new panel (see store/ui.js → showApp).
        this.$ui.openApp({ appKey, payload: { newInstance: true } })
      } else {
        this.$ui.setActiveTab(appKey)
      }
      this.$emit('close')
    },
    // Pin/unpin the currently active project. Pins live in the UI store and are
    // persisted in localStorage (uiState), then surfaced by PinnedProjectsSwitcher.
    togglePinCurrentProject() {
      const project = this.$storex.projects.activeProject
      if (!project?.project_id) {
        this.$ui.addNotification({ text: 'No active project to pin', type: 'warning' })
        return
      }
      this.$ui.togglePinProject(project.project_id)
      this.$ui.addNotification({
        text: this.isActiveProjectPinned
          ? `Pinned ${project.project_name}`
          : `Unpinned ${project.project_name}`
      })
    },
    // Opens the global "New project" modal. The modal itself is rendered once
    // at the app root and driven by the ui store flag `newProject`.
    handleNewProject() {
      this.$ui.showNewProject(true)
      this.$emit('close')
    },
    handleNavigateToNewChat() {
      if (this.$ui.isDesktopMode) {
        this.$service.chat.newQuickChat()
      } else {
        this.$storex.$router.$navigation.apps.openHome()
      }
      this.$emit('close')
    },
    // Opens the project Activity Wall. The wall is registered as the home of
    // the mobile view (see App.vue) and as the "activity" app everywhere else.
    handleNavigateToActivity() {
      this.openApp('activity')
    },
    handleNavigateToKanban() {
      this.openApp('tasks')
    },
    handleNavigateToPlanning() {
      this.openApp('planning')
    },
    handleNavigateToMessenger() {
      this.openApp('messenger')
    },
    handleNavigateToMeet() {
      this.openApp('meet')
    },
    // Open the Team screen via the UI store opener, which routes through the
    // unified openApp() (dockview panel on desktop / route in single mode).
    handleNavigateToTeam() {
      this.$storex.ui.openTeams()
      this.$emit('close')
    },
    handleNavigateToFileExplorer() {
      this.openApp('file-explorer')
    },
    handleNavigateToGitView() {
      this.openApp('git-view')
    },
    handleNavigateToWiki() {
      this.openApp('wiki')
    },
    toggleCollapse() {
      this.$emit('toggle-collapse')
    }
  }
}
</script>