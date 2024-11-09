<template>
  <div class="absolute top-0 left-0 right-0 bottom-0 flex flex-col justify-start items-center bg-base-300/10 z-50 p-12">
    <slot></slot>
  </div>
</template>
<script>
export default {
  mounted () {
    this.$root.$el.appendChild(this.$el)
  }
}
</script>