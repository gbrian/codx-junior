<script setup>
</script>

<template>
  <modal close="true" @close="close" class="flex flex-col gap-2 w-1/3 h-60">
    <h2 class="text-xl font-semibold mb-4">Load Plugin from File</h2>
    <input v-model="filePath" type="text" placeholder="Enter file path" class="input input-bordered mb-4" />
    <div class="flex justify-end">
      <button @click="loadFile" class="btn btn-sm btn-primary" :disabled="!filePath">Load Plugin</button>
    </div>
  </modal>
</template>

<script>
export default {
  data() {
    return {
      filePath: ''
    }
  },
  methods: {
    async loadFile() {
      if (this.filePath) {
        this.$emit('loadPlugin', this.filePath)
      }
    },
    close() {
      this.$emit('close')
    }
  }
}
</script>