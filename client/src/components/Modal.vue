<template>
  <div class="absolute top-0 left-0 right-0 bottom-0 flex flex-col justify-center items-center bg-base-300/10 z-50 2xl:p-12">
    <div class="modal-box">
      <slot></slot>
    </div>
  </div>
</template>
<script>
export default {
  mounted () {
    this.$root.$el.appendChild(this.$el)
  }
}
</script>