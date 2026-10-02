# Chats and agents

Everything in codx-junior is a chat: a quick question, a Kanban task, a team channel or a pull-request review. Chats belong to a project, so the AI always works with that project's files, knowledge and settings.

![Task manager](/images/NOV2025/codx-junior-task-manager.png)

## Starting a chat

From the home screen (quick chat) type a message, or create a chat from a Kanban column. For each chat you can choose:

* the **mode** (see below),
* one or more **profiles** that shape the AI's behaviour,
* the **LLM model** to use,
* the **users** involved,
* **files** and **attachments** (images, documents, other chats) to add to the context.

Chats can be nested: a chat can have sub-chats (sub-tasks), threads on a message, and links to other chats. A sub-chat can inherit its parent's messages, files and knowledge, or ignore them.

## Chat modes

| Mode | Use it to |
| --- | --- |
| `chat` | Have a normal conversation with the AI about the project. |
| `task` | Refine a single document, such as a specification or a plan, message after message. |
| `agent` | Let the AI use tools in a loop to complete the work. |
| `vibe` | Code with the AI while watching the file changes and the app preview. See [Vibe coding](/features/vibe-coding). |
| `topic` | Run a team channel where people and AI post messages. See [Teams](/features/teams). |
| `prview` | Review a pull request or a branch comparison. See [Code review](/features/code-review). |
| `browser` | Work with a web page inside the chat. |
| `slides` | Produce a presentation. |
| `tutorial` | Write a tutorial organised in chapters. |

## Agent tools

When tools are enabled, agents can call:

| Group | Tools |
| --- | --- |
| Project | `project_search`, `project_read_file`, `project_write_file`, `apply_file_changes`, `project_structure`, `read_folder`, `code_writer`, `get_file_last_version` |
| Web | `fetch_webpage`, `duckduckgo_search` |
| Images | `explain_image`, `generate_image` |
| Tasks | `create_task`, `process_task` |
| Docker | `docker_ps`, `docker_logs`, `docker_stats`, `docker_inspect`, `docker_images`, `docker_run`, `docker_start`, `docker_stop`, `docker_restart` and the Docker Compose equivalents |
| Tutorials and recipes | create, modify and delete chapters; list, start and complete recipe steps |

Projects can also register **MCP servers** in their settings.

The agent loop has guards against runaway behaviour: a maximum number of iterations (**Global settings → Agents**), a maximum number of tool calls per provider, loop detection, and a cancel button that stops the request at once. Every call is checked against the user's [budget](/features/budget-and-analytics) before it is sent.

## Working with messages

* Edit, delete, hide or pin messages, and mark them as read.
* Search inside a chat and across chats.
* Use the mini map and the chat navigator to move around long conversations and sub-chats.
* Upload images and documents, record voice messages, and export a chat.
* Add checklists and tags, and change the chat status.
* Create a chat from a URL, such as a GitHub issue.
