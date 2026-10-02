<script setup>
import ChatProjectIcon from '../ChatProjectIcon.vue'
</script>

<template>
  <div
    @click="$emit('select', chat)"
    class="card card-compact bg-white/5 border border-base-content/10 hover:border-codx-primary/50 hover:bg-white/10 cursor-pointer transition-all duration-200 p-2 gap-1"
    :class="[
      isActive ? 'border-codx-primary bg-codx-primary/10' : '',
      isVisible && 'border-warning border-2'
    ]"
  >
    <!-- Name and status -->
    <div class="flex items-center gap-2 min-w-0 tooltip" :data-tip="chat.name">
      <ChatProjectIcon :icon-only="true" :width="5" :chat="chat" />
      <h3 class="font-semibold text-xs truncate ">{{ chat.name || 'Untitled' }}</h3>
      <div :class="hasUnreadMessages ? 'text-warning/60' : 'text-success/60'" class="shrink-0">
        <i class="fa-solid fa-check-double text-xs"></i>
      </div>
      <div v-if="unreadCount > 0" class="badge badge-xs badge-error shrink-0">{{ unreadCount }}</div>
    </div>

    <!-- Message snippet -->
    <div v-if="messageSnippet" class="text-xs text-base-content/50 line-clamp-1 leading-relaxed">
      {{ messageSnippet }}
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatRecentItem',
  props: {
    chat: { type: Object, required: true },
    isActive: { type: Boolean, default: false },
    isVisible: { type: Boolean, default: false },
    unreadCount: { type: Number, default: 0 }
  },
  emits: ['select'],
  data() {
    return {
      messageUpdateCounter: 0
    }
  },
  computed: {
    hasUnreadMessages() {
      // Force dependency on messageUpdateCounter
      this.messageUpdateCounter
      
      const currentUsername = this.$user.username
      
      return (this.chat.messages || []).some(msg => {
        const isOthersMessage = msg.user !== currentUsername
        const isUnread = !msg.read_by || !msg.read_by.includes(currentUsername)
        return isOthersMessage && isUnread && !msg.hide
      })
    },
    messageSnippet() {
      // Force dependency on messageUpdateCounter
      this.messageUpdateCounter
      
      if (!this.chat.messages || this.chat.messages.length === 0) {
        return ''
      }

      const messagesWithContent = [...this.chat.messages]
        .reverse()
        .filter(m => m.content || m.think)

      if (messagesWithContent.length === 0) {
        return ''
      }

      const lastMsg = messagesWithContent[0]
      const snippet = lastMsg.content || lastMsg.think || ''
      return snippet.length > 50 ? snippet.substring(0, 50).trim() + '...' : snippet
    }
  },
  watch: {
    'chat.messages': {
      handler() {
        this.messageUpdateCounter++
      },
      deep: true
    }
  }
}
</script>