<script setup>
import ChatIntelliSense from './chat/ChatIntelliSense.vue'
</script>

<template>
  <div class="flex-1 max-w-md">
    <div class="relative">
      <div class="input input-sm input-bordered flex items-center gap-2">
        <i class="fa-solid fa-magnifying-glass text-base-content/50"></i>
        <input
          ref="searchInput"
          v-model="searchQuery"
          type="text"
          placeholder="Search files, profiles, chats..."
          class="grow bg-transparent outline-none text-sm"
          @keydown="onSearchKeyDown"
          @focus="showSuggestions = true"
          @blur="handleBlur"
        />
        <span v-if="searchQuery" class="cursor-pointer" @click="clearSearch">
          <i class="fa-regular fa-circle-xmark"></i>
        </span>
      </div>

      <!-- ChatIntelliSense positioned below search bar -->
      <div v-if="showSuggestions && (searchResults.length > 0 || isSearching)" class="absolute top-full left-0 right-0 z-50 mt-1">
        <ChatIntelliSense
          :suggestions="searchResults"
          :active-index="activeIndex"
          :query="searchQuery"
          :search-controller="searchController"
          :progress="searchProgress"
          :top="true"
          @select="onResultSelect"
          @hover="activeIndex = $event"
          @accept-multi="onAcceptMulti"
          @cancel="cancelSearch"
        />
      </div>
    </div>
  </div>
</template>

<script>
export default {
  components: {
    ChatIntelliSense
  },
  data() {
    return {
      searchQuery: '',
      searchResults: [],
      showSuggestions: false,
      activeIndex: 0,
      searchController: null,
      searchProgress: '',
      searchDebounce: null,
      searchDismissed: false,
      previousQuery: null,
      isSearching: false
    }
  },
  mounted() {
    document.addEventListener('keydown', this.onGlobalKeyDown)
  },
  unmounted() {
    document.removeEventListener('keydown', this.onGlobalKeyDown)
    if (this.searchController) {
      this.searchController.cancel()
    }
  },
  watch: {
    searchQuery() {
      this.scheduleSearch()
    }
  },
  methods: {
    onGlobalKeyDown(event) {
      if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
        event.preventDefault()
        this.$refs.searchInput?.focus()
      }
    },

    onSearchKeyDown(event) {
      if (this.searchResults.length === 0) return

      if (event.key === 'Tab' || event.key === 'Enter') {
        event.preventDefault()
        this.onResultSelect(this.searchResults[this.activeIndex])
        return
      }

      if (event.key === 'Escape') {
        this.cancelSearch()
        return
      }

      if (event.key === 'ArrowUp') {
        event.preventDefault()
        this.activeIndex = Math.max(0, this.activeIndex - 1)
        return
      }

      if (event.key === 'ArrowDown') {
        event.preventDefault()
        this.activeIndex = Math.min(this.searchResults.length - 1, this.activeIndex + 1)
        return
      }
    },

    handleBlur() {
      setTimeout(() => {
        this.showSuggestions = false
      }, 150)
    },

    clearSearch() {
      this.searchQuery = ''
      this.searchResults = []
      this.showSuggestions = false
      this.$refs.searchInput?.focus()
    },

    cancelSearch() {
      this.searchDismissed = true
      this.showSuggestions = false
      if (this.searchController) {
        this.searchController.cancel()
      }
    },

    async performSearch() {
      if (!this.searchQuery.trim()) {
        this.searchResults = []
        this.isSearching = false
        return
      }

      if (this.searchDismissed) {
        if (this.searchQuery !== this.previousQuery) {
          this.searchDismissed = false
        } else {
          return
        }
      }

      this.previousQuery = this.searchQuery
      this.searchController = await this.$storex.projects.createSearchController()
      this.activeIndex = 0
      this.isSearching = true

      this.searchController.onProgress = ({ stage, project }) => {
        this.searchProgress = `${stage}: ${project}`
      }

      try {
        await this.$storex.projects.activeProject?.$state?.searchMentions?.({
          query: this.searchQuery,
          limit: 15,
          controller: this.searchController,
          onResults: (results) => {
            if (!this.searchController.isCancelled) {
              this.searchResults = results
              this.activeIndex = 0
            }
          }
        })
      } catch (error) {
        if (error.message !== 'Search cancelled') {
          console.error('[TopBarSearch] Search error:', error)
        }
      } finally {
        this.searchProgress = ''
        this.isSearching = false
      }
    },

    scheduleSearch() {
      clearTimeout(this.searchDebounce)
      this.searchDebounce = setTimeout(() => this.performSearch(), 220)
    },

    onResultSelect(result) {
      const { file, name, user, profile } = result

      if (file) {
        this.$storex.ui.openFileInViewer(file)
      } else if (profile) {
        this.$storex.ui.showApp({
          key: `profile-${profile.name}`,
          name: profile.name,
          component: 'profile-viewer',
          params: { profile }
        })
      } else if (user) {
        this.$storex.ui.showApp({
          key: `user-${user.username}`,
          name: user.username,
          component: 'user-viewer',
          params: { user }
        })
      }

      this.clearSearch()
    },

    onAcceptMulti(items) {
      const activeChat = this.$storex.chats.activeChat
      if (!activeChat) {
        this.$ui?.addNotification?.({
          text: 'No active chat to add items to',
          type: 'warning'
        })
        return
      }

      items.forEach(({ file, name, profile }) => {
        if (file && !this.hasFileInChat(file)) {
          this.$storex.projects.chatSvc?.addFileToChat?.({
            chat: activeChat,
            file
          })
        }
      })

      this.clearSearch()
      this.$storex.chats.saveChat(activeChat)
    },

    hasFileInChat(file) {
      const activeChat = this.$storex.chats.activeChat
      return activeChat?.file_list?.some(f => 
        f?.toLowerCase?.() === file?.toLowerCase?.()
      )
    }
  }
}
</script>