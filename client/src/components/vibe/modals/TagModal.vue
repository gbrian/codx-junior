<script setup>
</script>

<template>
  <div class="flex flex-col gap-3 p-4">
    <div class="text-lg font-bold">Add tag</div>
    <select class="select select-sm select-bordered" @change="tagInput = $event.target.value">
      <option value="">New tag...</option>
      <option v-for="t in $storex.projects.allTags" :key="t" :value="t">{{ t }}</option>
    </select>
    <input type="text" class="input input-sm input-bordered" v-model="tagInput" placeholder="Tag name" />
    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm btn-error" @click="$emit('close')">Cancel</button>
      <button class="btn btn-sm" @click="submit" :disabled="!tagInput">Add</button>
    </div>
  </div>
</template>

<script>
export default {
  emits: ['add', 'close'],
  data() {
    return {
      tagInput: ''
    }
  },
  methods: {
    submit() {
      if (!this.tagInput) return
      this.$emit('add', this.tagInput)
      this.tagInput = ''
    }
  }
}
</script>