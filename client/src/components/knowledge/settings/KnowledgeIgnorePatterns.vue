<script setup>
</script>

<template>
  <div class="text-xs font-bold py-2 flex flex-col gap-2">
    <div class="text-xl">Ignored patterns:</div>
    <div class="flex input input-sm input-bordered gap-2 max-w-xs items-center">
      <input
        type="text"
        class="grow"
        v-model="addToIgnore"
        @keydown.enter="submitAdd"
      />
      <div class="btn btn-xs btn-circle btn-warning" @click="submitAdd">
        <i class="fa-solid fa-plus"></i>
      </div>
    </div>
    <div class="grid grid-cols-4 gap-2">
      <span
        class="badge flex gap-2 items-center w-fit rounded-full text-warning"
        v-for="(folder, ix) in ignoredFolders"
        :key="ix"
      >
        {{ folder }}
        <div class="click text-error" @click="$emit('remove', [folder])">
          <i class="fa-solid fa-trash-can"></i>
        </div>
      </span>
    </div>
  </div>
</template>

<script>
export default {
  emits: ['add', 'remove'],
  props: {
    ignoredFolders: Array
  },
  data() {
    return {
      addToIgnore: null
    }
  },
  methods: {
    submitAdd() {
      if (this.addToIgnore) {
        this.$emit('add', [this.addToIgnore])
        this.addToIgnore = null
      }
    }
  }
}
</script>