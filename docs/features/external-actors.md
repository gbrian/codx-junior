# External actors and outreach

> **Status: MVP implemented (email + manual relay).** The design below is
> implemented in this branch for the email and manual channels: global actor
> directory with per-project links, outreach requests, waiting state, answer
> packets, SMTP/IMAP bridge, REST API, agent tools and a project view. Slack,
> WhatsApp and the external portal remain designed but not implemented; the
> "MVP implementation" section at the end maps the code, API and known gaps.
>
> Companion reading: [Slack and WhatsApp channels](/features/slack-whatsapp-integration)
> (the mirroring design), [Teams and messenger](/features/teams),
> [Kanban and tasks](/features/kanban), [Profiles](/features/profiles),
> [Users and security](/features/users-and-security).

---

## 1. Decision in one page

**External participants must not be users with connectors.** The three things
that are being conflated need to stay separate:

| Concept | What it is | Who owns it | Has a login? |
| --- | --- | --- | --- |
| **Connector** | A configured transport account: a project mailbox, a Slack app installation, a WhatsApp business number | The organization (admin) or an internal user's linked account | No, it is a credential |
| **External actor** (contact) | A person outside the org: name, role, organization, language, one handle per channel | Global directory (the identity) + a link per project (the role and context) | No |
| **Outreach** (request) | One task-scoped ask: questions, deadline, expected answer, channel thread, status | The task that needs the answer | No |

The designer does not install anything and does not get an account. The
organization owns the mailbox / Slack app / WhatsApp number; the designer is a
**contact reached through it**. The agent's question and the designer's answer
are tracked as an **outreach request** attached to the task.

The actor identity is **global**: the same designer can be linked to several
projects (different customers) without being duplicated. What changes per
project is the relationship — role, title, notes, availability — and, above
all, the outreach: every request is bound to exactly one project and one task,
and every reply is routed back to that project and task.

If a connector already exists for an internal user (the Gmail and
"connect WhatsApp with user" work in the backlog), that is a different feature:
it mirrors *that user's* personal account. It is not how you reach a third
party, because it breaks when the user is on holiday and it exposes a personal
mailbox to project work.

**Recommended shape**

1. **M0 — workflow without connectors.** Contact book in the project, an
   `ask_external` tool, a `waiting_external` task state, an answer packet, and
   *manual relay* (a human pastes the WhatsApp/email reply). This ships the
   working method even before any provider is integrated.
2. **M1 — email** (first real connector). Universal reach, no provider
   approval, natural threading, attachments, async by default.
3. **M2 — Slack** for counterparts who already share a workspace, reusing the
   existing channel design.
4. **M3 — WhatsApp Cloud API** (best reach for freelancers, but templates and
   a 24-hour window add friction and external lead time).
5. **M4 — optional external portal** (magic link, scoped to one task) for
   people who must see a preview or approve a deliverable.

**Why not just "external user + connector":**

* a WhatsApp-only designer cannot complete an account, password reset or 2FA;
* `CodxUser` carries project permissions, wallet, apps and tool access — gross
  over-privilege for someone answering "which logo do you prefer?";
* connectors are credentials, not something you ask a third party to own. Your
  Slack app only works in workspaces that install it; reaching another
  organization needs Slack Connect (paid plans, both admins) or a guest
  account;
* the audit and consent model is per request, not per permanent account;
* the actual interaction is one question and one answer. A user account models
  a relationship that does not exist.

A long-term freelancer who works in the platform every day can still be
**promoted** to a restricted `CodxUser` (project-scoped, non-admin profile,
guardrails on) as an explicit admin action. That is the exception, not the
default.

---

## 2. The scenario this must support

> "I need a website. I can only reach the designer by WhatsApp, Slack or
> email. The website task is assigned to the `web_master` and `Designer`
> profiles, but they need the logo, the brand colors and the tone of voice
> before they can produce anything."

Today the task stops and a human becomes the messenger: the agent writes the
question in the chat, a person copies it to WhatsApp, waits, copies the answer
back. The goal is to keep the human in the loop for **approval and judgment**,
not for copy/paste, and to make the external dependency visible on the board.

Two valid triggers:

