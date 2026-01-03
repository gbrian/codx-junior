<script setup>
import { ref } from 'vue';

const email = ref('');
const register = () => {
  // Add register logic here
}
</script>

<template>
  <form class="flex gap-2 items-center" @submit.prevent="register">
    <div class="border border-white p-2 rounded-full">
    <input v-model="email" type="email" placeholder="Email" required />
    </div>
    <button class="btn" type="submit">Register</button>
  </form>
</template>