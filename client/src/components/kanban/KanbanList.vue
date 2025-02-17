<script setup>
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2">
    <h1 class="text-2xl font-bold mb-4">Kanban Boards Dashboard</h1>
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4" v-if="boards">
      <div v-for="board in boards" :key="board.title" 
          @click="selectBoard(board)"
        class="click card bg-base-100 shadow-md p-4 rounded-lg border border-sky-400/80">
        <h2 class="font-bold text-lg">{{ board.title }}</h2>
        <p class="text-sm">{{ board.description }}</p>
        <p class="text-xs text-gray-500">Last Update: {{ board.last_update }}</p>
        <div class="flex items-center mt-2">
          <i class="fas fa-columns text-gray-600 mr-2"></i>
          <span>{{ board.columns?.length || 0 }} Columns</span>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: ['boards'],
  methods: {
    selectBoard(board) {
      console.log("WTH", board)
      this.$emit('select', board.title)
    }
  }
}
</script>