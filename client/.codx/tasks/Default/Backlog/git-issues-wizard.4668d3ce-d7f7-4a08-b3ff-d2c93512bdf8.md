# [[{"id": "4668d3ce-d7f7-4a08-b3ff-d2c93512bdf8", "doc_id": null, "project_id": null, "parent_id": "c09b3bad-d5c9-46db-a9e0-6ed9937d1fa5", "status": "", "tags": [], "file_list": [], "profiles": ["software_developer"], "users": ["admin"], "name": "git issues wizard", "description": "You requested a tutorial for creating a kanban, tasks, and subtasks from a Git issue link. Then, you asked to add a new Vue component for a wizard, which displays steps based on a current step index, with dimmed future steps and a \"Close\" button upon completion. I provided a concise Vue component implementation using TailwindCSS, respecting your code structure and minimal change guidelines. Lastly, I summarized the conversation in five lines.", "created_at": "2025-05-30 03:56:58.255588", "updated_at": "2025-05-30T04:19:16.704616", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Default", "column": "Backlog", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/client/.codx/tasks/Default/Backlog/git-issues-wizard.4668d3ce-d7f7-4a08-b3ff-d2c93512bdf8.md", "model": "", "visibility": "", "knowledge_topics": []}]]
## [[{"doc_id": "8999823a-f222-431f-95eb-62d0f94443bb", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-30 03:56:58.253753", "updated_at": "2025-05-30 03:56:58.253831", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": null, "knowledge_topics": []}]]
Creates a tutorial on how to create a kanban, tasks and subtasks from an git issue link
## [[{"doc_id": "d8d9ff53-cbf0-4b79-8cab-9451857a1206", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-30 03:56:58.253753", "updated_at": "2025-05-30 03:56:58.253831", "images": [], "files": [], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": []}]]
We under components/wizards create a new vue component that will show wizard progress for the github issue turotial:
it will  have these steps:
* Loading issue information
* Creating kanban
* Creating analysis
* Searching project for information
* Creating subtasks
* Implementing task: task_name
* Done


Component will receive a property "step"  to indicate current setp index and "done"
Show all steps after the setp index dimmed
Show a "Close" button ($emit close) when done
## [[{"doc_id": "22d4c1d7-e40f-4e74-a080-5d5b197f83ba", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-30 03:56:58.253753", "updated_at": "2025-05-30 03:56:58.253831", "images": [], "files": [], "meta_data": {"time_taken": 6.263704061508179, "first_chunk_time_taken": 1.788635015487671, "model": "gpt-4.1-nano"}, "profiles": ["software_developer", "software_developer"], "user": null, "knowledge_topics": []}]]
Certainly! Below is a concise implementation of the wizard component based on your specifications. It will be placed inside `components/wizards` as a new Vue component, for example, `IssueWizard.vue`. It receives `step` and `done` props, displays all steps with future steps dimmed, and shows a "Close" button when `done` is true.

```vue
<template>
  <div class="p-4 border rounded shadow bg-white max-w-md mx-auto">
    <h2 class="text-xl font-semibold mb-4">Issue Wizard</h2>
    <ol class="space-y-2 list-decimal pl-4">
      <li :class="stepClass(0)">Loading issue information</li>
      <li :class="stepClass(1)">Creating kanban</li>
      <li :class="stepClass(2)">Creating analysis</li>
      <li :class="stepClass(3)">Searching project for information</li>
      <li :class="stepClass(4)">Creating subtasks</li>
      <li :class="stepClass(5)">Implementing task: task_name</li>
      <li :class="stepClass(6)">Done</li>
    </ol>

    <div v-if="done" class="mt-4 text-center">
      <button @click="$emit('close')" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
        Close
      </button>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    step: {
      type: Number,
      required: true
    },
    done: {
      type: Boolean,
      default: false
    }
  },
  methods: {
    stepClass(index) {
      if (index === this.step) {
        return 'font-semibold text-black';
      } else if (index > this.step) {
        return 'text-gray-400';
      } else {
        return 'font-semibold text-gray-800';
      }
    }
  }
}
</script>
```

### Usage:
- Pass `step` (0-based index) and `done` status.
- When `done` is true, a "Close" button appears that emits the `close` event.

This implementation respects your instructions for minimal, compatible, and styled code using TailwindCSS.