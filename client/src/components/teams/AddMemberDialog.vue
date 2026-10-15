<script setup>
import MemberAvatar from './MemberAvatar.vue'
</script>

<template>
  <div class="flex flex-col gap-4 p-2 w-80">
    <h3 class="font-bold text-lg flex items-center gap-2">
      <i class="fa-solid fa-user-plus text-primary"></i>
      Add Member
    </h3>

    <!-- Member type: a human user or an AI profile -->
    <div class="tabs tabs-boxed tabs-sm">
      <a
        class="tab flex-1"
        :class="form.memberType === 'user' ? 'tab-active' : ''"
        @click="setMemberType('user')"
      >
        <i class="fa-solid fa-user mr-1"></i> User
      </a>
      <a
        class="tab flex-1"
        :class="form.memberType === 'profile' ? 'tab-active' : ''"
        @click="setMemberType('profile')"
      >
        <i class="fa-solid fa-robot mr-1"></i> AI Profile
      </a>
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">
        {{ isProfile ? 'AI Profile' : 'User' }} *
      </label>
      <select
        v-model="form.username"
        class="select select-bordered select-sm"
        @change="onOptionSelected"
        ref="optionSelect"
      >
        <option value="">
          {{ isProfile ? 'Select a profile...' : 'Select a user...' }}
        </option>
        <option
          v-for="opt in selectOptions"
          :key="opt.value"
          :value="opt.value"
        >
          {{ opt.label }}
        </option>
      </select>
    </div>

    <div class="form-control gap-1" v-if="!isProfile">
      <label class="label label-text text-xs font-semibold">Role</label>
      <select class="select select-bordered select-sm" v-model="form.role">
        <option value="admin">👑 Admin</option>
        <option value="moderator">🛡️ Moderator</option>
        <option value="member">👤 Member</option>
        <option value="guest">🔍 Guest</option>
      </select>
    </div>

    <!-- Preview -->
    <div v-if="previewMember" class="flex items-center gap-3 p-3 bg-base-200 rounded-xl">
      <MemberAvatar :member="previewMember" size="sm" :show-status="false" />
      <div>
        <div class="font-semibold text-sm flex items-center gap-1">
          <i v-if="isProfile" class="fa-solid fa-robot text-xs text-primary"></i>
          {{ previewMember.username }}
        </div>
        <div class="text-xs text-base-content/50 capitalize">
          {{ isProfile ? 'AI profile' : form.role }}
        </div>
      </div>
    </div>

    <div v-if="emptyOptions" class="text-xs text-base-content/50 italic">
      {{ isProfile
        ? 'No AI profiles available. Create one from Profiles.'
        : 'No users available to add.' }}
    </div>

    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button
        class="btn btn-sm btn-primary"
        :disabled="!canSubmit || loading"
        :class="loading ? 'loading' : ''"
        @click="submit"
      >
        <i v-if="!loading" class="fa-solid fa-plus"></i>
        Add
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
      loading: false,
      form: {
        memberType: 'user',
        username: '',
        role: 'member'
      },
      selectedUser: null
    }
  },
  mounted() {
    this.$storex.users.loadUsers()
    const project = this.$storex.projects.activeProject
    if (project) this.$storex.profiles.loadProjectProfiles({ project })
    this.$nextTick(() => this.$refs.optionSelect?.focus())
  },
  computed: {
    isProfile() {
      return this.form.memberType === 'profile'
    },
    availableUsers() {
      const allUsers = this.$storex.users.users || []
      const existingMemberUsernames = (this.team.members || []).map(m => m.username)
      return allUsers.filter(u => !existingMemberUsernames.includes(u.username))
    },
    availableProfiles() {
      const profiles = this.$storex.profiles.profiles || []
      const existingProfiles = this.team.profiles || []
      return profiles.filter(p => !existingProfiles.includes(p.name))
    },
    selectOptions() {
      if (this.isProfile) {
        return this.availableProfiles.map(p => ({ value: p.name, label: p.name }))
      }
      return this.availableUsers.map(u => ({ value: u.username, label: u.username }))
    },
    emptyOptions() {
      return this.selectOptions.length === 0
    },
    canSubmit() {
      if (!this.form.username) return false
      return this.isProfile || !!this.selectedUser
    },
    previewMember() {
      if (!this.form.username) return null
      if (this.isProfile) {
        return { username: this.form.username, role: 'ai', status: 'online' }
      }
      return { username: this.form.username, role: this.form.role, status: 'online' }
    }
  },
  methods: {
    setMemberType(type) {
      if (this.form.memberType === type) return
      this.form.memberType = type
      this.form.username = ''
      this.selectedUser = null
    },
    onOptionSelected() {
      this.selectedUser = this.availableUsers
        .find(u => u.username === this.form.username) || null
    },
    async submit() {
      if (!this.canSubmit || this.loading) return
      this.loading = true
      try {
        if (this.isProfile) {
          // AI profiles live on the team's `profiles` list.
          await this.$storex.teams.addProfile({
            teamId: this.team.id,
            profileName: this.form.username
          })
          this.$emit('added')
        } else {
          const member = await this.$storex.teams.addMember({
            teamId: this.team.id,
            memberData: {
              username: this.selectedUser.username,
              role: this.form.role,
              status: 'offline'
            }
          })
          this.$emit('added', member)
        }
      } finally {
        this.loading = false
      }
    }
  }
}
</script>
