<script setup>
import UserAvatar from '../user/UserAvatar.vue'
</script>

<template>
    <div class="dropdown click" @click.stop="">
        <div tabindex="0" class="flex items-end gap-1 text-xs font-bold" @click="toggleDropdown">
          <UserAvatar class="ring rounded-full h-6" :user="selectedUser" width="6" />
          <div v-if="!mini">
            {{ selectedUser.name || selectedUser.username }}
          </div>
        </div>
        <ul v-if="isOpen" tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[50] w-52 p-2 shadow">
        <li v-for="user in usersList" :key="user.id" @click="selectUser(user)">
            <a>
              <UserAvatar :user="user" width="6" />
              {{ user.name || user.username }}
            </a>
        </li>
        </ul>
    </div>
</template>

<script>
export default {
  props: ['selectedUser', 'mini', 'open'],
  data() {
    return {
      isOpen: false,
    }
  },
  computed: {
    // Combine users from user and project profiles
    usersList() {
      return this.$projects.userList
    }
  },
  methods: {
    toggleDropdown() {
      this.isOpen = !this.isOpen
    },
    selectUser(user) {
      this.toggleDropdown()
      this.$emit('user-changed', user)
    }
  }
}
</script>