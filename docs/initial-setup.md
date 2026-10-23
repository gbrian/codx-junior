# Initial setup

After [installing codx-junior](/getting-started), open it in your browser.

## 1. First login

Log in with the `admin` user. The first password you type becomes the admin password; you can change it later in **Settings → User account**.

## 2. Add an AI provider and models

Open **Settings → Global settings → AI Models**.

1. Add a **provider**: a name, its OpenAI-compatible API URL and an API key. OpenAI, Ollama, LocalAI, LiteLLM and vLLM all work. You can also set the provider's pricing page and its cost in cxjcoins per 1K tokens.
2. Add the **models** you want to use from that provider.
3. Pick the default model for each purpose:

| Setting | Used for |
| --- | --- |
| LLM model | Chats, tasks and agents |
| RAG model | Knowledge search and summaries |
| Embeddings model | Indexing project files |
| Wiki model | Wiki generation |
| Vision model | Understanding images and screenshots |
| Image model | Image generation |

More in [AI providers and models](/features/ai-providers).

## 3. Add a project

From the projects menu, paste a **Git URL** to clone a repository or the **path of a folder** that already exists on the server, then press `+`. The new project becomes the active one.

Each project has its own **Project settings**: models (defaulting to the global ones), knowledge options, scripts, preview URL, wiki, MCP servers and member permissions.

## 4. Index the knowledge

Open **Settings → Knowledge settings**, review the ignore patterns and start indexing. Agents use this index to find the right files. See [Knowledge](/features/knowledge).

## 5. Invite your team

In **Global settings → Users** create users, set their role (`admin` or `user`), grant access to projects and apps, and configure their wallet and spending limits. Users can also sign in with GitHub when an OAuth provider is configured. See [Users and security](/features/users-and-security).

## 6. Create a workspace

Open **Workspaces** and create one from a template to get a dev container with VS Code in the browser, a virtual desktop and your app's preview. See [Workspaces](/features/workspaces).

## A quick tour

* **Home** is the quick chat launcher: start a chat, pick a profile and a model, and reopen recent chats.
* **Kanban** holds your boards and tasks.
* **Messenger** has your teams, channels and direct messages.
* **Workspaces** lists your dev containers and their apps.
* **Analytics** shows AI usage and cost.
* **Settings** has your account, project, knowledge and global settings, plus logs for admins.
