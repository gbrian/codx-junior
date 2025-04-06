<script setup>
import { ref, reactive } from 'vue'
</script>

<template>
  <div class="w-full h-full flex flex-col gap-4 p-4">
    <div class="flex items-center">
      <img :src="user.avatar" alt="User Avatar" class="rounded-full w-16 h-16 mr-4">
      <div>
        <div class="font-bold text-xl">{{ user.name }}</div>
        <div class="text-gray-600">{{ user.email }}</div>
      </div>
    </div>

    <div class="flex flex-col gap-2">
      <input v-model="user.name" class="input input-bordered" placeholder="Name" />
      <input v-model="user.email" class="input input-bordered" placeholder="Email" />
    </div>

    <button class="btn btn-primary" @click="saveUser">Save</button>
  </div>
</template>

<script>
export default {
  data() {
    return {
      user: reactive({
        name: '',
        email: '',
        avatar: ''
      })
    }
  },
  methods: {
    saveUser() {
      $user.saveUser(this.user)
    }
  }
}
</script>