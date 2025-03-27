<template>
  <div class="absolute top-0 left-0 right-0 bottom-0 flex flex-col justify-center items-center bg-base-300/10 z-50 2xl:p-12">
    <div class="modal-box">
      <div class="flex justify-end">
        <div class="text-error click mb-2" v-if="close" @click="$emit('close')">
          <i class="fa-solid fa-circle-xmark"></i>
        </div>
      </div>
      <slot></slot>
    </div>
  </div>
</template>
<script>
export default {
  props: ['close'],
  mounted () {
    this.$root.$el.appendChild(this.$el)
  }
}
</script>