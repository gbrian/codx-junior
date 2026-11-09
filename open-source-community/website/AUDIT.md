# Website readiness audit

**Target:** publish the VitePress site in `docs/` so a stranger can install and test
codx-junior.
**Audited:** 2026-11-09 · branch `v1.3-demo-site` · commit `34a4da11`
**Result:** *buildable, not publishable.* 8 P0 items block a public launch.

---

## 0. How this was audited

```bash
# build the site exactly as CI would
cd docs && npx vitepress build          # ✅ 32 pages, 7.99 s, no errors

# internal link integrity on the source markdown
# (script: resolve every /path link against docs/*.md)
# → 0 broken internal links

# built-output link integrity
# → 0 broken internal links (only "/" resolves to index.html)

# SEO surface of the built home page
grep -o '<meta[^>]*>' docs/.vitepress/dist/index.html
# → charset, viewport, description, generator, theme-color. No og:, no twitter:.

# publication state
curl -s -o /dev/null -w '%{http_code}' https://codx-junior.ai     # 000 (no DNS)
curl -s -o /dev/null -w '%{http_code}' https://codx-junior.com    # 000 (no DNS)
curl -s -o /dev/null -w '%{http_code}' https://gbrian.github.io/codx-junior/  # 404

# published images
curl -s https://hub.docker.com/v2/repositories/codxjunior/codx-junior/tags
# api/debian/client/dind — last_updated 2026-02-16 … 2026-01-17
```

## 1. Scorecard

| Dimension | Grade | Note |
| --- | --- | --- |
| Build reliability | A | Clean build, no warnings that matter |
| Content coverage | B− | Every feature documented; install path and lifecycle docs missing |
| Content safety | **F** | Two internal engineering reviews are published |
| Accuracy vs shipped product | **D** | Docs describe Nov 2026 features; Docker Hub images are from Feb 2026 |
| Install path | **D** | Works only via long source build; `docker compose pull` gives a stale product |
| Discoverability (SEO) | **F** | No sitemap, robots, canonical, OG/Twitter, structured data |
| Sharing (social unfurls) | **F** | No `og:image`; no 1200×630 asset exists |
| Accessibility | C | No alt-text standard; light-only theme; emoji-as-icon on home |
| Performance | C− | 17 MB dist, 14 MB of PNG screenshots, no WebP/AVIF |
| Legal/community | **F** | No CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, CHANGELOG, issue templates |
| Deploy automation | **F** | No workflow; `.github/workflows/docker-publish.yaml.wip` is disabled by its extension |
| Analytics | **F** | No measurement at all |

## 2. P0 — must fix before the site is public

### P0-1 · There is no site
`codx-junior.ai`, `codx-junior.com` and `gbrian.github.io/codx-junior` all fail. GitHub
Pages is not configured (`GET /repos/gbrian/codx-junior/pages` → 404). The only workflow is
`docker-publish.yaml.wip` is never executed (the `.wip` extension disables it) and is pinned to
the old `v1.2-find-a-mantainer` branch.

**Fix:** choose host + domain (PUBLISH_PLAN D1/D2), add deploy workflow, DNS, TLS.

### P0-2 · The default branch does not describe the product
`origin/main` is **52 commits behind** `v1.3-demo-site` and does not contain
`computer-use.md`, `browser-use.md`, `dsh-sync.md`, `company` docs, or the Nov 2026 README.
Publishing from `main` today ships a site for a nine-month-old product.

**Fix:** merge to `main`, tag `v1.3.0`, publish from `main` only.

### P0-3 · Published images are stale and unpinned
Docker Hub `codxjunior/codx-junior:{api,client,debian}` last updated **2026-02-16**.
`getting-started.md` tells users to build or pull; pulling gets a product without the
features the docs describe. There is no `vX.Y.Z` tag to pin and no changelog.

**Fix:** build/push versioned multi-arch images, pin them in compose, add `CHANGELOG.md`,
and make `docker compose pull` the documented default.

