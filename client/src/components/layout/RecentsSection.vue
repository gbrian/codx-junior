<script setup>
import ChatSearch from '../chat/ChatSearch.vue'
import ChatSidebarNodeExtended from '../chat/ChatSidebarNodeExtended.vue'
</script>

<template>
  <div
    class="flex flex-col border-b border-white/5 overflow-hidden flex-1"
    :class="isCollapsed && 'items-center'"
  >
    <!-- Toggle button (always visible when not collapsed) -->
    <button
      v-if="!isCollapsed || isMobile"
      class="flex items-center justify-between px-5 py-3 text-xs font-semibold text-white/60 hover:text-white/80 transition-colors shrink-0 w-full"
      @click.stop="recentsExpanded = !recentsExpanded"
      @touchend.stop.prevent="recentsExpanded = !recentsExpanded"
      title="Toggle Recents"
    >
      <span>RECENTS</span>
      <i :class="recentsExpanded ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'" class="text-xs"></i>
    </button>

    <!-- Content area (scrollable) -->
    <div v-if="recentsExpanded || isMobile" class="flex-1 overflow-hidden flex flex-col">
      <div
        class="grow overflow-hidden flex flex-col"
        :class="isCollapsed && 'items-center'"
      >
        <!-- Collapsed mode: Chat icons -->
        <div v-if="isCollapsed" class="flex flex-col gap-2 px-2 py-2 overflow-y-auto flex-1">
          <div
            v-for="chat in displayedChatsCollapsed"
            :key="chat.id"
            @click="handleSelectChat(chat)"
            class="relative cursor-pointer group"
            :title="chat.name"
          >
            <div
              class="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold border transition-all duration-200"
              :class="[
                activeChatId === chat.id
                  ? 'bg-codx-primary text-white border-codx-primary/60 shadow-md ring-2 ring-codx-primary/20'
                  : 'bg-white/10 text-white border-white/20 hover:bg-white/20 hover:border-white/30',
                isVisibleChat(chat) && 'ring-2 ring-warning/50'
              ]"
            >
              {{ getInitials(chat.name) }}
            </div>

            <!-- Unread badge -->
            <div v-if="getUnreadCount(chat) > 0" class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-error text-white text-[9px] font-bold flex items-center justify-center border border-[#1a1a1a]">
              {{ getUnreadCount(chat) > 9 ? '9+' : getUnreadCount(chat) }}
            </div>

            <!-- Tooltip -->
            <div class="absolute left-14 top-1/2 -translate-y-1/2 bg-white/20 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50 border border-white/20">
              {{ chat.name }}
            </div>
          </div>

          <!-- Loading spinner -->
          <div v-if="isLoading" class="flex justify-center py-2">
            <span class="loading loading-spinner loading-xs"></span>
          </div>

          <!-- Show more indicator -->
          <div v-if="recentChats.length > 5" class="text-[9px] text-white/30 text-center">
            +{{ recentChats.length - 5 }}
          </div>
        </div>

        <!-- Expanded mode: Chat cards list -->
        <div v-else class="overflow-y-auto flex-1 px-2 py-2" @scroll="handleScroll">
          <!-- Empty state -->
          <div v-if="recentChats.length === 0 && !isLoading" class="text-center py-8 text-white/30 text-xs">
            <i class="fas fa-inbox text-2xl mb-2 block"></i>
            <p>No recent chats</p>
          </div>

          <!-- Chat items -->
          <div v-else class="flex flex-col gap-2 overflow-x-hidden">
            <ChatSidebarNodeExtended
              v-for="chat in recentChats"
              :key="chat.id"
              :chatId="chat.id"
              :selected-chat-id="activeChatId"
              @select="handleSelectChat"
            />

            <!-- Loading indicator -->
            <div v-if="isLoading" class="flex justify-center py-2">
              <span class="loading loading-spinner loading-xs"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- Recents Footer -->
      <div v-if="!isCollapsed" class="px-3 py-3 shrink-0 flex items-center justify-between border-t border-white/5">
        <span class="text-xs font-semibold text-white/40 uppercase tracking-wide">Search Chats...</span>
        <button
          @click.stop="openSearchModal"
          @touchend.stop.prevent="openSearchModal"
          class="p-1.5 text-white/40 hover:text-white/80 transition-colors"
          title="Search chats"
        >
          <i class="fas fa-magnifying-glass text-sm"></i>
        </button>
      </div>
    </div>
  </div>

  <!-- Search Modal -->
  <div
    v-if="isSearchModalOpen"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
    @click.self="closeSearchModal"
  >
    <div class="bg-[#1a1a1a] rounded-lg border border-white/10 w-full max-w-md max-h-[90vh] flex flex-col">
      <!-- Modal Header -->
      <div class="px-4 py-3 border-b border-white/5 flex items-center justify-between shrink-0">
        <h2 class="text-sm font-semibold text-white">Search Chats</h2>
        <button
          @click="closeSearchModal"
          class="p-1 text-white/40 hover:text-white/80 transition-colors"
        >
          <i class="fas fa-xmark"></i>
        </button>
      </div>

      <!-- Modal Content -->
      <div class="flex-1 overflow-hidden flex flex-col">
        <!-- Search Input with Loading Animation -->
        <div class="px-4 py-3 border-b border-white/5 shrink-0 relative">
          <ChatSearch
            :userId="currentUser?.id"
            :isSearching="isSearching"
            :searchStatus="searchStatus"
            @search="executeSearch"
            @clear="clearSearch"
          />

          <!-- Loading overlay animation -->
          <transition name="fade">
            <div v-if="isSearching" class="absolute inset-0 bg-black/20 rounded-lg flex items-center justify-center">
              <div class="flex flex-col items-center gap-2">
                <span class="loading loading-spinner loading-md text-primary"></span>
                <span class="text-xs text-white/70">Searching...</span>
              </div>
            </div>
          </transition>
        </div>

        <!-- Search Results -->
        <div class="flex-1 overflow-y-auto">
          <!-- Results found -->
          <div v-if="searchResults.length > 0" class="flex flex-col gap-2 p-3">
            <div
              v-for="result in searchResults"
              :key="result.chat?.id || result.id"
              @click="selectSearchResult(result)"
              class="card card-compact bg-white/5 border border-white/10 hover:border-codx-primary/50 hover:bg-white/10 cursor-pointer transition-all duration-200 p-2 gap-1"
            >
              <div class="flex items-start justify-between gap-2 min-w-0">
                <h3 class="font-semibold text-xs truncate text-white">{{ (result.chat?.name || result.name) || 'Untitled' }}</h3>
              </div>
              <div v-if="result.snippet || result.content" class="text-xs text-white/50 line-clamp-1">
                {{ result.snippet || result.content }}
              </div>
            </div>

            <!-- Results count -->
            <div v-if="searchMeta" class="text-xs text-white/40 text-center py-2">
              {{ searchResults.length }} / {{ searchMeta.total || searchResults.length }} results
            </div>
          </div>

          <!-- No results state -->
          <div v-else-if="searchPerformed && !isSearching" class="text-center py-8 text-white/30">
            <i class="fas fa-inbox text-2xl mb-2 block"></i>
            <p class="text-xs">No chats found</p>
          </div>

          <!-- Initial state -->
          <div v-else-if="!isSearching" class="text-center py-8 text-white/30">
            <i class="fas fa-magnifying-glass text-2xl mb-2 block"></i>
            <p class="text-xs">Enter a search query</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0
}
</style>

