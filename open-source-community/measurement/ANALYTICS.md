# Measurement

Without numbers, the launch is a vibe. This is the smallest measurement system that lets us
answer: *did anyone arrive, did they install, did they come back, and did any of them pay?*

---

## 1. Stack

| Layer | Tool | Why |
| --- | --- | --- |
| Site analytics | **Plausible** (or self-hosted Umami) | Cookieless, no banner, simple events |
| Search console | Google Search Console + Bing | The only source of query intent |
| Product usage | **opt-in** weekly ping from the API + install survey | No telemetry by default (it is a selling point) |
| Revenue | invoices (managed team) | One sheet, updated weekly |
| Community | GitHub stars/forks/issues, Discord members | Free, public, honest |
| Launch | PH dashboard + UTM segment | Compare channels |

Do **not** add GA4, heatmaps, session recording or third-party pixels: it contradicts the
privacy positioning and makes the site slower.

## 2. UTM convention

`utm_source` · `utm_medium` · `utm_campaign` · `utm_content` (optional)

| Channel | Example |
| --- | --- |
| Product Hunt | `?utm_source=producthunt&utm_medium=launch&utm_campaign=ph_2027_01` |
| Hacker News | `?utm_source=hackernews&utm_medium=show_hn&utm_campaign=showhn_2027_01` |
| Reddit | `?utm_source=reddit&utm_medium=community&utm_campaign=selfhosted_2027_02` |
| X | `?utm_source=x&utm_medium=social&utm_campaign=launch_thread` |
| LinkedIn | `?utm_source=linkedin&utm_medium=social&utm_campaign=founder_post` |
| Newsletter | `?utm_source=newsletter&utm_medium=email&utm_campaign=issue_01` |
| Demo | `?utm_source=demo&utm_medium=internal` |

Rules: lowercase, no spaces, campaign = `topic_yyyymm`. Every paid or partner link gets one.

## 3. Events (site)

| Event | Trigger | Why |
| --- | --- | --- |
| `pageview` | every page | Baseline |
| `cta_quickstart_click` | hero / nav quickstart | Intent |
| `install_copy` | copy button on any code block containing `docker` or `git clone` | Proxy for install intent |
| `github_click` | any GitHub link | Community intent |
| `demo_request` | demo form submit | Sales intent |
| `newsletter_signup` | footer form | Owned audience |
| `docs_search` | search with a query | Content gaps (send the query string) |
| `docs_404` | 404 page view | Broken inbound links |
| `feature_page_view` | `/features/*` | Which features pull |

Keep it under 10 events. Every event must map to a decision.

## 4. Product measurement without telemetry

The install is the hard part: self-hosted means we cannot see it. Three honest mechanisms:

1. **Opt-in ping.** On first successful setup, the API asks the admin: "Send an anonymous
   weekly ping (version, tasks completed, no code, no prompts)?" Default **off**, explained in
   one sentence. Store only aggregates.
2. **Install survey.** After the first chat, an in-app card: "How did the install go? (1–5)" and
   one optional email field. One question, dismissible forever.
3. **Public proof.** GitHub stars, issues, and user-shared screenshots. Weak but free.

Never enable telemetry silently. It is a differentiator that we do not.

## 5. KPI tree

```
Reach
 ├── Site visits (by source/UTM)
 ├── GitHub stars added/week
 └── Newsletter subscribers

Intent
 ├── install_copy events / visits        (target > 8%)
 ├── Quickstart page → GitHub click      (target > 25%)
 └── Demo requests / visits              (target > 1%)

Activation
 ├── Installs started (survey/ping)
 ├── Installs completed first chat       (target > 60% of started)
 └── Time to first chat                  (target ≤ 15 min, median)

Retention
 ├── Week-4 active installs              (target ≥ 40%)
 ├── Tasks completed / project / week    (target ≥ 5)
 └── Projects per install                (target ≥ 2)

Revenue
 ├── Managed pilots signed               (target 3 by Feb 2027)
 ├── Revenue / pilot / month
 └── Gross margin per pilot (hours vs price)
```

## 6. Launch scorecard (fill on 2027-01-26 and weekly after)

| Metric | Baseline (Nov 9) | PH day | +7 d | +30 d |
| --- | --- | --- | --- | --- |
| GitHub stars | 5 | | | |
| Site visits | 0 | | | |
| install_copy events | 0 | | | |
| Install survey responses | 0 | | | |
| Demo requests | 0 | | | |
| Newsletter | 0 | | | |
| Managed pilots | ? | | | |
| MRR | ? | | | |

## 7. Weekly review (30 min, Mondays)

1. Which source produced the most **installs**, not visits?
2. Which page has the highest exit rate before the quickstart?
3. What did people search for and not find? → add to content backlog.
4. Which claim generated the most pushback? → fix the claim or the product.
5. One channel to double down on, one to pause.

## 8. Attribution caveats

- Self-hosted installs are largely invisible; treat survey/ping as a **sample**, not a census.
- Product Hunt traffic is heavily same-day; judge it on 7-day retention, not visits.
- HN traffic converts to GitHub stars better than to installs; measure both.
- Reddit traffic is high-bounce; look at time-on-page and quickstart clicks instead.
- Word of mouth is invisible; add "how did you hear about us?" to the install survey.

## 9. Privacy note published on the site

> We do not run third-party trackers or advertising pixels. The site uses cookieless analytics
> that records page views and clicks in aggregate. The product sends nothing to us unless you
> explicitly opt in to an anonymous weekly ping. Your code, prompts and models never leave your
> infrastructure.
