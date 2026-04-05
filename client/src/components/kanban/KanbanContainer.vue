<script setup>
import ChatViewVue from '../../views/ChatView.vue'
import KanbanList from './KanbanList.vue'
import ChatHistoryVue from './ChatHistory.vue'
import Kanban from './Kanban.vue'
import NewEditBoardModal from './NewEditBoardModal.vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-1">
    
    <!-- Chat History -->
    <ChatHistoryVue 
      :projects="[$project, ...$projects.childProjects]" 
      v-if="showHistory" />
    
    <!-- Kanban list -->
    <KanbanList
      :boards="boards"
      @select="selectBoard"
      @new="showNewBoardModal"
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
      v-if="showKanban" 
    />

    <modal close="true" @close="editBoard = null" v-if="editBoard">
      <NewEditBoardModal :board="editBoard" :boards="boards" @save="onSaveBoard" />
    </modal>
  </div>
</template>

<script>
export default {
  data() {
    return {
      showHistory: false,
      editBoard: null
    }
  },
  created() {
    this.projectChanged()
  },
  computed: {
    kanban() {
      return this.$projects.kanban || { boards: {} }
    },
    // Raw store boards — plain config objects, no tasks or view data attached
    rawBoards() {
      const { boards = {} } = this.kanban
      return Object.keys(boards).reduce((acc, id) => {
        acc[id] = { ...boards[id], id, title: id }
        return acc
      }, {})
    },
    // boards: enriched view-only map (adds tasks for KanbanList display)
    boards() {
      const keys = Object.keys(this.kanban.boards) 
      return keys.map(title => ({ title, ...this.kanban.boards[title] }))
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
      return !this.showHistory && !this.showChatView && this.activeBoard
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
    async setActiveChat(chat) {
      chat && await this.$projects.reloadChat(chat)
      this.$projects.setActiveChat(chat)
    },

    async projectChanged() {
      await this.$projects.loadKanban()
      this.selectBoard()
    },
    async selectBoard(board) {
      await this.$projects.setActiveBoard(board)
    },
    onEditBoard(board) {
      this.editBoard = board
    },
    onSaveBoard(board) {
      this.editBoard = null
    },
    showNewBoardModal() {},
    toggleBookmark() {},
    onDeleteBoard() {},
    onChatEditDone() {
      this.$projects.setActiveChat()
    },
    createSubTask() {},
    createSubTasks() {},
    setActiveChat() {},
    moveChatsToColumn() {},      
  }
}
</script>