<script setup>
import AppsSection from './AppsSection.vue'
import WorkspacesSection from './WorkspacesSection.vue'
import Notifications from '../Notifications.vue'
import WindowsMenu from '../main-menu/WindowsMenu.vue'
import RecentsSection from './RecentsSection.vue'
</script>

<template>
  <!-- Mobile Overlay & Sidebar Container -->
  <div v-if="isMobile" class="pointer-events-none">
    <!-- Mobile Overlay -->
    <div
      v-if="!isCollapsed"
      class="fixed inset-0 z-40 backdrop-blur-sm animate-fade-in pointer-events-auto"
      @click="handleClose"
    ></div>

    <!-- Mobile Sidebar (always the full panel, floats in from the left) -->
    <aside
      ref="sidebarEl"
      class="fixed left-0 top-0 bottom-0 z-50 w-64 flex flex-col h-full shrink-0 bg-base-100 border-r border-base-content/5 pointer-events-auto"
      :style="{
        transform: isCollapsed ? 'translateX(-100%)' : 'translateX(0)',
        transition: 'transform 0.3s ease-out'
      }"
    >
      <!-- Header Section -->
      <div class="px-3 py-4 shrink-0 border-b border-base-content/5">
        <div class="flex items-center justify-between gap-2">
          <button
            class="click w-6 h-6 rounded border border-base-content/20 flex items-center justify-center hover:bg-white/5 transition-colors"
            @click="handleClose"
            title="Close sidebar"
          >
            <i class="fa-solid fa-angle-left text-base-content/40 text-xs"></i>
          </button>
          <span class="text-lg font-semibold">
            <span class="text-codx-secondary">codx-</span>
            <span class="text-codx-secondary">junior</span>
          </span>
        </div>
      </div>

      <!-- Scrollable Content Area -->
      <div class="flex-1 overflow-y-auto flex flex-col">
        <!-- Apps Section -->
        <AppsSection
          :is-collapsed="false"
          :more-expanded="moreExpanded"
          @update:moreExpanded="moreExpanded = $event"
          @close="handleClose"
          @toggle-collapse="toggleCollapse"
        />
        
        <!-- Workspaces Section -->
        <WorkspacesSection
          :workspace-apps="workspaceApps"
          :is-collapsed="false"
          :current-workspace-id="currentWorkspaceId"
          @close="handleClose"
        />

      </div>

      <!-- Footer -->
      <div class="shrink-0 border-t border-base-content/5 px-2 py-3">
        <WindowsMenu @close="handleClose">
          <div class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors cursor-pointer w-full">
            <div class="avatar tooltip shrink-0" :data-tip="$user.username">
              <div class="w-8 rounded-full overflow-hidden">
                <img :src="$user.avatar">
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm truncate">{{ userName }}</div>
              <div class="text-xs text-base-content/40 truncate">{{ userSubtitle }}</div>
            </div>
            <i class="fas fa-chevron-down text-xs text-base-content/30 shrink-0"></i>
          </div>
        </WindowsMenu>
      </div>
    </aside>
  </div>

  <!-- Desktop Sidebar -->
  <!-- The WRAPPER lives in normal flow and owns the layout width:
       w-20 when collapsed (rail), w-64 when pinned (expanded).
       The <aside> inside is absolute, so on hover it can float to w-64 and
       overlap the neighbour WITHOUT shifting it. When pinned, the wrapper is
       also w-64 so the aside occupies real flow space. -->
  <div
    v-else
    ref="sidebarEl"
    class="relative h-full shrink-0 transition-all duration-200"
    :class="[isCollapsed ? 'w-20' : 'w-64']"
    @mouseenter="onSidebarMouseEnter"
    @mouseleave="onSidebarMouseLeave"
  >
    <aside
      class="absolute left-0 top-0 bottom-0 h-full flex flex-col shrink-0 bg-base-100 border-r border-base-content/5 transition-all duration-200"
      :class="[
        sidebarCollapsed ? 'w-20' : 'w-64',
        isFloating && 'z-50 shadow-2xl'
      ]"
    >
      <!-- Header Section -->
      <div class="px-3 py-4 shrink-0 border-b border-base-content/5">
        <div class="flex items-center justify-between gap-2">
          <div v-if="!sidebarCollapsed" class="flex items-center shrink-0 gap-2 flex-1">
            <!-- Floating: Pin (keep open) · Pinned: Collapse (back to rail) -->
            <button
              class="click w-6 h-6 rounded border border-base-content/20 flex items-center justify-center hover:bg-white/5 transition-colors"
              @click="onHeaderToggle"
              :title="isFloating ? 'Pin sidebar' : 'Collapse sidebar'"
            >
              <i
                class="text-base-content/40 text-xs"
                :class="isFloating ? 'fa-solid fa-thumbtack' : 'fa-solid fa-angle-left'"
              ></i>
            </button>
            <span class="text-lg font-semibold">
              <span class="text-codx-secondary">codx-</span>
              <span class="text-codx-secondary">junior</span>
            </span>
          </div>
          <div v-else class="flex justify-center w-full">
            <button
              class="click w-6 h-6 flex items-center justify-center hover:bg-white/5 transition-colors"
              title="Expand sidebar"
              @click="toggleCollapse()"
            >
              <img class="w-full" src="/only_icon.png" />
            </button>
          </div>

          <div v-if="!sidebarCollapsed" class="flex items-center gap-2">
            <Notifications />
          </div>        
        </div>
      </div>

      <!-- Scrollable Content Area -->
      <div class="flex-1 overflow-y-auto flex flex-col">
        <!-- Apps Section -->
        <AppsSection
          :is-collapsed="sidebarCollapsed"
          :more-expanded="moreExpanded"
          @update:moreExpanded="moreExpanded = $event"
          @close="handleClose"
          @toggle-collapse="toggleCollapse"
          @overlay-open="onOverlayOpen"
          @overlay-close="onOverlayClose"
        />
        
        <!-- Workspaces Section -->
        <WorkspacesSection
          :workspace-apps="workspaceApps"
          :is-collapsed="sidebarCollapsed"
          :current-workspace-id="currentWorkspaceId"
          @close="handleClose"
        />

        <RecentsSection
          @select-chat="handleSelectChat"
        />

      </div>

      <!-- Footer -->
      <div class="shrink-0 border-t border-base-content/5 px-2 py-3">
        <!-- Expanded Footer - opens the unified Windows-like menu -->
        <WindowsMenu v-if="!sidebarCollapsed" @open="onOverlayOpen" @close="onOverlayClose">
          <div class="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors cursor-pointer w-full">
            <div class="avatar tooltip shrink-0" :data-tip="$user.username">
              <div class="w-8 rounded-full overflow-hidden">
                <img :src="$user.avatar">
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm truncate">{{ userName }}</div>
              <div class="text-xs"
                :class="connected ? 'text-success/60': 'text-error'"
              >{{ connected ? 'online': 'offline' }}</div>
            </div>
            <i class="fas fa-chevron-down text-xs text-base-content/40 shrink-0"></i>
          </div>
        </WindowsMenu>

        <!-- Collapsed Footer - Icon Only -->
        <div v-else class="flex items-center justify-center py-2">
          <WindowsMenu @open="onOverlayOpen" @close="onOverlayClose">
            <div class="p-1 rounded-full hover:bg-white/5 transition-colors cursor-pointer">
              <div class="avatar tooltip tooltip-right" :data-tip="$user.username">
                <div class="w-8 rounded-full overflow-hidden">
                  <img :src="$user.avatar">
                </div>
              </div>
            </div>
          </WindowsMenu>
        </div>
      </div>
    </aside>
  </div>
