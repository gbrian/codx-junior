<script setup>
</script>

<template>
<div>
  <div>
    <label class="block mb-2">Name</label>
    <input v-model="board.title" type="text" class="input input-bordered w-full mb-4" />
    <label class="block mb-2">Description</label>
    <textarea v-model="board.description" class="textarea textarea-bordered w-full mb-4"></textarea>
    <label class="block mb-2">Remote board <i class="fa-solid fa-link"></i> </label>
    <input v-model="board.remote_url" type="text" class="input input-bordered w-full mb-4" />
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