<script setup>
</script>

<template>
  <div class="flex flex-col gap-4 p-2 w-80">
    <h3 class="font-bold text-lg flex items-center gap-2">
      <i class="fa-solid fa-folder text-primary"></i>
      Category Settings
    </h3>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Category Name *</label>
      <input
        v-model="draft.name"
        type="text"
        class="input input-bordered input-sm"
        placeholder="General"
        @keydown.enter="save"
      />
    </div>

    <!-- Danger zone -->
    <div class="divider text-xs text-error/60 my-0">Danger Zone</div>
    <button class="btn btn-sm btn-error btn-outline w-full" @click="$emit('delete')">
      <i class="fa-solid fa-trash"></i>
      Delete Category
    </button>

    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button class="btn btn-sm btn-primary" :disabled="!draft.name?.trim()" @click="save">
        Save
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'CategorySettings',
  emits: ['save', 'close', 'delete'],
  props: {
    category: { type: Object, required: true }
  },
  data() {
    return {
      draft: {}
    }
  },
  created() {
    this.draft = { ...this.category }
  },
  methods: {
    save() {
      if (!this.draft.name?.trim()) return
      this.$emit('save', { ...this.draft })
    }
  }
}
</script>