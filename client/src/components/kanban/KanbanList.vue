<script setup>
import moment from 'moment'
</script>

<template>
  <div class="kanban-list w-full flex flex-col gap-2">
    <div class="sticky top-0 z-20 flex flex-col gap-1">
      <h1 class="text-2xl font-bold flex justify-between gap-2 py-1">
        <div class="flex-1 flex gap-2">
          <input 
            type="text" 
            v-model="boardFilter" 
            class="input input-sm flex-1" 
            placeholder="Search boards, columns, and chats..." 
          />
          <button 
            v-if="boardFilter" 
            @click="boardFilter = ''" 
            class="btn btn-sm btn-ghost"
            title="Clear search"
          >
            <i class="fa-solid fa-times"></i>
          </button>
        </div>
        <button class="btn btn-sm btn-warning btn-outline" @click="$emit('new-board')">
          <i class="fa-solid fa-plus"></i> Board
          <span class="hidden @md:block">New kanban</span>
        </button>
        <button class="btn btn-sm" @click="$emit('toogle-history')">
          <i class="fa-solid fa-clock-rotate-left"></i>
          <span class="hidden @md:block">History</span>
        </button>
      </h1>
      <div v-if="boardFilter && filteredBoards.length === 0" class="text-sm text-gray-500 px-2">
        No results found for "{{ boardFilter }}"
      </div>
    </div>

    <div class="grid grid-cols-1 @sm:grid-cols-2 @xl:grid-cols-3 gap-4">
      <div
        v-for="board in bookmarks"
        :key="board.title"
        @click="selectBoard(board)"
        class="p-2 card card-bordered bg-base-100 shadow-md rounded-lg cursor-pointer bg-contain relative border-warning h-32"
      >
        <div 
          class="absolute top-0 left-0 bottom-0 right-0 opacity-30 rounded-md bg-cover"
          :style="`background-image: url(${board.background})`" 
          v-if="board.background"
        ></div>
        <h2 class="card-title flex tooltip group" :data-tip="board.title">
          <span class="flex items-center">
            <i
              :class="['fa-solid', 'fa-bookmark', board.bookmark ? 'text-warning' : 'text-gray-400']"
              @click.stop="toggleBookmark(board)"
              class="cursor-pointer mr-2"
            ></i>
            <div class="overflow-hidden">{{ board.title }}</div>
          </span>
        </h2>
      </div>
    </div>

    <div class="grid grid-cols-1 @sm:grid-cols-2 @xl:grid-cols-3 gap-4">
      <div
        v-for="board in sortedBoards"
        :key="board.title"
        @click="selectBoard(board)"
        class="card card-bordered bg-base-100 shadow-md rounded-lg cursor-pointer bg-contain relative h-60"
      >
        <div 
          class="absolute top-0 left-0 bottom-0 right-0 opacity-30 rounded-md bg-cover"
          :style="`background-image: url(${board.background})`" 
          v-if="board.background"
        ></div>
        <div class="card-body flex flex-col">
          <span class="text-xs" v-if="board.last_update">[{{ moment(board.last_update).fromNow() }}]</span>
          <span class="text-xs" v-if="board.parent_id">
            [{{ board.parent_id }}]
          </span>
          <h2 class="card-title flex tooltip group" :data-tip="board.title">
            <span class="flex items-center bg-base-100/80 pl-1 w-full rounded-md text-nowrap">
              <div class="overflow-hidden">{{ board.title }}</div>
            </span>
          </h2>
          <p class="text-sm">{{ board.description }}</p>
          <div class="grow"></div>
          
          <!-- Display matching columns and chats if search is active -->
          <div v-if="boardFilter && getMatchingContent(board).columns.length > 0" class="text-xs mb-2 p-1 bg-base-200 rounded">
            <div v-if="getMatchingContent(board).columns.length" class="text-gray-600">
              Columns: {{ getMatchingContent(board).columns.join(', ') }}
            </div>
            <div v-if="getMatchingContent(board).chatCount" class="text-gray-600">
              Matching chats: {{ getMatchingContent(board).chatCount }}
            </div>
          </div>
          
          <div class="flex justify-between items-center gap-1">
            <div class="flex gap-2 items-center text-xl">
              <i class="fas fa-columns text-gray-600"></i>
              <span class="-mt-1">{{ board.columns?.length || 0 }}</span>
              <i class="fa-brands fa-trello text-gray-600"></i>
              <span class="-mt-1">{{ board.tasks?.length || 0 }}</span>
            </div>
          </div>
          <div 
            class="text-xs underline overflow-hidden click"
            :title="board.remote_url"
            @click.stop="openRemoteBoard(board)"
            v-if="board.remote_url"
          >
            {{ board.remote_url }}
          </div>
        </div>
      </div>
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

      if (chat.file_list?.some(f => f.toLowerCase().includes(filterLower)))

      if (chat.messages && Array.isArray(chat.messages)) {
        return chat.messages.some(msg => 
          (msg.content && msg.content.toLowerCase().includes(filterLower)) ||
          (msg.think && msg.think.toLowerCase().includes(filterLower))||
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