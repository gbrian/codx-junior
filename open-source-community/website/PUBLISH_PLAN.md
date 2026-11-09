# Website publish plan — docs/ → public site

**Goal:** a stranger lands on the site, understands the product in 60 seconds, installs it in
under 15 minutes on a clean machine, and can give feedback.
**Audit basis:** [`AUDIT.md`](AUDIT.md) (2026-11-09).
**Target dates:** soft launch **2026-12-09**, public launch **2027-01-12**, Product Hunt
**2027-01-26** (Tuesday), YC X27 submission **2027-02-05**.

---

## 1. Definition of done

The site is publishable when all of these are true:

1. `https://<domain>` serves the built site over TLS; `http` and `www` redirect; no mixed content.
2. `npx vitepress build` runs in CI on every PR and fails on a dead internal link.
3. Zero internal review/engineering notes are published; a guard test enforces it.
4. The install path is **one compose file with pinned, freshly published images**, verified on
   three clean hosts (Ubuntu 24.04, macOS Apple Silicon, WSL2), time-to-first-chat ≤ 15 min.
5. The docs match the shipped release tag exactly (features, screenshots, config keys).
6. `sitemap.xml`, `robots.txt`, canonical URLs, OG/Twitter cards and a 1200×630 image are live
   and verified in the LinkedIn, X and Slack unfurl debuggers.
7. Every page has a working next step: quickstart, demo request, GitHub, or newsletter.
8. Analytics records page views and install-intent clicks with UTM attribution.
9. CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, CHANGELOG, license/AGPL FAQ exist.
10. A rollback exists: previous deployment restorable in < 5 minutes.

## 2. Decisions to make first (block everything else)

| ID | Decision | Options | Recommendation | Owner | By |
| --- | --- | --- | --- | --- | --- |
| D1 | Domain | `codx-junior.ai` (matches `join@` email), `codx-junior.com`, `.dev`, `getcodxjunior.com` | Register **codx-junior.ai** as canonical; buy `.com` defensively and 301 it; keep GitHub homepage in sync | Founder | 2026-11-12 |
| D2 | Hosting | Cloudflare Pages, GitHub Pages, Netlify, Vercel | **Cloudflare Pages**: free, preview deploys per PR, global edge, instant cache purge, no base-path pain | Founder | 2026-11-12 |
| D3 | Release branch | publish `v1.3-demo-site`, merge to `main`, or a `release/1.3` branch | Merge to **`main`**, tag `v1.3.0`, publish only from `main` | Dev | 2026-11-13 |
| D4 | Demo | hosted instance / request form / guided local / remove | **Request form now**, hosted read-only instance before Product Hunt | Founder | 2026-11-14 |
| D5 | Workspaces | fix / feature-flag / label experimental | Fix if ≥ 3 weeks of runway, else **feature-flag + docs edit** | Dev | 2026-11-16 |
| D6 | Site structure | single site at root, docs at `/docs/`, or subdomain | **Single site at root**, marketing home + `/features/` + `/getting-started`; add `/blog` later | Founder | 2026-11-13 |
| D7 | Analytics | Plausible, Umami, PostHog, GA4 | **Plausible** (cookieless, EU-friendly, cheap) | Founder | 2026-11-18 |
| D8 | Version display | none / footer / banner | Footer `v1.3.0 · active beta` + sticky "beta" notice on install page | Founder | 2026-11-20 |

> D1 note: the README already uses `join@codx-junior.ai` and `docs/` links to
> `codx-junior.ai`; GitHub's homepage field points at the dead `codx-junior.com`. One canonical
> domain, everywhere, or the launch leaks credibility.

## 3. Workstreams

| WS | Scope | Owner | Effort |
| --- | --- | --- | --- |
| **W1 Truth & safety** | Remove internal docs, fix demo, align docs with shipped code, workspaces decision | Dev + Founder | 3–6 dev-days |
| **W2 Install** | Versioned images, pinned compose, one-command quickstart, troubleshooting, sizing, upgrade/backup | Dev | 5–8 dev-days |
| **W3 Content** | New pages (quickstart, troubleshooting, operations, license FAQ, roadmap, changelog), copy edit, screenshots | Founder + Writer | 5–7 days |
| **W4 Design & assets** | OG cards, favicon set, screenshot set, 90 s demo video, PH gallery | Designer | 3–4 days |
| **W5 Pipeline** | CI (build, link check, guard), Cloudflare Pages deploy, preview envs, image publish workflow | Dev | 2–3 dev-days |
| **W6 SEO & measurement** | sitemap, robots, canonical, JSON-LD, analytics, UTM, 404, llms.txt | Dev | 1–2 dev-days |
| **W7 Community & legal** | CONTRIBUTING, SECURITY, CoC, issue/PR templates, CHANGELOG, AGPL FAQ, support SLA | Founder | 2 days |
| **W8 QA** | 3 clean-host installs, mobile pass, accessibility pass, Lighthouse, unfurl checks | All | 2–3 days |

