<script setup>
</script>
<template>
  <div class="w-full h-full flex flex-col items-center justify-center gap-4 p-4">
    <form @submit.prevent="handleLogin" class="card w-full max-w-md shadow-lg p-6 rounded-lg bg-base-300/80">
      <h2 class="text-3xl lg:text-5xl font-semibold mb-4 flex gap-2 items-center text-nowrap">
        <div class="avatar">
          <div class="w-24 rounded-full">
            <img src="/only_icon.png" />
          </div>
        </div>
        codx-junior
      </h2>
      <div class="form-control mb-4">
        <label class="label">
          <span class="label-text">Username</span>
        </label>
        <input type="text" v-model="username" class="input input-bordered w-full" placeholder="Enter your username" required />
      </div>
      <div class="form-control mb-6">
        <label class="label">
          <span class="label-text">Password</span>
        </label>
        <input type="password" v-model="password" class="input input-bordered w-full" placeholder="Enter your password" required />
      </div>
      <div class="flex flex-col gap-2">
        <button type="submit" class="btn btn-primary w-full">Login</button>
        <button @click="handleGithubLogin" class="btn w-full">
          Login <i class="fa-brands fa-github"></i>
        </button>
      </div>
    </form>
  </div>
</template>

<script>
export default {
  data() {
    return { 
      username: '', 
      password: '' 
    }
  },
  methods: {
    async handleLogin() {
      if (this.username && this.password) {
        const { username, password } = this
        await this.$users.login({ username, password })
        if (!this.$user) {
          this.$storex.session.onError("Invalid user name or password")
        }
        window.location.reload()
      }
    },
    async handleGithubLogin() {
      try {
        const { auth_url } = await this.$storex.api.oauth.getOAuthLoginUrl('github');
        window.location.href = auth_url;
      } catch (error) {
        this.$storex.session.onError("Failed to initiate GitHub login");
      }
    }
  }
}
</script>
