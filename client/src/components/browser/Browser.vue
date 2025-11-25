<script setup>
import NoVNC from '../NoVNC.vue';
</script>
<template>
  <NoVNC :token="token" :key="token"/>
</template>

<script>
export default {
  props: ['token'],
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

