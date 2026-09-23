<script setup>
import moment from 'moment'
</script>

<template>
  <div class="kanban-list w-full flex flex-col gap-3">

    <!-- ── Sticky header bar ── -->
    <div class="sticky top-0 z-10 flex flex-col gap-2 bg-base-100 pb-2 pt-1">
      <div class="flex gap-2 items-center">
        <!-- Search input -->
        <div class="input input-sm input-bordered flex items-center gap-2 flex-1 min-w-0">
          <i class="fa-solid fa-magnifying-glass opacity-40 text-sm shrink-0"></i>
          <input
            type="text"
            v-model="boardFilter"
            class="grow bg-transparent outline-none text-sm"
            placeholder="Search boards..."
          />
          <button
            v-if="boardFilter"
            @click="boardFilter = ''"
            class="btn btn-ghost btn-xs btn-circle shrink-0"
          >
            <i class="fa-solid fa-times text-xs"></i>
          </button>
        </div>

        <!-- New board button -->
        <button class="btn btn-sm btn-warning btn-outline shrink-0" @click="$emit('new-board')">
          <i class="fa-solid fa-plus"></i>
          <span class="hidden sm:inline">Board</span>
        </button>

        <!-- History button -->
        <button class="btn btn-sm btn-ghost shrink-0" @click="$emit('toogle-history')">
          <i class="fa-solid fa-clock-rotate-left"></i>
          <span class="hidden sm:inline">History</span>
        </button>
      </div>

      <!-- No results hint -->
      <div v-if="boardFilter && filteredBoards.length === 0" class="text-sm text-base-content/40 px-1">
        No boards found for "<span class="font-medium">{{ boardFilter }}</span>"
      </div>
    </div>

    <!-- ── Bookmarked boards (horizontal scroll on mobile) ── -->
    <div v-if="bookmarks.length">
      <div class="text-xs font-semibold text-base-content/40 uppercase tracking-wide px-1 mb-2">
        <i class="fa-solid fa-bookmark text-warning mr-1"></i> Bookmarks
      </div>
      <div class="flex gap-3 overflow-x-auto pb-1 snap-x snap-mandatory">
        <div
          v-for="board in bookmarks"
          :key="board.title"
          @click="selectBoard(board)"
          class="snap-start shrink-0 w-48 h-28 p-3 card card-bordered bg-base-100 shadow rounded-xl cursor-pointer border-warning relative overflow-hidden active:scale-95 transition-transform"
        >
          <div
            class="absolute inset-0 opacity-30 rounded-xl bg-cover bg-center"
            :style="`background-image: url(${board.background})`"
            v-if="board.background"
          ></div>
          <div class="relative flex flex-col h-full gap-1">
            <div class="flex items-center gap-1">
              <i
                class="fa-solid fa-bookmark text-warning cursor-pointer"
                @click.stop="toggleBookmark(board)"
              ></i>
              <span class="text-sm font-semibold truncate">{{ board.title }}</span>
            </div>
            <p class="text-xs text-base-content/50 line-clamp-2">{{ board.description }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- ── All boards grid ── -->
    <div v-if="sortedBoards.length">
      <div class="text-xs font-semibold text-base-content/40 uppercase tracking-wide px-1 mb-2">
        Boards
      </div>
      <!-- Single column on mobile, 2 on sm, 3 on xl -->
      <div class="grid grid-cols-1 sm:grid-cols-2 @xl:grid-cols-3 gap-3">
        <div
          v-for="board in sortedBoards"
          :key="board.title"
          @click="selectBoard(board)"
          class="card card-bordered bg-base-100 shadow rounded-xl cursor-pointer relative overflow-hidden active:scale-[0.98] transition-transform min-h-36"
        >
          <!-- Background image -->
          <div
            class="absolute inset-0 opacity-20 bg-cover bg-center"
            :style="`background-image: url(${board.background})`"
            v-if="board.background"
          ></div>

          <div class="card-body p-3 flex flex-col gap-1 relative">
            <!-- Timestamp -->
            <span class="text-xs text-base-content/40" v-if="board.last_update">
              {{ moment(board.last_update).fromNow() }}
            </span>

            <!-- Parent label -->
            <span class="text-xs text-base-content/40" v-if="board.parent_id">
              <i class="fa-solid fa-sitemap text-xs"></i> {{ board.parent_id }}
            </span>

            <!-- Title row -->
            <div class="flex items-start gap-2">
              <i
                class="fa-solid fa-bookmark mt-0.5 shrink-0 cursor-pointer"
                :class="board.bookmark ? 'text-warning' : 'text-base-content/20'"
                @click.stop="toggleBookmark(board)"
              ></i>
              <h2 class="font-bold text-sm leading-tight truncate flex-1" :title="board.title">
                {{ board.title }}
              </h2>
            </div>

            <!-- Description -->
            <p class="text-xs text-base-content/60 line-clamp-2" v-if="board.description">
              {{ board.description }}
            </p>

            <!-- Search match info -->
            <div
              v-if="boardFilter && getMatchingContent(board).columns.length > 0"
              class="text-xs p-1.5 bg-base-200 rounded-lg mt-1"
            >
              <div class="text-base-content/50 truncate">
                <i class="fa-solid fa-table-columns text-xs mr-1"></i>
                {{ getMatchingContent(board).columns.join(', ') }}
              </div>
              <div v-if="getMatchingContent(board).chatCount" class="text-base-content/50 mt-0.5">
                <i class="fa-solid fa-message text-xs mr-1"></i>
                {{ getMatchingContent(board).chatCount }} chats
              </div>
            </div>

            <div class="grow"></div>

            <!-- Footer stats -->
            <div class="flex items-center gap-3 text-base-content/40 text-xs mt-1">
              <span class="flex items-center gap-1">
                <i class="fas fa-columns"></i>
                {{ board.columns?.length || 0 }}
              </span>
              <span class="flex items-center gap-1">
                <i class="fa-brands fa-trello"></i>
                {{ board.tasks?.length || 0 }}
              </span>
              <!-- Remote URL -->
              <a
                v-if="board.remote_url"
                class="ml-auto text-xs underline text-primary truncate max-w-[120px]"
                :title="board.remote_url"
                @click.stop="openRemoteBoard(board)"
              >
                <i class="fa-solid fa-link text-xs mr-0.5"></i>
                {{ board.remote_url }}
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-if="!bookmarks.length && !sortedBoards.length" class="flex flex-col items-center justify-center py-16 text-base-content/30 gap-3">
      <i class="fa-brands fa-trello text-5xl"></i>
      <span class="text-sm">No boards yet</span>
      <button class="btn btn-sm btn-warning btn-outline" @click="$emit('new-board')">
        <i class="fa-solid fa-plus"></i> Create a board
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    boards: {
      type: Array,
      default: null
    },
    project: {
      type: Object,
      default: null
    },
    options: {
      type: Object,
      default: () => ({})
    }
  },
  data() {
    return {
      boardFilter: ''
    }
  },
  computed: {
    kanban() {
      return this.project?.$state?.kanban || { boards: {} }
    },
    allStoredBoards() {
      return Object.values(this.kanban.boards || {})
    },
    displayBoards() {
      if (this.boards && Array.isArray(this.boards) && this.boards.length > 0) {
        return this.boards
      }
      return this.allStoredBoards
    },
    allChats() {
      return this.$projects.allChats || []
    },
    chatMap() {
      const map = {}
      this.allChats.forEach(chat => {
        map[chat.id] = chat
      })
      return map
    },
    bookmarks() {
      return this.displayBoards.filter(b => b.bookmark && this.matchesFilter(b))
    },
    sortedBoards() {
      return this.filteredBoards
        .filter(b => !b.bookmark)
        .sort((a, b) =>
          a.last_update && b.last_update ?
            a.last_update > b.last_update ? -1 : 1 :
              a.last_update ? -1 : 1
        )
    },
    rootBoards() {
      if (this.boards && Array.isArray(this.boards)) {
        return this.boards
      }
      const allBoardIds = this.allStoredBoards.map(b => b.id)
      return this.allStoredBoards.filter(b => !allBoardIds.includes(b.parent_id))
    },
    filteredBoards() {
      if (!this.boardFilter) return this.rootBoards
      return this.rootBoards.filter(board => this.matchesFilter(board))
    }
  },
  methods: {
    matchesFilter(board) {
      const filterLower = this.boardFilter.toLowerCase()

      if (board.title && board.title.toLowerCase().includes(filterLower)) {
        return true
      }

      if (board.columns && Array.isArray(board.columns)) {
        if (board.columns.some(col =>
          col.title && col.title.toLowerCase().includes(filterLower)
        )) {
          return true
        }
      }

      if (board.columns && Array.isArray(board.columns)) {
        for (const column of board.columns) {
          if (column.chats && Array.isArray(column.chats)) {
            for (const chatId of column.chats) {
              const chat = this.chatMap[chatId]
              if (chat && this.chatMatches(chat, filterLower)) {
                return true
              }
            }
          }
        }
      }

      return false
    },
    chatMatches(chat, filterLower) {
      if (!chat) return false

      if (chat.name && chat.name.toLowerCase().includes(filterLower)) {
        return true
      }

      if (chat.file_list?.some(f => f.toLowerCase().includes(filterLower))) {
        return true
      }

      if (chat.messages && Array.isArray(chat.messages)) {
        return chat.messages.some(msg =>
          (msg.content && msg.content.toLowerCase().includes(filterLower)) ||
          (msg.think && msg.think.toLowerCase().includes(filterLower)) ||
          (msg.files && msg.files.some(f => f.toLowerCase().includes(filterLower)))
        )
      }

      return false
    },
    getMatchingContent(board) {
      const filterLower = this.boardFilter.toLowerCase()
      const matchingColumns = []
      let chatCount = 0

      if (board.columns && Array.isArray(board.columns)) {
        for (const column of board.columns) {
          let columnMatches = false

          if (column.title && column.title.toLowerCase().includes(filterLower)) {
            matchingColumns.push(column.title)
            columnMatches = true
          }

          if (column.chats && Array.isArray(column.chats)) {
            for (const chatId of column.chats) {
              const chat = this.chatMap[chatId]
              if (chat && this.chatMatches(chat, filterLower)) {
                chatCount++
                if (!columnMatches) {
                  matchingColumns.push(column.title)
                  columnMatches = true
                }
              }
            }
          }
        }
      }

      return {
        columns: [...new Set(matchingColumns)],
        chatCount
      }
    },
    selectBoard(board) {
      this.$emit('select', board.title)
    },
    openRemoteBoard(board) {
      window.open(board.remote_url, '_blank')
    },
    toggleBookmark(board) {
      this.$emit('bookmark', board)
    }
  }
}
</script>