### P0-4 · Workspaces are advertised and broken
See `research/PLATFORM_REVIEW.md` §3. `POST /api/workspaces` calls a non-existent method
(`api/codx/junior/api/workspaces.py:232`), and the client calls `/start`, `/stop`, `/status`,
`/logs`, `/generate-files`, `/templates` that the router never defines
(`client/src/api/modules/workspaces.js:110-159`). The landing page, README and
`features/workspaces.md` all sell it.

**Fix:** fix or feature-flag, and edit `docs/features/workspaces.md` + home page to match.

### P0-5 · Internal engineering reviews are published
Built and searchable in the public site:

* `docs/features/workspaces-container-routing-review.md` → `features/workspaces-container-routing-review.html`
* `docs/features/workspaces-settings-scope-review.md` → `features/workspaces-settings-scope-review.html`

They contain sentences like *"Workspace creation returns 500 on every call"*, *"the Traefik
auth middleware is a stub"*, *"proxied apps are effectively public"*. This is an unforced
error on a marketing site and a direct hit to investor confidence.

**Fix:** move to `docs-internal/` (not built), or delete after extracting the decisions into
engineering docs. Add a build guard: fail if any file under `docs/` matches
`*-review.md` or starts with an internal-status banner.

### P0-6 · The demo CTA is dead
`docs/demo.md` renders `<RegisterForm />`, but no such component is registered —
`docs/.vitepress/theme/index.ts` only exports `DefaultTheme`. The hero's third action
("Try the demo") lands on a page with a broken form and no demo instance.

**Fix (pick one):**
* **A. Hosted demo:** seeded read-only project, public credentials, nightly reset, cost cap.
  Highest conversion, ~5–8 days of infra work + ongoing abuse risk.
* **B. Request-a-demo:** Tally/Google Form + Cal.com link, 24 h response SLA. ~1 hour.
* **C. Guided local demo:** `docker compose -f demo.yaml up` with a seeded repo + script.
  ~2 days, no hosting cost.
* **D.** Remove the CTA and point to the quickstart. 5 minutes.

Recommend **B now, A before Product Hunt** (see PUBLISH_PLAN D4).

### P0-7 · `ignoreDeadLinks: true` hides rot
`docs/.vitepress/config.mts:10`. Links are currently clean, so this can be flipped to `false`
and enforced in CI before drift starts.

### P0-8 · Secrets in the example environment
`codx-junior-installer/codx-junior/.env.example` ships
`LITELLM_MASTER_KEY="sk-efwefwe-hwdwqfew!"` and `ACME_EMAIL="mail@mail.com"`. Nothing in
`getting-started.md` tells a user to change them before exposing the stack, and `localhost`
plus Let's Encrypt is a confusing default.

**Fix:** generate random keys in the quickstart (`openssl rand -hex 32`), add a "before you
expose this to the internet" checklist, and make the docs say plainly that the demo defaults
are not secure.

## 3. P1 — fix in the same release

