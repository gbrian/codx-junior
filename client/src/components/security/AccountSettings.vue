<script setup>
import ThemeSelector from '../ThemeSelector.vue'
</script>
<template>
  <div class="flex flex-col h-full overflow-auto items-center p-4 gap-4">
    <div class="text-2xl">Account settings</div>
    <div class="avatar">
      <div class="w-24 ring rounded-full">
        <img :src="avatar" />
      </div>
    </div>
    <div class="flex flex-col gap-2 w-full">
      <div class="text-3xl flex gap-2 items-center"> 
        {{ user.username }}
        <div class="badge badge-primary">{{ user.role }}</div>
      </div>
      <div class="text-xs">{{ user.token }}</div>
      <div class="flex justify-between gap-4"
      >
        <div class="form-control">
          <span class="font-semibold">Theme</span>
          <ThemeSelector @change="user.theme = $event"
            class=" tooltip" :data-tip="user.theme"
          />
        </div>
        <div class="form-control grow">
          <span class="font-semibold">Avatar</span>
          <input type="text" v-model="user.avatar" class="input input-bordered w-full" placeholder="Enter avatar URL" />
        </div>
      </div>
      
      <div class="form-control">
        <span class="font-semibold">Email</span>
        <input type="email" v-model="user.email" class="input input-bordered w-full" placeholder="Enter your email" />
      </div>

      <!-- Product shell: managers use the simplified company workspace,
           everyone else keeps today's project workspace. "Automatic" derives
           the shell from the role and the company memberships. -->
      <div class="form-control">
        <span class="font-semibold">Workspace</span>
        <select class="select select-bordered select-sm" :value="user.workspace_mode || 'auto'"
                @change="changeWorkspaceMode($event.target.value)">
          <option value="auto">Automatic (from my role)</option>
          <option value="company">Company workspace</option>
          <option value="work">Working workspace</option>
        </select>
        <span class="text-[10px] text-base-content/50 mt-1">
          Company workspace is the simplified manager view with the codx-junior assistant.
          Working workspace is the full project-oriented codx-junior.
        </span>
      </div>

      <div class="form-control">
        <span class="font-semibold">Assistant language</span>
        <select class="select select-bordered select-sm" v-model="user.language">
          <option value="auto">Automatic (match my message)</option>
          <option value="en">English</option>
          <option value="es">Español</option>
          <option value="pt">Português</option>
          <option value="fr">Français</option>
          <option value="de">Deutsch</option>
          <option value="it">Italiano</option>
          <option value="ca">Català</option>
          <option value="nl">Nederlands</option>
          <option value="ru">Русский</option>
          <option value="ar">العربية</option>
          <option value="zh">中文</option>
          <option value="ja">日本語</option>
        </select>
        <span class="text-[10px] text-base-content/50 mt-1">
          The assistant answers in this language. “Automatic” follows the language
          you write in.
        </span>
      </div>
      
      <div class="flex justify-between items-center">
        <button type="button" class="btn btn-outline" @click="showResetPasswordModal = true">Reset Password</button>
        <button type="submit" class="btn btn-primary" @click="$users.saveUser(user)">Update</button>
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
    },
    avatar () {
      return this.user.avatar
    }
  },
  methods: {
    async changeWorkspaceMode(mode) {
      try {
        await this.$users.setWorkspaceMode(mode)
        window.location.assign('/')
      } catch (error) {
        this.$toast.error('Could not change the workspace mode')
      }
    },
    resetPassword() {
      if (this.newPassword === this.confirmPassword) {
        this.$users.resetPassword(this.newPassword)
        this.$toast.success('Password reset successfully')
        this.showResetPasswordModal = false
      } else {
        this.$toast.error('Passwords do not match')
      }
    }
  }
}
</script>