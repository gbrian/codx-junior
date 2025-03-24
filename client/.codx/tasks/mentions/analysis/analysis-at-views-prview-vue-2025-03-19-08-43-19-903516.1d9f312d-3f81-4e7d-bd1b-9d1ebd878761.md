# [[{"id": "1d9f312d-3f81-4e7d-bd1b-9d1ebd878761", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": ["skip_knowledge"], "file_list": [], "profiles": [], "name": "analysis-at-views-prview-vue-2025-03-19-08-43-19-903516", "created_at": "2025-03-17 16:21:59.034533", "updated_at": "2025-03-19T08:43:35.481143", "mode": "chat", "kanban_id": "", "column_id": "", "board": "mentions", "column": "analysis", "chat_index": 0, "live_url": "", "branch": "", "file_path": "", "model": ""}]]
## [[{"doc_id": "c3acb15b-9196-427c-b5cf-437f662ae607", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-03-17 16:21:59.031224", "updated_at": "2025-03-17 16:21:59.031271", "images": [], "files": [], "meta_data": {}, "profiles": []}]]
You are a software developer maintaining the codebase.
* Keep your changes short and simple
* Make minimum changes as possiblle.
* Respect code structure.
* Make your changes compatible with the current code structure and format
* Don't add references or imports unless they are really necessary
Find all information needed to apply all changes to file: /shared/codx-junior/client/src/views/PRView.vue

Changes:
User commented in line 22: the parent branch can be from the list or from user input, add and icon to toggle betweem selector and an input. both will use same model

File content:
<script setup>
import GitDiffViewer from '@/components/code/GitDiffViewer.vue'
import Collapsible from '@/components/Collapsible.vue';
</script>

<template lang="pug">
  <div class="pr-view p-4 flex flex-col gap-4">
    <header class="flex justify-between items-start">
      <div class="flex flex-col gap-2">
        <h1 class="text-3xl font-bold">Changes review</h1>
        <div class="flex gap-2 items-center">
          <div class="flex items-center gap-2">
            <label class="block text-xs font-bold" for="branchSource">Source</label>
            <select id="branchSource" class="select select-bordered select-sm w-full max-w-xs" v-model="selectedBranchSource">
              <option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option>
            </select>
          </div>
          <div class="flex items-center gap-2">
            <label class="block text-xs font-bold" for="branchTarget">Target</label>
            <select id="branchTarget" class="select select-bordered select-sm w-full max-w-xs" v-model="selectedBranchTarget">
              <option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option>
            </select>
            @codx-ok, please-wait...: the parent branch can be from the list or from user input, add and icon to toggle betweem selector and an input. both will use same model
          </div>
        </div>
      </div>
    </header>
    .flex.flex-col.gap-4.grow

      Collapsible.hidden(v-model="overviewChecked" :start-expanded="true")
        template(v-slot:title)
          .flex.flex-col.grow
            .flex.justify-between.items-center
              | Overview
              button.btn.btn-sm.tooltip(data-tip="Rebuild summary" 
                                        @click="refreshSummary(true)")
                <i class="fa-solid fa-arrows-rotate"></i> Rebuild
            .text-sm Changes overview
        template(v-slot:content)
          Markdown(:text="$projects.changesSummary")

      Collapsible.hidden
        template(v-slot:title)
          .flex.flex-col.grow
            | Tasks
            .text-sm Tasks associated with {{ selectedBranchSource }}
        template(v-slot:content)
          

      Collapsible
        template(v-slot:title)
          .flex.flex-col.grow
            | Files
            .text-sm Files changed
        template(v-slot:content)
          div
            GitDiffViewer(:diff="$projects.project_branches.git_diff" v-if="$projects.project_branches.git_diff")
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedBranchSource: null,
      selectedBranchTarget: null,
      activeTab: 'Overview',
      overviewChecked: true 
    }
  },
  computed: {
    branches() {
      return this.$projects.project_branches.branches
    },
  },
  watch: {
    $project() {
      this.refreshSummary()
    },
    selectedBranchSource() {
      this.refreshSummary()
    },
    selectedBranchTarget() {
      this.refreshSummary()
    }
  },
  methods: {
    switchTab(tab) {
      this.activeTab = tab
    },
    copyText() {
      copyTextToClipboard(this.changesSummary)
    },
    async refreshSummary(rebuild = false) {
      // Refresh summary and reload branches
      this.$projects.refreshChangesSummary({
        source: this.selectedBranchSource,
        target: this.selectedBranchTarget,
        rebuild
      })
      await this.$projects.loadBranches()
      this.selectedBranchSource = this.$projects.currentBranch
      this.selectedBranchTarget = this.$projects.project_branches.parent_branch
    }
  },
  mounted() {
    this.refreshSummary(false)
  }
}
</script>
## [[{"doc_id": "68c3d8f6-c47d-4c67-8ca1-1561c8d1cfbc", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-03-17 16:21:59.031224", "updated_at": "2025-03-17 16:21:59.031271", "images": [], "files": [], "meta_data": {"time_taken": 15.574287176132202, "first_chunk_time_taken": 7.005337476730347, "model": "gpt-4o"}, "profiles": []}]]
To implement the feature of toggling between a select element and an input for the branch target, we can add a button to switch between these two components and bind them to the same Vue model. Here's how you could do it with minimal changes:

