<script setup>
</script>

<template>
  <div class="flex items-center gap-2 px-3 py-1.5 bg-base-200 border-b border-base-content/10 text-xs shrink-0">
    <!-- Vibe indicator -->
    <span class="flex items-center gap-1 text-success font-mono shrink-0">
      <i class="fa-solid fa-circle text-[8px] animate-pulse"></i>
      vibe
    </span>
    <span class="text-base-content-ERROR-40">|</span>
    <span class="font-mono text-base-content/60 truncate max-w-[120px]">{{ projectName }}</span>

    <!-- Git section -->
    <span class="text-base-content-ERROR-40">|</span>
    <div class="flex items-center gap-1 min-w-0">
      <!-- Current (working) branch -->
      <div class="flex items-center gap-1 min-w-0">
        <i class="fa-solid fa-code-branch text-success text-[10px] shrink-0"></i>
        <select
          class="select select-xs select-bordered w-[110px] max-w-[110px] font-mono text-ellipsis"
          :value="currentBranch"
          @change="onCurrentBranchChange">
          <option v-for="b in availableBranches" :key="b" :value="b" :title="b">{{ b }}</option>
        </select>
      </div>

      <!-- Create branch button -->
      <button class="btn btn-xs btn-ghost tooltip shrink-0" data-tip="Create new branch"
        @click="$emit('create-branch')">
        <i class="fa-solid fa-plus text-[10px]"></i>
      </button>

      <!-- Compare arrow + target branch -->
      <div class="flex items-center gap-1 text-base-content-ERROR-40 shrink-0">
        <i class="fa-solid fa-arrow-right text-[10px]"></i>
        <span class="text-[10px]"><i class="fa-solid fa-angles-right"></i></span>
      </div>
      <select
        class="select select-xs select-bordered w-[110px] max-w-[110px] font-mono text-warning text-ellipsis"
        :value="compareBranch"
        @change="onCompareBranchChange">
        <option v-for="b in allCompareBranches" :key="b" :value="b" :title="b">{{ b }}</option>
      </select>
    </div>

    <div class="grow"></div>

    <!-- Layout toggles -->
    <div class="join shrink-0">
      <button
        class="join-item btn btn-xs"
        :class="showChat ? 'btn-primary' : 'btn-ghost'"
        @click="$emit('toggle-view', 'chat')"
        title="Toggle chat panel">
        <i class="fa-solid fa-comments"></i>
      </button>
      <button
        class="join-item btn btn-xs"
        :class="showChanges ? 'btn-warning' : 'btn-ghost'"
        @click="$emit('toggle-view', 'changes')"
        title="Toggle changes panel">
        <i class="fa-solid fa-code-compare"></i>
      </button>
      <button
        class="join-item btn btn-xs"
        :class="showPreview ? 'btn-success' : 'btn-ghost'"
        @click="$emit('toggle-view', 'preview')"
        title="Toggle preview panel">
        <i class="fa-solid fa-display"></i>
      </button>
    </div>

    <button class="btn btn-xs btn-ghost shrink-0" @click="$emit('reload')" title="Refresh">
      <i class="fa-solid fa-rotate-right"></i>
    </button>
  </div>
</template>

<script>
export default {
  props: {
    chat: { type: Object, default: null },
    projectName: { type: String, default: '' },
    availableBranches: { type: Array, default: () => [] },
    showChat: { type: Boolean, default: true },
    showChanges: { type: Boolean, default: false },
    showPreview: { type: Boolean, default: true }
  },
  emits: ['toggle-view', 'reload', 'create-branch', 'branch-changed', 'compare-branch-changed', 'update:chat'],
  data() {
    return {
      currentBranch: 'main',
      compareBranch: 'local'
    }
  },
  created() {
    this.initFromChat()
  },
  computed: {
    allCompareBranches() {
      return ['local', ...this.availableBranches]
    }
  },
  watch: {
    chat(newChat) {
      this.initFromChat(newChat)
    },
    availableBranches(newBranches) {
      if (newBranches.length && !newBranches.includes(this.currentBranch)) {
        this.currentBranch = newBranches[0]
      }
    }
  },
  methods: {
    initFromChat(chat) {
      const source = chat || this.chat
      const meta = source?.meta_data || {}
      this.currentBranch = meta.current_branch || this.availableBranches[0] || 'main'
      this.compareBranch = meta.compare_branch || 'local'
    },

    onCurrentBranchChange(event) {
      this.currentBranch = event.target.value
      this.updateChatMetaData()
      this.$emit('branch-changed', this.currentBranch)
    },

    onCompareBranchChange(event) {
      this.compareBranch = event.target.value
      this.updateChatMetaData()
      this.$emit('compare-branch-changed', this.compareBranch)
    },

    updateChatMetaData() {
      if (!this.chat) return
      const updatedChat = {
        ...this.chat,
        meta_data: {
          ...(this.chat.meta_data || {}),
          current_branch: this.currentBranch,
          compare_branch: this.compareBranch
        }
      }
      this.$emit('update:chat', updatedChat)
    },

    onBranchCreated(branchName) {
      this.currentBranch = branchName
      this.updateChatMetaData()
      this.$emit('branch-changed', branchName)
    }
  }
}
</script>