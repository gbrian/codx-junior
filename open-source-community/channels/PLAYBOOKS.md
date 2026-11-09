# Channel playbooks

Ordered by expected return for a cold start with ~5 stars. Do the top four before touching
the long tail.

---

## 1. Hacker News (Show HN)

**Why:** the single best source of technical users, contributors and YC-adjacent credibility.
**When:** 1–2 weeks after Product Hunt — never the same week. Best window: Tue–Thu, 06:00–09:00 PT.
**Who posts:** the founder, with a real account that has history. No new accounts.

**Title (max 80 chars, no marketing):**
> Show HN: codx-junior – an open-source workspace where AI agents and humans share a board

Alternatives:
> Show HN: Self-hosted workspace for AI agents that edit your repo and report their cost
> Show HN: I built a Kanban where every card is an AI chat with a budget

**First comment (post immediately, technical, no pitch):**
> I built this because I kept losing context between the board, the agent, the container, the PR
> and the AI bill. A card here is a chat: moving it to "In progress" starts an agent with the
> repo indexed for RAG, a profile that sets the model/tools, and a per-user budget in cxjcoins.
> The diff and the cost land on the same card.
>
> Stack: FastAPI + Vue 3, Milvus for RAG, Docker Compose for the stack and for workspaces
> (workspaces are behind a flag right now — the runtime is the part I'm least happy with).
> Provider-agnostic: Ollama, LiteLLM, vLLM, OpenAI.
>
> It's AGPL, self-hosted, one maintainer, active beta. I'd genuinely like feedback on the review
> loop and the cost model — those are the two things I think are under-designed in every other
> tool.
>
> Docs: [link] · Code: [link]

**Rules that matter**
- Never ask for upvotes, never ring up a voting group; HN detects it and it kills the thread.
- Reply to every substantive comment, especially criticism. Concede fast and specifically.
- Do not argue about "yet another AI tool". Answer with the specific problem and move on.
- Expect "this is just Jira + Cursor". The answer is in `research/COMPETITORS.md` §2A.
- If it doesn't take off, do not repost for 3+ months with the same title.

## 2. Reddit

Post only where you have (or build) account history. Read each sub's self-promo rules; several
require a ratio of comments to posts.

| Sub | Angle | Format | Notes |
| --- | --- | --- | --- |
| r/selfhosted | "Self-hosted AI workspace, one compose file" | Screenshot + compose + honest limits | The best-fit sub. Lead with self-hosting, not AI. |
| r/LocalLLaMA | "Ollama/vLLM in a full dev workspace + per-user budgets" | Technical post + numbers | Show model config, context, cost per task |
| r/SideProject | Founder story, build-in-public | Short + gallery | Friendly, low technical bar |
| r/devops | Traefik + Milvus + Docker Compose architecture | Architecture diagram | Write-up, not a launch post |
| r/opensource | AGPL, contribution ask | Repo link + good-first-issues | Low volume, high intent |
| r/ExperiencedDevs / r/ExperiencedDevs | "Supervised autonomy" essay | Discussion | No link; put the repo in the profile |

**Rules:** no link-only posts, no cross-posting the same text within an hour, answer every
comment, disclose that you are the author, and never buy upvotes.

## 3. X / Twitter

**Why:** compounding build-in-public distribution and where PH/HN conversations continue.
**Cadence:** 4–5 posts/week. Threads on launch days.

Content mix:
1. **Build in public:** a screenshot, a number, a decision (`"We cut install time from 40 to 12
   min. Here's what was slow."`).
2. **Contrarian thesis:** `"Autonomous agents are a demo. Supervised autonomy is a product."`
3. **Teardown:** `"I audited 5 AI coding tools for cost visibility. Only 1 meters per user."`
4. **Demo clip:** 15–20 s, captioned, no music.
5. **Ask:** `"What's the one thing you'd want your AI agent to ask permission for?"`

Tag relevant people sparingly; you get one shot per person. Reply to bigger accounts with a
concrete example, never "great post!".

## 4. LinkedIn

**Why:** agencies, SMB tech leads, investors, YC partners. The founder-story channel.
**Cadence:** 1–2/week. Long-form, first-person, no hashtag soup (3 max).

Winning formats:
- **The problem I lived** (400 words, one screenshot).
- **The launch** (PH day, with numbers).
- **The lesson** (`"We published internal engineering reviews by accident. Here's the build
  guard we added."` — trust-building gold).
- **The customer** (with permission, named).

## 5. Developer directories (one afternoon, high ROI)

| Directory | What to submit | Notes |
| --- | --- | --- |
| awesome-selfhosted | PR adding the project under "Software Development" | Read CONTRIBUTING; needs a licence + demo |
| selfh.st | Submission form + weekly newsletter | Self-hosted audience, high conversion |
| LibHunt | Project listing | Pulls from GitHub; claim it |
| AlternativeTo | "Alternative to Jira/Cursor/Linear" | Long-tail SEO |
| Uneed, MicroLaunch, Peerlist, Fazier, Startup Stash | Launch listings | Free tier, do them on PH week |
| There's An AI For That / Futurepedia | AI directories | Low intent for devtools; do it anyway, it's free |
| dev.to / Hashnode | Cross-post the blog | Canonical URL back to the site |
| GitHub topics | `ai-agents, self-hosted, kanban, llm, rag, developer-tools` | Free discovery |

## 6. Newsletters and podcasts (pitch after launch, with numbers)

| Outlet | Pitch angle |
| --- | --- |
| selfh.st weekly | "New self-hosted AI workspace, one compose file" |
| TLDR / Bytes / Console | "OSS alternative to Jira + Cursor for AI teams" |
| DevOps'ish | "Traefik + Milvus + Compose architecture" |
| Changelog / Practical AI / Self-Hosted podcast | "Supervised autonomy: why agents need budgets" |
| Ben's Bites | Launch angle after a PH result |

Pitch template: one-line hook, the number, the link, the founder availability. Never attach a
deck to a first email.

## 7. Communities (join before you need them)

- **Ollama, LiteLLM, MCP, LangChain Discords** — answer questions for 2 weeks, then mention the
  project only where relevant.
- **Indie Hackers** — build-in-public thread with revenue numbers.
- **Local AI / self-hosting Matrix and Telegram groups** — share the compose file, not the pitch.
- **Your own Discord** — open it when the first 50 users exist; do not open an empty server.

## 8. GitHub as a channel

- [ ] Description: "Open-source workspace where your whole software project lives in one tab:
      Kanban, AI agents, dev containers, review and AI budgets."
- [ ] 10 topics; social preview image; README first screen matches the site hero.
- [ ] `good first issue` ×5, `help wanted` ×3, `roadmap` label, Discussions on.
- [ ] `CONTRIBUTING.md` with a 5-minute dev setup; `SECURITY.md`; issue forms.
- [ ] Release notes for every tag; `CHANGELOG.md` linked from the site.
- [ ] Pin the launch post; add the PH badge only if earned.

## 9. Outreach to design partners

Target 30 agencies / indie hackers. 5 sentences, no deck, one ask (20-minute call).

> Subject: **A workspace for your client projects (free during beta)**
>
> Hi [name] — I saw [specific project/post]. I'm building codx-junior: an open-source workspace
> where each client project gets a board, agents that work in the repo, containers, and a
> per-project AI budget. I'm looking for 5 shops to run one real project in it, free, with me
> helping directly.
>
> Worth 20 minutes this week? Happy to show it on your repo, not mine.

Track: sent / opened / replied / call / activated / paying.

## 10. Channel scorecard (review monthly)

| Channel | Effort/week | Signups | Installs | Paying | Keep? |
| --- | --- | --- | --- | --- | --- |
| Hacker News | event | | | | yes |
| Product Hunt | event | | | | yes |
| Reddit | 2 h | | | | yes |
| X | 3 h | | | | yes |
| LinkedIn | 2 h | | | | yes |
| Directories | one-off | | | | yes |
| Newsletters | 1 h | | | | after launch |
| Podcasts | 1 h | | | | after launch |
| Cold outreach | 5 h | | | | yes (revenue) |

Kill a channel after 8 weeks without a single install.
