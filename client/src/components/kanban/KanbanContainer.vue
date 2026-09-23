<script setup>
import KanbanList from './KanbanList.vue'
import Kanban from './Kanban.vue'
import NewEditBoardModal from './NewEditBoardModal.vue'
import ChatView from '@/views/ChatView.vue'
</script>

<template>
  <div class="@container w-full h-full flex flex-col overflow-hidden">
    <!-- ChatView (mobile: full screen overlay) -->
    <transition name="slide-up">
      <div v-if="activeChat" class="absolute inset-0 z-50 bg-base-100">
        <ChatView :chat="activeChat"
          @chats="$chats.setActiveChat(null)" />
      </div>
    </transition>

    <!-- Main content area -->
    <div class="w-full h-full flex flex-col overflow-hidden" :class="isMobile ? '' : 'p-2'">

      <!-- Kanban list -->
      <transition name="slide-left">
        <KanbanList
          v-if="showKanbanList"
          :boards="boards"
          :project="project"
          @select="selectBoard"
          @new-board="showNewBoardModal"
          @bookmark="toggleBookmark"
          @delete="onDeleteBoard"
          class="w-full h-full overflow-auto"
          :class="isMobile ? 'px-3 pt-2 pb-20' : 'p-2'"
        />
      </transition>

      <!-- Kanban board view -->
      <transition name="slide-right">
        <Kanban
          v-if="showKanban"
          :project="project"
          @edit-board="onEditBoard"
          @select-board="selectBoard"
          class="w-full h-full"
        />
      </transition>

    </div>

    <!-- New/Edit Board modal -->
    <modal close="true" @close="closeBoardModal" v-if="showBoardModal">
      <NewEditBoardModal
        :board="editingBoard"
        :boards="boards"
        :project="project"
        @close="closeBoardModal"
      />
    </modal>
  </div>
</template>

<script>
export default {
  props: ['params'],
  data() {
    return {
      showHistory: false,
      showBoardModal: false,
      editingBoard: null
    }
  },
  created() {
    this.projectChanged()
  },
  watch: {
    project() {
      this.projectChanged()
    }
  },
  computed: {
    isMobile() {
      return this.$ui.isMobile
    },
    project() {
      return this.$project
    },
    kanban() {
      return this.project?.$state?.kanban || { boards: {} }
    },
    boards() {
      const keys = Object.keys(this.kanban.boards || {})
      return keys
        .map(title => ({ title, ...this.kanban.boards[title] }))
        .filter(b => !this.selectedBoard || b.parent_id === this.selectedBoard)
    },
    selectedBoard() {
      return this.$projects.activeBoard
    },
    activeBoard() {
      return this.kanban?.boards[this.$projects.activeBoard]
        ? this.$projects.activeBoard
        : null
    },
    showKanban() {
      return !this.activeChat && !this.showHistory && !!this.activeBoard
    },
    showKanbanList() {
      return !this.activeChat && !this.showHistory && !this.showKanban
    },
    activeChat() {
      return this.$ui.isMobile ? this.$chats.activeChat : null
    }
  },
  methods: {
    async projectChanged() {
      if (!this.project?.$state?.kanban) {
        await this.$storex.projects.loadKanban({ project: this.project })
      }
      this.selectBoard()
    },
    async selectBoard(board) {
      await this.$projects.setActiveBoard(board)
    },
    showNewBoardModal() {
      this.editingBoard = {
        title: '',
        description: '',
        background: '',
        parent_id: this.activeBoard || null,
        columns: [],
        id: null
      }
      this.showBoardModal = true
    },
    onEditBoard(board) {
      const title = board?.title || this.activeBoard
      this.editingBoard = { title, ...this.kanban.boards[title] }
      this.showBoardModal = true
    },
    closeBoardModal() {
      this.showBoardModal = false
      this.editingBoard = null
    },
    toggleBookmark({ title } = {}) {
      const boardTitle = title || this.activeBoard
      const board = this.kanban.boards[boardTitle]
      if (!board) return
      board.bookmark = !board.bookmark
      this.$storex.projects.saveKanban({ project: this.project })
    },
    async onDeleteBoard(board) {
      const boardTitle = board?.title || board
      if (!boardTitle || !this.kanban.boards[boardTitle]) return
      delete this.kanban.boards[boardTitle]
      await this.$storex.projects.saveKanban({ project: this.project })
      this.closeBoardModal()
    },
    onChatEditDone() {
      this.$chats.setActiveChat()
    },
    async setActiveChat(chat) {
      chat && await this.$chats.reloadChat(chat)
      this.$chats.setActiveChat(chat)
    },
    async moveChatsToColumn({ chats, column }) {
      await Promise.all(
        chats.map(chat => this.$chats.saveChatInfo({ ...chat, column }))
      )
    }
  }
}
</script>

<style scoped>
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.25s ease, opacity 0.25s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.slide-left-enter-from,
.slide-left-leave-to {
  transform: translateX(-20px);
  opacity: 0;
}

.slide-right-enter-active,
.slide-right-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.slide-right-enter-from,
.slide-right-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>