<script setup>
import ProjectDetailt from '../ProjectDetailt.vue'
</script>

<template>
  <div class="w-full">
    <h2 class="font-bold text-3xl mb-4">{{ board?.id ? 'Edit Board' : 'Add New Board' }}</h2>

    <div class="space-y-4">
      <!-- Board name input -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Board Name</span>
        </label>
        <input 
          type="text" 
          v-model="boardData.title" 
          placeholder="Enter board name" 
          class="input input-bordered w-full"
        />
      </div>

      <!-- Board description input -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Description</span>
        </label>
        <textarea 
          v-model="boardData.description" 
          placeholder="Enter board description" 
          class="textarea textarea-bordered w-full"
          rows="3"
        ></textarea>
      </div>

      <!-- Board background image -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Background Image URL</span>
        </label>
        <input 
          type="text" 
          v-model="boardData.background" 
          placeholder="Enter background image URL" 
          class="input input-bordered w-full"
        />
        <div v-if="boardData.background" class="mt-2 h-20 rounded bg-cover bg-center opacity-50"
          :style="{ backgroundImage: `url(${boardData.background})` }"
        ></div>
      </div>

      <!-- Parent board selector -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Parent Board</span>
        </label>
        <select v-model="boardData.parent_id" class="select select-bordered w-full">
          <option :value="null">-- None --</option>
          <option v-for="b in availableBoards" :key="b.id" :value="b.id">
            {{ b.title }}
          </option>
        </select>
      </div>

      <!-- Project selector -->
      <div class="form-control">
        <label class="label">
          <span class="label-text font-semibold">Project</span>
        </label>
        <ProjectDetailt 
          v-model="boardData.project_id" 
          :options="{ showFolders: false, showIcon: true, showSelector: true }"
        />
      </div>
    </div>

    <!-- Delete warning -->
    <div class="mt-6 flex justify-end font-bold text-warning gap-2" v-if="confirmDelete">
      <i class="fa-solid fa-triangle-exclamation"></i>
      <span>All tasks will be deleted</span>
      <span @click="confirmDelete = false" class="text-error cursor-pointer underline">Cancel</span>
    </div>

    <!-- Action buttons -->
    <div class="modal-action mt-6">
      <button 
        class="btn btn-error" 
        @click="deleteBoard" 
        v-if="board?.id"
      >
        {{ confirmDelete ? 'Confirm Delete?' : 'Delete' }}
      </button>
      <div class="grow"></div>
      <button class="btn" @click="$emit('cancel-edit')">Cancel</button>
      <button 
        class="btn btn-primary" 
        @click="saveBoard"
        :disabled="!boardData.title"
      >
        Save
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    board: {
      type: Object,
      default: () => ({})
    },
    boards: {
      type: Array,
      default: () => []
    }
  },
  data() {
    return {
      boardData: {},
      confirmDelete: false
    }
  },
  computed: {
    availableBoards() {
      // Filter out current board from parent options
      return (this.boards || []).filter(b => b.id !== this.board?.id)
    }
  },
  watch: {
    board: {
      handler(newBoard) {
        this.boardData = newBoard ? { ...newBoard } : {}
      },
      deep: true,
      immediate: true
    }
  },
  methods: {
    saveBoard() {
      if (!this.boardData.title?.trim()) return
      this.$emit('change', this.boardData)
    },
    deleteBoard() {
      if (!this.confirmDelete) {
        this.confirmDelete = true
        return
      }
      this.$emit('delete', this.boardData)
    }
  }
}
</script>