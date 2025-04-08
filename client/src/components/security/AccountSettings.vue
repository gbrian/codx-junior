<script setup>
</script>
<template>
  <div class="flex flex-col items-center p-4 gap-4">
    <div class="avatar">
      <div class="w-24 ring rounded-full">
        <img :src="user.avatar" />
      </div>
    </div>
    <div class="flex flex-col gap-2 w-full">
      <div class="text-3xl flex gap-2 items-center"> 
        {{ user.username }}
        <div class="badge badge-primary">{{ user.role }}</div>
      </div>
      <div class="text-xs">{{ user.token }}</div>
      <div class="form-control">
        <span class="font-semibold">Avatar</span>
        <input type="text" v-model="user.avatar" class="input input-bordered w-full" placeholder="Enter avatar URL" />
      </div>
      
      <div class="form-control">
        <span class="font-semibold">Email</span>
        <input type="email" v-model="user.email" class="input input-bordered w-full" placeholder="Enter your email" />
      </div>
      
      <div class="flex justify-between items-center">
        <button type="button" class="btn btn-outline" @click="showResetPasswordModal = true">Reset Password</button>
        <button type="submit" class="btn btn-primary">Update</button>
        <button type="button" class="btn btn-secondary" @click="$users.logout()">Logout</button>
        <modal v-if="showResetPasswordModal" @close="showResetPasswordModal = false">
          <template #header>Reset Password</template>
          <template #body>
            <div class="form-control">
              <span class="font-semibold">New Password</span>
              <input type="password" v-model="newPassword" class="input input-bordered w-full" placeholder="Enter new password" />
            </div>
            <div class="form-control mt-2">
              <span class="font-semibold">Confirm Password</span>
              <input type="password" v-model="confirmPassword" class="input input-bordered w-full" placeholder="Confirm new password" />
            </div>
          </template>
          <template #footer>
            <button type="button" class="btn btn-primary" @click="resetPassword">Confirm</button>
          </template>
        </modal>
      </div>
    </div>
  </div>
</template>
<script>
export default {
  data() {
    return { 
      showResetPasswordModal: false,
      newPassword: '',
      confirmPassword: ''
    }
  },
  computed: {
    user() {
      return this.$user
    }
  },
  methods: {
    resetPassword() {
      if (this.newPassword === this.confirmPassword) {
        this.$users.resetPassword(this.newPassword)
        this.showResetPasswordModal = false
      } else {
        alert('Passwords do not match')
      }
    }
  }
}
</script>