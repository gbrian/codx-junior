<script setup>
import ChatSearch from '../chat/ChatSearch.vue'
import ChatProjectIcon from '../ChatProjectIcon.vue';
</script>

<template>
  <div class="grow overflow-hidden flex flex-col border-t border-white/5"
    :class="isCollapsed && 'items-center'"
  >
    <!-- Collapsed mode: Chat icons -->
    <div v-if="isCollapsed" class="flex flex-col gap-2 px-2 py-2 overflow-y-auto flex-1">
      <div
        v-for="chat in chats.slice(0, 5)"
        :key="chat.id"
        @click="handleSelectChat(chat)"
        class="relative cursor-pointer group"
        :title="chat.name"
      >
        <div
          class="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold border transition-all duration-200"
          :class="isActivChat(chat)
            ? 'bg-codx-primary text-white border-codx-primary/60 shadow-md ring-2 ring-codx-primary/20'
            : 'bg-white/10 text-white border-white/20 hover:bg-white/20 hover:border-white/30'"
        >
          {{ getInitials(chat.name) }}
        </div>

        <!-- Unread badge -->
        <div v-if="chat.unread_count > 0" class="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-error text-white text-[9px] font-bold flex items-center justify-center border border-[#1a1a1a]">
          {{ chat.unread_count > 9 ? '9+' : chat.unread_count }}
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
      <div v-if="chats.length > 5" class="text-[9px] text-white/30 text-center">
        +{{ chats.length - 5 }}
      </div>
    </div>

    <!-- Expanded mode: Chat cards list -->
    <div v-else class="overflow-y-auto flex-1 px-2 py-2" @scroll="handleScroll">
      <!-- Empty state -->
      <div v-if="displayedChats.length === 0 && !isLoading && !isSearching" class="text-center py-8 text-white/30 text-xs">
        <i class="fas fa-inbox text-2xl mb-2 block"></i>
        <p>No recent chats</p>
      </div>

      <!-- Chat cards -->
      <div v-else class="flex flex-col gap-2 overflow-x-hidden">
        <div
          v-for="chat in displayedChats"
          :key="chat.id"
          @click="handleSelectChat(chat)"
          class="card card-compact bg-white/5 border border-white/10 hover:border-codx-primary/50 hover:bg-white/10 cursor-pointer transition-all duration-200 p-2 gap-1"
          :class="isActivChat(chat) ? 'border-codx-primary bg-codx-primary/10' : ''"
        >
          <!-- Name and timestamp -->
          <div class="flex items-center gap-2 min-w-0 tooltip"
            :data-tip="chat.name"
          >
            <ChatProjectIcon :icon-only="true" :width="5" :chat="chat" />
            <h3 class="font-semibold text-xs truncate text-white">{{ chat.name || 'Untitled' }}</h3>
            <div v-if="chat.unread_count > 0" class="badge badge-xs badge-error shrink-0">{{ chat.unread_count }}</div>
          </div>

          <!-- Message snippet -->
          <div v-if="getLastMessageSnippet(chat)" class="text-xs text-white/50 line-clamp-1 leading-relaxed">
            {{ getLastMessageSnippet(chat) }}
          </div>
        </div>

        <!-- Loading indicator -->
        <div v-if="isLoading" class="flex justify-center py-2">
          <span class="loading loading-spinner loading-xs"></span>
        </div>
      </div>
    </div>

    <!-- Recents Footer -->
    <div v-if="!isCollapsed" class="px-3 py-3 shrink-0 flex items-center justify-between border-t border-white/5">
      <span class="text-xs font-semibold text-white/40 uppercase tracking-wide">Search Chats...</span>
      <button
        @click="openSearchModal"
        class="p-1.5 text-white/40 hover:text-white/80 transition-colors"
        title="Search chats"
      >
        <i class="fas fa-magnifying-glass text-sm"></i>
      </button>
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
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

<script>
import { ChatSearchRequest } from '@/api/model/ChatSearchRequest'

export default {
  props: {
    chats: { type: Array, default: () => [] },
    isCollapsed: { type: Boolean, default: false },
    isLoading: { type: Boolean, default: false },
    activeChatId: { type: String, default: null }
  },
  emits: ['select-chat', 'scroll-end'],
  data() {
    return {
      isSearchModalOpen: false,
      searchResults: [],
      searchMeta: null,
      searchPerformed: false,
      isSearching: false,
      searchStatus: null
    }
  },
  computed: {
    currentUser() {
      return this.$storex?.users?.user || this.$user
    },
    displayedChats() {
      return this.chats || []
    }
  },
  methods: {
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

        console.log('Executing search with:', searchRequest)

        const results = await this.$storex.chats.searchChats(searchRequest)

        console.log('Search results:', results)

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
    isActivChat(chat) {
      return this.activeChatId === chat.id
    },
    getLastMessageSnippet(chat) {
      if (!chat.messages || chat.messages.length === 0) {
        return ''
      }
      const messagesWithContent = [...chat.messages]
        .reverse()
        .filter(m => m.content || m.think)
      if (messagesWithContent.length === 0) {
        return ''
      }
      const lastMsg = messagesWithContent[0]
      const snippet = lastMsg.content || lastMsg.think || ''
      return snippet.length > 50 ? snippet.substring(0, 50).trim() + '...' : snippet
    },
    handleScroll(e) {
      const { scrollTop, clientHeight, scrollHeight } = e.target
      if (scrollHeight - scrollTop - clientHeight < 100) {
        this.$emit('scroll-end')
      }
    }
  }
}
</script>