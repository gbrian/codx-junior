<template>
  <div class="flex flex-col gap-2 h-full">
    <div class="text-xl font-medium my-2 flex justify-between">
      Global Settings
    </div>
    <div class="grow relative overflow-auto">
      <div class="flex flex-col">
        <button class="btn btn-warning" @click="updateEngine">
          <i class="fa-solid fa-triangle-exclamation"></i>
          Update engine code base
        </button>
        <div class="text-xs">This action will download latest version from engine.</div>
      </div>
    </div>
  </div>
</template>

<script>
import { API } from '../api/api'
export default {
  data() {
    return {
    };
  },
  methods: {
    updateEngine() {
      API.engine.update()
    },
  },
};
</script>