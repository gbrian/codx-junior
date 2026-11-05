# DSH task sync

codx-junior can mirror chats and sub-tasks created in a
[DSH](https://github.com/deepseek-ai/deepseek-harness) Harness. The DSH Session
stays the single copy of the conversation: the codx-junior card stores only the
task identity, hierarchy and board placement, and fetches the messages live
when you open it.

This is a two-sided integration:

| Side | Location | Responsibility |
|---|---|---|
| DSH Host plugin | `dsh-codx-junior/` | Bridge HTTP API, session change webhooks, live task/message projection |
| codx-junior API | `api/codx/junior/integrations/dsh.py`, `api/codx/junior/api/dsh.py` | Mirror tasks, authenticate webhooks, create DSH sessions, hydrate task details |

## How it works

1. The DSH plugin watches `session/created`, `session/updated` and
   `session.disposed`. It posts a compact task payload (id, title, parent,
   status, `cwd`, no messages) to `POST /api/dsh/events`.
2. codx-junior upserts a linked `Chat` on the `DSH` board. `Chat.parent_id`
   follows the DSH parent session, so subagent sessions appear as sub-tasks.
3. Opening the card calls `GET /api/chats?id=...`; the API fetches the live
   message surface from the DSH bridge (`GET /codx-junior/tasks/{id}`) and
   returns it in memory. Nothing is written to the task JSON.
4. `POST /api/dsh/tasks` creates a DSH Session (and optionally prompts it) and
   mirrors the returned Session as a codx-junior task.
5. `POST /api/dsh/tasks/{sessionId}/prompt` sends a follow-up prompt to DSH.
   Native codx-junior chat turns are refused on mirrored tasks so the two
   engines never write the same conversation.

DSH-created chats are mirrored from the webhook; you can also pull everything
on demand with `POST /api/dsh/sync`.

## Configuration

The plugin writes a shared secret to `<workspace>/.dsh-codx-junior/secret`.
codx-junior reads the same file. Do not commit it.

Environment variables (codx-junior API):

| Variable | Default | Meaning |
|---|---|---|
| `CODX_JUNIOR_DSH_URL` | `http://127.0.0.1:3080` | DSH web origin |
| `CODX_JUNIOR_DSH_SECRET` | — | explicit secret (overrides the file) |
| `CODX_JUNIOR_DSH_SECRET_FILE` | `<project>/.dsh-codx-junior/secret` | secret path |
| `CODX_JUNIOR_DSH_BOARD` | `DSH` | mirror board title |
| `CODX_JUNIOR_DSH_ENABLED` | `1` | set `0` to disable |
| `CODX_JUNIOR_DSH_ONLY_PROJECT` | `1` | ignore sessions outside the project |
| `CODX_JUNIOR_DSH_TIMEOUT` | `15` | bridge timeout in seconds |

Plugin row fields and the bridge API are documented in
`dsh-codx-junior/README.md`.

## Board behaviour

The integration creates the configured board lazily with four columns:
`Todo`, `Doing`, `On hold`, `Done`.

- new idle task → `Todo`
- DSH turn running → `Doing` (only when the card is still in `Todo`, so a
  manual move is never undone)
- DSH error → `On hold`
- disposed session → task state `closed` (the codx-junior card remains, so the
  board keeps its history)

## HTTP surface

All DSH bridge routes use `Authorization: Bearer <secret>`:

| Method | Path |
|---|---|
| `GET` | `/codx-junior/health` |
| `GET` | `/codx-junior/tasks` |
| `GET` | `/codx-junior/tasks/{sessionId}` |
| `POST` | `/codx-junior/tasks` |
| `POST` | `/codx-junior/tasks/{sessionId}/prompt` |
| `POST` | `/codx-junior/tasks/{sessionId}/cancel` |
| `POST` | `/codx-junior/tasks/{sessionId}/title` |

codx-junior routes:

| Method | Path |
|---|---|
| `POST` | `/api/dsh/events` |
| `GET` | `/api/dsh/status` |
| `POST` | `/api/dsh/sync` |
| `POST` | `/api/dsh/tasks` |
| `GET` | `/api/dsh/tasks/{sessionId}/messages` |
| `POST` | `/api/dsh/tasks/{sessionId}/prompt` |
| `POST` | `/api/dsh/tasks/{sessionId}/cancel` |
| `POST` | `/api/dsh/tasks/{sessionId}/rename` |

Webhook bodies are signed with
`X-DSH-Signature: sha256=<HMAC of the exact body>` and also carry the bearer
secret.

## Limitations

- A blank DSH Session is not mirrored until its first prompt, unless
  codx-junior created it explicitly.
- The mirrored task is read-only in the codx-junior chat UI; use DSH (or the
  prompt endpoint) to continue the conversation.
- Archiving/deleting the codx-junior card does not delete the DSH Session.
- The codx-junior API must be reachable by the DSH Host process (default
  loopback), and the DSH web server must be reachable by the API.
