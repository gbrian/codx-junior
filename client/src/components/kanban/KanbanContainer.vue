<script setup>
import KanbanList from './KanbanList.vue'
import Kanban from './Kanban.vue'
import NewEditBoardModal from './NewEditBoardModal.vue'
import ChatView from '@/views/ChatView.vue'
</script>

<template>
  <div class="@container p-2 w-full h-full flex flex-col gap-1 overflow-auto">
    <!-- ChatView -->
    <ChatView :chat="activeChat" 
      @chats="$chats.setActiveChat(null)"
      v-if="activeChat" />

    <!-- Kanban list -->
    <KanbanList
      :boards="boards"
      :project="project"
      @select="selectBoard"
      @new-board="showNewBoardModal"
      @bookmark="toggleBookmark"
      @delete="onDeleteBoard"
      v-if="showKanbanList"
    />

    <!-- Kanban board view -->
    <Kanban
      :project="project"
      @edit-board="onEditBoard"
      @select-board="selectBoard"
      v-if="showKanban"
    />

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