<script setup>
import KanbanList from './KanbanList.vue'
import Kanban from './Kanban.vue'
import NewEditBoardModal from './NewEditBoardModal.vue'
</script>

<template>
  <div class="@container p-2 w-full h-full flex flex-col gap-1 overflow-auto">

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

    <!-- New/Edit Board modal — uses KanbanSettings -->
    <modal close="true" @close="closeBoardModal" v-if="showBoardModal">
      <NewEditBoardModal
        :board="editingBoard"
        :boards="boards"
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
      // editingBoard: board config object passed into KanbanSettings
      editingBoard: null
    }
  },
  created() {
    this.projectChanged()
  },
  watch: {
    $project() {
      this.projectChanged()
    }
  },
  computed: {
    project() {
      return this.$projects.allProjectsById[this.params.params.project_id]
    },
    kanban() {
      return this.$projects.kanban || { boards: {} }
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
      return !this.showHistory && !!this.activeBoard
    },
    showKanbanList() {
      return !this.showHistory && !this.showKanban
    }
  },
  methods: {
    async projectChanged() {
      await this.$projects.loadKanban()
      this.selectBoard()
    },

    async selectBoard(board) {
      await this.$projects.setActiveBoard(board)
    },

    // Open modal for creating a new board (blank editingBoard)
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

    // Open modal for editing an existing board
    onEditBoard(board) {
      const title = board?.title || this.activeBoard
      this.editingBoard = { title, ...this.kanban.boards[title] }
      this.showBoardModal = true
    },

    // Save new or updated board from KanbanSettings @change
    async onSaveBoard(board) {
      if (!board?.title) return
      this.kanban.boards[board.title] = {
        ...board,
        id: board.id || board.title
      }
      await this.$projects.saveKanban()
      this.closeBoardModal()
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
      this.$projects.saveKanban()
    },

    async onDeleteBoard(board) {
      // Accept either a board object or a plain title string
      const boardTitle = board?.title || board
      if (!boardTitle || !this.kanban.boards[boardTitle]) return
      delete this.kanban.boards[boardTitle]
      await this.$projects.saveKanban()
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