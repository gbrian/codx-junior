# YC strategy

**Objective:** get an interview and an offer for a 2027 batch with a story that matches the
product we can actually demo.
**Current state (2026-11-09):** 5 GitHub stars, no public site, no revenue on record in this
repo, one founder + one account manager, a large working beta.

> Batch dates below are **provisional** — YC now runs four deadlines a year and confirms each
> on its apply page. Re-check <https://www.ycombinator.com/apply> before planning around any
> date. The Winter 2027 deadline (2026-11-02, 8 pm PT) has closed; on-time applicants hear back
> by 2026-12-11. The next window, Spring 2027, is *expected* around **2027-02-08**
> ([Round Funded calendar](https://www.roundfunded.com/en/blogs/yc-application-deadlines-2026-2027),
> third-party, unconfirmed).

---

## 1. Which batch, and when to submit

| Option | Timing | Pros | Cons | Verdict |
| --- | --- | --- | --- | --- |
| Late application to **W27** now | This week | Enters the queue; late apps are still read | No promised decision date; metrics are the weakest they will ever be | **No** |
| **Early Decision** for X27 now | Dec 2026 | Decision months early; good if fundraising timing is tight | Judged on pre-launch metrics; if rejected, burns a cycle | **Optional**, only after the site is live |
| **X27 on-time** (~2027-02-08) | Submit ~2027-02-05 | Best metrics: public site + PH launch + installs + pilot revenue | Wait ~3 months | **Recommended** |
| S27 (expected ~2027-05-03) | May 2027 | More traction | Six months of runway without YC | Fallback |

**Recommendation:** build and launch through January, submit X27 around **2027-02-05** with
Product Hunt (Jan 26) fresh in the numbers. If a fundraise is already in motion and an early
answer matters, apply Early Decision in mid-December and treat X27 as the real attempt.

## 2. The one-sentence company

> codx-junior is the operating system for AI-native software delivery: an open-source workspace
> where Kanban tasks, AI agents, dev containers, code review and per-user AI budgets live in one
> tab — sold as self-hosted software, with a managed team that runs it for you.

Shorter, for the "what are you building" box:

> We give small software teams the output of a much larger team: AI agents do the volume, humans
> keep the direction, and every task, diff and dollar is visible in one workspace.

## 3. Why this is a YC-shaped company (and the counter-arguments)

**For**
1. **Huge, urgent market.** Every software team is being reorganized around AI agents; the
   tooling to *govern* that work (context, review, cost) is immature.
2. **Bottom-up distribution works.** Open source + self-host is how developer infrastructure
   companies get their first 1,000 users without a sales team. PH/HN/GitHub are the channel.
3. **A real wedge with revenue.** The managed team funds development and produces the
   proprietary insight (what work agents actually do well) that becomes product.
4. **Compounding data moat (potential).** Profiles, task graphs and cost data across projects
   → benchmarks for what an agent run *should* cost and how reliable it is.
5. **Technical founder, deep product.** ~250k LOC across two stacks, built by one person.

**Against (YC partners will ask)**
1. *"This is an agency with a side project."* → Answer with product usage growth and services
   margin trend; show services revenue per project falling as the product does more.
2. *"Cursor/Copilot will eat this."* → They optimize the editing loop; governance, budget and
   multi-tool orchestration are a different buyer. Show integration, not competition.
3. *"Too many features, no focus."* → Pick the beachhead in the application: **small dev shops
   delivering client projects**. One sentence: "agencies run 10 client projects with 3 devs."
4. *"Open source + AGPL kills enterprise sales."* → Commercial license + hosted/managed path;
   AGPL is a distribution advantage for bottom-up adoption.
5. *"One founder, one maintainer."* → Be explicit about the plan; YC funds solo founders, but
   the bus factor is a real question. Show contributors, a support process, and the next hire.

## 4. The narrative (use this order everywhere)

1. **Problem.** A software project is spread across a board, an IDE agent, a container, a PR
   review and a provider dashboard. Every hand-off loses context; AI spend is invisible; the
   agent that writes the code is not accountable to anyone.
2. **Insight.** Fully autonomous agents fail in production, fully manual teams are too slow.
   The winning shape is *supervised autonomy*: agents do the volume, humans approve every
   change, and the cost of each run is a first-class object.
3. **Product.** One workspace where a task *is* a conversation, the agent works in your repo,
   the diff and the cost land on the same card, and the whole thing runs on your infrastructure.
4. **Why now.** Agent tool-calling became reliable enough in 2025–26; local models became good
   enough to self-host; every company is being asked "what is your AI policy and what does it
   cost?" — and nobody has an answer that is both auditable and usable.
5. **Traction.** Installs, weekly active projects, tasks completed, managed pilots, revenue.
6. **Business model.** OSS core (AGPL) → managed team (services, high margin per project) →
   enterprise (SSO, audit, support, commercial license).
7. **Ask.** $500K standard deal to turn the managed-team motion into a product-led one and hire
   the first two engineers.

## 5. Metrics we must have by 2027-02-05

| Metric | Why YC cares | Where it comes from | Target |
| --- | --- | --- | --- |
| Weekly active installs | Is anyone using it? | optional ping + survey | 25 |
| Projects with ≥ 1 agent task/week | Depth, not curiosity | local analytics shared by users | 40 |
| GitHub stars | Distribution signal | GitHub | 500 |
| PH result | Launch execution | PH | top 10 of day |
| Managed pilots signed | Revenue reality | invoices | 3 |
| MRR / pilot revenue | The business | invoices | $5–15k |
| Retention (4-week) | Does it stick? | install cohort survey | ≥ 40% |
| Cost per completed task | The budget thesis | cxjcoins export | a real number, published |
| Interview quotes | Proof of pain | 10 recorded calls | 10 |

If we cannot produce at least **installs + 3 paying pilots + retention**, the honest move is to
apply to a later batch and keep shipping. A weak application is not free: it sets the baseline
story.

## 6. Application strategy

* **Write it in a doc first** (`YC_APPLICATION_DRAFT.md`), then paste. Two weeks before the
  deadline, not two days.
* **Every answer starts with the concrete fact**, then the explanation. No adjectives.
* **One founder voice.** YC reads thousands; clarity beats completeness.
* **Numbers with denominators.** "40 of 61 installs completed a first task" beats "great
  retention".
* **Video (1 min):** founder on camera, screen share, the 90-second demo from
  `research/PLATFORM_REVIEW.md` §7, no music, no slides.
* **References:** 2–3 users who will vouch, with permission.
* **Company status:** if not incorporated, say so and state the plan (YC helps; do not let it
  block the application).

## 7. Interview preparation (10 minutes, 2–3 partners)

Structure the answers to 20–40 seconds. Practice out loud, on video, three times.

**The questions that decide it**

| Question | The answer we must have |
| --- | --- |
| What do you do? | One sentence, no jargon, then the demo. |
| Who uses it today? | Name the beachhead: small dev shops / solo tech leads. Real numbers. |
| How do you make money? | OSS core free; managed team paid; enterprise later. Show a pilot invoice. |
| Why will you win? | Supervised autonomy + open source + the only place where work, code and cost meet. |
| What's the insight? | "Agents don't need more autonomy; they need accountability and a budget." |
| Why now? | Tool calling + local models + AI cost panic. |
| What's the hardest thing? | Honest answer: trust/quality of agent output and the install experience. |
| Why hasn't Cursor done this? | Different buyer and shape; they sell an editor, we sell the delivery system. |
| How big can this get? | Bottom-up math, not a top-down TAM slide. |
| What will you do with $500K? | Two engineers, one designer/DevRel, 18 months of runway. |
| What's your growth rate? | A real weekly number, even if small. |
| Why are you the founder? | 20+ years shipping software, built this because you needed it, dogfooding daily. |

**Traps to avoid**
- Demoing more than three features. Show the loop, not the catalog.
- Saying "we have no competition". There is always an alternative: spreadsheets, Jira, Cursor.
- Defending weaknesses. Name them, then say what you are doing about them.
- Talking about the managed team before the product. Services is the wedge, not the story.
- Reading slides. There are no slides.

**Demo script for the interview (90 s)**
1. Board with a client project. *(5 s)*
2. Move a card → agent starts with the repo context. *(10 s)*
3. Agent searches, patches, tests, opens a diff. *(25 s)*
4. Approve the diff; the cost appears in the wallet. *(15 s)*
5. Computer session: the agent clicks through the running app and fixes a visual bug. *(25 s)*
6. "Self-hosted, AGPL, any model provider. 10-minute install." *(10 s)*

## 8. If YC says no (or nothing)

- Apply again next batch; YC explicitly accepts reapplications.
- Run the same narrative at: **a16z Speedrun**, **HF0**, **South Park Commons**, **Antler**,
  **Platanus Ventures** (LATAM), **500 Global**, **Techstars**.
- Keep the funnel alive with angels from the launch (Product Hunt + HN are the top of that funnel).
- YC Startup School + Bookface-adjacent communities for feedback, not for funding.

## 9. Timeline

| Date | Milestone |
| --- | --- |
| 2026-11-10 → 11-28 | Website P0s fixed, v1.3.0 images, public site ready |
| 2026-12-09 | Soft launch; external testers |
| 2026-12-15 | Draft YC answers v1; 10 user interviews booked |
| 2027-01-12 | Public site launch |
| 2027-01-26 | Product Hunt launch (metrics for YC) |
| 2027-01-27 → 02-03 | Update metrics; record 60 s founder video; 3 references confirmed |
| **2027-02-05** | **Submit X27** (deadline expected 02-08) |
| 2027-02-15 → 03-12 | Interview window (expected); practice daily |
| After decision | If in: plan the batch. If out: S27 (expected May) with 3 more months of traction |
