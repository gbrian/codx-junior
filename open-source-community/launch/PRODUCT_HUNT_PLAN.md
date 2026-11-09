# Product Hunt launch plan

**Target:** Tuesday **2027-01-26**, 12:01 AM PT (08:01 UTC).
**Why that date:** a Tuesday in the first month of the year, two weeks after the public site
launch (so the site is warm and the demo is hardened), and 13 days before the expected YC X27
deadline (so launch metrics can go in the application).

> Product Hunt changes its rules and ranking regularly. Re-read
> <https://help.producthunt.com> and the "Launch Guide" the week before, and treat every
> mechanical detail below as *verify-then-use*.

---

## 1. What we are launching

Not "an AI coding tool". Product Hunt's developer audience has seen 200 of those this year.
We launch **a different unit of work**:

> **codx-junior — the open-source workspace where a whole project lives in one tab.**
> Kanban cards that are AI chats. Agents that ship with review gates. Dev containers,
> team chat and per-user AI budgets. Self-host it, or hire the team that runs it.

The hook for the gallery: **"One tab. Six tools dead."** — board, chat, container, diff,
budget, team.

## 2. Who we are really talking to on PH

| Persona | What they will click | What they will read | What converts them |
| --- | --- | --- | --- |
| Indie hacker drowning in 4 tools | The "one tab" visual | The first comment | The 10-min quickstart |
| Self-hoster | "Open source, AGPL, your models" | The license answer | The compose file |
| Engineering lead | "per-user budgets" | Features page | The analytics screenshot |
| AI tinkerer | "computer use / browser agents" | Video | The demo video clip |

The site must answer, above the fold: **what it is, who it's for, what it costs, how to try it.**

## 3. Assets (build by 2027-01-19)

