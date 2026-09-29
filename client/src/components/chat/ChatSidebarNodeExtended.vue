<script setup>
import ChatIcon from './ChatIcon.vue'
import ProjectIcon from '../ProjectIcon.vue'
import ChatNodeHoverPanel from './ChatNodeHoverPanel.vue'
import Modal from '../Modal.vue'
import moment from 'moment'
</script>

<template>
  <div class="w-full">
    <!-- Node Row -->
    <div
      class="relative group p-2 rounded-lg border-l-4 cursor-pointer transition-all"
      :class="[
        $chats.statusBorderColor(chat.status),
        selectedChatId === chat.id
          ? 'bg-warning/10'
          : 'hover:bg-base-200',
        isVisibleChat && 'ring-1 ring-warning/40'
      ]"
      @click="$emit('select', chat)"
    >
      <div class="flex gap-2">
        <!-- Left Icon Column -->
        <div class="flex flex-col items-center gap-1 shrink-0">
          <ProjectIcon
            :icon-only="true"
            :width="3"
            :project="$chats.getChatWorkingProject(chat)" />
          <div v-if="isUpdating">
            <span class="loading loading-bars loading-xs shrink-0 text-info"></span>
          </div>
          <ChatIcon v-else :mode="chat.mode" class="text-xs shrink-0" />
          <div :class="unreadCountReactive ? 'text-warning/60' : 'text-success/60'">
            <i class="fa-solid fa-check-double text-xs"></i>
          </div>
        </div>

        <!-- Content Area -->
        <div class="flex-1 min-w-0">
          <span class="text-xs font-medium truncate block">{{ chat.name }}</span>
          <div v-if="chat.description" class="text-xs text-base-content/50 line-clamp-1 mt-1">
            {{ chat.description }}
          </div>
          <div class="text-xs mt-1 text-base-content/40">
            [{{ lastMessageTime }}]
          </div>
        </div>
      </div>

      <!-- Action buttons (visible on hover) -->
      <div class="absolute right-1 top-1 hidden group-hover:flex gap-1 rounded p-0.5 bg-base-100">
        <button
          class="btn btn-xs btn-ghost p-1 h-auto min-h-0"
          title="Add subtask"
          @click.stop="$emit('add-subtask', chat)"
        >
          <i class="fa-solid fa-plus text-xs"></i>
        </button>
        <button
          class="btn btn-xs btn-ghost p-1 h-auto min-h-0 text-error"
          title="Delete"
          @click.stop="showDeleteConfirm = true"
        >
          <i class="fa-solid fa-trash text-xs"></i>
        </button>
      </div>

      <!-- Hover Floating Panel -->
      <div
        class="absolute left-full top-0 ml-2 z-50 pointer-events-none opacity-0 group-hover:opacity-100 group-hover:pointer-events-auto transition-opacity duration-150"
      >
        <ChatNodeHoverPanel
          :chat="chat"
          :allChats="allChats"
          @add-subtask="$emit('add-subtask', $event)"
          @delete-chat="showDeleteConfirm = true"
        />
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <Modal v-if="showDeleteConfirm" :close="true" @close="showDeleteConfirm = false">
      <template #header>
        <span class="text-base font-semibold text-white">Delete Chat</span>
      </template>

      <div class="space-y-4">
        <p class="text-sm text-white/70">
          Are you sure you want to delete <strong class="text-white">{{ chat.name }}</strong>?
        </p>
        <p class="text-xs text-white/50">
          This action cannot be undone. All messages and child chats will be permanently deleted.
        </p>
      </div>

      <template #footer>
        <button
          class="btn btn-sm btn-ghost"
          @click="showDeleteConfirm = false"
          :disabled="isDeleting"
        >
          Cancel
        </button>
        <button
          class="btn btn-sm btn-error"
          @click="confirmDelete"
          :disabled="isDeleting"
          :class="isDeleting && 'loading'"
        >
          <span v-if="!isDeleting">Delete Chat</span>
        </button>
      </template>
    </Modal>
  </div>
</template>

<script>
export default {
  name: 'ChatSidebarNodeExtended',
  props: {
    chatId: { type: String, required: true },
    allChats: { type: Array, default: () => [] },
    selectedChatId: { type: String, default: null }
  },
  emits: ['select', 'add-subtask', 'delete-chat'],
  data() {
    return {
      unreadCountCache: 0,
      visibleChatIds: new Set(),
      showDeleteConfirm: false,
      isDeleting: false
    }
  },
  computed: {
    chat() {
      return this.$chats.chats[this.chatId]
    },
    children() {
      return this.allChats.filter(c => c.parent_id === this.chat.id)
    },
    hasChildren() {
      return this.children.length > 0
    },
    isUpdating() {
      return this.$storex.chats.isChatUpdating(this.chat.id)
    },
    unreadCountReactive() {
      return this.calculateUnreadCount()
    },
    isVisibleChat() {
      return this.visibleChatIds.has(this.chat.id)
    },
    lastMessageTime() {
      const lastMessage = [...this.chat.messages].sort((a, b) => a.updated_at > b.updated_at ? -1: 1)[0] 
      const timestamp = lastMessage?.updated_at || this.chat.updated_at
      if (!timestamp) return ''
      
      const momentTime = moment(timestamp)
      const threeDaysAgo = moment().subtract(1, 'days')
      
      if (momentTime.isAfter(threeDaysAgo)) {
        return momentTime.format('hh:mm:ss')
      }
      
      return momentTime.format('MMM DD, YYYY')
    }
  },
  watch: {
    'chat.messages': {
      handler() {
        this.updateUnreadCount()
      },
      deep: true
    }
  },
  mounted() {
    this.updateVisibleChats()
    this.updateUnreadCount()
  },
  methods: {
    calculateUnreadCount() {
      const currentUsername = this.$user?.username
      if (!currentUsername) return 0
      
      return (this.chat.messages || []).filter(msg => {
        const isAssistantMsg = msg.role === 'assistant'
        const isOtherUser = msg.user !== currentUsername
        const isUnread = !msg.read_by || !msg.read_by.includes(currentUsername)
        return isAssistantMsg && isOtherUser && isUnread && !msg.hide
      }).length
    },
    updateUnreadCount() {
      this.unreadCountCache = this.calculateUnreadCount()
    },
    updateVisibleChats() {
      this.visibleChatIds.clear()
      
      const openApps = this.$storex?.ui?.openApps || {}
      Object.values(openApps).forEach(app => {
        if (app.tabId) {
          this.visibleChatIds.add(app.tabId)
        }
      })

      try {
        const chatId = this.$storex?.$router?.$navigation?.getChatId?.()
        if (chatId) {
          this.visibleChatIds.add(chatId)
        }
      } catch (error) {
        console.log('Could not get chat ID from router')
      }
    },
    async confirmDelete() {
      this.isDeleting = true
      try {
        await this.$storex.chats.deleteChat(this.chat)
        this.showDeleteConfirm = false
        this.$emit('delete-chat', this.chat)
      } catch (error) {
        console.error('Failed to delete chat:', error)
        this.$storex.ui.addNotification({
          text: 'Failed to delete chat',
          type: 'error'
        })
      } finally {
        this.isDeleting = false
      }
    }
  }
}
</script>