</template>

<script>
export default {
  props: {
    isMobile: { type: Boolean, default: false },
    isMobileExpanded: { type: Boolean, default: false }
  },
  emits: ['settings', 'close'],
  data() {
    return {
      dailyLimitStatus: 'normal',
      moreExpanded: false,
      // True while hovering a collapsed desktop sidebar (temporary float, not persisted)
      isHoverExpanded: false,
      // Number of overlays (modal/menu) launched from the sidebar that are currently open.
      // While > 0 the sidebar stays expanded so the launcher (and its state) is not unmounted.
      overlayInteractions: 0
    }
  },
  computed: {
    isCollapsed() {
      return this.$storex.ui.sidebarCollapsed
    },
    // True while an overlay launched from the sidebar is open
    isInteracting() {
      return this.overlayInteractions > 0
    },
    // Content of the aside is "expanded" when pinned, hovering the collapsed rail,
    // or while an overlay launched from it is still open.
    sidebarCollapsed() {
      return this.isCollapsed && !this.isHoverExpanded && !this.isInteracting
    },
    // Collapsed rail that is temporarily floated open (hover or active overlay)
    isFloating() {
      return this.isCollapsed && (this.isHoverExpanded || this.isInteracting)
    },
    workspaceApps() {
      return this.$projects.projectApps || []
    },
    currentUser() {
      return this.$storex?.users?.user || this.$user
    },
    hasWorkspaceApps() {
      return this.workspaceApps && this.workspaceApps.length > 0
    },
    isProjectAdmin() {
      return this.$users?.isProjectAdmin || false
    },
    currentWorkspaceId() {
      return this.$storex.$router.$navigation.getWorkspaceId()
    },
    isDesktopMode() {
      return this.$storex.$router.$navigation.isDesktopMode
    },
    userName() { 
      return this.$users.user?.username 
    },
    userSubtitle() {
      const email = this.$users.user?.email
      return email && email.length > 20 ? email.substring(0, 20) + '...' : email
    },
    connected() {
      return this.$session.connected
    }
  },
  watch: {
    isMobileExpanded(val) {
      if (this.isMobile) {
        this.$storex.ui.setSidebarCollapsed(!val)
      }
    }
  },
  methods: {
    toggleCollapse() {
      this.$storex.ui.setSidebarCollapsed(!this.isCollapsed)
    },
    // "Pin" the temporarily floated sidebar so it occupies real layout space
    pinSidebar() {
      this.$storex.ui.setSidebarCollapsed(false)
    },
    // Header button: pin when floating, collapse when pinned
    onHeaderToggle() {
      if (this.isFloating) {
        this.pinSidebar()
      } else {
        this.toggleCollapse()
      }
    },
    // Only float-expand on hover when the sidebar is actually collapsed,
    // so a user-pinned (expanded) sidebar is never disturbed.
    onSidebarMouseEnter() {
      if (this.isCollapsed) {
        this.isHoverExpanded = true
      }
    },
    onSidebarMouseLeave() {
      this.isHoverExpanded = false
    },
    // Called when an overlay launched from the sidebar opens/closes.
    // Keeps the sidebar expanded while any such overlay is open.
    onOverlayOpen() {
      this.overlayInteractions++
    },
    onOverlayClose() {
      this.overlayInteractions = Math.max(0, this.overlayInteractions - 1)
    },
    handleClose() {
      if (this.isMobile) {
        this.$storex.ui.setSidebarCollapsed(true)
      }
      this.$emit('close')
    },
    handleSelectChat(chat) {
      this.$chats.setActiveChat(chat)
      if (this.isMobile) {
        this.handleClose()
      }
    }
  }
}
</script>

<style scoped>
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.animate-fade-in {
  animation: fadeIn 0.2s ease-out forwards;
}
</style>