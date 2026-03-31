<script setup>
</script>

<template>
  <modal v-if="show">
    <div class="flex flex-col gap-2">
      <div class="text-xl">Project file</div>
      <input
        type="text"
        class="input input-bordered"
        placeholder="File path"
        :value="filePath"
        @input="$emit('update:filePath', $event.target.value)"
      />
      <button class="btn btn-sm" @click="$emit('add-file')">
        Add file
      </button>
      <label class="file-select flex flex-col gap-2">
        <div class="select-button">
          <span>Select File(s)</span>
        </div>
        <input type="file" accept="image/*" multiple @change="$emit('file-change', $event)" />
      </label>
      <button class="btn btn-sm btn-error" @click="$emit('close')">
        Cancel
      </button>
    </div>
  </modal>
</template>

<script>
export default {
  props: {
    show: Boolean,
    filePath: { type: String, default: '' }
  },
  emits: ['close', 'add-file', 'file-change', 'update:filePath']
}
</script>