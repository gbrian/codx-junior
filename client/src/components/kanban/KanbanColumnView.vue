<script setup>
import draggable from 'vuedraggable'
import TaskCard from './TaskCard.vue'
import ChatIcon from '../chat/ChatIcon.vue'
</script>

<template>
  <draggable
    v-model="localColumns"
    group="columns"
    itemKey="id"
    :disabled="$ui.isMobile"
    @end="$emit('column-order-changed', localColumns)"
    class="min-h-60 grid grid-flow-col overflow-x-scroll relative gap-2 justify-start"
  >
    <template #item="{ element: column }">
      <div
        class="bg-info/20 rounded-lg px-3 py-3 w-80 rounded overflow-auto h-full flex flex-col"
        :class="column.color && 'border-t-4'"
        :style="{ borderColor: column.color }"
      >
        <!-- Column header -->
        <div class="group font-semibold font-sans tracking-wide text-sm flex gap-2 items-center">
          <div
            class="cursor-pointer w-6 h-6 flex items-center justify-center rounded-md group shadow-lg bg-base-100"
            :style="{ backgroundColor: column.color }"
            @click="$emit('open-column-props', column)"
          >
            <span class="hidden group-hover:block"><i class="fa-solid fa-bars"></i></span>
            <span class="group-hover:hidden">{{ column.tasks.length }}</span>
          </div>
          <div class="flex gap-2 items-center grow" :class="!column.valid && 'border border-dashed'">
            <div class="flex flex-col">
              {{ column.title }}
              <div class="text-xs -mt-1" v-if="column.project">
                {{ column.project.project_name }}
              </div>
            </div>
          </div>
          <!-- Add task dropdown -->
          <div class="flex gap-2 items-center">
            <div class="dropdown dropdown-end">
              <div tabindex="0" role="button" class="btn btn-sm m-1 flex items-center">
                <i class="mt-1 fa-solid fa-plus"></i>
              </div>
              <ul tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[1] w-52 p-2 shadow">
                <li @click="$emit('new-task', { column, mode: 'chat' })">
                  <a><ChatIcon mode="chat" /> Chat</a>
                </li>
                <li @click="$emit('new-task', { column, mode: 'task' })">
                  <a><ChatIcon mode="task" /> Document</a>
                </li>
                <li @click="$emit('new-task', { column, mode: 'topic' })">
                  <a><ChatIcon mode="topic" /> Discussion</a>
                </li>
                <li @click="$emit('new-task', { column, mode: 'prview' })">
                  <a><ChatIcon mode="prview" /> Changes review</a>
                </li>
                <li @click="$emit('import-task', column)">
                  <a>Import task</a>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <!-- Tasks draggable list -->
        <div class="column-tasks grow overflow-y-auto">
          <draggable
            v-model="column.tasks"
            group="tasks"
            itemKey="id"
            :disabled="$ui.isMobile"
            @end="$emit('task-order-changed', column)"
            class="mt-3 h-full"
          >
            <template #item="{ element: task }">
              <TaskCard
                v-if="taskMatchesFilter(task)"
                :task="task"
                :itemKey="'id'"
                class="cursor-pointer bg-base-100 overflow-hidden mt-2"
                :class="[
                  task.pinned && 'border-warning',
                  lastUpdatedTaskId === task.id ? 'border border-primary border-dashed' : '',
                  (column.showSubTasks !== false) || !task.parent_id ? '' : 'hidden'
                ]"
                @click="$emit('open-task', task)"
              />
            </template>
          </draggable>
        </div>
      </div>
    </template>
  </draggable>
</template>

<script>
export default {
  emits: [
    'column-order-changed',
    'task-order-changed',
    'open-column-props',
    'new-task',
    'import-task',
    'open-task'
  ],
  props: {
    columns: { type: Array, default: () => [] },
    filter: { type: String, default: '' },
    lastUpdatedTaskId: { type: String, default: null }
  },
  data() {
    return {
      // Local copy to allow drag reorder without mutating parent prop directly
      localColumns: []
    }
  },
  watch: {
    columns: {
      immediate: true,
      deep: true,
      handler(val) {
        this.localColumns = val
      }
    }
  },
  methods: {
    taskMatchesFilter(task) {
      const text = this.filter?.toLowerCase() || ''
      if (!text) return true
      return (
        task.name?.toLowerCase().includes(text) ||
        task.messages?.some(m => m.content?.toLowerCase().includes(text))
      )
    }
  }
}
</script>