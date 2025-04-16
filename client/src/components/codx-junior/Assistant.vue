<script setup>
</script>
<template>
  <div class="flex gap-2 justify-center group relative">
    <div class="absolute -mt-2 right-4 w-96 hidden group-hover:flex transition-all">
      <input type="text" placeholder="How can I help you?" class="input input-bordered w-full" />
    </div>
    <div class="avatar">
      <div class="w-8 rounded-full">
        <img src="/only_icon.png" />
      </div>
    </div>
  </div>
</template>
<script>
export default {
  props: [],
  data() {
    return {}
  },
  computed: {},
  watch: {},
  methods: {}
}
</script>