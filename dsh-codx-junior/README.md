# DSH ↔ codx-junior task sync

This DSH Host plugin keeps codx-junior boards aware of DSH chats without
copying the conversation. A DSH Session is the source of truth; the mirrored
codx-junior task stores only identity, hierarchy and board placement.

## What it does

- Mirrors every non-blank DSH Session (including subagent Sessions) as a task on
  the codx-junior `DSH` board.
- Sends `session.created`, `session.updated` and `session.disposed` webhooks to
  `POST /api/dsh/events` on codx-junior.
- Exposes a token-protected bridge under `/codx-junior/*` so codx-junior
  can list tasks, read the live message surface, create a Session and prompt
  it, send follow-up prompts, rename and cancel.
- Creates `<workspace>/.dsh-codx-junior/secret` on first load. codx-junior reads
  the same file, so no secret has to be copied into configuration.

## Bridge API

All routes require `Authorization: Bearer <secret>` (or `x-dsh-secret`).

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/codx-junior/health` | bridge status |
| `GET` | `/codx-junior/tasks` | list tasks (`cwd`, `includeBlank`, `limit`) |
| `GET` | `/codx-junior/tasks/{sessionId}` | task + live messages + `lastSeq` |
| `POST` | `/codx-junior/tasks` | create Session and prompt it |
| `POST` | `/codx-junior/tasks/{sessionId}/prompt` | queue or steer a prompt |
| `POST` | `/codx-junior/tasks/{sessionId}/cancel` | cancel the active turn |
| `POST` | `/codx-junior/tasks/{sessionId}/title` | rename the Session |

`POST /codx-junior/tasks` body:

```json
{
  "title": "Fix the login timeout",
  "prompt": "Investigate and fix the timeout",
  "cwd": "/home/me/project",
  "agentPreset": "default",
  "codxTaskId": "optional-codx-chat-id",
  "parentSessionId": "optional-parent-session"
}
```

Prompt bodies accept `{ "text": "...", "mode": "queue" | "steer" }`.

## Webhooks

The plugin posts a JSON body signed with HMAC-SHA256:

- `Authorization: Bearer <secret>`
- `x-dsh-secret: <secret>`
- `x-dsh-signature: sha256=<hex hmac of the exact request body>`

Task payloads contain `id`, `title`, `parentId`, `origin`, `isSubagent`,
`depth`, `cwd`, `agentPreset`, `createdAt`, `updatedAt`, `running`, `status`,
`webUrl`, `description` and `lastMessage`. No full message history is sent.

## Configuration

The bundle patch sets sensible defaults. Override them in the plugin row:

| Field | Default | Meaning |
|---|---|---|
| `codxApiUrl` | `http://127.0.0.1:19980` | codx-junior API origin |
| `codxPath` | `<cwd>/.codx` | codx-junior project scope for webhooks |
| `board` | `DSH` | codx-junior board title |
| `defaultColumn` | `Todo` | column for new idle tasks |
| `uiUrlTemplate` | `http://127.0.0.1:3080/?session={sessionId}` | deep link stored on the task |
| `webhookEnabled` | `true` | push task changes |
| `syncOnStart` | `true` | send an initial `sync.snapshot` |
| `debounceMs` | `900` | per-session webhook debounce |
| `requestTimeoutMs` | `15000` | bridge/webhook timeout |
| `projectPath` | empty | optional `cwd` filter for task listing |

`DSH_CODX_JUNIOR_SECRET` overrides the generated secret.

## Install

From this workspace:

```text
plugin_manager install_bundle target=/absolute/path/to/dsh-codx-junior
```

Then start (or reload) DSH. Inspect `/codx-junior/health` with the secret:

```bash
curl -H "Authorization: Bearer $(cat .dsh-codx-junior/secret)" \
  http://127.0.0.1:3080/codx-junior/health
```

## Notes

- A blank Session is not mirrored until its first prompt, unless codx-junior
  created it explicitly through `POST /codx-junior/tasks`.
- Session messages are projected at request time from the durable log. The
  bridge never writes a second conversation copy.
- The codx-junior counterpart lives in
  `api/codx/junior/integrations/dsh.py` and `api/codx/junior/api/dsh.py`.
