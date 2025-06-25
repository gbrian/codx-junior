<script setup>
import moment from 'moment'
</script>

<template>
  <div class="w-full flex flex-col gap-2">
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4" v-if="boards">
      <div
        v-for="board in sortedBoards"
        :key="board.title"
        @click="selectBoard(board)"
        class="card card-bordered bg-base-100 shadow-md rounded-lg cursor-pointer"
      >
        <div class="card-body flex flex-col">
          <span class="text-xs" v-if="board.last_update">[{{ moment(board.last_update).fromNow() }}]</span>
          <h2 class="card-title flex justify-between tooltip group" :data-tip="board.title">
            <div class="text-nowrap overflow-hidden">{{ board.title }}</div>
            <span @click.stop="onEditBoard(board)" class="hidden group-hover:block click text-warning">
              <i class="fas fa-cogs"></i>
            </span>
          </h2>
          <p class="text-sm">{{ board.description }}</p>
          <div class="grow"></div>
          <div class="flex justify-between items-center gap-1">
            <div class="flex gap-2 items-center text-xl">
              <i class="fas fa-columns text-gray-600"></i>
              <span class="-mt-1">{{ board.columns?.length || 0 }}</span>
              <i class="fa-brands fa-trello text-gray-600"></i>
              <span class="-mt-1">{{ board.tasks?.length || 0 }}</span>
            </div>
          </div>
        </div>
      </div>
      <div
        @click="emitNewKanban"
        class="card card-bordered card-dashed bg-base-200 border-slate-600 border-dashed shadow-md p-4 rounded-lg flex items-center justify-center cursor-pointer"
      >
        <div class="card-body flex items-center justify-center">
          <i class="fas fa-plus text-gray-600 mr-2"></i>
          <span class="font-bold text-lg">New Kanban</span>
        </div>
      </div>
    </div>
    <modal :close="true" @close="editBoard = null" v-if="editBoard">
      <div>
        <label class="block mb-2">Name</label>
        <input v-model="editBoard.title" type="text" class="input input-bordered w-full mb-4" />
        <label class="block mb-2">Description</label>
        <textarea v-model="editBoard.description" class="textarea textarea-bordered w-full mb-4"></textarea>
        <div class="flex justify-between">
          <button @click="saveBoard" class="btn">Save</button>
          <button @click="deleteBoard" class="btn btn-error">
            <span v-if="confirmDelete">Confirm delete</span>
            <span v-else>Delete</span>
          </button>
        </div>
      </div>
              <div class="mt-2 flex justify-end font-bold text-warning gap-2" v-if="confirmDelete">
          <i class="fa-solid fa-triangle-exclamation"></i>
          All tasks will be deleted
          <span @click="confirmDelete = false" class="text-error click underline">cancel</span>
        </div>

    </modal>
  </div>
</template>

<script>
export default {
  props: ['boards'],
  data () {
    return {
      editBoard: null,
      confirmDelete: false
    }
  },
  created() {
    this.$projects.loadKanban()
  },
  computed: {
    sortedBoards() {
      // Sort boards based on last_update
      return Object.values(this.boards)
        .sort((a, b) => 
          a.last_update && b.last_update ? 
            a.last_update > b.last_update ? -1 : 1 :
              a.last_update ? -1 : 1)
    }
  },
  methods: {
    selectBoard(board) {
      this.$emit('select', board.title)
    },
    emitNewKanban() {
      this.$emit('new')
    },
    saveBoard() {
      this.$emit('edit', this.editBoard)
      this.editBoard = null
    },
    deleteBoard() {
      if (this.confirmDelete) {
        this.$emit('delete', this.editBoard)
        this.editBoard = null
      } else {
        this.confirmDelete = true
      }
    },
    onEditBoard(board) {
      const { title, description } = board
      this.editBoard = { board, title, description }
      this.confirmDelete = false
    }
  }
}
</script>