<script setup>
import moment from 'moment'
</script>

<template>
  <!-- Icon mode - shows chat count badges -->
  <div v-if="collapsed" class="flex flex-col gap-3 w-full items-center">
    <div v-if="recentChats.length > 0" class="text-[9px] font-extrabold tracking-wider text-base-content-ERROR-40 uppercase mb-1 text-center">
      Chats
    </div>
    
    <!-- Chat icons with counters in collapsed mode -->
    <div class="flex flex-col gap-2 w-full items-center">
      <div
        v-for="chat in recentChats.slice(0, 5)"
        :key="chat.id"
        @click="selectChat(chat)"
        class="relative cursor-pointer transition-all duration-200 group"
        :title="chat.name"
      >
        <div
          class="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold border transition-all duration-200"
          :class="isActive(chat)
            ? 'bg-primary text-primary-content border-primary/60 shadow-md ring-2 ring-primary/20'
            : 'bg-base-300 text-base-content border-base-content/10 hover:bg-base-300/80 hover:border-base-content/20'"
        >
          {{ getInitials(chat.name) }}
        </div>

        <!-- Unread badge (if available) -->
        <div v-if="chat.unread_count > 0" class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-error text-white text-[9px] font-bold flex items-center justify-center border border-base-100">
          {{ chat.unread_count > 9 ? '9+' : chat.unread_count }}
        </div>

        <!-- Tooltip on hover -->
        <div class="absolute left-14 top-1/2 -translate-y-1/2 bg-base-300 text-base-content text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50 border border-base-content/10">
          {{ chat.name }}
        </div>
      </div>

      <!-- Show more indicator if chats exceed limit -->
      <div v-if="recentChats.length > 5" class="text-[9px] text-base-content-ERROR-40 mt-2">
        +{{ recentChats.length - 5 }}
      </div>
    </div>
  </div>

  <!-- Full mode - shows detailed chat cards -->
  <div v-else class="flex flex-col gap-1 w-full shrink-0">
    <div v-if="recentChats.length > 0" class="divider my-1 w-8 mx-auto opacity-40"></div>
    
    <!-- Header helper -->
    <div v-if="recentChats.length > 0" class="text-[9px] font-extrabold tracking-wider text-base-content-ERROR-40 uppercase mb-2 px-2">
      Recent Chats & Tasks
    </div>

    <!-- Scrollable container for recent chats -->
    <div
      class="flex flex-col gap-2 scrollbar-none"
      @scroll="handleScroll"
    >
      <div
        v-for="chat in recentChats"
        :key="chat.id"
        :class="[
          'p-3 rounded-xl border transition-all duration-200 cursor-pointer flex flex-col gap-2 relative overflow-hidden',
          isActive(chat)
            ? 'bg-primary/10 border-primary/40 text-base-content shadow-sm ring-1 ring-primary/20'
            : 'bg-base-300/30 border-base-content/5 hover:bg-base-300/60 hover:border-base-content/10'
        ]"
        @click="selectChat(chat)"
      >
        <!-- Top Row: Project context & Board & badge mode -->
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-2 min-w-0">
            <!-- Project indicator -->
            <div
              v-if="getChatProject(chat)"
              class="avatar shrink-0"
              :title="getChatProject(chat).project_name"
            >
              <div class="w-5 h-5 rounded-full overflow-hidden bg-base-300 border border-base-content/10">
                <img :src="getChatProject(chat).project_icon" />
              </div>
            </div>
            
            <span class="text-[11px] font-semibold text-base-content/50 truncate max-w-[150px]">
              {{ getChatProject(chat)?.project_name || 'Project' }}
              <span v-if="chat.board" class="text-base-content/30 mx-1">/</span>
              <span v-if="chat.board" class="text-base-content/70 font-bold">{{ chat.board }}</span>
            </span>
          </div>

          <!-- Mode/Badge -->
          <div class="flex items-center gap-1 shrink-0">
            <span
              v-if="chat.mode"
              :class="`badge badge-xs badge-outline text-[9px] px-1.5 py-1 font-semibold border-base-content/25 badge-${badgeColor[chat.mode] || 'ghost'}`"
            >
              {{ chat.mode }}
            </span>
          </div>
        </div>

        <!-- Middle Row: Chat initials, name and status dot -->
        <div class="flex items-center gap-2.5 min-w-0">
          <div
            class="w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-bold shrink-0 transition-all duration-200 overflow-hidden relative border border-base-content/10"
            :class="isActive(chat)
              ? 'bg-primary text-primary-content font-extrabold'
              : 'bg-base-300 text-base-content'"
          >
            {{ getInitials(chat.name) }}
          </div>

          <div class="flex-1 min-w-0">
            <div class="text-xs font-bold truncate text-base-content" :title="chat.name">
              {{ chat.name || 'Unnamed Chat' }}
            </div>
            <div class="text-[10px] text-base-content-ERROR-40 font-medium">
              {{ getFormattedDate(chat) }}
            </div>
          </div>

          <!-- Green indicator dot for the active chat -->
          <div
            v-if="isActive(chat)"
            class="w-2 h-2 bg-success rounded-full border border-base-100 shrink-0"
          ></div>
        </div>

        <!-- Bottom Row: Last Message Snippet -->
        <div class="text-[11px] text-base-content/60 leading-relaxed bg-base-300/20 rounded-lg p-2 border border-base-content/5 truncate">
          {{ getLastMessageSnippet(chat) }}
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    collapsed: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      limit: 8,
      badgeColor: {
        task: 'primary',
        chat: 'accent'
      }
    }
  },
  computed: {
    // Filter chats by active project, then sort by update timestamp descending
    sortedChats() {
      const activeProjectId = this.$storex?.projects?.activeProject?.project_id
      const chats = this.$storex?.chats?.allChats || []
      
      return [...chats]
        .filter(chat => chat && chat.id && (chat.project_id === activeProjectId || chat.owner_project_id === activeProjectId))
        .sort((a, b) => {
          const getChatTime = (c) => {
            if (c.updated_at) return new Date(c.updated_at).getTime()
            if (c.messages && c.messages.length > 0) {
              const lastMsg = c.messages[c.messages.length - 1]
              const t = lastMsg.updated_at || lastMsg.created_at
              if (t) return new Date(t).getTime()
            }
            return 0
          }
          return getChatTime(b) - getChatTime(a)
        })
    },
    // Slice current chunk for infinite scroll
    recentChats() {
      return this.sortedChats.slice(0, this.limit)
    }
  },
  methods: {
    // Infinite scroll handler
    handleScroll(e) {
      const { scrollTop, clientHeight, scrollHeight } = e.target
      if (scrollHeight - scrollTop - clientHeight < 40) {
        if (this.limit < this.sortedChats.length) {
          this.limit += 8
        }
      }
    },
    // Generate simple initials from the chat name
    getInitials(name) {
      if (!name) return 'CH'
      const cleanName = name.replace(/[^\w\s-]/g, '').trim()
      const words = cleanName.split(/\s+/)
      if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase()
      }
      return name.substring(0, 2).toUpperCase()
    },
    isActive(chat) {
      return this.$storex?.chats?.activeChat?.id === chat.id
    },
    async selectChat(chat) {
      await this.$storex.chats.setActiveChat(chat)
    },
    // Resolve parent project for the chat
    getChatProject(chat) {
      const projects = this.$storex?.projects?.allProjects || this.$projects?.allProjects || []
      return projects.find(p => p.project_id === chat.project_id || p.project_id === chat.owner_project_id) || this.$project
    },
    // Resolve date formatting matching TaskCardLite pattern
    getFormattedDate(chat) {
      const updatedAt = chat.updated_at || chat.created_at
      if (!updatedAt) return ''
      const isToday = moment(0, "HH").diff(updatedAt, "days") === 0
      return isToday ? moment(updatedAt).format('HH:mm:ss') : moment(updatedAt).format('YYYY-MM-DD HH:mm')
    },
    // Safely extract message snippet
    getLastMessageSnippet(chat) {
      if (!chat.messages || chat.messages.length === 0) {
        return 'No messages'
      }
      const messagesWithContent = [...chat.messages]
        .reverse()
        .filter(m => m.content || m.think)
      if (messagesWithContent.length === 0) {
        return 'No message content'
      }
      const lastMsg = messagesWithContent[0]
      const snippet = lastMsg.content || lastMsg.think || ''
      return snippet.length > 70 ? snippet.substring(0, 70).trim() + '...' : snippet
    }
  }
}
</script>