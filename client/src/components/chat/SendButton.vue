<script setup>
import UserAvatar from '../user/UserAvatar.vue'
</script>

<template>
  <div class="btn btn-sm flex gap-1" @click="sendSelectedUser">
    <div class="dropdown dropdown-top dropdown-end" @click.stop="">
      <div tabindex="0" class="" @click="toggleDropdown">
        <UserAvatar :user="selectedUser" />
      </div>
      <ul v-if="isOpen" tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[50] w-52 p-2 shadow">
        <li v-for="user in usersList" :key="user.id" @click="selectUser(user)">
          <a>{{ user.name }}</a>
        </li>
      </ul>
    </div>
    <div>
      <slot></slot>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      isOpen: false,
      selectedUser: null
    }
  },
  created () {
    this.selectedUser = this.$user
  },
  computed: {
    // Combine users from user and project profiles
    usersList() {
      return [this.$store.state.user, ...this.$store.state.projects.profiles]
    }
  },
  methods: {
    toggleDropdown() {
      this.isOpen = !this.isOpen
    },
    selectUser(user) {
      this.selectedUser = user
      this.toggleDropdown()
    },
    // Emit selected user to the parent component
    sendSelectedUser() {
      const selUser = this.selectedUser === this.$user ? null : this.selectedUser
      this.$emit('send', selUser)
    }
  }
}
</script>