<script setup>
import { computed } from 'vue'
import { $storex } from '@/store'
import QuickChatView from './QuickChatView.vue'
import MobileChatsView from '@/components/mobile/MobileChatsView.vue'

// "/:projectName/chats" is the mobile inbox; on desktop the same URL keeps the
// existing quick-chat surface (the desktop app normally opens chats as panels,
// but the route must remain valid for deep links and single-mode windows).
const isMobile = computed(() => $storex.ui.isMobile)
</script>

<template>
  <MobileChatsView v-if="isMobile" />
  <QuickChatView v-else />
</template>