| Asset | Spec | Content |
| --- | --- | --- |
| Thumbnail | 240×240 PNG | Logo on brand gradient (#550e57 → #8f008f), no text |
| Gallery 1 | 1270×760 | Hero shot: kanban board + open chat, headline "Your whole project in one tab" |
| Gallery 2 | 1270×760 | "Every card is a chat" — board with an agent running, diff visible |
| Gallery 3 | 1270×760 | "Budget you can see" — analytics, per-user wallet, cxjcoins |
| Gallery 4 | 1270×760 | "Agents with a whole machine" — computer session, human watching |
| Gallery 5 | 1270×760 | "Self-hosted, your models" — compose + provider list (Ollama/LiteLLM/OpenAI) |
| Gallery 6 | 1270×760 | "Open source, AGPL-3.0" + GitHub stars + quickstart command |
| Demo video | 60–90 s, 1080p, captioned | The §7 script from `research/PLATFORM_REVIEW.md` |
| GIF | 8–12 s, < 5 MB | Agent edits a file, test goes green |
| Tagline | ≤ 60 chars | options in `PRODUCT_HUNT_COPY.md` |
| Description | ≤ 260 chars | options in `PRODUCT_HUNT_COPY.md` |
| First comment | 300–500 words | maker story + what's beta + offer |
| Founder avatar | 400×400 | real photo, not logo |

Rules of thumb: gallery text ≥ 24 px at 1270 px wide, one idea per image, no laptop mockups
with fake code, real screenshots only.

## 4. Four-week pre-launch

### Week -4 (Dec 29 – Jan 4): foundation
- [ ] Confirm launch date against the PH calendar (avoid big AI launches; check "upcoming").
- [ ] Create the **Upcoming** page ("codx-junior — coming soon"), tagline + thumbnail + 3 images.
- [ ] Set up a launch list: Buttondown form on the site ("Get the launch + a 10-min install guide").
- [ ] Build the supporter sheet: 60 people, timezone, relationship, channel, asked? replied?
- [ ] Draft the first comment; have two people outside the team critique it.

### Week -3 (Jan 5 – 11): social proof
- [ ] Publish 2 blog posts (see `content/CALENDAR.md`).
- [ ] Post 3 build-in-public threads on X (the workspace problem, the budget problem, the agent-drift problem).
- [ ] DM 10 friendly devs for a pre-launch install test; collect 3 quotable sentences.
- [ ] Record the demo video v1; cut to 90 s; add captions.
- [ ] Prepare the "beta honesty" paragraph — PH commenters punish overclaiming.

### Week -2 (Jan 12 – 18): public site + rehearsal
- [ ] **Public site launch Jan 12** (see `website/PUBLISH_PLAN.md`).
- [ ] Soft-ask supporters: "we launch on the 26th, here's the upcoming page" (never "upvote me").
- [ ] Finalize gallery; A/B the hero line with 10 people.
- [ ] Hunter decision: **self-hunt** (default). A hunter is only worth it if they have a real,
      engaged audience and will write a genuine comment; otherwise it adds a dependency.
- [ ] Dry-run the launch day: runbook + roles + backup laptop + hotspot.

### Week -1 (Jan 19 – 25): lock
- [ ] Freeze the product: no risky merges after Jan 23; only docs and copy fixes.
- [ ] Demo instance: seeded, reset nightly, rate-limited, token-capped, public creds tested.
- [ ] Three clean-host installs; record the fastest (use the time in the first comment).
- [ ] Schedule the launch-day posts (X thread, LinkedIn, Discord, email) — do not auto-publish
      before the PH link is live.
- [ ] Prepare 10 comment replies (skeptic, AGPL, security, self-host effort, "why not Cursor").
- [ ] Offline copy of every asset on two laptops.

## 5. Launch day (2027-01-26) at a glance

Full hour-by-hour in [`LAUNCH_DAY_RUNBOOK.md`](LAUNCH_DAY_RUNBOOK.md).

| Time (PT) | Time (UTC) | Action |
| --- | --- | --- |
| 00:01 | 08:01 | Product goes live; post the first comment within 5 min |
| 00:10 | 08:10 | Personal network ping #1 (Asia/Europe awake) |
| 01:00 | 09:00 | X thread + LinkedIn post |
| 03:00 | 11:00 | Email the launch list |
| 06:00 | 14:00 | US East morning push |
| 08:00 | 16:00 | US West morning push; reply to every comment |
| 12:00 | 20:00 | Midday update comment (what people asked, what we fixed) |
| 16:00 | 00:00 (+1) | Europe evening push |
| 23:59 | 07:59 (+1) | Final reply sweep; thank-you comment |

## 6. Offer

Keep it simple, useful, and non-gimmicky:

> **Launch week:** free 45-minute onboarding call for the first 50 teams that install, and a
> direct line to the maintainer for setup blockers.

Add a "Founding self-hosters" list (name + logo, opt-in) — social proof for the next launch.

## 7. Ranking reality check

- PH ranks on **upvotes weighted by engagement**, not raw upvotes. Comments, profile
  completeness and time-on-page matter.
- Never ask for upvotes publicly or in DMs; ask people to "take a look and tell me what's
  confusing". Soliciting votes can get the launch penalized.
- A "Product of the Day" badge is nice; **200 installs and 30 conversations** is better.
- If we are not top 5 by 10:00 PT, shift from ranking to conversion: reply to everything,
  push the demo, capture emails.

## 8. Success metrics

| Metric | Target | Stretch |
| --- | --- | --- |
| Upvotes | 400 | 800 |
| Ranking | Top 10 of the day | Top 3 / Product of the Day |
| Site visits from PH (UTM) | 1,500 | 4,000 |
| GitHub stars added (day) | 150 | 400 |
| Install commands copied (event) | 200 | 500 |
| Verified installs (survey/ping) | 40 | 100 |
| Demo requests | 15 | 40 |
| Newsletter signups | 100 | 250 |
| Conversations with ICP | 10 | 25 |

## 9. If Product Hunt underperforms

PH is one amplifier, not the strategy. The same week:

- **Show HN** the following Tuesday with the technical story ("We built an OSS workspace where
  AI agents share a desktop with humans"), not the marketing story.
- **Reddit**: r/selfhosted, r/LocalLLaMA, r/SideProject, r/devops (rules in `channels/PLAYBOOKS.md`).
- **Directories**: awesome-selfhosted, selfh.st, LibHunt, AlternativeTo, Uneed, MicroLaunch,
  Peerlist, dev.to.
- **Design partners**: 30 personal emails to agencies and indie hackers; 45-min calls.

## 10. Post-launch (Jan 27 – Feb 5)

- [ ] Thank-you comment on PH and on X; tag the people who gave real feedback.
- [ ] Publish "launch retrospective" blog with numbers (great for YC and HN).
- [ ] Ship the top 3 fixes requested on launch day, publicly, within a week.
- [ ] Add the badge to the site (only if we actually got one; never fake it).
- [ ] Convert demo requests into 10 recorded user interviews.
- [ ] Feed everything into the YC application numbers.
