# [[{"id": "808e3a12-f39e-485a-a618-c4669d3a4454", "parent_id": "", "status": "", "tags": [], "file_list": [], "profiles": [], "name": "analyst", "created_at": "2024-12-29T16:18:48.349132", "updated_at": "2024-12-29T16:18:48.349132", "mode": "task", "board": "Profiles", "column": "new column", "chat_index": 0, "live_url": "", "branch": ""}]]
## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-12-29 15:29:58.133843", "updated_at": "2024-12-29 15:29:58.133870", "images": [], "files": []}]]
Update description and content for the analyst profile below.
Analyst will help users writting better task definitions ensuring every tasks has clear requirements, examples (if apply) and concise goal that will help developers to implement the feature, improve, or fix the code.
Add a markdown template to be used when writting tasks

Current profile:
```json

{"name": "analyst", "description": "", "category": "", "file_match": "", "content": "", "path": "/home/codxuser/projects/codx-junior/api/codx/junior/profiles/roles/analyst.json"}
```
## [[{"role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-12-29 15:29:58.133843", "updated_at": "2024-12-29 15:29:58.133870", "images": [], "files": ["/home/codxuser/projects/codx-junior/client/src/components/EditProfile.vue", "/client/src/views/ProfileView.vue", "/client/src/components/EditProfile.vue"]}]]
Below is an updated description and content for the analyst profile, along with a markdown template to be used when writing tasks.

Updated Analyst Profile:

```json
{
  "name": "analyst",
  "description": "The analyst ensures that every task is well-defined, with clear requirements, examples (if applicable), and a concise goal. This aids developers in implementing features, improvements, or fixes effectively.",
  "category": "Task Definition",
  "file_match": "*.json",
  "content": "The analyst is responsible for crafting precise task definitions that guide development. This involves clarifying requirements, providing examples, and setting clear objectives.",
  "path": "/home/codxuser/projects/codx-junior/api/codx/junior/profiles/roles/analyst.json"
}
```

Markdown Template for Writing Tasks:

```markdown
### Task Title

**Objective:**
- Clearly state the main goal of the task.

**Requirements:**
- List all necessary requirements or conditions.

**Examples:**
- Provide examples if applicable to clarify the task.

**Acceptance Criteria:**
- Define what constitutes successful completion of the task.

**Additional Notes:**
- Any other relevant information or context.
```

This template can be used in the `content` section of task descriptions to ensure clarity and consistency.
## [[{"role": "user", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-12-29 15:29:58.133843", "updated_at": "2024-12-29 15:29:58.133870", "images": [], "files": []}]]
Add the markdown template as part of the content
## [[{"role": "assistant", "task_item": "", "hide": false, "improvement": false, "created_at": "2024-12-29 15:29:58.133843", "updated_at": "2024-12-29 15:29:58.133870", "images": [], "files": ["/home/codxuser/projects/codx-junior/client/src/components/chat/Chat.vue", "/home/codxuser/projects/codx-junior/client/src/components/Markdown.vue", "/client/src/views/WikiView.vue", "/README.md", "/client/src/views/HomeView.vue", "/tailwind.config.js", "/home/codxuser/projects/codx-junior/client/src/views/WikiView.vue", "/client/src/components/ChatEntry.vue"]}]]
To include the markdown template in the Tailwind CSS configuration file's `content` array, you would add the path to markdown files or directories where these templates might be used. This ensures that Tailwind CSS scans these files for class names to generate the corresponding CSS. Here’s how you can adjust the configuration file:

```js
/shared/codx-junior/tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './shared/codx-junior/**/*.md', // Add this line to include markdown files
    './shared/codx-junior/**/*.vue', // Include Vue files that might render markdown
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Additionally, you can include the markdown template as part of the analyst profile content to guide task creation:

Analyst Profile with Markdown Template:
```json
{
  "name": "analyst",
  "description": "The analyst ensures that every task is well-defined, with clear requirements, examples (if applicable), and a concise goal. This aids developers in implementing features, improvements, or fixes effectively.",
  "category": "Task Definition",
  "file_match": "*.json",
  "content": "The analyst is responsible for crafting precise task definitions that guide development. This involves clarifying requirements, providing examples, and setting clear objectives.\n\n### Task Title\n\n**Objective:**\n- Clearly state the main goal of the task.\n\n**Requirements:**\n- List all necessary requirements or conditions.\n\n**Examples:**\n- Provide examples if applicable to clarify the task.\n\n**Acceptance Criteria:**\n- Define what constitutes successful completion of the task.\n\n**Additional Notes:**\n- Any other relevant information or context.",
  "path": "/home/codxuser/projects/codx-junior/api/codx/junior/profiles/roles/analyst.json"
}
```

This configuration ensures that your Tailwind CSS setup is aware of markdown files where these templates might be used, and the analyst profile now includes a markdown template for task definitions.