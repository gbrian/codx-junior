<script setup>
</script>

<template>
  <div class="w-full flex flex-col gap-4">
    <div class="text-xl font-bold">Environment Variables</div>
    <div v-for="(value, key) in settings.env" :key="key" class="flex items-center gap-2">
      <div class="w-1/2 rounded-md p-2 overflow-auto">{{ key  }}</div>
      <div class="w-1/2 rounded-md p-2 overflow-auto">{{ value  }}</div>
      <button class="btn btn-sm btn-success" @click="editKey(key)">
        <i class="fa-regular fa-pen-to-square"></i>
      </button>
      <button class="btn btn-sm btn-error" @click="removeEnvVar(key)">
        <i class="fa-regular fa-circle-xmark"></i>
      </button>
    </div>
    <div class="flex items-center gap-2 mt-2">
      <input v-model="newEnvVarKey" class="input input-sm input-bordered flex-grow" placeholder="New Key" />
      <input v-model="newEnvVarValue" class="input input-sm input-bordered flex-grow" placeholder="New Value" />
      <button class="btn btn-sm btn-primary" @click="addEnvVar">Save</button>
    </div>
  </div>
</template>

<script>
export default {
  props: ['settings'],
  data() {
    return {
      newEnvVarKey: '',
      newEnvVarValue: ''
    }
  },
  methods: {
    editKey(key) {
        this.newEnvVarKey = key
        this.newEnvVarValue = this.settings.env[key]
    },
    addEnvVar() {
      if (this.newEnvVarKey && this.newEnvVarValue) {
        this.settings.env = {
          ...this.settings.env,
          [this.newEnvVarKey]: this.newEnvVarValue 
        }
        this.newEnvVarKey = ''
        this.newEnvVarValue = ''
      }
    },
    removeEnvVar(key) {
      delete this.settings.env[key]
    }
  }
}
</script>