<template>
  <div class="modal modal-open" role="dialog">
    <div class="modal-box">
      <h3 class="font-bold text-lg">Add file</h3>
      <input type="text" class="input input-bordered w-full"
        placeholder="absolute path" v-model="filePath" />
      <div class="modal-action">
        <label for="my_modal_6" class="btn btn-success" @click="$emit('open', filePath)">
          Open
        </label>
        <label for="my_modal_6" class="btn" @click="$emit('close')">
          Close
        </label>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  data () {
    return {
      filePath: null
    }
  }
}
</script>