<script setup>
</script>

<template>
  <div class="flex flex-col gap-2 w-full">
    <!-- Mode toggle: branch vs commit -->
    <div class="flex gap-2 items-center">
      <span class="text-xs text-slate-400">Compare by:</span>
      <div class="join">
        <button class="join-item btn btn-xs" 
          :class="mode === 'branch' ? 'btn-primary' : 'btn-ghost'"
          @click="mode = 'branch'">
          <i class="fa-solid fa-code-branch"></i> Branch
        </button>
        <button class="join-item btn btn-xs"
          :class="mode === 'commit' ? 'btn-primary' : 'btn-ghost'"
          @click="mode = 'commit'">
          <i class="fa-solid fa-code-commit"></i> Commit
        </button>
      </div>
    </div>

    <!-- Branch mode -->
    <div class="flex gap-2 items-center" v-if="mode === 'branch'">
      <slot />
    </div>

    <!-- Commit mode -->
    <div class="flex gap-2 items-center flex-wrap" v-if="mode === 'commit'">
      <div class="flex flex-col gap-1">
        <span class="text-xs text-slate-400">Branch (for commit list)</span>
        <select class="select select-xs select-bordered w-40" v-model="selectedBranch" @change="loadCommits">
          <option value="">-- HEAD --</option>
          <option v-for="b in branches" :key="b" :value="b">{{ b }}</option>
        </select>
      </div>

      <div class="flex flex-col gap-1" v-if="commits.length">
        <span class="text-xs text-slate-400">From commit (newer)</span>
        <select class="select select-xs select-bordered max-w-xs" v-model="fromCommit" @change="emitCommit">
          <option value="">-- select --</option>
          <option v-for="c in commits" :key="c.commit" :value="c.commit" :title="c.message">
            {{ c.label }}
          </option>
        </select>
      </div>

      <div class="flex flex-col gap-1" v-if="commits.length">
        <span class="text-xs text-slate-400">To commit (base)</span>
        <select class="select select-xs select-bordered max-w-xs" v-model="toCommit" @change="emitCommit">
          <option value="">-- select --</option>
          <option v-for="c in commits" :key="c.commit" :value="c.commit" :title="c.message">
            {{ c.label }}
          </option>
        </select>
      </div>

      <div class="flex items-end pb-1" v-if="commits.length && fromCommit && toCommit">
        <button class="btn btn-xs btn-primary" @click="emitCommit">
          <i class="fa-solid fa-arrows-rotate"></i> Compare
        </button>
      </div>

      <div class="flex items-center gap-1 text-xs text-slate-400" v-if="loadingCommits">
        <span class="loading loading-spinner loading-xs"></span> Loading commits...
      </div>
    </div>
  </div>
</template>

<script>
export default {
  props: ['branches', 'projectApi'],
  emits: ['commit-compare', 'mode-change'],
  data() {
    return {
      mode: 'branch',
      selectedBranch: '',
      commits: [],
      fromCommit: '',
      toCommit: '',
      loadingCommits: false
    }
  },
  watch: {
    mode(val) {
      this.$emit('mode-change', val)
      if (val === 'commit' && !this.commits.length) {
        this.loadCommits()
      }
    }
  },
  methods: {
    async loadCommits() {
      if (!this.projectApi) {
        console.error('Project API not available')
        return
      }
      this.loadingCommits = true
      this.fromCommit = ''
      this.toCommit = ''
      try {
        const branch = this.selectedBranch || undefined
        this.commits = await this.projectApi.repo.commits({ branch, limit: 80 })
      } catch (ex) {
        console.error('Error loading commits', ex)
        this.commits = []
      } finally {
        this.loadingCommits = false
      }
    },
    emitCommit() {
      if (!this.fromCommit || !this.toCommit) return
      this.$emit('commit-compare', {
        fromCommit: this.fromCommit,
        toCommit: this.toCommit
      })
    }
  }
}
</script>