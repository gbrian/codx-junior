<script setup>
import moment from 'moment'
import KanbanSettings from './KanbanSettings.vue';
import ProjectIcon from '../ProjectIcon.vue';
</script>

<template>
  <div class="w-full flex flex-col gap-2" v-if="boards">
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4" >
      <div
        v-for="board in bookmarks"
        :key="board.title"
        @click="selectBoard(board)"
        class="p-2 card card-bordered bg-base-100 shadow-md rounded-lg cursor-pointer bg-contain relative border-warning h-32">
            <div class="absolute top-0 left-0 bottom-0 right-0 opacity-30 rounded-md bg-cover"
              :style="`background-image: url(${board.background})`" v-if="board.background">
            </div>
          <h2 class="card-title flex tooltip group" :data-tip="board.title">
            <span class="flex items-center">
              <i
                :class="['fa-solid', 'fa-bookmark', board.bookmark ? 'text-warning' : 'text-gray-400']"
                @click.stop="toggleBookmark(board)"
                class="cursor-pointer mr-2"
              ></i>
              <div class="overflow-hidden">{{ board.title }}</div>
            </span>
          </h2>
      </div>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4" >
      <div
        v-for="board in sortedBoards"
        :key="board.title"
        @click="selectBoard(board)"
        class="card card-bordered bg-base-100 shadow-md rounded-lg cursor-pointer bg-contain relative h-60">
        <div class="absolute top-0 left-0 bottom-0 right-0 opacity-30 rounded-md bg-cover"
           :style="`background-image: url(${board.background})`" v-if="board.background">
        </div>
        <div class="card-body flex flex-col">
          <span class="text-xs" v-if="board.last_update">[{{ moment(board.last_update).fromNow() }}]</span>
          <h2 class="card-title flex tooltip group" :data-tip="board.title">
            <span class="flex items-center">
              <i
                :class="['fa-solid', 'fa-bookmark', board.bookmark ? 'text-warning' : 'text-gray-400']"
                @click.stop="toggleBookmark(board)"
                class="cursor-pointer mr-2"
              ></i>
              <div class="overflow-hidden">{{ board.title }}</div>
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
          <div class="text-xs underline overflow-hidden click"
            :title="board.remote_url"
            @click.stop="openRemoteBoard(board)"
            v-if="board.remote_url">
            {{ board.remote_url }}
          </div>

        </div>
      </div>
      <div
        @click="emitNewKanban"
        class="card card-bordered card-dashed bg-base-200 border-slate-600 border-dashed shadow-md p-4 rounded-lg flex items-center justify-center cursor-pointer"
        v-if="options?.addNew !== false"
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
  props: ['boards', 'options'],
  data () {
    return {
    }
  },
  computed: {
    bookmarks() {
      return this.boards.filter(b => b.bookmark)
    },
    sortedBoards() {
      return Object.values(this.boards.filter(b => !b.bookmark))
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
    onDeleteBoard() {
      this.$emit('delete', this.board)
    },
    openRemoteBoard(board) {
      window.open(board.remote_url, '_blank')
    },
    toggleBookmark(board) {
      this.$emit('bookmark', board);
    }
  }
}
</script>