```vue
<template lang="pug">
  <div class="pr-view p-4 flex flex-col gap-4">
    <header class="flex justify-between items-start">
      <div class="flex flex-col gap-2">
        <h1 class="text-3xl font-bold">Changes review</h1>
        <div class="flex gap-2 items-center">
          <div class="flex items-center gap-2">
            <label class="block text-xs font-bold" for="branchSource">Source</label>
            <select id="branchSource" class="select select-bordered select-sm w-full max-w-xs" v-model="selectedBranchSource">
              <option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option>
            </select>
          </div>
          <div class="flex items-center gap-2">
            <label class="block text-xs font-bold" for="branchTarget">Target</label>
            <div class="relative">
              <button @click="toggleBranchInput" class="btn btn-xs absolute right-0 top-0">
                <i class="fa-solid" :class="isInputVisible ? 'fa-list' : 'fa-pen'"></i>
              </button>
              <select
                v-if="!isInputVisible"
                id="branchTarget"
                class="select select-bordered select-sm w-full max-w-xs"
                v-model="selectedBranchTarget"
              >
                <option v-for="branch in branches" :key="branch" :value="branch">{{ branch }}</option>
              </select>
              <input
                v-else
                id="branchTargetInput"
                type="text"
                class="input input-bordered input-sm w-full max-w-xs"
                v-model="selectedBranchTarget"
              />
            </div>
          </div>
          <!-- User's original comment -->
          @codx-ok, please-wait...: the parent branch can be from the list or from user input, add and icon to toggle between selector and an input. both will use same model
        </div>
      </div>
    </header>
    .flex.flex-col.gap-4.grow

      Collapsible.hidden(v-model="overviewChecked" :start-expanded="true")
        template(v-slot:title)
          .flex.flex-col.grow
            .flex.justify-between.items-center
              | Overview
              button.btn.btn-sm.tooltip(data-tip="Rebuild summary" 
                                        @click="refreshSummary(true)")
                <i class="fa-solid fa-arrows-rotate"></i> Rebuild
            .text-sm Changes overview
        template(v-slot:content)
          Markdown(:text="$projects.changesSummary")

      Collapsible.hidden
        template(v-slot:title)
          .flex.flex-col.grow
            | Tasks
            .text-sm Tasks associated with {{ selectedBranchSource }}
        template(v-slot:content)
          

      Collapsible
        template(v-slot:title)
          .flex.flex-col.grow
            | Files
            .text-sm Files changed
        template(v-slot:content)
          div
            GitDiffViewer(:diff="$projects.project_branches.git_diff" v-if="$projects.project_branches.git_diff")
  </div>
</template>

<script>
export default {
  data() {
    return {
      selectedBranchSource: null,
      selectedBranchTarget: null,
      activeTab: 'Overview',
      overviewChecked: true,
      isInputVisible: false 
    }
  },
  computed: {
    branches() {
      return this.$projects.project_branches.branches
    },
  },
  watch: {
    $project() {
      this.refreshSummary()
    },
    selectedBranchSource() {
      this.refreshSummary()
    },
    selectedBranchTarget() {
      this.refreshSummary()
    }
  },
  methods: {
    switchTab(tab) {
      this.activeTab = tab
    },
    copyText() {
      copyTextToClipboard(this.changesSummary)
    },
    async refreshSummary(rebuild = false) {
      // Refresh summary and reload branches
      this.$projects.refreshChangesSummary({
        source: this.selectedBranchSource,
        target: this.selectedBranchTarget,
        rebuild
      })
      await this.$projects.loadBranches()
      this.selectedBranchSource = this.$projects.currentBranch
      this.selectedBranchTarget = this.$projects.project_branches.parent_branch
    },
    toggleBranchInput() {
      this.isInputVisible = !this.isInputVisible
    }
  },
  mounted() {
    this.refreshSummary(false)
  }
}
</script>
```

### Explanation:
1. **Button for toggling**: A button with a font-awesome icon is added next to the branch target selection. It toggles between a dropdown selector and a text input.
2. **Computed icon class**: The icon changes between a list icon (`fa-list`) and a pen icon (`fa-pen`) based on the current input state.
3. **Toggled input element**: The branch target can be selected from a dropdown or entered manually in a text input, both are bound to `selectedBranchTarget`.