* **declared** — the task itself lists required external inputs ("brand assets
  from Ana, due before design starts"), so planning can block on it;
* **discovered** — the agent, mid-task, calls `ask_external(...)` because it
  cannot proceed.

Both create the same `OutreachRequest`.

---

## 3. Actor model

### 3.1 Taxonomy

| Actor | Identity | Auth | Stored in | Can trigger an AI turn | Owns a connector |
| --- | --- | --- | --- | --- | --- |
| **Internal user** | `username` | login / OAuth | `GlobalSettings.users` | Yes (UI) | Optional, personal |
| **AI profile** | profile name | none (acts on behalf of a run) | `.codx/profiles` | Yes (assigned to task) | No |
| **External actor** | `actor_id` + channel handles | none; verified per message | global `<config>/external/actors.json` + a project link in `.codx/external/contacts.json` | **No** — only via the outreach policy | No |
| **Portal guest** (M4) | signed magic link scoped to one task | link token | project store | No | No |
| **Service** | agent token | bearer token | global settings | Yes (API) | No |

Only internal users and AI profiles are "members". External actors are
**contacts**: they cannot be assigned tasks, mentioned with `@`, added to a
team roster, or given a wallet. They appear in a task only as the counterparty
of an outreach.

This is why "users with connectors" is the wrong primitive: it forces every
external person into the membership graph, where all of the above becomes
possible by accident.

### 3.2 Relationship to the existing channel design

The Slack/WhatsApp design defines channel roles R1–R6: room mirror, notification
sink, personal DM mirror, command surface, approval surface and agent outbound
tool. None of them is "the agent needs an answer from a person who is not in
the platform". This proposal adds:

| Role | Direction | Purpose |
| --- | --- | --- |
| **R7 — Outreach** | Agent asks, external answers | Task-scoped question/answer with a deadline, tracked as a dependency |

R7 shares the transport, identity mapping and outbox with R1–R6, but has its
own lifecycle and its own security default: the external person is answering a
specific question, not joining a room. If R1 ships first, R7 reuses its
gateway; if not, R7 can ship on a thin adapter and R1 can adopt it later.

### 3.3 Connector ownership

A connector is a **project resource** for outreach (shared mailbox
`website@acme.com`, a Slack app in the agency workspace, the company WhatsApp
number), not a user's personal account. Two consequences:

* the sender identity is stable and survives people leaving;
* secrets live in global settings (admin-only) and the project only references
  `connector_id`, matching the existing rule that project settings are
  user-readable.

### 3.4 One actor, many projects

A designer who works for two customers is **one actor** with **two project
links**:

```
                    global directory
                 ┌──────────────────────┐
                 │ act_ana              │
                 │ Ana · Studio Norte   │
                 │ email: ana@…         │
                 │ whatsapp: +34…       │
                 └──────────┬───────────┘
                            │
          ┌─────────────────┴─────────────────┐
          │                                   │
  Acme project (.codx)                Beta project (.codx)
  contact: designer, priority         contact: brand reviewer
  request out_a1 → task "Website"     request out_b7 → task "Rebrand"
```

**Storage split**

| Data | Scope | Why |
| --- | --- | --- |
| Name, organization, channel handles, consent, opt-out | Global | The person is the same; one place to update an email or block a contact |
| Role, title, notes, active flag | Per project | Ana is the designer for Acme and the brand reviewer for Beta |
| Outreach request, questions, answers, thread ids | Per project | Cost, audit and data belong to the project that asked |

**Routing rules (the important part)**

Because one person can have open requests in several projects, an inbound
message cannot be routed by sender alone. In order:

1. **Opaque reply token** in the reply address or a `References` header —
   carries `project_id` + `request_id` + `actor_id`. This is the primary key.
2. **Thread headers** (`In-Reply-To` / `References`) matched against the
   outbound `Message-ID` index.
3. **Sender + exactly one open request** across all projects — accepted only
   when there is no ambiguity.
4. **Sender + several open requests** — quarantined, never guessed. The owner
   of each candidate request is asked to confirm; the reply is not posted to a
   project.

**Context in every message**

Every outbound email carries the project and the task in human-readable form
(subject tag, body block) *and* in the routing metadata:

```
Subject: [Acme · Website v1] Question from Acme (ref out_a1)
Reply-To: outreach+<signed-token>@acme.com
X-Codx-Project: <project_id>
X-Codx-Task: <chat_id>
X-Codx-Request: out_a1

Hi Ana,

Project: Acme Website (Acme)
Task:    Website v1
Ref:     out_a1

1. ...
```

The reply is delivered to the project that asked, even if Ana is answering
from the same mailbox she uses for Beta. The Beta project never sees this
thread.

**Privacy rule**

A project sees only its own links and requests. The fact that Ana also works
for Beta is visible only in the global directory (admin), never in the Acme
project API or UI. Directory search from a project returns a *minimal* match
(name, organization, handles) so an admin can link an existing actor without
exposing the other customers.

**Identity uniqueness**

One channel handle maps to at most one actor. If the same person uses different
addresses per customer, add both identities to the same actor with labels
("work", "studio") and pick the handle per request. If two actors claim the
same email, creation fails instead of silently creating a routing ambiguity.

---

## 4. How it works

### 4.1 Ask → wait → answer → resume

```
 Task chat (internal)                     External actor
 ─────────────────────                    ──────────────
 agent calls ask_external
        │
        ▼
 policy gate ── approval? ──► project admin approves
        │
        ▼
 OutreachRequest (draft → sent)  ───────►  email / Slack / WhatsApp
        │                                        │
        ▼                                        │
 task status = waiting_external                   │
 agent turn ends (no polling, no spend)           │
        │                                        │
        │  reminder T-1d, escalation at due      │
        │                                        ▼
        │                                  reply arrives
        │                                        │
        │                                  adapter verifies sender,
        │                                  matches thread/token,
        │                                  strips quotes/signature
        │                                        │
        │                                        ▼
        │                                  message stored in the
        │                                  outreach thread chat,
        │                                  tagged untrusted
        │                                        │
        ▼                                        ▼
 answer packet (structured answers + quotes + attachments)
        │
        ▼
 task status = in progress
 optional auto-resume turn ──► agent continues the work
```

Key point: **the external message never drives the agent directly.** It is
stored as evidence, summarized into an answer packet, and the task turn is
re-triggered under project policy. This single rule removes most prompt
injection and runaway-cost risk.

### 4.2 What the agent sees

Inbound text is first processed by a **tool-less extraction step** (classify +
map to the asked questions). The working agent does not receive the raw email
as instructions; it receives a structured answer packet. The MVP uses a
deterministic extractor (numbered answers map by position; anything else is
kept whole and flagged `unstructured`); an LLM-backed classifier can replace it
without changing the packet contract.

* the request id, actor, channel and timestamps;
* per question: the answer (verbatim if short, summarized if long), and the
  attachment references;
* confidence and flags (`partial`, `ambiguous`, `out_of_office`,
  `counter_question`);
* an explicit provenance line: *answered by Ana (external) · email · 12 Nov*.

The raw message stays in the outreach thread and can be pulled with a read
tool, inside an untrusted-content wrapper. This keeps injected instructions out
of the working agent's instruction stream while preserving the full evidence.

### 4.3 Conversation placement

| Data | Location | Why |
| --- | --- | --- |
| External conversation | `Chat(mode="channel")` linked to the task (`parent_id`, `meta_data.external`) | One room per thread; UI already renders it; answers are attributable |
| Task conversation | the task `Chat` | Stays internal and readable |
| Request state | `.codx/external/requests/<id>.json` | Queryable, survives chat edits, one file per request |
| Contact book | global `<config>/external/actors.json` (identity) + `<project>/.codx/external/contacts.json` (role, link) | One person, many customers; the identity is shared, the relationship is local |
| Reply tokens | opaque high-entropy token, stored hashed in a global index (project + request + actor) | Binds every reply to one project/task even when the actor has other open requests; revocable |
| Attachments | project `.codx/external/media/` | Size/MIME checked, hash-named |

For a faster v0, external messages can go directly into the task chat with an
author prefix. That is acceptable for the manual-relay milestone; the split
above is the target because it keeps untrusted content and internal notes
separate.

**MVP note.** The implemented MVP stores the request under
`.codx/external/requests/`, posts the answer packet into the task chat, and
keeps the raw reply in the request timeline/attachments. The separate
channel-chat per thread is the M2 target, not a dependency for the email
workflow.

### 4.4 Waiting state and orchestration

* `Chat.status = "waiting_external"` (free-form today) plus
  `meta_data.waiting = {requests: [...], since, due_at}`.
* The status is the source of truth. A project can add a **Waiting on client**
  column and move the card there with the same owner action (or a small board
  rule); no schema change is required, but the move is not implicit.
* The worker skips tasks with an open blocking request: no repeated AI turns,
  no silent retries, no cost.
* When the last blocking request is answered or cancelled, the task returns to
  its previous status. Auto-resume is a per-project policy, not a hardcoded
  behavior.
* Orchestration runs that need the answer record the request as a dependency
  and pause the step. The worker never busy-waits: it is woken by the request
  state change.

### 4.5 Reminders and escalation

| When | Action |
| --- | --- |
| T-24h before due | Gentle nudge in the same thread (email reply, Slack thread; WhatsApp free-form inside the 24 h window, template outside) |
| At due | Request → `overdue`; notify the task owner, not the external person again |
| T+2d overdue | One final follow-up, then stop (rate limit) |
| No answer after N days | Offer "close as unanswered", "try another channel", "assign to a human" |
| Actor replies "stop" | Opt-out recorded, request closed, suppression honored |

Snoozing, re-sending on another channel and extending the deadline are explicit
actions, so the audit trail shows who decided what.

---

## 5. Data model (minimal)

```python
# api/codx/junior/model/external.py (new)

class ActorIdentity(BaseModel):
    provider: Literal["email", "slack", "whatsapp"]
    handle: str                  # address, Slack user id, wa_id
    label: str = ""
    verified: bool = False       # confirmed by a reply or by an admin


class ActorConsent(BaseModel):
    status: Literal["unknown", "granted", "opted_out"] = "unknown"
    source: str = ""             # "admin", "replied", "imported"
    at: str = ""


class ExternalActor(BaseModel):
    """Global identity. One record per person, shared by every project."""
    id: str                      # "act_..."
    name: str
    organization: str = ""
    language: str = "auto"
    timezone: str = ""
    identities: List[ActorIdentity] = []
    consent: ActorConsent = ActorConsent()
    status: Literal["active", "blocked", "archived"] = "active"
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""


class ProjectContact(BaseModel):
    """The relationship: what this actor is for *this* project."""
    actor_id: str
    role: str = ""               # designer, client, vendor, legal
    title: str = ""
    notes: str = ""
    active: bool = True
    created_by: str = ""
    created_at: str = ""


class OutreachQuestion(BaseModel):
    id: str
    text: str
    answer_type: Literal["text", "choice", "date", "number", "file"] = "text"
    choices: List[str] = []
    required: bool = True


class OutreachAnswer(BaseModel):
    question_id: str
    text: str = ""
    files: List[str] = []
    source_message_id: str = ""
    confidence: Literal["high", "medium", "low"] = "high"
    flags: List[str] = []


class OutreachEvent(BaseModel):
    at: str
    type: str                    # created, sent, reminded, answered, cancelled...
    actor: str = ""              # username or "system"
    message: str = ""
    data: Dict[str, Any] = {}


class OutreachRequest(BaseModel):
    id: str                      # "out_..."
    project_id: str
    project_name: str = ""       # snapshot for the email/audit
    task_chat_id: str            # the Kanban card / task
    task_name: str = ""          # snapshot
    thread_chat_id: str = ""     # external conversation chat
    actor_ids: List[str]
    actor_name: str = ""
    actor_handle: str = ""       # the address/phone used for this request
    connector_id: str = ""
    channel: Literal["email", "slack", "whatsapp", "manual"] = "email"
    status: Literal[
        "draft", "pending_approval", "sent", "answered",
        "declined", "overdue", "cancelled", "failed",
    ] = "draft"
    blocking: bool = True
    subject: str = ""
    questions: List[OutreachQuestion] = []
    answers: List[OutreachAnswer] = []
    due_at: str = ""
    reminders_sent: int = 0
    thread_refs: Dict[str, str] = {}   # email Message-ID / slack ts / wa conversation
    reply_token_hash: str = ""
    reply_to: str = ""
    message_id: str = ""
    inbound_message_ids: List[str] = []
    timeline: List[OutreachEvent] = []
    last_error: str = ""
    created_by: str = ""               # "profile:web_master" or username
    approved_by: str = ""
    close_reason: str = ""
    created_at: str = ""
    sent_at: str = ""
    answered_at: str = ""
    updated_at: str = ""
```

`OutreachRequest` is the unit shown in the task panel and in the audit. It is
deliberately small: the messages are chats, the transport details are
`thread_refs`, and the answers are structured so the agent does not have to
re-parse prose.

### 5.1 Message tagging

```json
{
  "external": {
    "actor_id": "act_ana",
    "provider": "email",
    "connector_id": "mail-website",
    "outreach_id": "out_123",
    "direction": "inbound",
    "external_message_id": "<...>",
    "external_thread_id": "<...>",
    "trust": "untrusted"
  }
}
```

Rules:

* every inbound and outbound message carries the tag; it drives dedupe, loop
  prevention, UI badges and audit;
* `trust: "untrusted"` is consumed by prompt assembly and by the tool policy;
* do **not** reuse `Chat.external_source` / `external_id` (reserved for DSH
  mirror tasks and protected by a `409` on write), and do not overload
  `Chat.users` / `Chat.assignees` with external ids.

### 5.2 Tools exposed to profiles

| Tool | Effect | Notes |
| --- | --- | --- |
| `ask_external(actor, questions, due_at, channel?, blocking?)` | Creates a request, sends it or parks it for approval | Returns `request_id`; the agent should end its turn |
| `list_external_requests(task?)` | Open/answered requests for context | Read-only |
| `record_external_reply(request_id, text, files?)` | Manual relay: a human pastes the answer | Works before any connector exists |
| `cancel_external_request(request_id, reason)` | Closes the request | Never deletes the audit trail |

The tool is only available when the profile (or project policy) allows it, and
it is never available to a turn triggered by an external message.

---

## 6. Channels

### 6.1 Capability comparison for *outreach*

| | Email | Slack | WhatsApp Cloud API |
| --- | --- | --- | --- |
| Reach a person with no account | Yes | No — needs Slack Connect (paid, both admins) or a guest account | Yes |
| Setup friction | Mailbox + DNS (SPF/DKIM/DMARC) | App install, workspace admin | Meta business verification, templates |
| First outbound message | Any | Any (if connected) | Must be an approved template |
| Conversation window | None | None | 24 h; templates outside it |
| Threading | `Message-ID` / `In-Reply-To` / `References` | `thread_ts` | None (contextual reply) |
| Attachments | Yes | Yes | Yes, media API |
| Identity strength | Weak (address is spoofable) → signed reply token + From match | Strong (workspace user id) | Strong (verified number) |
| Latency | Minutes to hours | Seconds | Seconds |
| Cost | ~0 | Plan-dependent | Per conversation |
| Best for | Anyone, especially one-off designers/clients | Teams already sharing a workspace | Freelancers and clients who live on the phone |

**Recommendation: email first.** It is the only channel that reaches any
designer with zero account, zero workspace and zero provider approval, and its
async nature matches the "ask a question, continue when answered" workflow.
Slack is second because the design already exists and the integration is
cheap, but it only works when the counterparty is already in a shared
workspace. WhatsApp is third: the 24-hour window and template approval make it
the wrong first connector, even though it is often the most likely reply
channel for a freelancer. Telegram (recommended by the M6 channel spike as the
cheapest demo provider) remains a useful internal demo, not a customer channel.

### 6.2 Email specifics

* **Sender**: a dedicated project mailbox (e.g. `website@acme.com`), not a
  personal account. Reply-To carries an opaque token:
  `outreach+<token>@acme.com` (plus `In-Reply-To` matching for clients that
  drop the Reply-To).
* **Project and task context**: the subject is tagged with both
  (`[Acme · Website v1] … ref out_a1`) and the body opens with a
  `Project / Task / Ref` block. The token carries `project_id`, `request_id`
  and `actor_id`, which is what makes an answer unambiguous when the same
  designer has open requests in other projects.
* **Threading**: store `Message-ID`, send `References`, and match replies by
  token first, headers second, sender+subject last.
* **Parsing**: strip quoted history and signatures, keep attachments, cap
  size, never execute or auto-open files.
* **Receiving**: IMAP poll (portable) or Gmail API history (if the org is on
  Workspace). Both are adapters behind the same interface; do not build a mail
  server.
* **Deliverability**: SPF, DKIM, DMARC and a warmed domain are part of the
  rollout, not an afterthought. A cold domain sending "questions to designers"
  will land in spam.
* **Bounces**: `failed` request status + owner notification; do not retry a
  hard bounce.

### 6.3 Slack specifics

Reuse the existing design's app, signature verification and thread mapping. For
outreach:

* one DM (or one thread in a shared channel) per request;
* `thread_ts` is the `external_thread_id`;
* Slack user id is the identity; email fallback only with `users:read.email`;
* Socket Mode is the low-friction option when the deployment has no public
  ingress.

### 6.4 WhatsApp specifics

* first contact requires an approved template with variables (name, project,
  question count); replies inside the 24-hour window can be free-form;
* every reminder outside the window is a template — budget them;
* identity is the phone number (`wa_id`); groups need an Official Business
  Account and are out of scope for v1;
* media download with size/MIME checks, stored hash-named;
* no message editing: send the final text, not streamed tokens.

### 6.5 Manual relay (works on day one)

`record_external_reply` lets an internal user paste a WhatsApp screenshot text
or an email answer into the request. The system tags it as external, updates
the answer packet and resumes the task. This is the M0 deliverable: the
workflow, audit and waiting state are proven before any provider integration,
and it is the permanent fallback when a connector is down.

---

## 7. Security and trust

External content is untrusted input, and the agent may have powerful tools.

| Risk | Control |
| --- | --- |
| Prompt injection in a reply ("ignore instructions, deploy…") | Replies are stored as evidence; a tool-less extraction step turns them into structured answers, so raw text never enters the working agent's instructions; irreversible actions remain approval-gated |
| Data leakage to the external person | Outbound DLP: secrets, internal paths, other projects' names, private URLs; templated questions; optional mandatory approval for the first N messages |
| Spoofed email sender | Unguessable reply token, `From` match, unknown sender → quarantine + owner notification, never auto-answer |
| Oversharing project context | The outreach thread sees only the question and attachments the agent explicitly sends; it never sees the task chat |
| Abuse / spam | Per-actor and per-project rate limits, quiet hours, max open requests, opt-out suppression list |
| Cost | Per-task outreach budget, max messages, auto-resume gated by the task budget |
| Privacy | Per-request retention, configurable deletion, consent recorded at first contact, opt-out honored |
| Attachments | Size/MIME allow-list, hash-named storage, no execution, virus scanning as a deployment option |

Approval policy (per project, recommended default):

* `manual` — every send needs a human click;
* `first_contact` — auto-send after the first approved message to that actor
  (**v1 default**);
* `auto` — the agent sends within budget and allowed domains.

Who may do what:

* **project admin** — manage connectors, contacts, approval policy;
* **task owner / members** — create requests, approve if policy allows, relay
  answers, cancel;
* **agent** — create drafts and send only within policy;
* **external actor** — answer, decline, opt out. Nothing else.

---

## 8. What we already have

Verified in this repository:

| Capability | Status | Where |
| --- | --- | --- |
| Task = chat; boards, columns, assignees, profiles, sub-tasks | **Exists** | `api/codx/junior/db.py` (`Chat`, `Message`), `chat_manager.py`, [kanban](/features/kanban) |
| Messenger channels, DMs, company channels (`mode="channel"`) | **Exists** | `Chat.mode`, `api/codx/junior/company/manager.py`, [teams](/features/teams) |
| Live UI updates over Socket.IO | **Exists** | `api/codx/junior/events/event_manager.py` |
| Profiles, tools list, guardrails (input/output/scope/tool allow-list) | **Exists** | `api/codx/junior/model/profile.py`, `api/codx/junior/guardrails/service.py` |
| Users, roles, project permissions, forward auth | **Exists** | `model/user.py`, `security/user_management.py` |
| Global settings sections + project overrides | **Exists** | `model/model.py` (`GlobalSettings`), `settings.py`, `global_settings.py` |
| Background worker container and scheduled loops | **Exists** | `api/codx/junior/background.py`, board manager and orchestration workers |
| OAuth provider registry + GitHub OAuth precedent | **Exists** | `security/github_oauth.py`, `oauth_providers` in global settings |
| Signed webhook + service-token precedent | **Exists** | `api/codx/junior/api/dsh.py`, `api/dsh_agent.py` |
| Durable chat turns / recovery after restart | **Exists** | `api/codx/junior/chat/turn_store.py`, `turn_recovery.py` |
| Slack + WhatsApp channel bridge design (bindings, outbox, identity, security) | **Design only** | [slack-whatsapp-integration](/features/slack-whatsapp-integration), tasks under `.codx/tasks/External connectors/` and `.codx/tasks/Channels/` |
| Gmail account connector (connect, read, send) | **Spec only** | `.codx/tasks/External connectors/GMAIL/` (M1–M4 + contract spec) |
| Email send/receive (SMTP/IMAP) | **Implemented (MVP)** | `api/codx/junior/external/email.py`; live-server verification still pending |
| Slack / WhatsApp / Telegram runtime | **Missing** | reserved; the email/manual MVP does not implement them |
| External actor / contact model | **Implemented (MVP)** | `api/codx/junior/model/external.py`, `api/codx/junior/external/store.py` |
| Outreach request lifecycle, waiting state, reminders | **Implemented (MVP)** | `api/codx/junior/external/service.py`; reminder runs at the deadline |
| Inbound reply matching (token/thread) and dedupe | **Implemented (MVP)** | `external/service.py` (`_resolve_inbound`), `external/store.py` (thread index, seen set) |
| Outbound DLP / approval UI for external messages | **Partial** | approval API implemented; content DLP and a dedicated approval UI remain |
| External portal (magic link) | **Missing** | — |

The important nuance: the Slack/WhatsApp document is a complete *mirroring*
design, and the Gmail backlog is about *internal users linking their own
accounts*. Neither covers reaching a third party with a question. The
primitives they build (connectors, adapters, outbox, identity mapping) are
reusable, but the request/answer workflow is new.

The MVP in this branch implements the email and manual-relay half of that
workflow (items 1–7 below). Slack, WhatsApp, the portal and the full DLP/UI
hardening remain as designed.

---

## 9. What we need

### 9.1 Build list, in dependency order

Items **1–6 and the email part of 7** are implemented in this branch; the
table is kept as the original scope and effort reference.

| # | Deliverable | Depends on | Rough effort |
| --- | --- | --- | --- |
| 1 | `ExternalActor` global directory + `ProjectContact` links store/API; project settings for outreach policy | — | 3–4 d |
| 2 | `OutreachRequest` store + lifecycle; `waiting_external` status and board wiring | 1 | 2–3 d |
| 3 | `ask_external` / `record_external_reply` / `cancel` tools + tool-less answer extraction + answer packet | 2 | 2–3 d |
| 4 | Project view UI: contacts, requests, deadline, answer, relay, audit | 1–3 | 3–4 d |
| 5 | Email adapter (SMTP send, IMAP/Gmail receive, tokens, threading, attachments, bounces) | 2 | 8–10 d |
| 6 | Reminder/escalation scheduler + notifications | 2 | 2–3 d |
| 7 | Outbound DLP + approval flow | 3–5 | 3–4 d |
| 8 | Slack adapter (reuse channel design; Events API or Socket Mode) | 2, 5 (shared outbox) | 6–8 d |
| 9 | WhatsApp Cloud API adapter (templates, 24 h window, media) | 2, 5 | 8–12 d + Meta lead time |
| 10 | Portal guest magic link (view, answer, approve) | 4 | 6–10 d |
| 11 | Metrics/audit: time-to-answer, unanswered rate, cost per answer | all | 2 d |

**Read this as:** M0 (items 1–4 and 6, plus a minimal approval gate from item
7) ≈ **10–13 engineer-days** and needs no external provider at all; email
(item 5) adds **8–10 days**; each extra provider adds **6–12 days** plus vendor
approval time. Estimates assume one senior backend engineer with part-time
frontend help.

### 9.2 What we need from outside the codebase

| Need | Owner | Why |
| --- | --- | --- |
| A sending mailbox/domain with SPF, DKIM, DMARC | Ops | Deliverability; without it email "works" but lands in spam |
| Slack app + workspace admin approval (or Socket Mode token) | Whoever owns the counterparty's workspace | Only if Slack is in scope |
| Meta business verification, display name, template approval | Ops / legal | Required before the first WhatsApp message |
| Consent wording and retention policy | Legal / product | First contact must say who we are and how to opt out |
| Named contacts with roles and preferred channels | Project owner | The contact book is only useful if curated |

---

## 10. Phased plan

| Phase | Scope | Exit criterion |
| --- | --- | --- |
| **M0 — Workflow** (implemented) | Global directory, project links, requests, waiting state, manual relay, answer packet, project view, audit | A task can ask a question, wait, receive a pasted answer, resume, and show who answered — with no connector |
| **M1 — Email** (implemented, live-server check pending) | Shared project mailbox, opaque reply tokens, threading, attachments, reminders at the deadline, approval | A real designer answers by email; the task resumes automatically or on click; the thread is auditable end to end |
| **M2 — Slack** | App install, DM/thread per request, Events API (Socket Mode optional) | Same flow over Slack with strong identity; no regression to M1 |
| **M3 — WhatsApp** | Cloud API, template for first contact, 24 h window handling, media | First contact via template, answer handled, reminders counted and capped |
| **M4 — Portal** | Magic link scoped to one task: view question, upload files, approve | An external person approves a deliverable without an account |
| **Later** | Group outreach (multiple actors on one request), Telegram demo adapter, CRM sync | — |

Sequencing rationale: M0 proves the product workflow and pays for itself even
with manual relay; email has the lowest external friction; Slack is cheap once
the outbox exists; WhatsApp is last because its approvals are the longest and
its messaging rules are the strictest.

---

## 11. Acceptance scenario (the website case)

1. Board task **"Website v1"** is assigned to `web_master` and `Designer`;
   project settings allow outreach with `first_contact` approval. Ana already
   exists in the global directory and is linked to Beta as brand reviewer; Acme
   links the same actor as *designer* instead of duplicating her.
2. The task lists required inputs: logo (SVG), brand colors, tone of voice.
   The board shows the task as **blocked on external inputs**.
3. The agent calls `ask_external(actor="Ana — designer", questions=[...],
   due_at=+3 business days, channel="email")`.
4. The project admin approves the draft; it is sent from
   `website@acme.com` with an opaque Reply-To. Task → `waiting_external`.
5. Ana replies by email with two attachments and inline answers.
6. The reply is verified, matched to the request, stored in the outreach
   thread, and summarized into an answer packet on the task.
7. The task resumes; the agent produces the design brief and cites
   *"answered by Ana · email · 12 Nov"*. Reminders are cancelled.
8. **WhatsApp variant:** Ana prefers WhatsApp, so the same request goes out as
   an approved template; her reply follows the same path.
9. **Follow-up:** a later message from the same actor before the task closes is
   appended to the request and flagged as a new answer, so the task never
   loses context.
10. If Ana had not replied: a nudge at T-24h, an owner escalation at due, and
    the task stays visibly waiting — never silently "done".
11. **Same actor, other project:** Beta also has an open request (`out_b7`).
    Ana's Acme reply goes to Acme only; Beta's panel never shows it. A reply
    without a token/thread that matches two open requests is **quarantined**,
    not guessed.

Failure paths that must be demoed too: unknown sender (quarantine), reply that
is only a counter-question (packet flags it, task stays waiting), opt-out
(suppression honored), bounced email (request failed + owner notified), and a
reply that tries to instruct the agent (ignored as instruction, stored as
evidence).

---

## 12. Open decisions

| # | Decision | Options | Recommendation |
| --- | --- | --- | --- |
| 1 | Contact book scope | Global directory / project-scoped / both | **Global directory + per-project links**: the person is one, the relationship is local |
| 2 | Sender identity | Shared project mailbox / per-user Gmail | **Shared project mailbox**; per-user stays for internal mirror |
| 3 | First connector | Email / Slack / WhatsApp | **Email** |
| 4 | Default approval | Manual / first contact / auto | **First contact**, manual for new domains |
| 5 | Auto-resume after answer | Always / policy / never | **Policy default on**, gated by budget and confidence |
| 6 | Where the external thread lives | Task chat / separate channel chat | **Separate channel chat**, answer packet in the task |
| 7 | Multi-actor requests | One request per actor / one request with many actors | **One per actor** in v1; group thread later |
| 8 | Identity proof for email | Token only / token + From / + DKIM | **Token + From match**, DKIM as signal |
| 9 | Retention | Keep forever / configurable | **Configurable 90–180 days** for media; requests follow task retention |
| 10 | Portal in v1? | Yes / later | **Later (M4)**; link-based file exchange is enough for M1 |

---

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Prompt injection through replies | High | High | Evidence-only storage, tool-less extraction, untrusted wrapping, approvals |
| Leaking internal data to a third party | Medium | High | DLP, templated questions, approval, no task-chat mirroring |
| Email lands in spam | Medium | Medium | Dedicated warmed domain, SPF/DKIM/DMARC, plain-text-friendly templates |
| WhatsApp template rejection / account limits | Medium | Medium | Start with email/Slack; budget Meta lead time |
| Scope creep into "chat with the AI" | High | Medium | R7 is request/answer only; free chat is explicitly out of scope |
| Reminder fatigue / harassment | Medium | Medium | Caps, quiet hours, opt-out, owner escalation instead of more nudges |
| Contact data rot | High | Low | Verified flag, last-contacted, archive stale contacts |
| Duplicate inbound messages | Medium | Low | Dedupe on provider message id, token+thread matching |
| Cost from auto-resume | Low | Medium | Per-task budget, max turns per answer, no auto-resume on low confidence |

---

## 14. Non-goals

* Assigning tasks to external actors. They answer questions; they do not own
  work.
* Free-form chat between external people and agents. R7 is scoped to a
  request; a general inbox is a later product decision.
* Letting an external actor see the project, the board or internal chats.
  A portal guest (M4) sees one task's question and deliverables, nothing else.
* Replacing the Slack/WhatsApp mirroring work. R7 and R1–R6 share transport
  and identity; they are not the same feature.
* Building an email server or a WhatsApp bridge outside the official API.

---

## 15. MVP implementation

This branch implements M0 (the full workflow, manual relay) and M1 (email), plus
the global directory that makes one actor reusable across projects. It is
backend-complete and exercised by tests; the SMTP/IMAP path is not verified
against a live mailbox in this environment.

### 15.1 Code map

| Area | Files |
| --- | --- |
| Models | `api/codx/junior/model/external.py` (`ExternalActor`, `ProjectContact`, `OutreachRequest`, `ExternalSettings`) |
| Global + project storage | `api/codx/junior/external/store.py` |
| Email build/parse/SMTP/IMAP | `api/codx/junior/external/email.py` |
| Lifecycle, routing, waiting state, packets, reminders | `api/codx/junior/external/service.py` |
| REST API | `api/codx/junior/api/external.py` |
| Agent tools | `api/codx/junior/tools/external_tools.py` (registered in `tools/__init__.py`) |
| Background poll/overdue worker | `api/codx/junior/background.py` (`external_mail_worker`) |
| Settings section | `GlobalSettings.external_settings` in `api/codx/junior/model/model.py` |
| Client | `client/src/views/ExternalOutreachView.vue`, `client/src/api/modules/external.js`, route `/:projectName/external` |

### 15.2 Storage layout

```
<config>/
  settings/external_settings.json     # mailbox + defaults (admin section)
  external/
    actors.json                       # global directory (identity, consent)
    reply_tokens.json                 # sha256(token) -> project/request/actor
    threads.json                      # Message-ID -> project/request
    mail_seen.json                    # inbound dedupe (bounded)

<project>/.codx/external/
  contacts.json                       # actor_id + role/title/notes (per project)
  requests/<out_...>.json             # lifecycle, questions, answers, timeline
  media/<out_...>/<file>              # attachments, hash-prefixed names
```

Chat integration:

* the task `Chat.status` becomes `waiting_external` and
  `meta_data.external_waiting` lists the blocking request ids and the previous
  status;
* the answer packet is a `role="user"` message with
  `meta_data.external.trust="untrusted"`, `kind="answer"` (or `"followup"`);
* the "question sent" note is an assistant message with `kind="outreach_sent"`.

### 15.3 API

All project routes are scoped by `codx_path`; the Vue client appends it
automatically. Global directory/settings/email routes require an installation
admin; project writes require a project admin.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET/PUT` | `/api/external/settings` | Read/update mailbox + defaults (passwords masked) |
| `GET` | `/api/external/actors` | Actors linked to the project, with open-request counts |
| `POST` | `/api/external/actors` | Create a global actor and link it to the project |
| `GET` | `/api/external/directory` | Admin: full global directory |
| `GET` | `/api/external/directory/lookup` | Minimal exact-identity lookup (link an existing actor) |
| `PUT` | `/api/external/actors/{id}` | Admin: edit the global identity/consent |
| `POST` | `/api/external/actors/{id}/link` | Link an existing actor with this project's role |
| `DELETE` | `/api/external/actors/{id}/link` | Unlink (refuses while requests are open) |
| `GET` | `/api/external/requests` | List requests (filter by task/status) |
| `POST` | `/api/external/requests` | Create a draft (or send immediately as project admin) |
| `GET` | `/api/external/requests/{id}` | Request detail + answer packet |
| `POST` | `/api/external/requests/{id}/send` | Approve/send (email) or mark manual as sent |
| `POST` | `/api/external/requests/{id}/relay` | Record a manually received answer |
| `POST` | `/api/external/requests/{id}/cancel` | Cancel, keeping the audit trail |
| `GET` | `/api/external/email/status` | Configured/not, hosts, poll interval |
| `POST` | `/api/external/email/poll` | Pull UNSEEN mail now |
| `POST` | `/api/external/email/inbound` | Ingest one raw message (base64; demo/testing) |

### 15.4 Configuration and runbook

1. **Mailbox.** Set `external_settings` (the **Email bridge** card in the
   External actors view, the Global Settings section, or
   `PUT /api/external/settings`) with `email.enabled`, `from_address`,
   `reply_domain`, `smtp_*` and `imap_*`. Set SPF/DKIM/DMARC for the sending
   domain; without them the first emails will land in spam.
2. **Contact.** Create the actor once, or link the existing directory entry by
   exact email. The same actor can be linked to as many projects as needed; the
   role/notes are per project.
3. **Request.** From a task, either the agent calls `ask_external` (tool must be
   in the profile/chat tool list) or the project view creates the draft. A
   project admin sends it; with `email.require_approval=false` the agent can send
   directly within policy.
4. **Reply.** The inbox worker polls every `email.poll_seconds` (default 120 s)
   or `POST /api/external/email/poll` forces a poll. The token routes the reply
   to the project/request; the sender must match the actor. The answer packet is
   posted to the task and the task leaves `waiting_external`.
5. **Manual relay.** If the answer arrives by WhatsApp/Slack/phone, use
   "Record answer" in the project view (or `POST .../relay`); it takes the same
   path and produces the same packet.
6. **Kill switch.** `CODX_JUNIOR_EXTERNAL_MAIL=0` disables the background poll
   and overdue loop.

**Reusing the same actor in another project.** The identity is global; the link
is local. From the second project an admin can:

```bash
# 1. Resolve the existing actor by an exact channel identity.
curl -s "https://codx.example/api/external/directory/lookup?provider=email&handle=ana@studio.com" \
  -H "authentication: Bearer <token>"

# 2. Link that actor to this project with the role it has here.
curl -s -X POST "https://codx.example/api/external/actors/act_ana/link?codx_path=/projects/beta/.codx" \
  -H "authentication: Bearer <token>" \
  -H "content-type: application/json" \
  -d '{"role": "brand reviewer", "title": "Beta rebrand"}'
```

Re-posting the link updates the role/title/notes; it does not create a new actor
and it does not expose Beta's requests in Acme (or vice versa). A new request
created in Beta gets a fresh token whose payload points to Beta, even though the
same email address is used.

Example global section:

```json
{
  "enabled": true,
  "default_due_days": 3,
  "max_open_requests_per_task": 5,
  "email": {
    "enabled": true,
    "from_address": "website@acme.com",
    "from_name": "Acme Studio",
    "reply_domain": "acme.com",
    "smtp_host": "smtp.acme.com",
    "smtp_port": 587,
    "smtp_username": "website@acme.com",
    "smtp_password": "${SMTP_PASSWORD}",
    "smtp_starttls": true,
    "imap_host": "imap.acme.com",
    "imap_port": 993,
    "imap_username": "website@acme.com",
    "imap_password": "${IMAP_PASSWORD}",
    "imap_folder": "INBOX",
    "poll_seconds": 120,
    "require_approval": true,
    "reminders_enabled": true
  }
}
```

Secrets are never returned: `GET /api/external/settings` masks
`smtp_password`/`imap_password`, and a `PUT` that sends the mask back keeps the
stored value. `${ENV_VAR}` references are resolved by the transport through the
environment, matching the existing provider-secret convention.

### 15.5 Tests

```
CODX_JUNIOR_API_LOGS=$PWD/.test-logs \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
PYTHONPATH=api:/path/to/pipcheck/site \
python3 -m pytest api/tests/test_external_*.py -q
```

Covered (21 tests):

* global directory identity dedupe, reply-token resolution/revocation, thread
  index, project links, request store, attachment path safety;
* message build includes project/task/ref and the Reply-To token; parsing
  extracts attachments, thread ids, reply token, quote stripping and numbered
  answers;
* one actor linked to two projects; email round trip updates the request, posts
  the packet and restores the task status; a reply is routed to the right
  project by token even with a second open request; a tokenless reply is routed
  by `In-Reply-To`/`References`; a tokenless, threadless reply with two open
  requests is `ambiguous` and changes nothing; manual relay; cancellation;
  unknown sender quarantine; deadline reminder/overdue;
* REST endpoints for actor create/lookup/duplicate, request draft/send/relay,
  waiting state and masked settings;
* tool schema and `ask_external` request creation.

### 15.6 Known gaps (next increments)

| Gap | Impact | Next step |
| --- | --- | --- |
| No live SMTP/IMAP verification | Transport is untested outside fakes | Run the runbook against a staging mailbox, add a provider contract test |
| No outbound content DLP | Prompt injection/leak prevention is approval + prompt policy only | Add secret/PII scan before send, block on findings |
| Reminder only at the deadline | No T-24h nudge | Add a scheduler window and per-request reminder timestamps |
| No auto-resume AI turn | A human or the next agent turn must continue | Add a policy-gated `chat_with_project` after the packet |
| Raw thread lives in the request file, not a channel chat | UI shows the packet, not the full thread | Create the M2 channel chat and link it |
| No Slack/WhatsApp/Telegram | Only email/manual reach today | Port the adapter behind the same store/service |
| No external portal | External people cannot see previews/approve in a UI | Magic-link view scoped to one task |
| No token revocation on cancel | A cancelled request can still receive mail (it is ignored) | Revoke by hash on cancel and reject early |
| No outgoing attachments | Questions are text only | Allow the agent to attach a brief/file to the request |
| UI has no global directory/settings editor | Admin work is API-only | Add the admin tabs next to the project view |
