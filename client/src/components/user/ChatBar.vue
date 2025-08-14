<template>
  <div class="flex flex-col">
    <div v-for="user in users" :key="user.username" class="avatar tooltip"
      :data-tip="user.username"
      @click="$service.project.openUserChat(user)"
    >
      <div class="w-8 rounded-full">
        <img :src="user.avatar" @error="user.avatar = errorAvatar" />
      </div>
    </div>
  </div>
</template>
<script>
export default {
  data() {
    return {
      errorAvatar: 'https://freesvg.org/img/abstract-user-flat-4.png'
    }
  },
  computed: {
    users() {
      return this.$project?.users
    }
  }
}
</script>