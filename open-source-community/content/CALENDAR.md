# Content calendar — 12 weeks to launch

Two goals: fill the site with proof (posts that answer real objections), and build an audience
before Product Hunt. One blog post per week, three social posts, one channel action.

**Publishing rules**
- Blog posts live on the site (`/blog/...`), cross-posted to dev.to with a canonical link.
- Every post has one screenshot and one concrete number.
- No post announces a feature that is not shipped and demoable.
- Every post ends with a next step: quickstart, GitHub, or the launch list.

---

## Weekly plan

| Week | Blog post | Social (X / LinkedIn) | Channel action | Launch milestone |
| --- | --- | --- | --- | --- |
| **Nov 9–15** | *Why unsupervised AI agents fail* (draft in `drafts/`) | X: thesis thread. LI: founder story | Remove internal docs; fix demo CTA | P0s closed |
| **Nov 16–22** | *What actually happens when you move a Kanban card* (agent loop, RAG, profile) | X: 20 s demo clip. LI: "the unit of work is a task" | Reddit r/selfhosted comment history begins | v1.3.0 images published |
| **Nov 23–29** | *The AI bill nobody sees: metering per user with cxjcoins* | X: budget screenshot + numbers. LI: cost governance | Pitch 3 newsletters for December | Quickstart v2 tested |
| **Nov 30–Dec 6** | *Self-hosting an AI dev workspace in 10 minutes* (the quickstart, with timings) | X: install video. LI: "Docker is the product" | Submit awesome-selfhosted PR | Site soft-launch ready |
| **Dec 7–13** | *We published our internal reviews by accident — here's the guard we added* | X: build-in-public post. LI: trust/transparency | 5 external testers | **Soft launch Dec 9** |
| **Dec 14–20** | *Kanban where every card is a chat: the data model* | X: schema diagram. LI: architecture | Post in 2 Discords (value first) | Fix soft-launch findings |
| **Dec 21–27** | *Freeze — no publishing* | 1 end-of-year post | None | — |
| **Dec 28–Jan 3** | *2026 in review: what we shipped, what broke* | X: year recap. LI: lessons | Open the launch list | Buy domain → 301s |
| **Jan 4–10** | *Agents with a whole machine: computer use in a dev workspace* | X: computer-session clip. LI: QA automation angle | PH upcoming page live | Demo instance hardened |
| **Jan 11–17** | *AGPL for a dev tool: what it means for your company* | X: licence thread. LI: "open source is the distribution" | Submit to 5 directories | **Public site launch Jan 12** |
| **Jan 18–24** | *How a small shop runs 10 client projects with 3 devs* (case study) | X: pre-launch thread. LI: launch announcement | All supporter DMs sent | Launch assets final |
| **Jan 25–31** | *Launch retrospective: numbers, what broke, what's next* (Jan 28) | X + LI launch day posts; thank-you thread | **Product Hunt Jan 26**; Show HN Jan 28–29 | Launch week |
| **Feb 1–7** | *Supervised autonomy: a spec for agent permissions and budgets* | X: YC/build thread. LI: metrics | 10 user interviews | **YC X27 submit Feb 5** |

## Blog backlog (write after launch)

1. Ollama + LiteLLM + vLLM in one workflow: choosing models per purpose.
2. MCP servers per project: what we allow and why.
3. The review loop: how we make a 400-line diff reviewable in 60 seconds.
4. From Jira + Copilot + Docker to one tab: a migration guide.
5. What an agent run should cost: benchmarks across providers.
6. Workspaces, completed: the runtime we should have built first (post-mortem).
7. Multi-tenant budgets: designing cxjcoins so nobody can burn the company.
8. Company mode: an org chart where agents are members.
9. Browser co-browsing: letting a human and an agent share a page.
10. Why we chose AGPL and what we tell enterprise legal teams.

## Social cadence

| Day | Post |
| --- | --- |
| Mon | Build-in-public update (number + screenshot) |
| Wed | Thesis / contrarian take |
| Fri | Demo clip or customer quote |

LinkedIn: Tuesday or Wednesday, one long post per week.
Comments: 15 minutes/day replying in r/selfhosted, HN threads and X — before posting anything.

## Newsletter (start when the site launches)

- Biweekly, 300–500 words: one shipped thing, one number, one link.
- Issue #1 (Jan 13): "The site is live and here's the 10-minute install."
- Issue #2 (Jan 27): "Product Hunt results + what we fixed."
- Issue #3 (Feb 10): "YC, and the roadmap you voted for."

## Content QA

- [ ] Title promises a specific outcome, not a vibe.
- [ ] First 40 words contain the problem.
- [ ] One screenshot minimum, with alt text.
- [ ] One number the reader could verify.
- [ ] Next step at the end.
- [ ] Read once for claims against `research/PLATFORM_REVIEW.md`.
