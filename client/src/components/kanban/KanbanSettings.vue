<script setup>
import ProjectDetailt from '../ProjectDetailt.vue';
</script>

<template>
<div>
  <h2 class="font-bold text-3xl">{{ editBoard ? 'Edit Board' : 'Add New Board' }}</h2>
  
  <ProjectDetailt 
      :project="boardProject" 
      :options="{ folders: false }"
      @select="board.project_id = $event.project_id" />

    <div class="collapse bg-contain"
      :style="`background-image:url('${ newBoardBackground }')`"
    >
      <input type="radio" name="newboard"  v-model="newBoardType" value="manual" />
      <div class="hidden collapse-title text-xl font-medium"><i class="fa-solid fa-gear"></i> Manual settings</div>
      <div class="collapse-content">
        <div class="text-xl text-info font-bold" v-if="activeBoard">Parent {{ activeBoard.title }}</div>
        <input type="text" v-model="board.title" placeholder="Enter board name" class="input input-bordered w-full mt-2"/>
        <input type="text" v-model="newBoardDescription" placeholder="Enter board description" class="input input-bordered w-full mt-2"/>
        <input type="text" v-model="newBoardBackground" placeholder="Enter board backgorund image" class="input input-bordered w-full mt-2"/>
        <select v-model="newBoardParent" class="select select-bordered w-full mt-2">
          <option value="">-- none --</option>
          <option v-for="board in boards" :key="board.id" :value="board.id">{{ board.title }}</option>
        </select>
      </div>
    </div>
    <div class="modal-action">
      <button class="btn" @click="addOrUpdateBoard" :disabled="isBoardNameTaken || !board.title">Save</button>
      <button class="btn" @click="showBoardModal = false">Cancel</button>
    </div>

  <div class="mt-2 flex justify-end font-bold text-warning gap-2" v-if="confirmDelete">
    <i class="fa-solid fa-triangle-exclamation"></i>
    All tasks will be deleted
    <span @click="confirmDelete = false" class="text-error click underline">cancel</span>
  </div>
</div>
</template>

<script>
export default {
  props: ['board'],
  data() {
    return {
      confirmDelete: false
    }
  },
  computed: {
    boardProject() {
      return this.$projects.allProjects.find(p => p.project_id === this.board.project_id)
    }
  },
  methods: {
    updateBoardSettings() {
      this.$emit('change', this.board)
    },
    cancelEdit() {
      this.$emit('cancel-edit')
    },
    deleteBoard() {
      if (this.confirmDelete) {
        this.$emit('delete', this.board)
        this.board = null
      } else {
        this.confirmDelete = true
      }
    },
    saveBoard() {
      this.$emit('change', this.board)
    }
  }
}
</script>