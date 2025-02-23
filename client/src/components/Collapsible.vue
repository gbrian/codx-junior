<template lang="pug">
  <div class="w-full h-full flex flex-col gap-2">
    <div class="collapse" :class="expanded === true && 'collapse-open'" @click="expanded = false">
      <input type="checkbox" />
      <div class="collapse-title font-medium text-3xl flex gap-2 items-start">
        <i class="fa-solid fa-caret-down"></i>
        <slot name="title"></slot>
      </div>
      <div class="collapse-content w-full overflow-auto">
        <slot name="content"></slot>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['start-expanded'],
  data() {
    return {
      expanded: !!this.$props.startExpanded
    }
  },
  computed: {
    
  },
  watch: {},
  methods: {
  }
}
</script>