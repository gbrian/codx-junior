<script setup>
import Chat from '@/components/chat/Chat.vue'
import MemberAvatar from '@/components/teams/MemberAvatar.vue'
</script>

<template>
  <div class="flex flex-col h-full overflow-hidden">
    <!-- DM header -->
    <div class="flex items-center gap-3 px-4 py-2 border-b border-base-content/10 bg-base-200/50 shrink-0">
      <MemberAvatar :member="member" size="xs" :show-status="true" />
      <div>
        <span class="font-bold text-sm">{{ member.username }}</span>
        <span class="text-xs text-base-content/50 ml-2 capitalize">{{ member.role }}</span>
      </div>
      <div class="ml-auto flex items-center gap-1">
        <span class="badge badge-xs" :class="statusBadgeClass">
          {{ member.status }}
        </span>
      </div>
    </div>

    <!-- DM chat -->
    <div class="flex-1 min-h-0 overflow-hidden">
      <Chat
        v-if="chat"
        class="flex-1 min-w-0 p-2 h-full"
        :chat="chat"
      />
      <div v-else class="flex-1 flex items-center justify-center text-base-content/40 h-full">
        <span class="loading loading-spinner"></span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TeamDM',
  props: {
    params: { type: Object, default: () => ({}) }
  },
  data() {
    return {
      chat: null
    }
  },
  computed: {
    member() {
      return this.params?.member || {}
    },
    team() {
      return this.params?.team || null
    },
    statusBadgeClass() {
      const map = { online: 'badge-success', away: 'badge-warning', busy: 'badge-error', offline: 'badge-ghost' }
      return map[this.member?.status] || 'badge-ghost'
    }
  },
  created() {
    this.loadChat()
  },
  methods: {
    async loadChat() {
      const chatId = this.params?.chatId
      if (!chatId) return
      const cached = this.$chats.chats[chatId]
      if (cached) {
        this.chat = cached
      } else {
        const loaded = await this.$chats.loadChat({ id: chatId })
        this.chat = this.$chats.chats[chatId] || loaded
      }
    }
  }
}
</script>