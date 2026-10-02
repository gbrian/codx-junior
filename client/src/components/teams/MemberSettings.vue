<script setup>
</script>

<template>
  <div class="flex flex-col gap-4 p-2 w-80">
    <h3 class="font-bold text-lg flex items-center gap-2">
      <i class="fa-solid fa-user-gear text-primary"></i>
      Member Settings
    </h3>

    <!-- Avatar -->
    <div class="flex items-center gap-3 p-3 bg-base-200 rounded-xl">
      <div class="avatar placeholder">
        <div class="w-10 h-10 rounded-full bg-secondary text-secondary-content flex items-center justify-center font-bold">
          {{ draft.username?.[0]?.toUpperCase() || '?' }}
        </div>
      </div>
      <div>
        <div class="font-semibold">{{ draft.username }}</div>
        <div class="text-xs text-base-content/50">Joined {{ joinedLabel }}</div>
      </div>
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Username</label>
      <input
        v-model="draft.username"
        type="text"
        class="input input-bordered input-sm"
        placeholder="username"
      />
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Role</label>
      <select class="select select-bordered select-sm" v-model="draft.role">
        <option value="admin">Admin</option>
        <option value="moderator">Moderator</option>
        <option value="member">Member</option>
        <option value="guest">Guest</option>
      </select>
    </div>

    <div class="form-control gap-1">
      <label class="label label-text text-xs font-semibold">Status</label>
      <select class="select select-bordered select-sm" v-model="draft.status">
        <option value="online">🟢 Online</option>
        <option value="away">🟡 Away</option>
        <option value="busy">🔴 Busy</option>
        <option value="offline">⚫ Offline</option>
      </select>
    </div>

    <!-- Danger -->
    <div class="divider text-xs text-error/60 my-0">Danger Zone</div>
    <button class="btn btn-sm btn-error btn-outline w-full" @click="$emit('remove')">
      <i class="fa-solid fa-user-minus"></i>
      Remove from team
    </button>

    <div class="flex gap-2 justify-end">
      <button class="btn btn-sm" @click="$emit('close')">Cancel</button>
      <button class="btn btn-sm btn-primary" @click="save">Save</button>
    </div>
  </div>
</template>

<script>
import moment from 'moment'

export default {
  name: 'MemberSettings',
  emits: ['save', 'close', 'remove'],
  props: {
    member: { type: Object, required: true }
  },
  data() {
    return { draft: {} }
  },
  created() {
    this.draft = { ...this.member }
  },
  computed: {
    joinedLabel() {
      return this.draft.joinedAt ? moment(this.draft.joinedAt).fromNow() : 'recently'
    }
  },
  methods: {
    save() {
      this.$emit('save', { ...this.draft })
    }
  }
}
</script>