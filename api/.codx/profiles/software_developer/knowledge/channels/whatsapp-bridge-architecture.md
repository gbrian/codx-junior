# WhatsApp ⇄ messenger bridge (decided architecture)

Status: revised 2026-04 (board **Channels**, column **WhatsApp**, parent chat `ee7b29bd-72ca-4fb5-a777-a33d08b921e1`).

## Decisions taken by the user
- **Transport**: official **WhatsApp Cloud API** (Meta Graph). No Baileys / whatsapp-web.js.
- **Groups API**: **ignored for now**. Groups are created and managed by the user in the WhatsApp
  client; codx-junior only *stores* the group name/id in the chat and syncs messages.
- **Secrets**: live in **global settings → `integrations`** (`GlobalSettings.integrations`), a generic
  list so Slack / other providers can be added later. No env-var references as the primary path,
  nothing in `.codx` project JSON, nothing in git.
- **Identity**: each `CodxUser` can carry a phone number (`wa_id`) plus an `enabled` WhatsApp flag.
  A chat-level user integration decides which participants are synced to WhatsApp.
- **Direction**: full duplex. People talk on the messenger side and on WhatsApp and both see each other.
- **Unit of linking**: a codx-junior **group chat (`Chat`)** is connected to **one** WhatsApp
  group/DM. The chat stores the WhatsApp group name/id in its integration config; inbound messages
  are routed back by that id (fallback: group name).
- **Board convention**: every WhatsApp task lives on board `Channels`, column `WhatsApp`.

## Layering
```
WhatsApp  <-- Cloud API / webhook -->  channels/whatsapp/{client,webhook,adapter}
                                             |
                                       channels/bridge  (inbound normalize -> Chat)
                                             |
                                       channels/store   (binding kept on the Chat + per-user map)
                                             |
   EventManager.message_event --> channels/sink (+ formatting) --> WhatsApp
```

## Config surface
- `GlobalSettings.integrations[]` — `{ id, provider: "whatsapp"|"slack", enabled, config{app_id,
  phone_number_id, waba_id, token, app_secret, verify_token} }`.
- `CodxUser` — `phone_number` / `wa_id` + `integrations: { whatsapp: { enabled: bool } }`.
- `Chat` — `integrations.whatsapp = { enabled, group_id, group_name, participants[] }`.

## Key integration points (verified in code)
| Need | Piece |
|---|---|
| Persist chats/messages | `codx/junior/chat_manager.py` (`add_message`, `save_chat` → emits `chat-event`) |
| Message/chat models | `codx/junior/db.py` — `Chat` (`users`, `visibility`, `chat_links`, `meta`), `Message.meta_data` |
| Live UI updates | `codx/junior/events/event_manager.py` (`message_event`, `chat_event`) — also where the **outbound sink** is registered |
| Long tasks off the request thread | `ThreadPoolExecutor` pattern of `SIO_POOL` in `codx/junior/sio/sio.py` |
| Router pattern | `codx/junior/api/*.py` + `app.include_router(..., prefix="/api")`; `require_admin` / `get_current_session` |
| Global settings + providers | `codx/junior/model/model.py` (`GlobalSettings`, `AIProvider` is the model for the `integrations` list), `read_global_settings` / `write_global_settings` |

## Non-negotiables
1. **Loop prevention**: every mirrored message is tagged `meta_data["channel"] = {"provider":"whatsapp",
   "external_id":..., "external_message_id":...}`; the sink skips tagged messages. Idempotency comes
   from WhatsApp message ids.
2. **Never block the webhook**: return 200 fast, process in a worker pool.
3. **Secrets never leave global settings** (and are never echoed back by the API — write-only fields).
4. **Signature**: `X-Hub-Signature-256` HMAC-SHA256 over the raw body, `hmac.compare_digest`.
5. **Formatting**: Markdown → WhatsApp markup, split at ≤4096 chars, never inside a code fence.
6. AI answers are **opt-in** (`reply_policy` = off|mention|prefix|always); `off` must produce zero LLM calls.

## Known caveats
- Business-initiated messages outside the 24h customer-service window require approved templates.
- Unknown `wa_id` must not silently join a chat: reject or auto-provision as read-only guest.
- Rate limits, media size limits, token expiry.