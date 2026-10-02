<script setup>
</script>

<template>
  <div class="flex flex-col gap-2">
    <h2 class="text-lg font-bold mb-2">{{ plugin.name }}</h2>
    <!-- Editable plugin details -->
    <div v-for="arg in editablePlugin.arguments" :key="arg.name" class="mb-2">
      <div v-text="arg.name" class="block"></div>
      <input v-model="arg.default_value" type="text" class="input input-bordered w-full" />
    </div>

    <div class="modal-action">
      <button @click="updatePlugin" class="btn btn-sm btn-success">Save Changes</button>
      <button @click="removePlugin" class="btn btn-sm btn-error">{{ confirmDeletion ? "Confirm Deletion?" : "Delete" }}</button>
    </div>
  </div>
</template>

<script>
export default {
  props: ['plugin'],
  data() {
    return {
      editablePlugin: { ...this.plugin },
      confirmDeletion: false,
    }
  },
  methods: {
    async updatePlugin() {
      this.$emit('save', this.editablePlugin)
    },
    async removePlugin() {
      if (this.confirmDeletion) {
        this.$emit('remove')
      } else {
        this.confirmDeletion = true
      }
    }
  }
}
</script>