## 4. Phases and gates

### Phase 0 — Decisions and unblocking · 2026-11-10 → 11-14

- [ ] D1–D3 decided and written down here.
- [ ] Domain registered; Cloudflare zone created; DNS ready (no records yet).
- [ ] `main` fast-forwarded/merged from `v1.3-demo-site`; `v1.3.0` tag created.
- [ ] Delete/move `docs/features/workspaces-*-review.md`; rebuild; confirm nothing under
      `dist/features/` matches `review`.
- [ ] Replace `<RegisterForm />` in `docs/demo.md` with decision D4's flow.
- [ ] Flip `ignoreDeadLinks: false` **after** the first clean build (currently 0 broken links).

**Gate G0:** build passes with dead-link checking on, no internal docs in `dist/`, demo page
renders a real form.

### Phase 1 — Install truth · 2026-11-10 → 11-24

This is the single highest-leverage workstream. A launch is judged on the first 10 minutes.

- [ ] Build and push multi-arch `codxjunior/codx-junior:{api,client,debian}` for `v1.3.0`
      plus `latest`; include OCI labels (`source`, `revision`, `version`), SBOM, and a digest
      in the release notes.
- [ ] Pin images in `codx-junior-installer/codx-junior/docker-compose.yaml`:
      `image: codxjunior/codx-junior:api-1.3.0` (or `@sha256:...`), never bare `latest`.
- [ ] Add `docker-compose.release.yaml` (pull-only, no `build:` keys) as the documented install.
- [ ] Quickstart rewrite (`docs/getting-started.md`) — ready-to-edit draft in
      [`QUICKSTART_DRAFT.md`](QUICKSTART_DRAFT.md):
      1. prerequisites + sizing table,
      2. `curl -fsSLO https://<domain>/install.sh && bash install.sh` **or** 3-line compose,
      3. generate secrets, don't ship placeholders,
      4. open URL, first login, add provider, add project, indexing,
      5. "this should take 10 minutes" stopwatch claim — verify it.
- [ ] `docs/troubleshooting.md`: ports 80/443 taken, `API disconnected`, milvus unhealthy,
      docker.sock permission, Traefik cert failure, out-of-memory, wrong architecture.
- [ ] `docs/operations.md`: volumes, backup/restore, upgrade, downgrade, uninstall, logs.
- [ ] `docs/faq.md` incl. hardware sizing per scenario (API models vs local models).
- [ ] Security pass: `.env.example` placeholders replaced with generated values in the
      quickstart; "before exposing to the internet" checklist.
- [ ] Remove `docs/docker-compose.yaml` (broken port mapping) or fix it to `5173:5173` and the
      correct volume path.
- [ ] Workspaces decision D5 executed (fix routes or feature-flag + docs edit).

**Gate G1:** a person who has never seen the repo installs from the docs alone, on a clean
Ubuntu box, in ≤ 15 min, and completes a first chat. Recorded on video.

### Phase 2 — Content completion · 2026-11-16 → 12-02

- [ ] Home page rewrite: hero, 3 proof bullets, 6 feature cards, a 30 s video, quickstart
      snippet, "self-host or managed" split, GitHub stars, newsletter.
- [ ] `/features/` overview aligned with `research/PLATFORM_REVIEW.md` status column.
- [ ] Feature pages: add a status badge to each (`stable` / `beta` / `experimental`).
- [ ] `/blog` section + first three posts (see `content/CALENDAR.md`).
- [ ] `/roadmap` (public, honest) and `/changelog` (from GitHub Releases).
- [ ] `/license` — AGPL FAQ: internal use, SaaS obligation, commercial licensing contact.
- [ ] `/contributing`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, issue forms, PR template.
- [ ] `/about` or `/team` updated; consistent founder story and contact.
- [ ] Screenshot set replaced (see `assets/ASSET_CHECKLIST.md`), alt text everywhere.
- [ ] Copy edit pass: remove "4x faster", "elite", "production-ready"; add the beta label.

**Gate G2:** every page answers "what do I do next?" and no claim contradicts the audit.

### Phase 3 — Discoverability and measurement · 2026-11-18 → 11-27

`docs/.vitepress/config.mts` head additions:

