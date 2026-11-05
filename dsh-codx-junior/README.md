# DSH → codx-junior agent channel

This DSH Host plugin connects **outbound** to a codx-junior instance. It
registers itself, sends heartbeats, long-polls commands and posts task events.
codx-junior never needs to reach DSH, so DSH can stay behind its normal
security boundary.

The DSH Session remains the single copy of the conversation. A mirrored
codx-junior task stores only its identity, parent/child relationship and board
placement; messages are read on demand through the command channel and are not
persisted by codx-junior.

## What it does

- `POST /api/dsh/agent/register` on startup (and after token rotation).
- `POST /api/dsh/agent/heartbeat` every few seconds with session/running counts.
- `GET /api/dsh/agent/commands` long-poll; executes `create_task`, `prompt`,
  `cancel`, `rename`, `get_task`, `list_tasks` and posts each result.
- `POST /api/dsh/agent/events` for `session.created`, `session.updated` and
  `session.disposed`, including subagent sessions.
- Registers once per Host; the `instance_id` is persisted in
  `.dsh-codx-junior/instance.json`.

## Configuration

The plugin row accepts:

| Field | Default | Meaning |
|---|---|---|
| `codxApiUrl` | `http://127.0.0.1:19980` | codx-junior API origin reachable **from DSH** |
| `token` | empty | Agent token generated in codx-junior Global Settings |
| `agentEnabled` | `true` | Enable the outbound channel |
| `bridgeEnabled` | `false` | Legacy inbound bridge; leave off unless debugging locally |
| `heartbeatMs` | `5000` | Heartbeat interval |
| `pollWaitMs` | `25000` | Command long-poll window |
| `syncOnStart` | `true` | Send an initial task snapshot after registration |
| `instanceName` | host + project | Display name in the codx-junior dashboard |
| `instanceId` | generated | Stable instance identity |

If `token` is empty, the plugin reads
`<workspace>/.dsh-codx-junior/token`. The codx-junior dashboard writes that
file when it generates a token on the same filesystem. For remote DSH, paste
the token into the plugin row.

## Quick start

1. Rebuild/restart codx-junior so the **DSH Harness** tab and
   `/api/dsh/agent/*` routes are deployed.
2. In codx-junior open **Global Settings → DSH Harness**.
3. Click **Generate token**.
4. In DSH set `codxApiUrl` to the codx-junior API and paste the token (or let
   the plugin read the token file).
5. Start/reload DSH. The instance appears in the dashboard within a few
   seconds.
6. Save the board and click **Sync from instance**.
7. Open the board; use **Trigger a DSH task** to create a Session from
   codx-junior.

## Agent protocol (called by DSH)

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/dsh/agent/register` | register/refresh an instance |
| `POST` | `/api/dsh/agent/heartbeat` | liveness and load |
| `GET` | `/api/dsh/agent/commands` | long-poll commands |
| `POST` | `/api/dsh/agent/commands/{id}/result` | command result |
| `POST` | `/api/dsh/agent/events` | task events/snapshot |
| `POST` | `/api/dsh/agent/unregister` | clean shutdown |

Every call carries `Authorization: Bearer <agent-token>` and the project
`codx_path` query. codx-junior verifies the token before touching the registry.

## Legacy direct bridge

`bridgeEnabled: true` keeps the old token-protected `/codx-junior/*` HTTP route
for local debugging. It is disabled by default and is not used by the
dashboard.
