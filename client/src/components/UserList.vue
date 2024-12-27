<script setup>
import UserAvatar from './UserAvatar.vue';
</script>
<template>
  <div class="flex flex-col gap-1">
    <UserAvatar :user="user" v-for="user in $storex.users.allUsers" :key="user.userName" />
  </div>
</template>