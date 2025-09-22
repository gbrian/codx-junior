# [[{"id": "087a50c1-5edc-43f7-ae4c-f780f0cb0431", "doc_id": null, "project_id": null, "parent_id": null, "message_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/client/src/components/Splitter.vue"], "check_lists": [], "profiles": [], "users": ["admin"], "name": "Update splitter to show workspacesviewer", "pinned": false, "description": "The user has requested an update to a component to display the \"WorkspacesViewer\" in a new panel. They have also provided a guideline on how to format code snippets with file paths in responses. There is no additional context or details provided about the specific component or the environment in which this update should be made. The request is focused on modifying the UI layout to accommodate the \"WorkspacesViewer\" in a separate panel.", "created_at": "2025-09-18 14:16:00.211922", "updated_at": "2025-09-18T15:29:45.714042", "mode": "task", "kanban_id": "", "column_id": "", "board": "Workspaces", "column": "ToDo", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/client/.codx/tasks/Workspaces/ToDo/update-splitter-to-show-workspacesviewer.087a50c1-5edc-43f7-ae4c-f780f0cb0431.md", "llm_model": "", "visibility": "", "remote_url": "", "knowledge_topics": [], "chat_links": [], "pr_view": {}}]]
## [[{"doc_id": "7dab0e19-4342-436d-bfc0-72c857a8adaa", "role": "user", "task_item": "", "think": "", "hide": true, "is_answer": false, "improvement": false, "created_at": "2025-09-18 14:16:00.203859", "updated_at": "2025-09-18 14:16:00.203931", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true, "read_by": []}]]
Update component to show WorkspacesViewer in a new panel
## [[{"doc_id": "005921a1-c458-4edf-835d-f155fd42c578", "role": "assistant", "task_item": "analysis", "think": null, "hide": false, "is_answer": false, "improvement": false, "created_at": "2025-09-18 14:16:00.203859", "updated_at": "2025-09-18 14:16:00.203931", "images": [], "files": [], "meta_data": {"time_taken": 82.78025388717651, "first_chunk_time_taken": 0.00021529197692871094, "model": "openai/gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": false, "read_by": []}]]
To update the `Splitter.vue` component to show the `WorkspacesViewer` in a new panel, you will need to add a new `SplitterPanel` for the `WorkspacesViewer` component. Here's how you can do it:

