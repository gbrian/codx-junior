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
        class="card card-bordered bg-base-300 shadow-md rounded-lg cursor-pointer"
      >
        <div class="card-body flex flex-col">
          <span class="text-xs" v-if="board.last_update">[{{ moment(board.last_update).fromNow() }}]</span>
          <h2 class="card-title flex justify-between tooltip group" :data-tip="board.title">
            <div class="text-nowrap overflow-hidden">{{ board.title }}</div>
            <span @click.stop="emitEditEvent(board)" class="hidden group-hover:block click text-warning">
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
  </div>
</template>

<script>
export default {
  props: ['boards'],
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