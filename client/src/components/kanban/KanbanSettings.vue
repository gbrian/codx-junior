<script setup>
</script>

<template>
  <div class="w-full h-full flex flex-col gap-2">
    <h2 class="font-bold text-lg">Edit Kanban Board Settings</h2>
    <input type="text" v-model="boardData.name" placeholder="Enter board name" class="input input-bordered w-full mt-2" />
    <input type="text" v-model="boardData.description" placeholder="Enter board description" class="input input-bordered w-full mt-2" />
    <input type="text" v-model="boardData.branch" placeholder="Enter branch name" class="input input-bordered w-full mt-2" />
    <select v-model="boardData.template" class="select select-bordered w-full mt-2">
      <option disabled value="">Select a Template</option>
      <option v-for="template in templates" :key="template.name" :value="template">{{ template.name }}</option>
    </select>
    <div class="modal-action">
      <button class="btn" @click="updateBoardSettings">Save</button>
      <button class="btn" @click="cancelEdit">Cancel</button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    board: {
      type: Object,
      required: true
    },
    templates: {
      type: Array,
      required: true
    }
  },
  data() {
    return {
      boardData: { ...this.board }
    }
  },
  methods: {
    updateBoardSettings() {
      this.$emit('update-board', this.boardData)
    },
    cancelEdit() {
      this.$emit('cancel-edit')
    }
  }
}
</script>