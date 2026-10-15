<script setup>
import { WALL_NAV } from './wallKinds'
</script>

<template>
  <!--
    Activity Wall — its own bottom bar (mobile only).

    Above `md` the wall uses the left rail (WallNav.vue); below `md` that rail is
    hidden and this bar takes over. The Menu entry opens the app sidebar through
    the single ui-store flag (`$storex.ui.expandSidebar()`), the same source of
    truth App.vue and DesktopSidebar share, so the sidebar and its backdrop stay
    in sync.
  -->
  <nav
    class="md:hidden fixed bottom-0 inset-x-0 z-40 flex items-stretch justify-around bg-base-300 border-t border-base-content/10 safe-area-bottom"
    aria-label="Activity navigation"
  >
    <!-- App sidebar -->
    <button
      class="flex-1 min-w-0 flex flex-col items-center gap-1 px-1 py-2 text-base-content/50 transition-colors"
      @click="$storex.ui.expandSidebar()"
      aria-label="Open sidebar"
    >
      <i class="fa-solid fa-bars text-lg"></i>
      <span class="text-[10px] truncate w-full text-center">Menu</span>
    </button>

    <button
      v-for="item in nav"
      :key="item.key"
      class="relative flex-1 min-w-0 flex flex-col items-center gap-1 px-1 py-2 transition-colors"
      :class="route === item.key ? 'text-primary' : 'text-base-content/50'"
      :aria-current="route === item.key ? 'page' : undefined"
      :title="item.label"
      @click="$emit('action', 'nav', item)"
    >
      <i :class="item.icon" class="text-lg"></i>
      <span class="text-[10px] truncate w-full text-center">{{ item.label }}</span>
      <span
        v-if="badgeFor(item.key)"
        class="badge badge-primary badge-xs absolute top-1 right-1"
      >{{ badgeFor(item.key) }}</span>
    </button>
  </nav>
</template>

<script>
export default {
  props: {
    route: { type: String, default: 'home' },
    notifications: { type: Number, default: 0 },
    messages: { type: Number, default: 0 }
  },
  emits: ['action'],
  data() {
    // Only the core destinations belong on the small bottom bar; the rest
    // (Bookmarks / Profile) stay reachable from the left rail and the header.
    return {
      nav: WALL_NAV.filter(n => ['home', 'explore', 'notifications', 'messages'].includes(n.key))
    }
  },
  methods: {
    badgeFor(key) {
      if (key === 'notifications') return this.notifications
      if (key === 'messages') return this.messages
      return 0
    }
  }
}
</script>