```ts
export default defineConfig({
  sitemap: { hostname: 'https://codx-junior.ai' },   // generates sitemap.xml
  head: [
    ['link', { rel: 'icon', href: '/favicon.ico' }],
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/logo.svg' }],
    ['link', { rel: 'apple-touch-icon', href: '/apple-touch-icon.png' }],
    ['link', { rel: 'canonical', href: 'https://codx-junior.ai/' }], // see note
    ['meta', { name: 'theme-color', content: '#550e57' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'codx-junior' }],
    ['meta', { property: 'og:title', content: 'codx-junior — run your whole project in one tab' }],
    ['meta', { property: 'og:description', content: 'Open-source workspace for hybrid AI + human software teams.' }],
    ['meta', { property: 'og:image', content: 'https://codx-junior.ai/og/codx-junior-og.png' }],
    ['meta', { property: 'og:image:width', content: '1200' }],
    ['meta', { property: 'og:image:height', content: '630' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:site', content: '@codxjunior' }],
  ],
})
```

> Canonical/OG tags are per-page in VitePress if you want them perfect; use
> `transformHead` with `pageData.relativePath` to map each doc to its own OG card. Start with a
> site-wide card and one per top-level section (`/features/`, `/getting-started`).

- [ ] `docs/public/robots.txt`:
      `User-agent: *\nAllow: /\nSitemap: https://codx-junior.ai/sitemap.xml`
- [ ] `docs/public/llms.txt` with the product one-liner, links to guide + features + install.
- [ ] JSON-LD `SoftwareApplication` on the home page (name, applicationCategory
      `DeveloperApplication`, operatingSystem `Linux, macOS, Windows (WSL)`, offers → free,
      license AGPL-3.0, sameAs GitHub).
- [ ] Custom `docs/404.md`: "Page not found — try the quickstart" + search box + top links.
- [ ] Analytics (D7) with a privacy note; no cookie banner needed if cookieless.
- [ ] UTM conventions from `measurement/ANALYTICS.md` applied to every outbound link.
- [ ] Newsletter capture in footer (Buttondown/Listmonk).
- [ ] Verify unfurls: LinkedIn Post Inspector, X Card Validator, Slack/Discord paste, WhatsApp.

**Gate G3:** Lighthouse mobile ≥ 90 performance, 100 accessibility, 100 SEO on home +
getting-started; OG card renders in all four unfurl tools.

### Phase 4 — Pipeline and hosting · 2026-11-20 → 11-27

`.github/workflows/docs.yml` (check on PR, deploy on main):

```yaml
name: docs
on:
  pull_request:
    paths: ["docs/**", ".github/workflows/docs.yml"]
  push:
    branches: [main]
    paths: ["docs/**", ".github/workflows/docs.yml"]
permissions:
  contents: read
  deployments: write
jobs:
  build:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: docs } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: npm, cache-dependency-path: docs/package-lock.json }
      - run: npm ci
      - run: npm run build:css          # regenerates public/custom.css
      - run: npm run docs:build
      - name: guard — no internal docs
        run: |
          if ls .vitepress/dist/features | grep -qi review; then
            echo "internal review docs published"; exit 1; fi
      - name: guard — no insecure example secrets
        run: ! grep -rn "sk-efwefwe" ../codx-junior-installer/codx-junior/.env.example
      - name: deploy
        if: github.ref == 'refs/heads/main'
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          command: pages deploy .vitepress/dist --project-name=codx-junior
```

- [ ] Cloudflare Pages project, custom domain, `www` → apex redirect, `http` → `https`.
- [ ] PR previews enabled; bot comment with the preview URL.
- [ ] Image publishing workflow replacing `docker-publish.yaml.wip`: buildx multi-arch,
      tags `vX.Y.Z` + `latest`, `docker/metadata-action`, SBOM, digest in release notes.
- [ ] Branch protection on `main`: docs build + guard must pass.
- [ ] Uptime check on `/` and `/getting-started` (UptimeRobot/Better Stack), alert to email.

**Gate G4:** a docs-only PR gets a preview URL; merging to `main` deploys in < 3 min; a
deliberately broken link fails the build.

### Phase 5 — QA and soft launch · 2026-11-30 → 12-11

- [ ] Three clean-host installs (Ubuntu 24.04, macOS arm64, WSL2) — stopwatch each, fix docs
      where they stumble, record the fastest run.
- [ ] Mobile pass on iOS Safari + Android Chrome: home, features, getting-started.
- [ ] Accessibility: keyboard nav, focus states, contrast, alt text, heading order.
- [ ] `docs/getting-started.md` copy-paste test in a fresh terminal, every command.
- [ ] Broken-link crawl of the deployed site (not just the build).
- [ ] 5 external readers (not the team) go through the install and report blockers.
- [ ] Soft launch: post the link in 3 small communities (Discord, a private beta list),
      watch session recordings/heatmaps for 48 h, fix the top 3 confusions.

**Gate G5:** 5/5 external testers reach a first chat without asking a question.

