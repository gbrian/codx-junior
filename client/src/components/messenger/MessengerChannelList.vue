<script setup>
import moment from 'moment'
</script>

<template>
  <div class="flex flex-col h-full" :class="isCollapsed ? 'w-16' : 'w-72'" style="transition: width 0.2s">

    <!-- ── Header ── -->
    <div class="shrink-0 flex items-center gap-2 px-3 py-3 border-b border-base-content/10">
      <button
        class="flex items-center justify-center w-8 h-8 rounded-lg text-base-content/60 hover:text-base-content hover:bg-base-content/5 transition-colors shrink-0"
        :title="isCollapsed ? 'Expand' : 'Collapse'"
        @click="$emit('toggle-collapse')"
      >
        <i :class="isCollapsed ? 'fas fa-chevron-right' : 'fas fa-chevron-left'" class="text-xs"></i>
      </button>
      <template v-if="!isCollapsed">
        <span class="text-sm font-semibold text-base-content flex-1">Channels</span>
        <button
          class="flex items-center justify-center w-8 h-8 rounded-lg text-base-content/60 hover:text-base-content hover:bg-base-content/5 transition-colors"
          title="New channel"
          @click="$emit('new-group')"
        >
          <i class="fas fa-plus text-sm"></i>
        </button>
      </template>
      <button
        v-else
        class="flex items-center justify-center w-8 h-8 rounded-lg text-base-content/60 hover:text-base-content hover:bg-base-content/5 transition-colors"
        title="New channel"
        @click="$emit('new-group')"
      >
        <i class="fas fa-plus text-xs"></i>
      </button>
    </div>

    <!-- ── Search (expanded only) ── -->
    <div v-if="!isCollapsed" class="shrink-0 px-3 py-2 border-b border-base-content/10">
      <div class="flex items-center gap-2 bg-base-content/5 border border-base-content/10 rounded-lg px-3 py-2 focus-within:border-primary/50 transition-colors">
        <i class="fas fa-magnifying-glass text-base-content/50 text-xs shrink-0"></i>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search channels..."
          aria-label="Search channels"
          class="bg-transparent text-xs text-base-content placeholder:text-base-content/40 outline-none flex-1 min-w-0"
        />
        <button
          v-if="searchQuery"
          class="text-base-content/50 hover:text-base-content transition-colors"
          title="Clear search"
          @click="searchQuery = ''"
        >
          <i class="fas fa-xmark text-xs"></i>
        </button>
      </div>
    </div>

    <!-- ── Channel List ── -->
    <div class="flex-1 overflow-y-auto min-h-0 py-2">

      <!-- Loading -->
      <div v-if="loading" class="flex justify-center py-6">
        <span class="loading loading-spinner loading-sm text-base-content/40"></span>
      </div>

      <!-- Empty state -->
      <div v-else-if="filteredGroups.length === 0" class="flex flex-col items-center justify-center py-10 px-4 gap-3 text-base-content/50">
        <i class="fas fa-hashtag text-3xl"></i>
        <span v-if="!isCollapsed" class="text-xs text-center">
          {{ searchQuery ? 'No channels match your search' : 'No channels yet.\nClick + to create one.' }}
        </span>
      </div>

      <!-- Channel items -->
      <template v-else>
        <!-- Collapsed: show avatar icons -->
        <div v-if="isCollapsed" class="flex flex-col items-center gap-2 px-2">
          <button
            v-for="chat in filteredGroups"
            :key="chat.id"
            class="relative flex items-center justify-center w-10 h-10 rounded-xl text-xs font-bold transition-all duration-200"
            :class="activeChat?.id === chat.id
              ? 'bg-primary text-primary-content shadow-md ring-2 ring-primary/30'
              : 'bg-base-content/10 text-base-content/70 hover:bg-base-content/20 hover:text-base-content'"
            :title="chat.name"
            @click="$emit('select', chat)"
          >
            <span>{{ getInitials(chat.name) }}</span>
            <span
              v-if="unreadCount(chat) > 0"
              class="absolute -top-1 -right-1 min-w-[18px] h-[18px] rounded-full bg-primary text-primary-content text-[9px] font-bold flex items-center justify-center px-1"
            >{{ unreadLabel(chat) }}</span>
          </button>
        </div>

        <!-- Expanded: full channel rows -->
        <div v-else class="flex flex-col gap-0.5 px-2">
          <button
            v-for="chat in filteredGroups"
            :key="chat.id"
            class="flex items-center gap-3 px-3 py-2.5 rounded-xl text-left w-full transition-colors duration-150 group"
            :class="activeChat?.id === chat.id
              ? 'bg-primary/15 text-base-content ring-1 ring-primary/30'
              : 'text-base-content/70 hover:bg-base-content/5 hover:text-base-content'"
            :aria-current="activeChat?.id === chat.id ? 'true' : 'false'"
            @click="$emit('select', chat)"
          >
            <!-- Hash icon or avatar -->
            <div
              class="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold"
              :class="activeChat?.id === chat.id ? 'bg-primary/30 text-primary' : 'bg-base-content/10 text-base-content/70'"
            >
              {{ getInitials(chat.name) }}
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between gap-2">
                <span class="text-sm font-medium truncate">{{ chat.name }}</span>
                <span class="text-[10px] text-base-content/50 shrink-0 tabular-nums">{{ formatTime(chat.updated_at) }}</span>
              </div>
              <div class="text-[11px] text-base-content/50 truncate mt-0.5">
                {{ getSnippet(chat) }}
              </div>
            </div>

            <!-- Unread badge -->
            <span
              v-if="unreadCount(chat) > 0"
              class="shrink-0 min-w-[18px] h-[18px] rounded-full bg-primary text-primary-content text-[9px] font-bold flex items-center justify-center px-1"
            >{{ unreadLabel(chat) }}</span>
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    groups: { type: Array, default: () => [] },
    activeChat: { type: Object, default: null },
    userName: { type: String, default: 'User' },
    isCollapsed: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
    // Map of chat id → unread count, computed by the parent (MessengerView)
    unreadCounts: { type: Object, default: () => ({}) }
  },
  emits: ['select', 'new-group', 'toggle-collapse', 'settings'],
  data() {
    return {
      searchQuery: ''
    }
  },
  computed: {
    filteredGroups() {
      if (!this.searchQuery.trim()) return this.groups
      const q = this.searchQuery.toLowerCase()
      return this.groups.filter(c => c.name?.toLowerCase().includes(q))
    }
  },
  methods: {
    unreadCount(chat) {
      return (this.unreadCounts || {})[chat.id] || 0
    },
    unreadLabel(chat) {
      const count = this.unreadCount(chat)
      return count > 9 ? '9+' : count
    },
    getInitials(name) {
      if (!name) return '#'
      const words = name.trim().split(/\s+/)
      if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase()
      return name.substring(0, 2).toUpperCase()
    },
    formatTime(date) {
      if (!date) return ''
      const m = moment(date)
      const now = moment()
      if (now.diff(m, 'days') === 0) return m.format('HH:mm')
      if (now.diff(m, 'days') === 1) return 'Yesterday'
      if (now.diff(m, 'days') < 7) return m.format('ddd')
      return m.format('DD/MM/YY')
    },
    getSnippet(chat) {
      if (!chat.messages?.length) return 'No messages'
      const last = [...chat.messages].reverse().find(m => m.content && !m.hide)
      if (!last) return 'No messages'
      const prefix = last.user ? `${last.user}: ` : ''
      const text = last.content || ''
      return prefix + (text.length > 50 ? text.slice(0, 50) + '…' : text)
    }
  }
}
</script>