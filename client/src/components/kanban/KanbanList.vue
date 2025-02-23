<script setup>
import moment from 'moment'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2">
    <h1 class="text-2xl font-bold mb-4">Kanban Boards Dashboard</h1>
    <div class="flex justify-end">
      <button class="btn btn-sm btn-warning btn-outline" @click="emitNewKanban">
        <i class="fa-solid fa-plus"></i> New Kanban
      </button>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4" v-if="boards">
      <div
        v-for="board in sortedBoards"
        :key="board.title"
        @click="selectBoard(board)"
        class="card card-bordered bg-base-100 shadow-md p-4 rounded-lg cursor-pointer"
      >
        <div class="card-body flex flex-col">
          <h2 class="card-title">{{ board.title }}</h2>
          <p class="text-sm">{{ board.description }}</p>
          <div class="grow"></div>
          <div class="flex flex-col">
            <p class="text-xs text-gray-500">Last Update: <span v-if="board.last_update">{{ moment(board.last_update).fromNow() }}</span></p>
            <div class="flex items-center mt-2">
              <i class="fas fa-columns text-gray-600 mr-2"></i>
              <span>{{ board.columns?.length || 0 }} Columns</span>
            </div>
          </div>
          <button @click.stop="emitEditEvent(board)" class="btn btn-sm btn-outline mt-2">
            <i class="fas fa-cogs"></i> Edit
          </button>
        </div>
      </div>
      <div
        @click="emitNewKanban"
        class="card card-bordered card-dashed bg-base-100 shadow-md p-4 rounded-lg flex items-center justify-center cursor-pointer"
      >
        <div class="card-body flex items-center justify-center">
          <i class="fas fa-plus text-gray-600 mr-2"></i>
          <span class="font-bold text-lg">New Kanban</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['boards'],
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
      this.$emit('select', board.title) // Emit select event with board title
    },
    emitNewKanban() {
      this.$emit('new') // Emit new Kanban event
    },
    emitEditEvent(board) {
      this.$emit('edit', board) // Emit edit event with board object
    }
  }
}
</script>