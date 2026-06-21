<script setup>
import UserSecuritySettings from './UserSecuritySettings.vue'
</script>

<template>
  <div class="w-full h-full">
    <div class="flex flex-col gap-5 p-5">
      <!-- Header -->
      <div class="flex items-center justify-between bg-gradient-to-r from-primary/10 to-transparent rounded-2xl p-4">
        <div class="flex items-center gap-3">
          <div class="bg-primary/20 rounded-xl p-3">
            <i class="fa-solid fa-users text-primary text-xl"></i>
          </div>
          <div>
            <h1 class="text-lg font-bold">Security Users</h1>
            <p class="text-xs text-base-content-ERROR-40">Manage user access and wallets</p>
          </div>
        </div>
        <button class="btn btn-primary btn-sm gap-1" @click="addNewUser">
          <i class="fa-solid fa-plus"></i> New User
        </button>
      </div>

      <!-- Stats bar -->
      <div class="grid grid-cols-3 gap-3">
        <div class="bg-base-200 rounded-xl p-3 text-center">
          <div class="text-2xl font-bold text-primary">{{ users.length }}</div>
          <div class="text-xs text-base-content/50">Total</div>
        </div>
        <div class="bg-base-200 rounded-xl p-3 text-center">
          <div class="text-2xl font-bold text-success">{{ users.filter(u => !u.disabled).length }}</div>
          <div class="text-xs text-base-content/50">Active</div>
        </div>
        <div class="bg-base-200 rounded-xl p-3 text-center">
          <div class="text-2xl font-bold text-warning">{{ users.filter(u => u.wallet).length }}</div>
          <div class="text-xs text-base-content/50">With Wallet</div>
        </div>
      </div>

      <!-- Cards Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
        <div
          v-for="(user, index) in users"
          :key="user.username"
          class="card bg-base-100 border border-base-300 hover:border-primary/50 hover:shadow-md transition-all cursor-pointer group"
          @click="openUserDetail(user)"
        >
          <div class="card-body p-4 gap-3">
            <!-- Card Header -->
            <div class="flex items-start justify-between">
              <div class="flex items-center gap-2">
                <div class="avatar" :class="user.disabled ? 'grayscale opacity-50' : ''">
                  <div class="w-10 h-10 rounded-lg ring ring-offset-1" :class="user.disabled ? 'ring-error/40' : 'ring-primary/30'">
                    <img :src="user.avatar" :alt="user.username" />
                  </div>
                </div>
                <div>
                  <div class="font-bold text-sm">{{ user.username }}</div>
                  <div class="badge badge-ghost badge-xs font-mono mt-0.5">{{ user.role }}</div>
                </div>
              </div>
              <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  class="btn btn-xs btn-ghost text-error"
                  @click.stop="confirmDeleteUser(index)"
                  title="Delete user"
                >
                  <i class="fa-solid fa-trash text-xs"></i>
                </button>
              </div>
            </div>

            <!-- Email -->
            <div class="flex items-center gap-2 bg-base-200 rounded-lg px-2 py-1.5">
              <i class="fa-solid fa-envelope text-xs text-info"></i>
              <span class="text-xs text-base-content/60 truncate" :title="user.email">
                {{ user.email || 'No email' }}
              </span>
            </div>

            <!-- Wallet info -->
            <div class="flex items-center justify-between text-xs text-base-content/50">
              <span v-if="user.wallet" class="flex items-center gap-1">
                <i class="fa-solid fa-wallet text-success"></i>
                <span class="text-success font-semibold">{{ user.wallet.balance_cxjcoins?.toFixed(4) ?? '0.0000' }}</span>
                <span class="text-base-content-ERROR-40">cxj</span>
              </span>
              <span v-else class="flex items-center gap-1 text-base-content/30">
                <i class="fa-solid fa-wallet"></i> No wallet
              </span>
              <span
                :class="user.disabled ? 'badge badge-error badge-xs' : 'badge badge-success badge-xs'"
              >
                {{ user.disabled ? 'Disabled' : 'Active' }}
              </span>
            </div>

            <!-- Spending limit preview -->
            <div v-if="user.wallet?.spending_limits?.length" class="flex items-center gap-1 text-xs text-base-content-ERROR-40">
              <i class="fa-solid fa-gauge-high text-warning"></i>
              <span>{{ user.wallet.spending_limits.length }} spending limit(s)</span>
              <span class="ml-auto text-warning">
                {{ user.wallet.spending_limits[0].period }}:
                {{ user.wallet.spending_limits[0].limit_cxjcoins }} cxj
              </span>
            </div>
          </div>
        </div>

        <!-- Add New Card -->
        <div
          class="card border-2 border-dashed border-base-300 hover:border-primary/50 cursor-pointer transition-colors group"
          @click="addNewUser"
        >
          <div class="card-body p-4 items-center justify-center gap-2 text-base-content/30 group-hover:text-primary transition-colors">
            <i class="fa-solid fa-plus-circle text-2xl"></i>
            <span class="text-xs font-semibold">Add User</span>
          </div>
        </div>
      </div>

      <!-- Edit User Modal -->
      <modal close="true" class="w-2/3 h-2/3 overflow-auto" @close="userSelected = null" v-if="userSelected">
        <UserSecuritySettings :settings="settings" :user="userSelected" @save="saveUser" />
      </modal>

      <!-- Delete Confirm Modal -->
      <modal close="true" v-if="userToDelete !== null" @close="userToDelete = null">
        <div class="flex flex-col gap-4 p-2">
          <div class="flex items-center gap-3">
            <div class="bg-error/10 rounded-full p-3">
              <i class="fa-solid fa-triangle-exclamation text-error"></i>
            </div>
            <div>
              <div class="font-bold">Delete User</div>
              <div class="text-sm text-base-content/60">
                Remove <strong>{{ users[userToDelete]?.username }}</strong>?
              </div>
            </div>
          </div>
          <div class="flex justify-end gap-2">
            <button class="btn btn-sm btn-ghost" @click="userToDelete = null">Cancel</button>
            <button class="btn btn-sm btn-error" @click="deleteUser">
              <i class="fa-solid fa-trash mr-1"></i>Delete
            </button>
          </div>
        </div>
      </modal>
    </div>
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
  data() {
    return {
      userSelected: null,
      userSelectedIx: -1,
      userToDelete: null
    }
  },
  computed: {
    users() {
      return this.settings.users || []
    }
  },
  methods: {
    openUserDetail(user) {
      this.userSelected = { ...user }
      this.userSelectedIx = this.users.findIndex(u => u === user)
    },
    addNewUser() {
      this.userSelected = {
        role: 'user',
        avatar: 'https://gravatar.com/avatar/baa8db8ab2afb7ababc235269e762662?s=400&d=robohash&r=analyst'
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