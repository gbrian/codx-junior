# Competitive set — where we win, where we lose

Honest comparison for the website, Product Hunt comments and the YC application.
Update before every launch; the field moves monthly.

---

## 1. The map

| Player | Category | What they own | Where codx-junior differs |
| --- | --- | --- | --- |
| **Cursor / Windsurf / Kiro** | AI IDE | The editing loop; best-in-class tab completion | We are the system *around* the editor: plan, run, review, budget. We do not try to beat their completion. |
| **Claude Code / Codex CLI / Gemini CLI** | Terminal agents | Repo-level agent loops, huge model quality | We add persistent tasks, profiles, review gates, budgets, multi-user governance and a UI a non-CLI teammate can use. |
| **Devin / Factory / OpenHands** | Autonomous agent | "Give it a ticket, get a PR" | We deliberately keep a human in the loop and make the cost/authority visible. Also self-hostable. |
| **Lovable / Bolt / Replit / v0** | App generators | Idea → running app in minutes, hosting included | We work on *your* repo, *your* Docker, *your* cloud — no lock-in, no proprietary runtime. |
| **Jira / Linear / Plane** | Project management | Planning, workflows, reporting | Our cards are chats with tools; the agent doing the work is the assignee. AI-native org, not a field on a ticket. |
| **GitHub + Copilot** | Code hosting + review | The source of truth for code and PRs | We integrate rather than replace; review, diffs and issues are first-class inside the workspace. |
| **Gitpod / Coder / DevPod** | Cloud dev environments | Reproducible dev containers | We orchestrate containers *and* the agents that work inside them, with routing/auth. |
| **Dify / n8n / Langflow** | AI workflow builders | Composable AI pipelines | We are opinionated about one workflow: delivering software. Less building, more shipping. |

## 2. The three comparisons buyers actually make

### A. "Why not just Cursor + Linear?"

Because the hand-off is the cost. In Cursor + Linear, the task lives in one tool, the
conversation in another, the container in a third, the review in a fourth, and the bill
nowhere. codx-junior's card *is* the conversation; the diff and the cost are attached to it.

**When they should pick Cursor + Linear:** they are a 3-person team with one repo and no
budget pressure. Say so — it buys credibility.

### B. "Why not Devin / an autonomous agent?"

Because you cannot audit or cap what you cannot see. codx-junior lets an agent do the volume
but requires a human approval step, and meters spend per user with hard limits. Autonomy is
configurable, not the default.

**When they should pick an autonomous agent:** a greenfield repo, no compliance, no multi-user
cost concerns.

### C. "Why not Lovable / Replit?"

Because those are excellent at *starting* an app and poor at *running someone's existing
system*. codx-junior assumes a real repo, real Docker, real PRs and a team.

## 3. Feature comparison (public-safe)

Only include rows where we are **at least as good**, or where the gap is honest and explained.

| Dimension | codx-junior | AI IDE (Cursor et al.) | Autonomous agent | App generator | PM tool |
| --- | --- | --- | --- | --- | --- |
| Works on your existing repo | ✅ | ✅ | ✅ | ⚠️ mostly new apps | ➖ |
| Task → agent → diff in one object | ✅ | ❌ | ⚠️ partial | ❌ | ❌ |
| Human approval gate | ✅ | ✅ (you edit) | ⚠️ optional | ⚠️ | ➖ |
| Runs your Docker / dev containers | ⚠️ beta (workspaces flagged) | ❌ | ❌ | ❌ | ❌ |
| Per-user AI budgets + wallets | ✅ | ❌ | ⚠️ org plan | ⚠️ credits | ❌ |
| Any OpenAI-compatible provider / local models | ✅ | ⚠️ partial | ❌ | ❌ | ➖ |
| Self-hostable | ✅ AGPL-3.0 | ❌ | ⚠️ enterprise | ❌ | ✅ |
| Team chat where agents are members | ✅ | ❌ | ❌ | ❌ | ⚠️ integrations |
| Shared desktop/browser the AI actually drives | ✅ beta | ❌ | ⚠️ sandbox | ❌ | ❌ |
| Time to first value | ⚠️ 10 min install | ✅ seconds | ✅ minutes | ✅ minutes | ✅ |
| Polish | ⚠️ beta | ✅✅ | ✅ | ✅ | ✅✅ |

Legend: ✅ yes · ⚠️ partial/beta · ❌ no · ➖ not applicable.

## 4. Where we lose today (say it before they do)

1. **Polish and onboarding.** A hosted SaaS signs you in in 20 seconds; we ask for Docker.
2. **Model quality is not ours.** We ride on the provider; we cannot out-complete Cursor.
3. **Brand.** 5 GitHub stars vs. nine-figure marketing budgets.
4. **Workspaces.** Broken in the current tree — never claim it in a comparison until fixed.
5. **Mobile.** "Only needs a browser" is true on desktop; phone support is unproven.
6. **Support.** One maintainer. Be explicit about response times.

## 5. Defensible wedge

Nobody else combines (a) an OSS, self-hostable engine, (b) an org model where agents are
members with budgets and permissions, and (c) a human managed-team business on top of the
same product. Any one of those is copyable; the combination is a multi-year position, and the
managed team generates the revenue that funds the product.

## 6. Sources to keep fresh

- Cursor / Windsurf / Claude Code release notes (monthly)
- OpenHands, Devin, Factory changelogs
- r/LocalLLaMA and r/selfhosted front page (monthly)
- Product Hunt "Developer Tools" top launches (monthly)
- YC's Request for Startups (each batch)
