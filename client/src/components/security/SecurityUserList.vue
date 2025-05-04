<script setup>
import UserSecurityDetail from './UserSecurityDetail.vue';
</script>
<template>
  <div>
    <h1 class="text-2xl flex justify-between">
      Security User List
      <button class="btn btn-sm" @click="addNewUser">
        Add
      </button>
    </h1>
    <table class="table">
      <thead>
        <tr>
          <th>Avatar</th>
          <th>Username</th>
          <th>Email</th>
          <th>Role</th>
          <th>Delete</th>
        </tr>
      </thead>
      <tbody>
        <tr class="click" v-for="(user, index) in users" :key="user.username" @click="openUserDetail(user)">
          <td>
            <div class="avatar ring ring-red-600 rounded-md" :class="!user.enabled ? 'ring-red-800 grayscale' : 'ring-sky-800'">
              <div class="w-12 rounded">
                <img :src="user.avatar" />
              </div>
            </div>
          </td>
          <td>{{ user.username }}</td>
          <td>{{ user.email }}</td>
          <td>{{ user.role }}</td>
          <td>
            <i class="fa-solid fa-trash-can cursor-pointer" @click.stop="confirmDeleteUser(index)"></i>
          </td>
        </tr>
      </tbody>
    </table>
    <modal close="true" @close="userSelected = null" v-if="userSelected">
      <UserSecurityDetail :user="userSelected" @save="saveUser" />
    </modal>
    <modal close="true" v-if="userToDelete !== null" @close="userToDelete = null">
      <div class="text-center">
        <h2 class="text-lg">Confirm Deletion</h2>
        <p>Are you sure you want to delete this user?</p>
        <div class="flex justify-center gap-2 mt-4">
          <button class="btn btn-error" @click="deleteUser">Delete</button>
          <button class="btn" @click="userToDelete = null">Cancel</button>
        </div>
      </div>
    </modal>
  </div>
</template>

<script>
export default {
  name: 'SecurityUserList',
  props: {
    settings: {
      type: Object,
      required: true
    }
  },
  data () {
    return {
      userSelected: null,
      userSelectedIx: -1,
      userToDelete: null
    }
  },
  computed: {
    users() {
      return this.settings.users
    }
  },
  methods: {
    openUserDetail(user) {
      this.userSelected = { ...user }
      this.userSelectedIx = this.users.findIndex(u => u === user)
    },
    addNewUser() {
      this.userSelected = {
        "role": "user",
        "avatar": "https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=400&d=robohash&r=analyst",
      }
      this.userSelectedIx = -1
    },
    saveUser() {
      if (this.userSelectedIx === -1) {
        this.users.push(this.userSelected)
      } else {
        this.users.splice(this.userSelectedIx, 1, this.userSelected)
      }
      this.userSelectedIx = -1
      this.userSelected = null
    },
    confirmDeleteUser(index) {
      this.userToDelete = index
    },
    deleteUser() {
      if (this.userToDelete !== null) {
        this.users.splice(this.userToDelete, 1)
        this.userToDelete = null
      }
    }
  }
}
</script>