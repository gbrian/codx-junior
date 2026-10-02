<script setup>
</script>

<template>
  <div class="flex flex-col gap-4 p-4 min-w-96">
    <h3 class="font-bold text-lg">Split into subtasks</h3>
    <textarea v-model="instructions" class="textarea textarea-bordered" rows="4" placeholder="Instructions for AI..." />
    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button class="btn btn-sm btn-primary" @click="submit">Create</button>
    </div>
  </div>
</template>

<script>
export default {
  emits: ['create', 'close'],
  data() {
    return {
      instructions: ''
    }
  },
  methods: {
    submit() {
      this.$emit('create', this.instructions)
      this.instructions = ''
    }
  }
}
</script>