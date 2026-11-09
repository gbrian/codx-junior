# YC application — draft

**Target batch:** X27 (submit ~2027-02-05; deadline expected ~2027-02-08)
**Status:** draft v1, 2026-11-09. `[…]` = a real number or fact to fill before submitting.

Rules for this draft:
* Every `[bracket]` must be replaced with a number you can defend in an interview.
* No adjective survives without a fact behind it.
* 50-word answers stay under 50 words. YC reads fast.

---

## Company

**Company name:** codx-junior (legal entity: `[incorporated? where?]`)

**Describe what your company does in 50 characters or less:**
> Open-source workspace for human + AI dev teams

*(48 chars. Alternatives: "One tab for kanban, AI agents and dev budgets" = 49.)*

**What is your company going to make? (50 words):**
> A self-hosted workspace where a software project lives in one tab: Kanban cards that are AI
> chats, agents that work in your repo, dev containers, team chat, code review and per-user AI
> budgets. Agents do the volume; humans approve every change and see every dollar.

**Website:** `https://[domain]` (after Phase 0; until then, the GitHub repo)

**Demo video (1 min):** `[link]` — see the script in `YC_STRATEGY.md` §7.

---

## Progress

**How far along are you?**
> Shipped and dogfooded daily. ~250k lines across a Python/FastAPI API and a Vue 3 client:
> agent runtime with project tools, RAG over Milvus, Kanban where cards are chats, git/PR review,
> per-user budgets and analytics, computer and browser sessions, teams, an OpenAI-compatible API
> and a plugin system. Public beta site launching `[date]`. `[N]` installs, `[M]` weekly active
> projects, `[K]` managed pilots signed.

**How many users / revenue?**
> Users: `[N]` installs, `[M]` weekly active projects, `[S]` GitHub stars.
> Revenue: `[$X]` from `[K]` managed-team pilots (human hours + AI tokens).
> Retention: `[P]%` of installs ran a task in week 4.

**How long have you been working on this?**
> `[X]` months full-time on codx-junior; `[Y]` years on the predecessor codx platform.

---

## Idea

**Why did you pick this idea?**
> I kept losing the same thing on every project: context. The board in one tool, the agent in the
> IDE, the container in Docker, the review in GitHub, the AI bill in a dashboard I checked once a
> month. I built codx-junior because I wanted one place where a task, the agent doing it, the diff
> it produced and the money it cost were the same object. I use it every day.

**Why now?**
> Three things became true within 18 months: tool-calling agents got reliable enough to work in a
> real repo; local and open models got good enough to self-host; and every company started asking
> "what does AI cost us and who approved this change?" Nobody has an answer that is both
> auditable and usable. That answer is a workspace, not a model.

**Who are your users?**
> Beachhead: small software shops (2–15 devs) delivering client projects, and solo technical
> founders running several projects at once. They need per-client isolation, visible AI cost and a
> review trail — the things a single-player IDE never had to solve. `[X]` of them use it today;
> here is what they say: `[quote]`.

**Who are your competitors, and what do you understand that they don't?**
> Cursor/Windsurf own the editing loop; Devin/OpenHands sell autonomy; Lovable/Replit sell
> greenfield apps; Jira/Linear own planning. Each sees a slice. What they miss is that the unit of
> work is not a file, a ticket or an agent run — it is a **task with its agent, its diff and its
> cost**. That unit only exists if planning, execution, review and metering are one system. Our
> users do not switch editors; they switch where the work lives.

**How do or will you make money?**
> 1) Managed team: we run codx-junior for a client and execute their roadmap; we charge human
> hours and AI tokens, both metered in the product. `[$X]` from `[K]` pilots. 2) Commercial
> licensing and support for companies that cannot use AGPL. 3) Later: hosted enterprise with SSO,
> audit and SLA. The OSS core is free forever.

**How much could you make?**
> Bottom-up: `[N]` small dev shops × `[$X]`/month managed or license. At 1,000 shops at $500/month
> that is $6M ARR; the same base at $2k/month managed is $24M. We are not claiming a top-down TAM;
> we are counting the shops we can reach through open source.

**How will you get users?**
> Open source is the channel: GitHub, Product Hunt (launch 2027-01-26), Show HN, self-hosted and
> local-model communities, and the docs site as the funnel. The managed team converts the top of
> that funnel into revenue and into the case studies the next cohort needs.

---

## Team

**Founders:** `[names, roles, % equity]`

**Founder bios (100 words each):**
> `[Gustavo Brian]` — `[20+]` years building and shipping software `[for whom]`. Built `[codx]`,
> `[what it did, scale]`. Wrote most of codx-junior: API, agent runtime, client, installer.
> Based in `[city]`, `[nationality]`, `[committed full-time since date]`.
>
> `[Estefania Nuñez]` — `[background]`, runs accounts and `[what]` at codx-junior. `[committed?]`

**Are you looking for a co-founder?** `[no / yes — for what role]`

**How many hours per week?** `[60+]`

**Who writes code?** `[names]`

**Equity split:** `[X/Y]`

**Incorporated?** `[state]`. If not: "Not yet; we will incorporate as a Delaware C-Corp if
accepted, and we have no conflicting obligations."

---

## Risks and honesty

**What is your biggest risk?**
> Trust in agent output. A workspace that lets agents change code is only useful if a human can
> verify the change in seconds and cap the cost. If review is slow or noisy, the product is worse
> than a manual workflow. We invest in diffs, profiles and budgets for that reason — and the
> beta label is real: workspaces (dev containers) are behind a flag until the runtime is finished.

**What do you understand about your business that others don't?**
> That the buyer of AI software delivery is not the individual developer — it is the person
> accountable for the delivery and the bill. That person needs a system of record, not a faster
> autocomplete.

---

## Anything else

> The whole thing is public: `[repo]`, `[docs]`. The roadmap and the changelog are public, and so
> are the numbers we can share. We are raising a seed round and onboarding early partners;
> `[early customer/testimonial]`.

---

## Inconsistencies to fix before submitting

| Check | Why |
| --- | --- |
| Website live and matching the product | Partners open the link during the read |
| Demo video ≤ 60 s, no slides, real product | The single highest-signal artifact |
| Star count, install count, revenue all current | Stale numbers kill credibility |
| GitHub description + topics updated | It is the second link they click |
| README first screen tells the same story | Third link they click |
| No claim the product cannot do | The interview will test it |
