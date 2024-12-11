<script setup>
import NoVNC from '../NoVNC.vue';
</script>
<template>
  <NoVNC class="m-1" :token="$ui.monitorToken" :key="$ui.monitorToken"/>
</template>

<script>
export default {
  data () {
    return {
      chat: {
        messages: []
      }
    }
  },
  methods: {
  }
}
</script>

