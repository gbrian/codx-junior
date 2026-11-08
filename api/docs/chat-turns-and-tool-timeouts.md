# Tool timeouts, durable chat turns and restart recovery

Two failure modes made long chats look "stuck forever":

1. **A tool that blocks.** Synchronous tools were called directly inside the
   agent's event loop. A hanging tool (network, subprocess, lock) froze the
   whole turn and could block the process.
2. **A turn lost on restart.** The response message was persisted before the AI
   call, but the *intent to run the turn* lived only in process memory. After an
   app restart the assistant message stayed at
   `* Processing request, please wait...*` (`done=False`) and clients had no
   terminal event and no reliable stop.

This change addresses both.

---

## 1. Tool execution timeout

Every tool execution is bounded (`SmolAgent._invoke_tool`):

* **Synchronous tools** run in a daemon thread, so a blocking call no longer
  freezes the event loop. `asyncio.wait_for` abandons the wait when the timeout
  expires; the thread is left to finish on its own and is never awaited.
* **Async tools** are awaited with `asyncio.wait_for`.
* On timeout the model receives a normal tool error
  (`Tool '<name>' timed out after <n>s...`), a `TOOL_ERROR` event is emitted with
  `timeout=true`, and the turn continues. The tool is cached as a failure (so
  the model is not encouraged to blindly repeat it).

### Configuration priority

| Priority | Setting | Where |
|---|---|---|
| 1 | `timeout_seconds` | Tool registry `settings` (`ToolSettings.timeout_seconds`) |
| 2 | `tool_timeout_seconds` | `AISettings` (model > provider) |
| 3 | `CODX_JUNIOR_TOOL_TIMEOUT_SECONDS` | Environment |
| 4 | `DEFAULT_TOOL_TIMEOUT_SECONDS` (300 s) | `codx/junior/ai/smol/constants.py` |

`0` (or a negative value) disables the timeout for that tool.

---

## 2. Durable chat turns

`ChatEngine.chat_with_project` now writes a small
`ChatTurnRecord` to `<project>/.codx/chat_turns/<turn_id>.json` before the AI
call and holds an exclusive `flock` on `<turn_id>.lock` for the whole turn
(`codx/junior/chat/turn_store.py`).

* The conversation itself is still persisted by `ChatManager` / 
  `ChatEventBridge`; the record only stores the identifiers needed to reload it.
* On success / cancellation / handled failure the record is finalized and
  removed.
* The response message is stamped with `meta_data.turn_id` and
  `meta_data.turn_attempt`.

Orchestration-owned chats (`run_id` / `run_step_id`) are excluded: the
orchestration worker already recovers them.

---

## 3. Recovery after an app restart

`codx/junior/chat/turn_recovery.py` starts with the application
(`app.startup_event`) and sweeps every project every 20 s
(`CODX_JUNIOR_CHAT_TURN_RECOVERY_INTERVAL`):

1. load the active turn records,
2. skip records whose `flock` is held by a live process,
3. repair orphaned `done=False` assistant messages (mark `done=True`, hide them
   from prompt history),
4. resume the turn through the normal `ChatEngine` pipeline (profiles, tools,
   knowledge, streaming, cost — unchanged),
5. bound retries with `CODX_JUNIOR_CHAT_TURN_MAX_ATTEMPTS` (default 3), then mark
   the turn failed and repair the message so the client never stays in
   "processing".

Disable recovery with `CODX_JUNIOR_CHAT_TURN_RECOVERY=0`.

The per-turn `flock` makes recovery safe in both processes (API and background):
only one owner can resume a turn. If the process crashed *after* the answer was
persisted, recovery detects the completed assistant message and finalizes the
record instead of running the turn twice.

---

## 4. Client control

### Stop a turn

`POST /api/chat/cancel`

```json
{ "chat_id": "<chat id>" }
```

or

```json
{ "token_id": "<cancellation token UUID>" }
```

The endpoint cancels the in-memory token when it exists and also stops the
durable turn: the record is marked cancelled (never resumed), and its orphaned
response message is repaired. This is the stop path that still works after a
restart, when no `CancellationToken` exists in memory.

Response:

```json
{ "cancelled": true, "method": "chat_id", "stopped_turns": 1 }
```

### List processing turns

`GET /api/chat/processing?codx_path=<project>/.codx`

```json
{
  "turns": [
    {
      "turn_id": "...",
      "chat_id": "...",
      "status": "running",
      "attempts": 1,
      "max_attempts": 3,
      "started_at": "...",
      "updated_at": "...",
      "error": null,
      "alive": true
    }
  ]
}
```

Clients can render the processing state from this list and offer the stop
action.

---

## 5. Tests

* `tests/ai/smol/test_tool_timeout.py` — sync/async/per-tool timeout.
* `tests/chat/test_turn_store.py` — record lifecycle, cancellation, message
  repair and restart recovery.

Made with ❤️ by codx-junior
