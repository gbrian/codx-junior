<script setup>
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4" @keydown.esc="$emit('close')">
    <div class="bg-base-200 border border-base-content/10 rounded-xl w-full max-w-sm shadow-xl">
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-base-content/10">
        <h2 class="text-base font-semibold flex items-center gap-2">
          <i class="fa-solid fa-share-nodes text-primary"></i>
          Invite to Meet
        </h2>
        <button @click="$emit('close')" class="btn btn-ghost btn-sm btn-circle">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <!-- Content -->
      <div class="px-6 py-4 space-y-4">

        <!-- Meet info -->
        <div class="p-3 rounded-lg bg-base-content/5 border border-base-content/10 space-y-2">
          <div class="text-xs font-semibold text-base-content/60 uppercase">Meet ID</div>
          <div class="flex items-center gap-2">
            <code class="flex-1 text-sm font-mono bg-base-300 px-3 py-2 rounded text-center">{{ meetId }}</code>
            <button @click="copyMeetId" class="btn btn-ghost btn-sm btn-square">
              <i :class="copied ? 'fa-solid fa-check text-success' : 'fa-regular fa-copy'"></i>
            </button>
          </div>
        </div>

        <!-- Copy invite link -->
        <div class="space-y-2">
          <div class="text-xs font-semibold text-base-content/60 uppercase">Invite Link</div>
          <div class="flex items-center gap-2">
            <input
              type="text"
              :value="inviteLink"
              readonly
              class="input input-bordered input-sm flex-1 text-xs"
            />
            <button @click="copyInviteLink" class="btn btn-ghost btn-sm btn-square">
              <i :class="copiedLink ? 'fa-solid fa-check text-success' : 'fa-regular fa-copy'"></i>
            </button>
          </div>
        </div>

        <!-- Send to online users -->
        <div class="space-y-2">
          <div class="text-xs font-semibold text-base-content/60 uppercase">Send to</div>
          <div v-if="onlineUsers.length > 0" class="space-y-2 max-h-40 overflow-y-auto">
            <button
              v-for="user in onlineUsers"
              :key="user.username"
              @click="selectUser(user.username)"
              class="w-full flex items-center gap-3 p-2.5 rounded-lg border transition-all text-left"
              :class="isSelectedUser(user.username)
                ? 'bg-primary/10 border-primary/40'
                : 'bg-base-content/5 border-base-content/10 hover:border-base-content/20'"
            >
              <div class="relative w-8 h-8 shrink-0">
                <img
                  :src="user.avatar || `https://api.dicebear.com/7.x/initials/svg?seed=${user.username}`"
                  :alt="user.username"
                  class="w-8 h-8 rounded-full"
                />
                <div class="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-success rounded-full border border-base-200"></div>
              </div>
              <div class="flex-1 min-w-0 text-sm font-medium truncate">{{ user.username }}</div>
              <i v-if="isSelectedUser(user.username)" class="fa-solid fa-check text-primary text-xs shrink-0"></i>
            </button>
          </div>
          <div v-else class="text-center py-4 text-base-content/40 text-sm">
            <i class="fa-solid fa-users block text-lg mb-1"></i>
            No other users online
          </div>
        </div>

        <!-- Share options -->
        <div class="space-y-2">
          <div class="text-xs font-semibold text-base-content/60 uppercase">Share via</div>
          <div class="flex gap-2">
            <button
              @click="shareViaClipboard"
              class="flex-1 btn btn-ghost btn-sm gap-2 border border-base-content/20"
              title="Copy to clipboard"
            >
              <i class="fa-regular fa-clipboard"></i>
              Clipboard
            </button>
            <button
              @click="shareViaEmail"
              class="flex-1 btn btn-ghost btn-sm gap-2 border border-base-content/20"
              title="Share via email"
              disabled
            >
              <i class="fa-regular fa-envelope"></i>
              Email
            </button>
          </div>
        </div>

      </div>

      <!-- Actions -->
      <div class="flex gap-3 px-6 py-4 border-t border-base-content/10">
        <button @click="$emit('close')" class="flex-1 btn btn-ghost btn-sm">
          Close
        </button>
        <button
          @click="sendInvites"
          :disabled="selectedUsers.length === 0"
          class="flex-1 btn btn-primary btn-sm gap-2"
        >
          <i class="fa-solid fa-send"></i>
          Send Invites
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MeetInviteModal',
  props: {
    meetId: { type: String, default: '' }
  },
  emits: ['close', 'invites-sent'],
  data() {
    return {
      selectedUsers: [],
      copied: false,
      copiedLink: false,
      copyTimeout: null
    }
  },
  computed: {
    inviteLink() {
      const { origin } = window.location
      return `${origin}/meet/${this.meetId}`
    },
    onlineUsers() {
      const onlineMap = this.$storex.users.onlineUsers || {}
      const currentUser = this.$storex.users.user?.username
      return Object.values(onlineMap)
        .filter(u => u.username && u.username !== currentUser)
        .slice(0, 15)
    }
  },
  methods: {
    selectUser(username) {
      const idx = this.selectedUsers.indexOf(username)
      if (idx > -1) {
        this.selectedUsers.splice(idx, 1)
      } else {
        this.selectedUsers.push(username)
      }
    },
    isSelectedUser(username) {
      return this.selectedUsers.includes(username)
    },
    copyMeetId() {
      navigator.clipboard.writeText(this.meetId)
      this.copied = true
      clearTimeout(this.copyTimeout)
      this.copyTimeout = setTimeout(() => {
        this.copied = false
      }, 2000)
    },
    copyInviteLink() {
      navigator.clipboard.writeText(this.inviteLink)
      this.copiedLink = true
      clearTimeout(this.copyTimeout)
      this.copyTimeout = setTimeout(() => {
        this.copiedLink = false
      }, 2000)
    },
    shareViaClipboard() {
      const text = `Join my meet: ${this.inviteLink}`
      navigator.clipboard.writeText(text)
      this.$storex.session.onInfo('Invite link copied to clipboard')
    },
    shareViaEmail() {
      // Not implemented yet
      this.$storex.session.onWarning('Email sharing coming soon')
    },
    async sendInvites() {
      if (this.selectedUsers.length === 0) return

      try {
        for (const username of this.selectedUsers) {
          // Mock: in real implementation, would emit socket event
          if (!this.$storex.meets._mockMode) {
            this.$storex.session.emit({
              event: 'meet-invitation',
              data: {
                meetId: this.meetId,
                to: username,
                from: this.$storex.users.user?.username,
                inviteLink: this.inviteLink,
                timestamp: new Date().getTime()
              }
            })
          }
        }

        this.$storex.session.onInfo(`Invite sent to ${this.selectedUsers.length} user(s)`)
        this.$emit('invites-sent', this.selectedUsers)
        this.$emit('close')
      } catch (error) {
        console.error('Failed to send invites:', error)
        this.$storex.session.onError('Failed to send invites')
      }
    }
  },
  beforeUnmount() {
    clearTimeout(this.copyTimeout)
  }
}
</script>