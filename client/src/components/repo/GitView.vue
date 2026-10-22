<script setup>
import ChangesPanel from '@/components/vibe/panels/ChangesPanel.vue'
</script>

<template>
  <div class="git-view h-full w-full flex flex-col bg-base-100 overflow-hidden">
    <!-- ── Toolbar ──────────────────────────────────────────────────────── -->
    <header class="flex items-center gap-2 px-3 py-1.5 bg-base-200 border-b border-base-content/10 shrink-0">
      <i class="fa-solid fa-code-branch text-warning"></i>
      <span class="font-mono text-sm font-semibold truncate min-w-0" :title="projectPath">{{ projectName }}</span>

      <div class="grow"></div>

      <div class="join">
        <button
          class="join-item btn btn-xs"
          :class="activeTab === 'changes' ? 'btn-primary' : 'btn-ghost'"
          @click="activeTab = 'changes'"
          title="Compare branches and review diffs"
        >
          <i class="fa-solid fa-code-compare"></i> Changes
        </button>
        <button
          class="join-item btn btn-xs"
          :class="activeTab === 'history' ? 'btn-primary' : 'btn-ghost'"
          @click="activeTab = 'history'"
          title="Branches and commits"
        >
          <i class="fa-solid fa-clock-rotate-left"></i> History
        </button>
      </div>
    </header>

    <!-- ── Changes: ChangesPanel (pick two branches, review diffs) ───────── -->
    <!-- v-show keeps the panel mounted so the branch selection survives tab switching -->
    <ChangesPanel
      v-show="activeTab === 'changes'"
      :project="project"
      class="grow min-h-0 overflow-hidden"
    />

    <!-- ── History: branches + commits ──────────────────────────────────── -->
    <div v-show="activeTab === 'history'" class="grow flex overflow-hidden">
      <!-- Sidebar: branches + commits -->
      <aside class="w-56 shrink-0 border-r border-base-content/10 flex flex-col overflow-y-auto">
        <div class="px-2 py-1.5 text-xs font-bold uppercase tracking-wide opacity-50">
          Branches
        </div>
        <ul class="menu menu-sm p-1">
          <li v-for="branch in branches" :key="branch.name">
            <a class="gap-2" :class="branch.current ? 'active' : ''">
              <i class="fa-solid fa-code-branch text-xs"></i>
              <span class="truncate">{{ branch.name }}</span>
            </a>
          </li>
        </ul>

        <div class="px-2 py-1.5 text-xs font-bold uppercase tracking-wide opacity-50">
          Commits
        </div>
        <ul class="p-1 flex flex-col gap-1">
          <li
            v-for="commit in commits"
            :key="commit.id"
            class="p-2 rounded-lg cursor-pointer hover:bg-base-200"
            :class="selectedCommit === commit.id ? 'bg-base-200 border border-primary/30' : ''"
            @click="selectedCommit = commit.id"
          >
            <div class="flex items-center gap-2 text-xs">
              <span class="font-mono opacity-60">{{ commit.id.slice(0, 7) }}</span>
              <span class="badge badge-ghost badge-xs ml-auto">{{ commit.date }}</span>
            </div>
            <div class="text-xs truncate mt-1">{{ commit.message }}</div>
            <div class="text-[10px] opacity-50">{{ commit.author }}</div>
          </li>
        </ul>
      </aside>

      <!-- Main -->
      <div class="grow overflow-auto p-3 flex flex-col gap-2">
        <div v-for="commit in commits" :key="commit.id" class="card bg-base-200 compact">
          <div class="card-body p-3">
            <div class="flex items-center gap-2">
              <i class="fa-solid fa-code-commit text-warning text-xs"></i>
              <span class="font-mono text-xs opacity-60">{{ commit.id.slice(0, 7) }}</span>
              <span class="text-xs font-semibold truncate">{{ commit.message }}</span>
              <span class="badge badge-xs badge-ghost ml-auto">{{ commit.date }}</span>
            </div>
            <div class="text-[10px] opacity-50">{{ commit.author }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GitView',
  components: { ChangesPanel },
  props: {
    params: { type: Object, default: () => ({}) }
  },
  data() {
    const commits = [
      { id: 'bc9287b4', author: 'gbrian', message: 'Add git view mockup', date: '2h ago' },
      { id: '5952c0b1', author: 'gbrian', message: 'PR merge fixes', date: '1d ago' },
      { id: '1a9f0c22', author: 'codx-junior', message: 'Initial commit', date: '3d ago' }
    ]
    return {
      activeTab: 'changes',
      branches: [
        { name: 'main', current: true },
        { name: 'develop', current: false },
        { name: 'feature/git-view', current: false }
      ],
      commits,
      selectedCommit: commits[0].id
    }
  },
  computed: {
    /** Project the git view works with: explicit panel param, else active project */
    project() {
      return this.params?.project || this.$storex.projects.activeProject || null
    },
    projectName() {
      return this.project?.project_name || 'No project'
    },
    projectPath() {
      return this.project?.abs_project_path || this.project?.codx_path || ''
    }
  }
}
</script>