# [[{"id": "c09b3bad-d5c9-46db-a9e0-6ed9937d1fa5", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": [], "profiles": ["software_developer"], "users": ["admin"], "name": "codx-junior wizards overview", "description": "You asked about integrating on-screen tutorials for `codx-junior` using Vue. I recommended using `vue-tour`, a lightweight Vue-compatible library. I provided steps to install, register, and add a tutorial component with minimal code modifications. Finally, I summarized the instructions, emphasizing simplicity and compatibility.", "created_at": "2025-05-30 03:56:58.255588", "updated_at": "2025-05-30T04:08:40.732194", "mode": "chat", "kanban_id": "", "column_id": "", "board": "codx-junior wizards", "column": "Backlog", "chat_index": 0, "url": "", "branch": "", "file_path": "/home/codx-junior/codx-junior/client/.codx/tasks/codx-junior wizards/Backlog/codx-junior-wizards-overview.c09b3bad-d5c9-46db-a9e0-6ed9937d1fa5.md", "model": "", "visibility": "", "knowledge_topics": []}]]
## [[{"doc_id": "badb9496-681f-4de4-af2b-8c151a87181a", "role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-30 03:56:58.253753", "updated_at": "2025-05-30 03:56:58.253831", "images": [], "files": [], "meta_data": {}, "profiles": ["software_developer"], "user": "admin", "knowledge_topics": []}]]
We want to add codx-junior a set of wizards that will guide user on using the UI
We need to define the behavior of the on the screen tutorials and find librearies that we can integrate with vue
## [[{"doc_id": "36b83489-a515-42f4-8354-e3d78b6efe34", "role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2025-05-30 03:56:58.253753", "updated_at": "2025-05-30 03:56:58.253831", "images": [], "files": [], "meta_data": {"time_taken": 5.261849641799927, "first_chunk_time_taken": 2.3631861209869385, "model": "gpt-4.1-nano"}, "profiles": ["software_developer"], "user": null, "knowledge_topics": []}]]
To add a set of wizards for guiding users, I recommend using a lightweight Vue-compatible library like `vue-tour` or `intro.js`. Since you want minimal changes, here’s a straightforward approach:

1. **Choose Library**  
Let's select `vue-tour` as an example, which is easy to integrate.

2. **Install the library**  
Assuming you can run npm commands in your environment:  
```bash
npm install vue-tour
```

3. **Register `vue-tour` globally**  
In your main Vue setup (e.g., `main.js`), add:

```js
import Vue from 'vue'
import VueTour from 'vue-tour'
import 'vue-tour/dist/vue-tour.css'

Vue.use(VueTour)
```

4. **Add the wizard (tour) component to your UI**  
Within the component where you want the tutorials, add:

```vue
<template>
  <div>
    <button @click="startTour">Guide Me</button>
    <vue-tour :steps="steps" ref="tour"></vue-tour>
  </div>
</template>

<script>
export default {
  data() {
    return {
      steps: [
        {
          target: '.selector1',
          content: 'This is the first step of the tutorial.',
        },
        {
          target: '.selector2',
          content: 'Here you can do this.',
        },
        // Add more steps as needed
      ],
    }
  },
  methods: {
    startTour() {
      this.$refs.tour.start()
    },
  },
}
</script>
```

**Summary of minimal changes:**
- Install and register the library.
- Add a button and the `<vue-tour>` component.
- Define tutorial steps.
- Call `start()` method on button click.

This setup respects existing code structure and requires only minimal additions.