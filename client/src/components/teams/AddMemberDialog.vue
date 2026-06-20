<script setup>
import MemberAvatar from './MemberAvatar.vue'
</script>

<template>
  <div class="flex flex-col gap-4 p-2 w-80">
    <h3 class="font-bold text-lg flex items-center gap-2">
      <i class="fa-solid fa-user-plus text-primary"></i>
      Add Member
    </h3>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">User *</label>
      <select
        v-model="form.username"
        class="select select-bordered select-sm"
        @change="onUserSelected"
        ref="userSelect"
      >
        <option value="">Select a user...</option>
        <option
          v-for="user in availableUsers"
          :key="user.username"
          :value="user.username"
        >
          {{ user.username }}
        </option>
      </select>
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Role</label>
      <select class="select select-bordered select-sm" v-model="form.role">
        <option value="admin">👑 Admin</option>
        <option value="moderator">🛡️ Moderator</option>
        <option value="member">👤 Member</option>
        <option value="guest">🔍 Guest</option>
      </select>
    </div>

    <!-- Preview -->
    <div v-if="selectedUser" class="flex items-center gap-3 p-3 bg-base-200 rounded-xl">
      <MemberAvatar :member="previewMember" size="sm" :show-status="false" />
      <div>
        <div class="font-semibold text-sm">{{ selectedUser.username }}</div>
        <div class="text-xs text-base-content/50 capitalize">{{ form.role }}</div>
      </div>
    </div>

    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button
        class="btn btn-sm btn-primary"
        :disabled="!form.username"
        @click="submit"
      >
        <i class="fa-solid fa-user-plus"></i>
        Add Member
      </button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AddMemberDialog',
  emits: ['added', 'close'],
  props: {
    team: { type: Object, required: true }
  },
  data() {
    return {
      form: {
        username: '',
        role: 'member'
      },
      selectedUser: null
    }
  },
  mounted() {
    this.$storex.users.loadUsers()
    this.$nextTick(() => this.$refs.userSelect?.focus())
  },
  computed: {
    availableUsers() {
      const allUsers = this.$storex.users.users
      const existingMemberIds = (this.team.members || []).map(m => m.username)
      return allUsers.filter(u => !existingMemberIds.includes(u.username))
    },
    previewMember() {
      if (!this.selectedUser) return null
      return {
        username: this.selectedUser.username,
        role: this.form.role,
        status: 'online'
      }
    }
  },
  methods: {
    onUserSelected() {
      this.selectedUser = this.availableUsers.find(u => u.username === this.form.username) || null
    },
    submit() {
      if (!this.form.username || !this.selectedUser) return
      const member = this.$storex.teams.addMember({
        teamId: this.team.id,
        memberData: {
          username: this.selectedUser.username,
          role: this.form.role,
          status: 'offline'
        }
      })
      this.$emit('added', member)
    }
  }
}
</script>