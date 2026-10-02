<script setup>
</script>

<template>
  <div class="flex flex-col gap-4 p-4">
    <h3 class="font-bold text-lg">New Subtask</h3>
    <input v-model="name" type="text" class="input input-bordered input-sm" placeholder="Subtask name" />
    <select v-model="mode" class="select select-bordered select-sm">
      <option value="task">Task</option>
      <option value="chat">Chat</option>
      <option value="vibe">Vibe</option>
      <option value="topic">Topic</option>
      <option value="prview">PR View</option>
    </select>
    <textarea v-model="description" class="textarea textarea-bordered textarea-sm" rows="3" placeholder="Description (optional)" />
    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button class="btn btn-sm btn-primary" @click="submit" :disabled="!name.trim()">Create</button>
    </div>
  </div>
</template>

<script>
export default {
  emits: ['create', 'close'],
  data() {
    return {
      name: '',
      mode: 'task',
      description: ''
    }
  },
  methods: {
    submit() {
      if (!this.name.trim()) return
      this.$emit('create', {
        name: this.name,
        mode: this.mode,
        description: this.description
      })
      this.resetForm()
    },
    resetForm() {
      this.name = ''
      this.mode = 'task'
      this.description = ''
    }
  }
}
</script>