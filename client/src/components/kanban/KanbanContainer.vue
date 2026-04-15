<script setup>
import ChatViewVue from '../../views/ChatView.vue'
import KanbanList from './KanbanList.vue'
import ChatHistoryVue from './ChatHistory.vue'
import Kanban from './Kanban.vue'
import NewEditBoardModal from './NewEditBoardModal.vue'
</script>

<template>
  <div class="@container p-2 w-full h-full flex flex-col gap-1 overflow-auto">
    <!-- Chat History -->
    <ChatHistoryVue
      :projects="[$project, ...$projects.childProjects]"
      v-if="showHistory" />

    <!-- Kanban list -->
    <KanbanList
      :boards="boards"
      @select="selectBoard"
      @new-board="showNewBoardModal"
      @bookmark="toggleBookmark"
      @delete="onDeleteBoard"
      v-if="showKanbanList"
    />

    <!-- Active chat view -->
    <ChatViewVue
      class="h-full rounded-lg my-2"
      @chats="onChatEditDone"
      @sub-task="createSubTask"
      @sub-tasks="createSubTasks"
      @chat="setActiveChat($event)"
      @change-column="moveChatsToColumn"
      :kanban="activeBoard"
      :chat="$projects.activeChat"
      v-if="showChatView"
    />

    <!-- Kanban board view -->
    <Kanban
      @edit-board="onEditBoard"
      @select-board="selectBoard"
      v-if="showKanban"
    />

    <!-- New/Edit Board modal — uses KanbanSettings -->
    <modal close="true" @close="closeBoardModal" v-if="showBoardModal">
      <NewEditBoardModal
        :board="editingBoard"
        :boards="boards"
        @change="onSaveBoard"
        @cancel-edit="closeBoardModal"
        @delete="onDeleteBoard"
      />
    </modal>

  </div>
</template>

<script>
import { v4 as uuidv4 } from 'uuid'

export default {
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
  computed: {
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
    showChatView() {
      return !this.showHistory && !!this.$projects.activeChat
    },
    showKanban() {
      return !this.showHistory && !this.showChatView && !!this.activeBoard
    },
    showKanbanList() {
      return !this.showHistory && !this.showChatView && !this.showKanban
    }
  },
  watch: {
    project() {
      this.projectChanged()
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
      this.$projects.setActiveChat()
    },

    async setActiveChat(chat) {
      chat && await this.$projects.reloadChat(chat)
      this.$projects.setActiveChat(chat)
    },

    async createSubTask({ parent, name, mode, description, project_id, parent_id, message_id, file_list, activateChat, child_index, column, profiles }) {
      const chat = await this.$projects.createNewChat({
        id: uuidv4(),
        board: parent.board,
        name,
        mode,
        profiles,
        column: column || parent.column,
        parent_id: parent_id || parent.id,
        message_id,
        project_id: project_id || parent.project_id,
        messages: description ? [{ role: 'user', content: description }] : [],
        file_list,
        child_index
      })
      if (activateChat !== false) await this.setActiveChat(chat)
      await this.$projects.saveChat(chat)
      if (description) this.$storex.projects.chatWihProject(chat)
    },

    async createSubTasks(event) {
      this.$projects.createSubtasks(event)
    },

    async moveChatsToColumn({ chats, column }) {
      await Promise.all(
        chats.map(chat => this.$projects.saveChatInfo({ ...chat, column }))
      )
    }
  }
}
</script>