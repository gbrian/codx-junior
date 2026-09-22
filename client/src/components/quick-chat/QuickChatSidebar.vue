<script setup>
import RecentChatsQuickAccess from '@/components/chats/RecentChatsQuickAccess.vue'
import WorkspaceAppSelector from './WorkspaceAppSelector.vue'
</script>

<template>
  <!-- ── Desktop sidebar ── -->
  <aside
    v-if="!isMobile"
    ref="sidebarEl"
    class="flex flex-col h-full shrink-0 bg-[#1a1a1a] border-r border-white/5 transition-all duration-200"
    :class="isCollapsed ? 'w-16' : 'w-64'"
  >
    <!-- Primary Nav -->
    <nav class="px-2 pt-3 flex flex-col gap-0.5 shrink-0">
      <!-- Collapse toggle button -->
      <button
        class="flex items-center justify-center gap-3 px-3 py-2.5 rounded-xl text-sm text-white/60 hover:bg-white/8 hover:text-white transition-colors w-full"
        :title="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="toggleCollapse"
      >
        <i :class="isCollapsed ? 'fas fa-chevron-right' : 'fas fa-chevron-left'" class="w-5 text-center shrink-0"></i>
        <span v-if="!isCollapsed" class="text-xs">Collapse</span>
      </button>

      <!-- New chat button -->
      <button
        class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-white/80 hover:bg-white/8 hover:text-white transition-colors text-left w-full"
        :class="isCollapsed ? 'justify-center' : ''"
        :title="isCollapsed ? 'New chat' : ''"
        @click="$emit('new-chat')"
      >
        <i class="fas fa-pen-to-square w-5 text-center shrink-0"></i>
        <span v-if="!isCollapsed">New chat</span>
      </button>
    </nav>

    <!-- Workspace App Selector -->
    <div v-if="true || workspaceApps.length > 0" class="shrink-0 border-t border-white/5 py-2">
      <WorkspaceAppSelector
        :is-collapsed="isCollapsed"
        :selected-app="selectedWorkspaceApp"
        :workspace-apps="workspaceApps"
        @select-app="$emit('select-workspace-app', $event)"
        class="ml-2"
        v-if="activeChat"
      />
    </div>

    <!-- Chats list -->
    <div class="grow overflow-hidden">
      <RecentChatsQuickAccess 
        :collapsed="isCollapsed"
        @select="$emit('open-chat', $event)"
      />
    </div>

    <!-- Footer -->
    <div class="shrink-0 border-t border-white/5 px-2 py-3 flex flex-col gap-0.5">
      <div
        class="flex items-center gap-3 px-3 py-2.5 rounded-xl"
        :class="isCollapsed ? 'justify-center' : ''"
      >
        <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
          <i class="fas fa-user text-primary text-xs"></i>
        </div>
        <template v-if="!isCollapsed">
          <div class="flex-1 min-w-0">
            <div class="text-sm text-white font-medium truncate">{{ userName }}</div>
            <div class="text-xs text-white/30">Quick Chat</div>
          </div>
          <button
            class="p-1.5 text-white/30 hover:text-white/80 transition-colors"
            title="Settings"
            @click="$emit('settings')"
          >
            <i class="fas fa-gear text-sm"></i>
          </button>
        </template>
      </div>

      <!-- Settings button (visible when collapsed) -->
      <button
        v-if="isCollapsed"
        class="flex items-center justify-center px-3 py-2.5 rounded-xl text-white/30 hover:text-white/80 transition-colors"
        title="Settings"
        @click="$emit('settings')"
      >
        <i class="fas fa-gear text-sm"></i>
      </button>
    </div>
  </aside>

  <!-- ── Mobile bottom navigation bar ── -->
  <nav
    v-else
    class="fixed bottom-0 left-0 right-0 z-50 flex items-center justify-around bg-[#1a1a1a] border-t border-white/10 px-2 py-2 safe-area-bottom"
  >
    <button
      class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl text-white/50 hover:text-white transition-colors"
      @click="$emit('new-chat')"
    >
      <i class="fas fa-pen-to-square text-lg"></i>
      <span class="text-[10px]">New</span>
    </button>

    <button
      class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl transition-colors"
      :class="showMobileChats ? 'text-primary' : 'text-white/50 hover:text-white'"
      @click="$emit('toggle-mobile-chats')"
    >
      <i class="fas fa-comments text-lg"></i>
      <span class="text-[10px]">Chats</span>
    </button>

    <button
      class="flex flex-col items-center gap-0.5 px-4 py-1.5 rounded-xl text-white/50 hover:text-white transition-colors"
      @click="$emit('account-settings')"
    >
      <div class="w-6 h-6 rounded-full bg-primary/30 flex items-center justify-center">
        <i class="fas fa-user text-xs text-primary"></i>
      </div>
      <span class="text-[10px]">Account</span>
    </button>
  </nav>
</template>

<script>
export default {
  props: {
    userName: { type: String, default: 'User' },
    showMobileChats: { type: Boolean, default: false },
    workspaceApps: { type: Array, default: () => [] },
    selectedWorkspaceApp: { type: Object, default: null },
    activeChat: { type: Object, default: null }
  },
  emits: ['new-chat', 'settings', 'toggle-mobile-chats', 'account-settings', 'select-workspace-app', 'open-chat'],
  data() {
    return {
      isCollapsed: false,
      userCollapsed: false,
      resizeObserver: null
    }
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    }
  },
  mounted() {
    this.$nextTick(() => this.setupResizeObserver())
  },
  beforeUnmount() {
    this.resizeObserver?.disconnect()
  },
  methods: {
    setupResizeObserver() {
      const el = this.$refs.sidebarEl
      if (!el) return
      const parent = el.parentElement
      if (!parent) return
      this.resizeObserver = new ResizeObserver(([entry]) => {
        const width = entry.contentRect.width
        if (!this.userCollapsed) {
          this.isCollapsed = width < 600
        }
      })
      this.resizeObserver.observe(parent)
    },
    toggleCollapse() {
      this.userCollapsed = !this.userCollapsed
      this.isCollapsed = this.userCollapsed
    }
  }
}
</script>