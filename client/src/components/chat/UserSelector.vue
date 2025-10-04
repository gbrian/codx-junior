<script setup>
import UserAvatar from '../user/UserAvatar.vue'
</script>

<template>
    <div class="dropdown click" @click.stop="">
        <div tabindex="0" class="flex items-end gap-1 text-xs font-bold" @click="toggleDropdown">
          <UserAvatar class="ring rounded-full h-6" :user="selectedUser" width="6" v-if="selectedUser" />
          <div v-else>
            <i class="fa-solid fa-plus"></i>
          </div>
          <div v-if="!mini">
            {{ selectedUser?.name || selectedUser?.username }}
          </div>
        </div>
        <ul v-if="isOpen" tabindex="0" class="dropdown-content menu bg-base-100 rounded-box z-[150] w-52 p-2 shadow">
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
  props: ['selectedUser', 'mini', 'open', 'allUsers'],
  data() {
    return {
      isOpen: false,
    }
  },
  computed: {
    // Combine users from user and project profiles
    usersList() {
      const users = [...this.$projects.userList]
      if (this.allUsers) {
        users.push(this.$project.users.map(u => ({ ...u, name: u.username })))
      }
      return users.filter((v,ix,arr) => arr.findIndex(u => u.name === v.name) === ix)
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