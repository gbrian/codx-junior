# Launch-day runbook — Product Hunt, 2027-01-26

Times in **PT** (UTC = PT + 8). Two people minimum: **Maker** (founder, replies + posts) and
**Ops** (site, demo, infra, screenshots). A third **Reader** (community, DMs, triage) helps
from 06:00 PT.

---

## T-7 days: freeze and verify

- [ ] Product freeze: no risky merges after 2027-01-23 18:00 PT.
- [ ] Re-read the PH Launch Guide; confirm gallery specs and topic list in the dashboard.
- [ ] Every URL in every asset returns 200 (home, quickstart, demo, GitHub, roadmap).
- [ ] Demo instance: seeded, public creds tested in a private window, nightly reset on.
- [ ] Uptime monitors green; alert email + phone tested.
- [ ] Rollback tested (Cloudflare Pages previous deployment).
- [ ] Supporter sheet final: 60 names, timezone, channel, sent? replied?
- [ ] All posts drafted and scheduled *as drafts* (nothing auto-publishes before the link exists).
- [ ] Two laptops charged, hotspot ready, assets on both + cloud folder.
- [ ] Analytics dashboard: PH UTM segment saved; live view bookmarked.

## T-1 day: dry run

- [ ] Submit the PH draft for review (PH allows scheduling; schedule for 00:01 PT).
- [ ] Walk the runbook end-to-end with the Ops person, including the reply templates.
- [ ] Prepare the pinned X post and the LinkedIn post as drafts.
- [ ] Email the launch list the "tomorrow" note (optional, 18:00 PT).
- [ ] Sleep. Do not ship anything after 21:00 PT.

## Launch day — hour by hour

### 00:00 PT — go
- [ ] Product live. Open the page in a private window: images, video, links, first comment.
- [ ] Post the first comment (`PRODUCT_HUNT_COPY.md` §6) within 5 minutes.
- [ ] Verify the "Visit website" link carries `?utm_source=producthunt&utm_medium=launch&utm_campaign=ph_2027_01`.
- [ ] Ops: confirm the site is up from two regions; screenshot the PH page (for the archive).

### 00:15 PT — first circle
- [ ] Ping supporter group A (Europe/Asia awake): "we're live, here's the page — take a look
      when you have a minute". **Never "upvote".**
- [ ] Reply to every comment as it lands (< 10 min).

### 01:00 PT — public posts
- [ ] Publish the X thread (`PRODUCT_HUNT_COPY.md` §9), pinned.
- [ ] Publish the LinkedIn post (§10).
- [ ] Post in 2 friendly Discords/Slacks (value first: "I built this, happy to answer questions").

### 03:00 PT — email
- [ ] Send the launch email to the list: 120 words, one link, one ask ("install and tell me
      where you got stuck").

### 06:00 PT — US East
- [ ] Ping supporter group B (US East).
- [ ] Post in r/SideProject or r/selfhosted **only if** the sub's self-promo rules allow it and
      the account has history; otherwise skip to keep the account safe.
- [ ] Mid-morning check: ranking, upvotes, traffic, install events, GitHub stars (**record numbers**).

### 08:00 PT — US West
- [ ] Ping supporter group C (US West).
- [ ] Reply sweep. Ask one substantive question per reply to keep threads alive.

### 12:00 PT — midday update
- [ ] Post an update comment: "3 things people asked for today; here's what we fixed already".
- [ ] Ship one tiny fix live if a real bug was reported (announce it).
- [ ] Record metrics in the launch sheet.

### 16:00 PT — Europe evening
- [ ] Ping group D; publish a 3-tweet "what we learned today" thread.
- [ ] Reply sweep.

### 20:00 PT — final push
- [ ] Personal emails (not mass) to the 10 warmest contacts.
- [ ] Reply to every unanswered comment; nothing left hanging.

### 23:30 PT — close
- [ ] Thank-you comment.
- [ ] Screenshot the final rank/upvotes; export the day's analytics.
- [ ] Write 10 lines: what worked, what broke, top 3 requests, tomorrow's plan.

## Roles

| Role | Owns | Does not |
| --- | --- | --- |
| Maker | PH page, comments, X/LinkedIn posts, demo calls | Debug infra mid-day |
| Ops | Site, demo, uptime, deploy | Reply to product questions |
| Reader | DMs, community threads, issue triage, metrics sheet | Post on PH |

## Incident playbooks

| Incident | First action | Then |
| --- | --- | --- |
| Site down | Check Cloudflare status + last deployment | Roll back to previous deployment; post "site hiccup, back in N min" on PH + X |
| Demo down | Point the demo CTA to the quickstart page | Restart the demo stack; post a comment |
| Demo costs spike | Kill the demo container; switch CTA | Cap tokens; re-enable with a queue |
| Wrong claim spotted in a comment | Correct it publicly in the thread | Fix the site/docs the same day; add to the "claims discipline" table |
| Hostile comment | Reply once, factually, no defensiveness | Do not engage further; let the community answer |
| PH page rejected/held | Contact PH support; check tagline/assets against rules | Re-schedule, do not re-create the page |

## Message templates

**Supporter ping (WhatsApp/Slack, 1:1):**
> We're live on PH today: [link]. No need to vote — if you have 2 minutes, tell me if the page
> makes sense. If you install it, I'll help you personally this week.

**Reply to "looks cool":**
> Thank you! If you install it, the quickstart is here: [link]. Tell me where you get stuck and
> I'll fix it today.

**Reply to "why not X":**
> Fair question — X is better at [specific thing]. We're not trying to replace it; we're the
> workspace around it: plan, run, review, budget. If X is enough for your team, genuinely use X.

**Correction template:**
> You're right, that claim is too strong. [Correct fact]. I've updated the page. Thanks for
> catching it.

## Do / don't

**Do**
- Reply to everyone, including critics.
- Say "beta" when it's beta.
- Give the install command in the comments.
- Convert commenters into demo calls.
- Record numbers hourly.

**Don't**
- Ask for upvotes anywhere, ever.
- Argue about ranking.
- Post the same text in five subreddits the same hour.
- Overclaim to rescue a slow morning.
- Read the leaderboard more than once an hour.

## T+1 to T+7

- [ ] Thank-you comment + X post with real numbers.
- [ ] Publish the retrospective post (numbers, what broke, what's next).
- [ ] Ship the top 3 requested fixes; announce each.
- [ ] Email everyone who gave an email: "here's what we changed after launch".
- [ ] 10 user interviews booked from launch contacts.
- [ ] Update the YC application numbers while the data is fresh.