```vue /shared/codx-junior/client/src/components/Splitter.vue
<script setup>
import { SplitterGroup, SplitterPanel, SplitterResizeHandle } from 'radix-vue'
import BrowserVue from './browser/Browser.vue'
import CoderVue from '../components/apps/Coder.vue'
import PreviewVue from '../components/apps/Preview.vue'
import CodxJuniorVue from '../views/CodxJunior.vue'
import NavigationBar from '../components/NavigationBar.vue'
import LogViewerVue from './LogViewer.vue'
import Wizard from '../components/wizards/Wizard.vue'
import WorkspacesViewer from './workspaces/WorkspacesViewer.vue' // Already imported
</script>

<template>
  <div class="bg-base-300 flex">
    <SplitterGroup id="splitter-group-1" class="relative" 
      direction="horizontal" auto-save-id="splitter-group-1">
      <SplitterPanel id="splitter-group-1-panel-1" :order="0" :min-size="20" class="" v-if="$ui.showApp">
        <SplitterGroup id="splitter-group-2" 
          :direction="isHorizontal ? 'horizontal' : 'vertical'"
          auto-save-id="splitter-group-2"
          v-if="$ui.appDivided !== 'none'"
        >
          <SplitterPanel id="splitter-group-2-panel-1" :order="0" :min-size="20" v-if="$ui.showCoder">
            <CoderVue class="h-full w-full" />
          </SplitterPanel>
          <SplitterResizeHandle id="splitter-group-2-resize-handle-1" class="bg-stone-800 hover:bg-slate-600"
            :class="isHorizontal ? 'w-1' : 'h-1'" v-if="$ui.showBrowser && $ui.showCoder" />
          <SplitterPanel id="splitter-group-2-panel-2" :min-size="20" class="" :order="1" v-if="$ui.showBrowser">
            <PreviewVue class="h-full w-full" :app="'preview'" />
          </SplitterPanel>
        </SplitterGroup>
        <div class="h-full w-full" v-if="$ui.showApp && $ui.appDivided === 'none'">
          <CoderVue class="h-full w-full" v-if="$ui.showCoder" />
          <PreviewVue class="h-full w-full" :app="'preview'"
            v-if="$ui.showBrowser" />
        </div>
      </SplitterPanel>

      <SplitterResizeHandle id="splitter-group-1-resize-handle-1" class="bg-stone-800 hover:bg-slate-600 w-1"
        v-if="$ui.showApp && showCodxJunior" />

      <SplitterPanel id="splitter-group-1-panel-2" :order="1" :min-size="showCodxJuniorFloating ? 0 : $ui.showApp ?  20 : 100"
        :defaultSize="showCodxJuniorFloating ? 0 : $ui.codxJuniorWidth"
        class="flex items-center justify-center transition-all transition-discrete"
        :class="[
          showCodxJuniorFloating ? 'absolute z-50 right-0 top-0 bottom-0 border-red-600 w-2 opacity-30 hover:w-2/4 hover:opacity-90' : '',
          (showCodxJuniorFloating && mouseOnNavigation) && 'w-2/4 opacity-90'
        ]"
        @resize="size => $ui.setCodxJuniorWidth(size)"
        v-if="showCodxJunior">
        <CodxJuniorVue ref="codxJunior" class="w-full h-full" :class="`zoom:${zoom}`"
          :style="`zoom:${ zoom }`" 
        />
      </SplitterPanel>

      <SplitterResizeHandle id="splitter-group-1-resize-handle-2" class="bg-stone-800 hover:bg-slate-600 w-1" v-if="$ui.showLogs"/>

      <SplitterPanel id="splitter-group-1-panel-3" :order="3" :defaultSize="25" :minSize="20" class="flex items-center justify-center"
        v-if="$ui.showLogs">
        <LogViewerVue class="text-xs bg-base-300 w-full h-full" />
      </SplitterPanel>

      <!-- New SplitterPanel for WorkspacesViewer -->
      <SplitterResizeHandle id="splitter-group-1-resize-handle-3" class="bg-stone-800 hover:bg-slate-600 w-1" v-if="showWorkspaces" />

      <SplitterPanel id="splitter-group-1-panel-4" :order="4" :defaultSize="25" :minSize="20" class="flex items-center justify-center"
        v-if="showWorkspaces">
        <WorkspacesViewer class="w-full h-full" />
      </SplitterPanel>

    </SplitterGroup>
    <div class="flex flex-col w-2/5 h-full overflow-auto" v-if="$projects.activeWizards.length">
      <Wizard 
        :wizard="wizard" 
        v-for="wizard in $projects.activeWizards" :key="wizard.id" 
        @close="$projects.removeWizard(wizard)" />
    </div>
    <NavigationBar :right="true" 
      @mouseenter="mouseOnNavigation = true" 
      @mouseover="mouseOnNavigation = true"
      @mouseleave="mouseOnNavigation = false"
      @blur="mouseOnNavigation = false"
      v-if="$ui.isLandscape" />

  </div>
</template>
<script>
export default {
  data() {
    return {
      mouseOnNavigation: false
    }
  },
  computed: {
    zoom() {
      return this.$ui.showApp && this.showCodxJunior ? 1.2 : 1
    },
    isHorizontal() {
      return this.$ui.appDivided === 'horizontal'
    },
    showCodxJunior() {
      return !!this.$ui.activeTab
    },
    showApp() {
      return this.$ui.showApp
    },
    showCodxJuniorFloating() {
      return this.$ui.floatingCodxJunior || (this.$ui.showBrowser && this.$ui.showCoder)
    },
    showWorkspaces() {
      return this.$storex.projects.openedWorkspaces.length
    }
  },
  mounted() {
  },
  watch: {
  },
  methods: {
    onDblclickCodxJunior() {
      console.log("onDblclickCodxJunior")
    }
  }
}
</script>
```

### Changes Made:
1. Added a new `SplitterPanel` for `WorkspacesViewer` with a resize handle.
2. Updated the `showWorkspaces` computed property to determine when to display the `WorkspacesViewer`.

This setup will create a new panel for the `WorkspacesViewer` within the existing `SplitterGroup`.