<script setup>
import ChatSearch from '../chat/ChatSearch.vue'
import ChatCard from '../chat/ChatCard.vue'
</script>

<template>
  <!-- Icon mode - shows chat count badges -->
  <div v-if="collapsed" class="flex flex-col gap-3 w-full h-full items-center">
    <div v-if="recentChats.length > 0 || isSearching" class="text-[9px] font-extrabold tracking-wider text-base-content-ERROR-40 uppercase mb-1 text-center">
      {{ isSearching ? 'Search' : 'Recent Chats' }}
    </div>
    
    <!-- Chat icons with counters in collapsed mode -->
    <div class="flex flex-col gap-2 w-full items-center">
      <!-- Search toggle button -->
      <div
        @click="toggleSearchMode"
        class="relative cursor-pointer transition-all duration-200 group"
        :title="isSearching ? 'Back to recent chats' : 'Search chats'"
      >
        <div
          class="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold border transition-all duration-200"
          :class="isSearching
            ? 'bg-primary text-primary-content border-primary/60 shadow-md ring-2 ring-primary/20'
            : 'bg-base-300 text-base-content border-base-content/10 hover:bg-base-300/80 hover:border-base-content/20'"
        >
          <i :class="isSearching ? 'fa-solid fa-xmark' : 'fa-solid fa-magnifying-glass'"></i>
        </div>

        <!-- Tooltip on hover -->
        <div class="absolute left-14 top-1/2 -translate-y-1/2 bg-base-300 text-base-content text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none whitespace-nowrap z-50 border border-base-content/10">
          {{ isSearching ? 'Back to chats' : 'Search chats' }}
        </div>
      </div>

      <!-- Chat icons with counters -->
      <template v-if="!isSearching">
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
        <div v-if="totalChats > 5" class="text-[9px] text-base-content-ERROR-40 mt-2">
          +{{ totalChats - 5 }}
        </div>
      </template>
    </div>
  </div>

  <!-- Full mode - shows detailed chat cards with scrollable list -->
  <div v-else class="flex flex-col w-full h-full gap-0 overflow-hidden">
    <!-- Always visible header with controls -->
    <div class="flex-shrink-0 border-b border-base-300">
      <!-- Title and filter/search buttons row -->
      <div class="flex items-center justify-between px-2 py-2 gap-2">
        <div class="text-[9px] font-extrabold tracking-wider text-base-content-ERROR-40 uppercase flex-1">
          {{ isSearching ? 'Search Results' : 'Recent Chats' }}
        </div>

        <!-- Action buttons -->
        <div class="flex gap-1 flex-shrink-0">
          <!-- Search button -->
          <button
            @click="toggleSearchMode"
            class="btn btn-xs btn-ghost"
            :class="isSearching ? 'btn-active' : ''"
            title="Search chats"
          >
            <i class="fa-solid fa-magnifying-glass text-sm"></i>
          </button>
        </div>
      </div>

      <!-- Search input (visible only when searching) -->
      <div v-if="isSearching" class="px-2 py-2 border-t border-base-300">
        <!-- Chat search input with userId -->
        <ChatSearch
          :userId="currentUser?.id"
          @search="onSearchResults"
          @clear="closeSearch"
          @error="onSearchError"
          @no-results="onNoResults"
        />
      </div>
    </div>

    <!-- Content area - scrollable -->
    <div
      class="flex-1 overflow-y-auto min-h-0"
      ref="scrollContainer"
      @scroll="handleScroll"
    >
      <!-- Search results mode -->
      <template v-if="isSearching">
        <div class="flex flex-col gap-2 p-2">
          <div v-if="searchResults && searchResults.length > 0">
            <ChatCard
              v-for="result in searchResults"
              :key="result.chat?.id || result.id"
              :chat="result.chat || result"
              :isActive="isActive(result.chat || result)"
              :badgeColor="badgeColor"
              :snippet="result.snippet || getLastMessageSnippet(result.chat || result)"
              @select="selectChat(result.chat || result)"
            />
          </div>

          <!-- No results state -->
          <div v-else-if="searchPerformed" class="text-center py-8 text-base-content/50">
            <i class="fa-solid fa-inbox text-3xl mb-2 block"></i>
            <p class="text-sm">No chats found</p>
          </div>

          <!-- Initial state (before search) -->
          <div v-else class="text-center py-8 text-base-content/50">
            <i class="fa-solid fa-magnifying-glass text-3xl mb-2 block"></i>
            <p class="text-sm">Enter a search query</p>
          </div>
        </div>

        <!-- Pagination info -->
        <div v-if="searchPerformed && searchData" class="sticky bottom-0 text-xs text-base-content/50 text-center py-2 bg-base-100 border-t border-base-300">
          {{ searchResults.length || 0 }} / {{ searchData.total || 0 }} results
        </div>
      </template>

      <!-- Recent chats mode -->
      <template v-else>
        <!-- Empty state -->
        <div v-if="recentChats.length === 0" class="flex flex-col items-center justify-center h-full text-base-content/50">
          <i class="fa-solid fa-inbox text-3xl mb-2"></i>
          <p class="text-sm">No recent chats</p>
        </div>

        <!-- Chat cards list -->
        <div v-else class="flex flex-col gap-2 p-2">
          <ChatCard
            v-for="chat in recentChats"
            :key="chat.id"
            :chat="chat"
            :isActive="isActive(chat)"
            :chatProject="getChatProject(chat)"
            :badgeColor="badgeColor"
            :snippet="getLastMessageSnippet(chat)"
            @select="selectChat(chat)"
          />

          <!-- Loading indicator for pagination -->
          <div v-if="isLoadingMore" class="flex justify-center py-4">
            <span class="loading loading-spinner loading-sm"></span>
          </div>

          <!-- End of list indicator -->
          <div v-if="!hasMoreChats && recentChats.length > 0" class="text-center text-xs text-base-content/40 py-4">
            No more chats
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
export default {
  components: {
    ChatSearch,
    ChatCard
  },
  props: {
    collapsed: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      pageSize: 10,
      currentPage: 1,
      totalChats: 0,
      badgeColor: {
        task: 'primary',
        chat: 'accent'
      },
      isSearching: false,
      searchData: null,
      searchResults: [],
      recentChats: [],
      isLoadingMore: false,
      hasMoreChats: true,
      initialSearchPerformed: false,
      searchPerformed: false
    }
  },
  computed: {
    currentUser() {
      return this.$storex?.users?.user || this.$user
    }
  },
  mounted() {
    this.loadRecentChats()
  },
  methods: {
    async loadRecentChats(append = false) {
      try {
        this.isLoadingMore = true
        const currentUserId = this.currentUser?.id

        const response = await this.$project.$api.chats.getRecentChats({
          filters: {
            user_id: currentUserId
          },
          page: this.currentPage,
          pageSize: this.pageSize
        })

        if (response.error) {
          console.error('Error loading recent chats:', response.error)
          this.isLoadingMore = false
          return
        }

        this.totalChats = response.total

        if (append) {
          this.recentChats.push(...response.chats)
        } else {
          this.recentChats = response.chats
        }

        this.hasMoreChats = response.has_next
        this.isLoadingMore = false
      } catch (error) {
        console.error('Error loading recent chats:', error)
        this.isLoadingMore = false
      }
    },
    handleScroll(e) {
      const { scrollTop, clientHeight, scrollHeight } = e.target
      // Trigger load when user scrolls near bottom (100px threshold)
      // Only load if: not already loading, has more pages, and user isn't searching
      if (scrollHeight - scrollTop - clientHeight < 100 && this.hasMoreChats && !this.isLoadingMore && !this.isSearching) {
        this.currentPage += 1
        this.loadRecentChats(true)
      }
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
    isActive(chat) {
      return this.$storex?.chats?.activeChat?.id === chat.id
    },
    async selectChat(chat) {
      this.$emit('select', chat)
    },
    getChatProject(chat) {
      const projects = this.$storex?.projects?.allProjects || this.$projects?.allProjects || []
      return projects.find(p => p.project_id === chat.project_id || p.project_id === chat.owner_project_id) || this.$project
    },
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
    },
    toggleSearchMode() {
      this.isSearching = !this.isSearching
      if (!this.isSearching) {
        this.searchResults = []
        this.searchData = null
        this.searchPerformed = false
      } else {
        this.searchPerformed = false
      }
    },
    closeSearch() {
      this.isSearching = false
      this.searchResults = []
      this.searchData = null
      this.searchPerformed = false
    },
    onSearchResults(searchData) {
      this.searchData = searchData.results
      this.searchResults = searchData.results.results || []
      this.searchPerformed = true
    },
    onSearchError(error) {
      console.error('Search error:', error)
      this.searchPerformed = true
    },
    onNoResults() {
      this.searchResults = []
      this.searchData = { results: [], total: 0 }
      this.searchPerformed = true
    }
  }
}
</script>