| # | Item | Evidence | Fix |
| --- | --- | --- | --- |
| P1-1 | No sitemap | `dist/` has no `sitemap.xml` | `sitemap: { hostname: 'https://<domain>' }` |
| P1-2 | No robots.txt | `dist/robots.txt` missing | `public/robots.txt` with sitemap line |
| P1-3 | No social meta | 0 `og:`/`twitter:` tags in built HTML | `head` entries + generated 1200×630 cards |
| P1-4 | No canonical | no `<link rel=canonical>` | set `base`/`hostname` consistently |
| P1-5 | No analytics | — | Plausible/Umami, cookieless |
| P1-6 | No structured data | — | `SoftwareApplication` JSON-LD on home |
| P1-7 | No version shown | — | "v1.3.0 · Active beta" in nav/footer |
| P1-8 | No changelog page | — | `/changelog` fed from GitHub Releases |
| P1-9 | No troubleshooting page | `getting-started.md` has 4 bullet points | dedicated `/troubleshooting` with logs, ports, common errors |
| P1-10 | No upgrade/backup/restore | — | `/operations` page: volumes, pg/milvus backup, upgrade path |
| P1-11 | No AGPL FAQ | — | `/license` page: internal use, SaaS, commercial licensing |
| P1-12 | No hardware sizing | "4 CPUs / 16 GB" single line | table per scenario (local models vs API, per project) |
| P1-13 | No security policy / contributing / CoC | `ls` at repo root | `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` |
| P1-14 | No issue/PR templates | `.github/` has only `workflows/` | issue forms, PR template, Discussions on |
| P1-15 | `docs/docker-compose.yaml` is wrong | maps `19000:19000` but `vitepress dev` serves 5173 and the volume points `./docs` from inside `docs/` | fix or delete (it is not the deploy path) |
| P1-16 | Generated CSS is committed and manual | `docs/public/custom.css` (71 KB) | run `build:css` in CI before build; do not hand-edit |
| P1-17 | Internal workspace metadata in the repo | 17 tracked files under `docs/.codx/` (project.json, tasks, profiles) | gitignore + remove from repo |
| P1-18 | README says `npm run docs:dev` with no root package.json | repo root has no `package.json` | `cd docs && npm run docs:dev` |
| P1-19 | GitHub metadata is off | description "💪🦾 Hi, I'm codx-junior!…", homepage → dead `codx-junior.com`, 3 topics | rewrite description, homepage → new site, topics: `ai-agents, developer-tools, self-hosted, kanban, rag, llm, fastapi, vue` |
| P1-20 | 14 MB of PNGs | `docs/public/images` 14 MB; `codx-junior-desktop.png` 1916×1005 | WebP/AVIF, max 1600 px wide, lazy loading, target < 3 MB total |
| P1-21 | No alt text standard | images use bare `<img>` in `index.md` | alt text on every image |
| P1-22 | Light theme only | `custom.css` defines only `:root` brand colors | verify dark mode or pin the site to light |
| P1-23 | No 404 experience | default VitePress 404 | custom `404.md` with search + quickstart links |
| P1-24 | No newsletter capture | — | footer signup (Buttondown/Listmonk) |
| P1-25 | No `llms.txt` | — | add for AI crawlers/assistants |

## 4. P2 — after launch

* Docs versioning (`/v1.3/`, `/latest/`) once there is a second release.
* i18n: `es` first (founder market), then `pt-BR`.
* Search analytics (what people fail to find) → content backlog.
* RSS for `/changelog` and `/blog`.
* Docs preview deployments per PR with a comment bot.
* Lighthouse CI budget in the pipeline.
* Video embeds with privacy-friendly player; transcripts for a11y.

## 5. What happens if we publish today

A Product Hunt visitor lands on a good-looking hero, clicks **Try the demo**, and gets a dead
form. They read *Getting started*, `git clone`, wait 20+ minutes for three Docker builds (or
pull a February image), log in and see a product missing most of the advertised features.
If they click **Workspaces**, they get a 500. If they search the docs, they find an internal
review explaining that the auth middleware is a stub and workspace creation is broken.

That is the entire launch, in one paragraph. Fix P0-1 → P0-8 before spending a dollar or an
hour on promotion.

## 6. Re-audit command block (run before every launch)

```bash
cd docs
npx vitepress build
test -f .vitepress/dist/sitemap.xml && echo "sitemap ok"
test -f .vitepress/dist/robots.txt && echo "robots ok"
grep -q 'og:image' .vitepress/dist/index.html && echo "og ok"
ls .vitepress/dist/features | grep -i review && echo "!! internal docs published"
python3 - <<'PY'   # 0 broken internal links
# (script in website/GO_LIVE_CHECKLIST.md §4)
PY
curl -s -o /dev/null -w '%{http_code}\n' https://<domain>/
```
