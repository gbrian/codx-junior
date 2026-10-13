<template>
  <div class="git-view h-full w-full flex flex-col bg-base-100 overflow-hidden">
    <!-- ── Toolbar ──────────────────────────────────────────────────────── -->
    <header class="flex items-center gap-2 px-3 py-1.5 bg-base-200 border-b border-base-content/10 shrink-0">
      <i class="fa-solid fa-code-branch text-warning"></i>
      <span class="font-mono text-sm font-semibold">main</span>

      <div class="flex items-center gap-1">
        <span class="badge badge-xs badge-ghost">
          <i class="fa-solid fa-file-pen text-warning"></i> {{ files.length }}
        </span>
        <span class="badge badge-xs badge-ghost text-success">
          <i class="fa-solid fa-plus"></i> {{ insertions }}
        </span>
        <span class="badge badge-xs badge-ghost text-error">
          <i class="fa-solid fa-minus"></i> {{ deletions }}
        </span>
      </div>

      <div class="grow"></div>

      <div class="join">
        <button
          class="join-item btn btn-xs"
          :class="activeTab === 'changes' ? 'btn-primary' : 'btn-ghost'"
          @click="activeTab = 'changes'"
        >
          <i class="fa-solid fa-code-compare"></i> Changes
        </button>
        <button
          class="join-item btn btn-xs"
          :class="activeTab === 'history' ? 'btn-primary' : 'btn-ghost'"
          @click="activeTab = 'history'"
        >
          <i class="fa-solid fa-clock-rotate-left"></i> History
        </button>
      </div>
    </header>

    <div class="grow flex overflow-hidden">
      <!-- ── Sidebar: branches + commits ────────────────────────────────── -->
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

      <!-- ── Main ───────────────────────────────────────────────────────── -->
      <div class="grow flex flex-col overflow-hidden">
        <!-- Changes view -->
        <template v-if="activeTab === 'changes'">
          <div class="flex items-center justify-between px-3 py-1 bg-base-200/50 border-b border-base-content/10 shrink-0">
            <span class="text-xs font-semibold">Changed files ({{ files.length }})</span>
            <span class="badge badge-xs badge-outline font-mono">{{ selectedFile.path }}</span>
          </div>

          <!-- File list -->
          <div class="max-h-40 overflow-y-auto border-b border-base-content/10 shrink-0">
            <div
              v-for="file in files"
              :key="file.path"
              class="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-base-200"
              :class="selectedFile.path === file.path ? 'bg-base-200' : ''"
              @click="selectedFile = file"
            >
              <i class="fa-regular fa-file-lines"></i>
              <span class="truncate grow">{{ file.path }}</span>
              <span class="badge badge-xs text-success">+{{ file.insertions }}</span>
              <span class="badge badge-xs text-error" v-if="file.deletions">-{{ file.deletions }}</span>
              <span class="badge badge-xs" :class="statusClass(file.status)">{{ file.status }}</span>
            </div>
          </div>

          <!-- Diff mock -->
          <div class="grow overflow-auto font-mono text-[11px] leading-5">
            <div
              v-for="(line, index) in diffLines"
              :key="index"
              class="flex px-2"
              :class="lineClass(line)"
            >
              <span class="w-10 shrink-0 text-right pr-2 opacity-40 select-none">{{ line.old ?? '' }}</span>
              <span class="w-10 shrink-0 text-right pr-2 opacity-40 select-none">{{ line.new ?? '' }}</span>
              <span class="w-4 shrink-0 select-none">{{ lineIndicator(line) }}</span>
              <span class="grow whitespace-pre">{{ line.text }}</span>
            </div>
          </div>
        </template>

        <!-- History view -->
        <div v-else class="grow overflow-auto p-3 flex flex-col gap-2">
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
  </div>
</template>

<script>
export default {
  props: [],
  data() {
    const files = [
      { path: 'src/components/repo/GitView.vue', status: 'added', insertions: 128, deletions: 0 },
      { path: 'src/config/apps.js', status: 'modified', insertions: 6, deletions: 0 },
      { path: 'src/store/ui.js', status: 'modified', insertions: 4, deletions: 0 }
    ]
    const commits = [
      { id: 'bc9287b4', author: 'gbrian', message: 'Add git view mockup', date: '2h ago' },
      { id: '5952c0b1', author: 'gbrian', message: 'PR merge fixes', date: '1d ago' },
      { id: '1a9f0c22', author: 'codx-junior', message: 'Initial commit', date: '3d ago' }
    ]
    const diffLines = [
      { type: 'hunk', old: null, new: null, text: '@@ -1,3 +1,5 @@' },
      { type: 'context', old: 1, new: 1, text: '<' + 'script setup>' },
      { type: 'context', old: 2, new: 2, text: "import { ref } from 'vue'" },
      { type: 'add', old: null, new: 3, text: '' },
      { type: 'add', old: null, new: 4, text: '// Git view mockup' },
      { type: 'del', old: 3, new: null, text: '// placeholder' },
      { type: 'context', old: 4, new: 5, text: '<' + '/script>' }
    ]
    return {
      activeTab: 'changes',
      branches: [
        { name: 'main', current: true },
        { name: 'develop', current: false },
        { name: 'feature/git-view', current: false }
      ],
      commits,
      files,
      selectedFile: files[0],
      selectedCommit: commits[0].id,
      diffLines
    }
  },
  computed: {
    insertions() {
      return this.files.reduce((sum, file) => sum + file.insertions, 0)
    },
    deletions() {
      return this.files.reduce((sum, file) => sum + file.deletions, 0)
    }
  },
  methods: {
    statusClass(status) {
      if (status === 'added') return 'badge-success'
      if (status === 'deleted') return 'badge-error'
      return 'badge-warning'
    },
    lineClass(line) {
      if (line.type === 'add') return 'bg-success/10'
      if (line.type === 'del') return 'bg-error/10'
      if (line.type === 'hunk') return 'bg-base-200/60'
      return ''
    },
    lineIndicator(line) {
      if (line.type === 'add') return '+'
      if (line.type === 'del') return '-'
      return ''
    }
  }
}
</script>