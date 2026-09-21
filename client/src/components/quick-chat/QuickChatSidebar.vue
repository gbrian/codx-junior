<script setup>
import CodxJuniorLogo from '@/components/CodxJuniorLogo.vue'
import ProjectDetailt from '@/components/ProjectDetailt.vue'
import RecentChatsQuickAccess from '@/components/chats/RecentChatsQuickAccess.vue'
</script>

<template>
  <aside class="flex flex-col h-full w-64 shrink-0 bg-[#1a1a1a] border-r border-white/5">
    <!-- Project Selector -->
    <div class="px-3 py-3 shrink-0">
      <ProjectDetailt
        :options="{ showIcon: true, showFolders: false, showSelector: true }"
        @select="$emit('project-selected', $event)"
      />
    </div>

    <!-- Primary Nav -->
    <nav class="px-2 flex flex-col gap-0.5 shrink-0">
      <button
        class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-white/80 hover:bg-white/8 hover:text-white transition-colors text-left w-full"
        @click="$emit('new-chat')"
      >
        <i class="fa-regular fa-pen-to-square w-5 text-center"></i>
        <span>New chat</span>
      </button>
    </nav>

    <!-- Chats list via RecentChatsQuickAccess -->
    <div class="flex-1 min-h-0 px-2 py-3 flex flex-col">
      <RecentChatsQuickAccess :collapsed="false" />
    </div>

    <!-- Footer -->
    <div class="shrink-0 border-t border-white/5 px-2 py-3 flex flex-col gap-0.5">
      <div class="flex items-center gap-3 px-3 py-2.5 rounded-xl">
        <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
          <i class="fa-solid fa-user text-primary text-xs"></i>
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-sm text-white font-medium truncate">{{ userName }}</div>
          <div class="text-xs text-white/30">Quick Chat</div>
        </div>
        <button
          class="p-1.5 text-white/30 hover:text-white/80 transition-colors"
          title="Settings"
          @click="$emit('settings')"
        >
          <i class="fa-regular fa-gear text-sm"></i>
        </button>
      </div>
    </div>
  </aside>
</template>

<script>
export default {
  props: {
    userName: { type: String, default: 'User' }
  },
  emits: ['new-chat', 'project-selected', 'settings']
}
</script>