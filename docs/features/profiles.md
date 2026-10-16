# Profiles

Profiles are reusable instructions that tell the AI how to behave. They encode your coding standards, your architecture and your preferences.

![Profiles](/images/NOV2025/codx-junior-profiles.png)

## What a profile contains

| Field | Description |
| --- | --- |
| Name, avatar, description | How the profile appears in chats and mentions. |
| Category | `global`, `file`, `coding` and others. |
| File match | A pattern; the profile is applied automatically to matching files. |
| Content | The instructions, in Markdown. |
| Linked profiles | Other profiles to include. |
| Model | The LLM the profile uses. |
| Tools | The [agent tools](/features/chats-and-agents#agent-tools) it may call. |
| Use knowledge | Whether the profile searches the project's knowledge. |
| Chat mode | Changes how the conversation works, for example writing a document instead of chatting. |
| API settings | Expose the profile as a model through the [OpenAI-compatible API](/features/api). |

## Built-in profiles

codx-junior ships with profiles such as **analyst**, **software developer**, **teacher**, **browser**, **project** and **wiki**. Use them as they are or as a starting point.

## Using profiles

* Pick profiles for a chat or a Kanban task.
* Mention a profile in a message to bring it into the conversation.
* Let file-matching profiles apply automatically when the AI edits matching files.
* Edit profiles from the profile view, or ask the AI to improve a profile from a chat.
