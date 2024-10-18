<script setup>
</script>

<template>
  <div class="w-full h-full flex bg-base-300 relative" data-theme="dark">
    <router-view />
  </div>
</template>
<script>
export default {
  data () {
    return {
    }
  },
  created () {
    this.$storex.init()
  },
  computed: {
  },
  watch: {
  },
  methods: {
  }
}
</script>