<script>
import { ChatSearchRequest } from '@/api/model/ChatSearchRequest'

export default {
  name: 'RecentsSection',
  props: {
    isCollapsed: { type: Boolean, default: false },
    isMobile: { type: Boolean, default: false }
  },
  emits: ['select-chat'],
  data() {
    return {
      activeChatId: null,
      currentPage: 1,
      initialPageSize: 20,
      subsequentPageSize: 10,
      isInitialLoad: true,
      recentsExpanded: true,
      isSearchModalOpen: false,
      searchResults: [],
      searchMeta: null,
      searchPerformed: false,
      isSearching: false,
      searchStatus: null,
      visibleChatIds: new Set(),
      unreadCountCache: {},
    }
  },
  computed: {
    currentUser() {
      return this.$storex?.users?.user || this.$user
    },
    recentChats() {
      return this.$storex.chats.recentChats
    },
    isLoading() {
      return this.$storex.chats.recentChatsLoading
    },
    hasMoreChats() {
      return this.$storex.chats.recentChatsHasMore
    },
    displayedChatsCollapsed() {
      return this.recentChats.slice(0, 5)
    }
  },
  mounted() {
    this.loadRecentChats()
    this.updateVisibleChats()
  },
  methods: {
    async loadRecentChats(append = false) {
      const pageSize = this.isInitialLoad ? this.initialPageSize : this.subsequentPageSize
      await this.$storex.chats.loadRecentChats({
        userId: this.currentUser?.id,
        page: this.currentPage,
        pageSize,
        append
      })
      this.activeChatId = this.$storex?.chats?.activeChat?.id || null
      this.isInitialLoad = false
    },
    loadMoreChats() {
      if (this.hasMoreChats && !this.isLoading) {
        this.currentPage += 1
        this.loadRecentChats(true)
      }
    },
    updateUnreadCountCache() {
      const currentUsername = this.$user?.username
      if (!currentUsername) return

      this.recentChats.forEach(chat => {
        const count = (chat.messages || []).filter(msg => {
          const isAssistantMsg = msg.role === 'assistant'
          const isOtherUser = msg.user !== currentUsername
          const isUnread = !msg.read_by || !msg.read_by.includes(currentUsername)
          return isAssistantMsg && isOtherUser && isUnread && !msg.hide
        }).length
        this.unreadCountCache[chat.id] = count
      })
    },
    getUnreadCount(chat) {
      return this.unreadCountCache[chat.id] || 0
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
    isVisibleChat(chat) {
      return this.visibleChatIds.has(chat.id)
    },
    handleSelectChat(chat) {
      this.$emit('select-chat', chat)
    },
    getInitials(name) {
      if (!name) return 'CH'
      const cleanName = name.replace(/[^\w\s-]/g, '').trim()
      const words = cleanName.split(/\s+/)
      if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase()
      }
      return name.substring(0, 2).toUpperCase()
    },
    handleScroll(e) {
      const { scrollTop, clientHeight, scrollHeight } = e.target
      if (scrollHeight - scrollTop - clientHeight < 100) {
        this.loadMoreChats()
      }
    },
    openSearchModal() {
      this.isSearchModalOpen = true
    },
    closeSearchModal() {
      this.isSearchModalOpen = false
      this.clearSearch()
    },
    async executeSearch(searchData) {
      this.isSearching = true
      this.searchStatus = null
      this.searchPerformed = true
      this.searchResults = []

      try {
        const searchRequest = new ChatSearchRequest({
          query: searchData.query,
          user_id: this.currentUser?.id,
          from_date: searchData.dateRange?.from_date,
          to_date: searchData.dateRange?.to_date,
          page: searchData.page || 1,
          page_size: searchData.pageSize || 20,
          filters: searchData.filters || {}
        })

        const results = await this.$storex.chats.searchChats(searchRequest)

        if (!results) {
          this.searchStatus = 'No response from server'
          return
        }

        if (results.error) {
          this.searchStatus = `Error: ${results.error}`
          return
        }

        if (results.total === 0) {
          this.searchStatus = 'No results found'
          this.searchResults = []
        } else {
          this.searchStatus = `Found ${results.total} result${results.total !== 1 ? 's' : ''}`
          this.searchResults = results.results || []
          this.searchMeta = {
            total: results.total,
            total_pages: results.total_pages || 1,
            page: searchData.page || 1,
            pageSize: searchData.pageSize || 20
          }
        }
      } catch (error) {
        console.error('Search error:', error)
        this.searchStatus = `Error: ${error.message || 'Search failed'}`
        this.searchResults = []
      } finally {
        this.isSearching = false
      }
    },
    selectSearchResult(result) {
      const chat = result.chat || result
      this.handleSelectChat(chat)
      this.closeSearchModal()
    },
    clearSearch() {
      this.searchResults = []
      this.searchMeta = null
      this.searchPerformed = false
      this.searchStatus = null
      try {
        this.$storex.chats.clearChatSearch?.()
      } catch (e) {
        console.log('Clear search called')
      }
    }
  }
}
</script>