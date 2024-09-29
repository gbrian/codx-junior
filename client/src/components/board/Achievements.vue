<template>
  <div class="achievements flex justify-around">
    <div v-for="column in kanbanColumns" :key="column.name" class="achievement flex flex-col items-center">
      <img :src="column.icon" alt="Column Icon" class="w-12 h-12" />
      <span class="text-lg font-semibold">{{ column.taskCount }}</span>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      kanbanColumns: [
        { name: 'To Do', icon: 'path/to/todo-icon.jpg', taskCount: 10 },
        { name: 'In Progress', icon: 'path/to/inprogress-icon.jpg', taskCount: 5 },
        { name: 'Done', icon: 'path/to/done-icon.jpg', taskCount: 20 }
      ]
    }
  }
}
</script>