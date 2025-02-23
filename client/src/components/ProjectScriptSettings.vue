<script setup>
import { ref, watch } from 'vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4 p-4">
    <h1 class="text-xl font-bold">Edit Project Script</h1>
    <div class="flex flex-col gap-4">
      <div class="form-control">
        <label class="label" for="name">Name:</label>
        <input class="input input-bordered" type="text" id="name" v-model="formData.name" required />
      </div>

      <div class="form-control">
        <label class="label" for="description">Description:</label>
        <textarea class="textarea textarea-bordered" id="description" v-model="formData.description"></textarea>
      </div>

      <div class="form-control">
        <label class="label" for="script">Script:</label>
        <textarea class="textarea textarea-bordered" id="script" v-model="formData.script" required></textarea>
      </div>

      <div class="form-control">
        <label class="label" for="status">Status:</label>
        <select class="select select-bordered" id="status" v-model="formData.status">
          <option value="running">Running</option>
          <option value="stopped">Stopped</option>
          <option value="error">Error</option>
        </select>
      </div>

      <div class="form-control">
        <label class="label cursor-pointer" for="background">
          <span>Background:</span>
          <input class="toggle" type="checkbox" id="background" v-model="formData.background" />
        </label>
      </div>

      <div class="form-control">
        <label class="label cursor-pointer" for="restart">
          <span>Restart:</span>
          <input class="toggle" type="checkbox" id="restart" v-model="formData.restart" />
        </label>
      </div>

      <div class="flex gap-4">
        <button class="btn btn-primary" @click="saveChanges">Save</button>
        <button class="btn btn-secondary" @click="discardChanges">Discard</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['project_script'],
  data() {
    return {
      formData: {
        name: '',
        description: '',
        script: '',
        status: 'stopped',
        background: false,
        restart: false
      }
    }
  },
  watch: {
    project_script: {
      handler(newScript) {
        if (newScript) {
          this.formData = { ...newScript }
        }
      },
      immediate: true
    }
  },
  methods: {
    saveChanges() {
      this.$emit('save', this.formData)
    },
    discardChanges() {
      this.$emit('discard', this.formData)
    }
  }
}
</script>