### Phase 6 — Public launch and promotion · 2027-01-12 → 01-26

Public site launch **2027-01-12**, Product Hunt **2027-01-26**. See
`launch/PRODUCT_HUNT_PLAN.md` and `content/CALENDAR.md`.

- [ ] Announcement blog post + X thread + LinkedIn post.
- [ ] Submit to directories (see `channels/PLAYBOOKS.md`).
- [ ] Show HN 1–2 weeks after PH (never the same day).
- [ ] YC application drafted in parallel; submit by 2027-02-05.

## 5. Calendar (all dates 2026 → 2027)

| Week | Dates | Milestone |
| --- | --- | --- |
| W1 | Nov 10–14 | Decisions, domain, branch merge, internal docs removed, demo form |
| W2 | Nov 17–21 | v1.3.0 images published, compose pinned, quickstart v1 |
| W3 | Nov 24–28 | Troubleshooting/operations/FAQ/license pages, OG assets, CI + hosting |
| W4 | Dec 1–5 | Content completion, screenshots, Lighthouse, guard tests |
| W5 | Dec 8–12 | **Soft launch** to small communities; external tester round |
| W6 | Dec 15–19 | Fix soft-launch findings; blog posts 1–3; changelog live |
| W7–W8 | Dec 22–Jan 4 | Freeze (holidays). Monitor only; no launches |
| W9 | Jan 5–9 | Demo instance hardened + seeded; final QA; press kit |
| W10 | Jan 12–16 | **Public site launch**; directories; newsletter #1 |
| W11 | Jan 19–23 | PH pre-launch: upcoming page, supporter list, assets final |
| W12 | Jan 26–30 | **Product Hunt launch**; Show HN follow-up |
| W13 | Feb 2–6 | Convert launch traffic; **YC X27 submit by Feb 5** |

## 6. Budget (order of magnitude)

| Item | Cost |
| --- | --- |
| Domain (`codx-junior.ai` + `.com` defensive) | ~$120/year |
| Cloudflare Pages | $0 |
| Plausible | $9/month (or self-hosted Umami $0) |
| Demo host (4 vCPU / 16 GB VPS) | $40–80/month |
| OG/social design (or in-house) | $0–500 one-off |
| Demo video (in-house Loom/QuickTime) | $0 |
| Newsletter (Buttondown) | $0–9/month |
| **Total to launch** | **< $1,000** |

## 7. Risks

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Workspaces fix slips | High | Launch copy lies | Feature-flag + docs edit (D5 fallback) |
| Images break on a user's arch (arm64) | Medium | Install fails | Multi-arch buildx + tested on Apple Silicon |
| PH traffic spikes the demo cost | Medium | Surprise bill | Read-only demo, hard token caps, rate limits |
| Internal docs ship again | Medium | Embarrassment | CI guard + release checklist |
| Domain/handle inconsistency | Low | Trust leak | One canonical domain, redirect the rest |
| Single maintainer burns out during launch | Medium | No support | Pre-written FAQ + 48 h response SLA + community helpers |
| AGPL confuses enterprise visitors | Medium | Lost leads | Plain-language license page + commercial contact |

## 8. Day-1 patch list (copy-paste ready)

```bash
# 1. Internal docs out of the public site
mkdir -p docs-internal
git mv "docs/features/workspaces-container-routing-review.md" docs-internal/
git mv "docs/features/workspaces-settings-scope-review.md" docs-internal/
printf '\n# Internal engineering notes — never built into the docs site\ndocs-internal/\n' >> .gitignore

# 2. No dead links tolerated
sed -i 's/ignoreDeadLinks: true/ignoreDeadLinks: false/' docs/.vitepress/config.mts

# 3. No insecure example keys
cd codx-junior-installer/codx-junior
sed -i 's/^LITELLM_MASTER_KEY=.*/LITELLM_MASTER_KEY="change-me"/' .env.example
sed -i 's/^LITELLM_SALT_KEY=.*/LITELLM_SALT_KEY="change-me"/' .env.example
# document: LITELLM_MASTER_KEY=$(openssl rand -hex 32) before exposing the stack

# 4. Rebuild + verify
cd ../../docs && npm run docs:build
ls .vitepress/dist/features | grep -i review && echo "FAIL" || echo "OK: no internal docs"
```

## 9. Ownership

| Role | Person | Responsibilities |
| --- | --- | --- |
| Founder | GB | Decisions, story, copy, PH, YC, partner calls |
| Engineering | TBD | Images, install path, workspaces, CI/CD |
| Designer | TBD (or founder) | OG cards, screenshots, video, PH gallery |
| Writer/editor | TBD | Copy edit, blog drafts, changelog |
| Community | TBD (or founder) | Discord/GitHub Discussions, issue triage, launch day replies |
