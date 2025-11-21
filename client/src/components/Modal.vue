<template>
  <div class="absolute top-0 left-0 right-0 bottom-0 flex flex-col justify-center items-center bg-base-300/10 z-50 2xl:p-12">
    <div v-bind="$attrs" class="bg-base-300 rounded-md relative p-4 pt-10">
      <div class="flex justify-end">
        <div class="text-error click mb-2 absolute right-4 top-4" v-if="close" @click="$emit('close')">
          <i class="fa-solid fa-circle-xmark"></i>
        </div>
      </div>
      <div class="h-full flex flex-col gap-2">
        <slot></slot>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  inheritAttrs: false,
  props: ['close'],
  mounted () {
    this.$root.$el.appendChild(this.$el)
  }
}
</script>