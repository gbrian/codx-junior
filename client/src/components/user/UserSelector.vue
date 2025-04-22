<script setup>
</script>

<template>
  <div class="grid grid-cols-3 gap-4">
    <div v-for="user in users" :key="user.id" class="flex items-center p-4 shadow rounded cursor-pointer" @click="selectUser(user)">
      <img :src="user.avatar" alt="User Avatar" class="w-12 h-12 rounded-full mr-4">
      <span>{{ user.username }}</span>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
    }
  },
  computed: {
    users() {
      return this.$storex.api.users
    }
  },
  methods: {
    selectUser(user) {
      this.$emit('select', user)
    }
  }
}
</script>