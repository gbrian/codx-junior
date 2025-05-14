<script setup>
import { ref } from 'vue';

const email = ref('');
const register = () => {
  // Add register logic here
}
</script>

<template>
  <form @submit.prevent="register">
    <input v-model="email" type="email" placeholder="Email" required />
    <button type="submit">Register</button>
  </form>
</template>