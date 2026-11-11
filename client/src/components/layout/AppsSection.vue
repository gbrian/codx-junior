<script setup>
import NavItem from './NavItem.vue'
import ProjectDetailt from '../ProjectDetailt.vue'
import ViewModeToggle from './ViewModeToggle.vue'
import PinnedProjectsSwitcher from './PinnedProjectsSwitcher.vue';
import { isMultiInstance } from '@/config/apps'
import { isOpenInNewTabEvent, openProjectInNewTab } from '@/utils/projectLinks'
</script>

<template>
  <div class="px-2 py-3 shrink-0 border-b border-base-content/5">
    <div class="flex gap-2 pb-1 min-w-0">  
      
      <!-- Project selector -->
      <ProjectDetailt 
        v-if="!isCollapsed"
        class="flex-1 min-w-0"
        @click.stop=""
        :options="{ folders: true, showIcon: true }"
        @select="onProjectSelected"
        @open="$emit('overlay-open')"
        @close="$emit('overlay-close')"
      />

      <!-- Pin / unpin the active project (quick switcher) -->
      <button
        v-if="!isCollapsed"
        class="btn tooltip tooltip-right shrink-0"
        :class="isActiveProjectPinned ? 'click text-primary' : 'click text-base-content/50'"
        :data-tip="isActiveProjectPinned ? 'Unpin project' : 'Pin project'"
        :aria-pressed="isActiveProjectPinned"
        aria-label="Pin project"
        @click.stop="togglePinCurrentProject"
      >
        <i class="fa-solid fa-thumbtack text-xs"></i>
      </button>

      <ViewModeToggle v-if="!isCollapsed"
        class="shrink-0" />
          
    </div>

    <!-- Pinned projects quick switcher (icons only while the rail is collapsed) -->
    <PinnedProjectsSwitcher 
      v-if="!isCollapsed"
      @select="onProjectSelected"
    />

    <button
      v-if="!isCollapsed"
      class="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-base-content/60 hover:text-base-content/80 transition-colors"
      @click="primaryNavExpanded = !primaryNavExpanded"
      title="Toggle Primary Navigation"
    >
      APPS
      <i :class="primaryNavExpanded ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'" class="text-xs"></i>
    </button>

    <!-- Single, unfiltered application launcher: every option is always
         visible, whatever the user's workspace mode is. -->
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

      <!-- Cross-project management dashboard: what is happening, what is
           stuck and when it ships — across EVERY project, with a time filter
           (last 7 days by default), blockers, delivery forecast, team load and
           AI cost. Opens a panel on desktop, the
           "/:projectName/management-dashboard" route otherwise (config/apps.js). -->
      <NavItem
        icon="fas fa-table-columns"
        label="Management"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToManagementDashboard"
      />

      <!-- Native harness observability: runs, worker/watchdog health and the
           audit journal of every piece of work handled by @codx-junior. -->
      <NavItem
        icon="fas fa-bolt"
        label="Harness"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToHarness"
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

      <!-- Company: the top-level hybrid organization (org chart, teams of
           humans + AI profiles, linked projects, missions and autonomy). -->
      <NavItem
        icon="fas fa-building-columns"
        label="Company"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToCompany"
      />

      <NavItem
        icon="fas fa-folder-open"
        label="File Explorer"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToFileExplorer"
      />

      <!-- Running Chromium sessions shared by the user and the AI. Opens the
           session manager (list + live co-browsing view) on desktop and the
           "/:projectName/browsers" route in single / mobile mode. -->
      <NavItem
        icon="fa-regular fa-compass"
        label="Computer sessions"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToBrowserSessions"
      />

      <NavItem
        icon="fas fa-code-branch"
        label="Git"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToGitView"
      />

      <!-- `/api/infra/*` is admin-only, including the container shell. Hide the
           entry for other roles instead of opening a view that can only 403. -->
      <NavItem
        v-if="$users.isAdmin"
        icon="fas fa-server"
        label="Infrastructure"
        :is-collapsed="isCollapsed"
        @click="handleNavigateToInfra"
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
    // Project selector → switch the ACTIVE PROJECT IN PLACE.
    //
    // The switch is fully store-driven: `activeProjectChanged` reloads the
    // project's settings, chats, models and boards while the shell (sidebar +
    // desktop layout) stays mounted. It must never end in a URL/route change:
    // navigating to "/<project_name>" leaves the desktop shell and reloads the
    // document, which is exactly what we don't want when just picking another
    // project.
    //
    // Ctrl/Cmd+click (or middle click) is the browser's "open in a new tab"
    // gesture: the project then opens in ANOTHER tab and the current one keeps
    // running untouched (see utils/projectLinks.js).
    async onProjectSelected(project, event) {
      if (!project?.project_id) {
        this.$ui.addNotification({ text: 'Invalid project', type: 'error' })
        return
      }

      // New tab gesture → never touch the current tab, not even when the
      // project is already the active one.
      if (isOpenInNewTabEvent(event)) {
        openProjectInNewTab(project)
        this.$emit('close')
        return
      }

      // Selecting the project that is already active is a no-op, not a reload.
      if (project.project_id === this.$storex.projects.activeProject?.project_id) {
        this.$emit('close')
        return
      }

      window.location.href = `${window.location.origin}/${project.project_name}`
    },
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
        // "New" is the composer, not the management dashboard. This is the
        // mobile entry point and the single-mode entry point alike.
        this.$storex.$router.$navigation.apps.openNewChat()
      }
      this.$emit('close')
    },
    handleNavigateToKanban() {
      this.openApp('tasks')
    },
    handleNavigateToPlanning() {
      this.openApp('planning')
    },
    // Opens the cross-project management dashboard. It is registered as
    // 'management-dashboard' in config/apps.js, so this single call opens a
    // dockview panel on desktop and navigates to
    // "/:projectName/management-dashboard" in single / mobile mode.
    handleNavigateToManagementDashboard() {
      this.openApp('management-dashboard')
    },
    // Opens the native harness observability view (runs, worker/watchdog
    // health, audit journal). Registered as 'harness' in config/apps.js.
    handleNavigateToHarness() {
      this.openApp('harness')
    },
    handleNavigateToCompany() {
      this.openApp('company')
      this.$emit('close')
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
    // Opens the co-browsing session manager so the user can create, inspect,
    // open, restart or delete the Chromium sessions shared with the AI.
    handleNavigateToBrowserSessions() {
      this.openApp('browser-sessions')
    },
    handleNavigateToGitView() {
      this.openApp('git-view')
    },
    // Docker infrastructure (containers, compose stacks, images, volumes,
    // networks, daemon events). Uses the same unified opener as the other
    // entries: a dockview panel on desktop, "/:projectName/infra" in
    // single / mobile mode (see config/apps.js → infra).
    // NOTE: `/api/infra/*` is admin-only on the backend; gate this NavItem with
    // v-if="$users.isProjectAdmin" once the role is enforced server-side.
    handleNavigateToInfra() {
      this.openApp('infra')
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
