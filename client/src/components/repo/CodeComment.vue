<template>
  <div class="flex w-full flex-col border rounded-md p-2">
    Add comment:
    <textarea class="textarea"  v-model="editComment" />
    <div class="m-[5px] mt-[0.8em] text-right">
      <div class="inline-flex justify-end gap-x-[12px]">
        <button class="rounded-[4px] border px-[12px] py-[6px]" @click="$emit('close')">
          Close
        </button>
        <button
          class="rounded-[4px] border px-[12px] py-[6px]"
          @click="$emit('change', editComment)"
        >
          Save
        </button>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: ['comment'],
  data () {
    return {
      editComment: this.comment
    }
  }
}
</script>
