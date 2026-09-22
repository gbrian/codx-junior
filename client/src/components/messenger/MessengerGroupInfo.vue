<template>
  <div class="flex flex-col h-full bg-[#1a1a1a] border-l border-white/5 w-72">

    <!-- Header -->
    <div class="shrink-0 flex items-center gap-3 px-4 py-4 border-b border-white/5">
      <div class="flex-1 min-w-0">
        <h3 class="text-sm font-semibold text-white/80">Group Info</h3>
        <p class="text-[11px] text-white/30 mt-0.5">Manage channel members</p>
      </div>
      <button
        class="w-8 h-8 flex items-center justify-center rounded-lg text-white/30 hover:text-white hover:bg-white/8 transition-colors"
        @click="$emit('close')"
      >
        <i class="fas fa-xmark text-sm"></i>
      </button>
    </div>

    <!-- Channel Name (editable) -->
    <div class="shrink-0 px-4 py-4 border-b border-white/5">
      <label class="text-[10px] text-white/30 uppercase tracking-wider font-semibold block mb-2">Channel Name</label>
      <div class="flex items-center gap-2">
        <input
          v-if="editingName"
          v-model="nameInput"
          ref="nameInput"
          type="text"
          class="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 outline-none focus:border-primary/50"
          @keydown.enter="saveName"
          @keydown.escape="cancelEditName"
          @blur="saveName"
        />
        <span v-else class="flex-1 text-sm text-white/70 font-medium truncate"># {{ chat?.name }}</span>
        <button
          class="w-7 h-7 flex items-center justify-center rounded-lg text-white/30 hover:text-white hover:bg-white/8 transition-colors"
          :title="editingName ? 'Cancel' : 'Edit name'"
          @click="editingName ? cancelEditName() : startEditName()"
        >
          <i :class="editingName ? 'fas fa-xmark' : 'fas fa-pen'" class="text-xs"></i>
        </button>
      </div>
    </div>

    <!-- Members section -->
    <div class="flex-1 overflow-y-auto min-h-0 px-4 py-4">
      <div class="flex items-center justify-between mb-3">
        <label class="text-[10px] text-white/30 uppercase tracking-wider font-semibold">
          Members ({{ currentMembers.length }})
        </label>
      </div>

      <!-- Current members list -->
      <div class="flex flex-col gap-1 mb-4">
        <div
          v-for="member in currentMembers"
          :key="member.name"
          class="flex items-center gap-3 px-3 py-2 rounded-xl bg-white/4 group"
        >
          <!-- Avatar -->
          <div class="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
            <i v-if="member.icon" :class="member.icon" class="text-primary text-xs"></i>
            <span v-else class="text-primary text-xs font-bold">{{ member.name?.charAt(0)?.toUpperCase() }}</span>
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm text-white/70 font-medium truncate">{{ member.name }}</div>
            <div v-if="member.description" class="text-[10px] text-white/30 truncate">{{ member.description }}</div>
          </div>
          <!-- Remove button -->
          <button
            class="w-7 h-7 flex items-center justify-center rounded-lg text-white/0 group-hover:text-white/30 hover:!text-error hover:bg-error/10 transition-all"
            title="Remove from group"
            @click="removeMember(member)"
          >
            <i class="fas fa-xmark text-xs"></i>
          </button>
        </div>

        <div v-if="currentMembers.length === 0" class="text-center py-4 text-white/20 text-xs">
          No members yet
        </div>
      </div>

      <!-- Add members section -->
      <div>
        <label class="text-[10px] text-white/30 uppercase tracking-wider font-semibold block mb-2">Add Members</label>
        <div class="flex items-center gap-2 bg-white/5 rounded-lg px-3 py-2 mb-2">
          <i class="fas fa-magnifying-glass text-white/25 text-xs shrink-0"></i>
          <input
            v-model="memberSearch"
            type="text"
            placeholder="Search profiles..."
            class="bg-transparent text-xs text-white/70 placeholder:text-white/25 outline-none flex-1"
          />
        </div>

        <div class="flex flex-col gap-1 max-h-48 overflow-y-auto">
          <button
            v-for="profile in availableProfiles"
            :key="profile.name"
            class="flex items-center gap-3 px-3 py-2 rounded-xl text-left w-full hover:bg-white/6 transition-colors group"
            @click="addMember(profile)"
          >
            <div class="w-7 h-7 rounded-full bg-white/8 flex items-center justify-center shrink-0">
              <i v-if="profile.icon" :class="profile.icon" class="text-white/40 text-xs"></i>
              <span v-else class="text-white/40 text-xs font-bold">{{ profile.name?.charAt(0)?.toUpperCase() }}</span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-xs text-white/60 font-medium truncate group-hover:text-white/80">{{ profile.name }}</div>
            </div>
            <i class="fas fa-plus text-xs text-white/20 group-hover:text-primary transition-colors"></i>
          </button>

          <div v-if="availableProfiles.length === 0" class="text-center py-4 text-white/20 text-xs">
            {{ memberSearch ? 'No profiles match' : 'All profiles added' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Actions footer -->
    <div class="shrink-0 border-t border-white/5 px-4 py-3">
      <button
        class="flex items-center gap-2 w-full px-3 py-2.5 rounded-xl text-error/60 hover:text-error hover:bg-error/10 transition-colors text-sm"
        @click="$emit('leave-group', chat)"
      >
        <i class="fas fa-right-from-bracket text-sm"></i>
        <span>Leave channel</span>
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, default: null },
    profiles: { type: Array, default: () => [] }
  },
  emits: ['close', 'update-members', 'update-name', 'leave-group'],
  data() {
    return {
      editingName: false,
      nameInput: '',
      memberSearch: ''
    }
  },
  computed: {
    currentMembers() {
      const chatProfiles = this.chat?.profiles || []
      return this.profiles.filter(p => chatProfiles.includes(p.name))
    },
    availableProfiles() {
      const chatProfiles = this.chat?.profiles || []
      const search = this.memberSearch.toLowerCase()
      return this.profiles
        .filter(p => !chatProfiles.includes(p.name))
        .filter(p => !search || p.name?.toLowerCase().includes(search))
    }
  },
  methods: {
    startEditName() {
      this.nameInput = this.chat?.name || ''
      this.editingName = true
      this.$nextTick(() => this.$refs.nameInput?.focus())
    },
    cancelEditName() {
      this.editingName = false
      this.nameInput = ''
    },
    saveName() {
      const name = this.nameInput.trim()
      if (name && name !== this.chat?.name) {
        this.$emit('update-name', name)
      }
      this.editingName = false
    },
    addMember(profile) {
      const current = [...(this.chat?.profiles || [])]
      if (!current.includes(profile.name)) {
        this.$emit('update-members', [...current, profile.name])
      }
    },
    removeMember(profile) {
      const updated = (this.chat?.profiles || []).filter(p => p !== profile.name)
      this.$emit('update-members', updated)
    }
  }
}
</script>