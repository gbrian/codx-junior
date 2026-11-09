# Go-live checklist

Print this. Tick every box in order. Do not skip §2.

---

## 1. Pre-flight (T-1 day)

Content and truth

- [ ] `docs/.vitepress/config.mts` has `ignoreDeadLinks: false`
- [ ] No file under `docs/` is an internal review/engineering note
- [ ] Demo page has a working form or the hero CTA is removed
- [ ] Every feature page carries a status badge (`stable` / `beta` / `experimental`)
- [ ] Version string matches the released tag (`v1.3.0`) in nav/footer/changelog
- [ ] All screenshots are from the **released** build, not from a dev branch
- [ ] No claim contradicts `research/PLATFORM_REVIEW.md` (no workspaces, no "4x", no "production ready")
- [ ] `LICENSE.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` exist
- [ ] Contact addresses work: `join@`, `hello@`, `security@` (send a test email)

Build

```bash
cd docs
npm ci
npm run build:css
npm run docs:build
```

- [ ] Build exits 0
- [ ] `dist/index.html` contains `og:image` and `twitter:card`
- [ ] `dist/sitemap.xml` exists and lists every page
- [ ] `dist/robots.txt` exists and references the sitemap
- [ ] `dist/404.html` exists and is branded
- [ ] `ls dist/features | grep -i review` → empty
- [ ] `du -sh dist` ≤ 4 MB (excluding videos)

Links

```bash
python3 - <<'PY'
import re, pathlib, urllib.parse
root = pathlib.Path('docs'); have = set()
for p in root.rglob('*.md'):
    if 'node_modules' in str(p) or '.codx' in str(p): continue
    rel = p.relative_to(root).as_posix()
    have.add('/' + rel[:-3]); have.add('/' + rel[:-9] if rel.endswith('index.md') else '/x')
bad = []
for p in root.rglob('*.md'):
    if 'node_modules' in str(p) or '.codx' in str(p): continue
    for m in re.finditer(r'\]\((/(?!images|only_icon|spelling)[^)#?\s]*)(#[^)\s]*)?\)', p.read_text(errors='ignore')):
        link = urllib.parse.unquote(m.group(1)).rstrip('/')
        if link and link not in have and not (root/'public'/link.lstrip('/')).exists():
            bad.append((p.as_posix(), link))
print(bad or "OK: 0 broken internal links")
PY
```

- [ ] 0 broken internal links
- [ ] 0 references to `localhost:5173` in deployed copy
- [ ] All external links open (spot-check GitHub, docs, email)

Assets

- [ ] `og/codx-junior-og.png` is exactly 1200×630 and < 300 KB
- [ ] favicon.ico + 32/180/192/512 PNGs present
- [ ] OG image loads at `https://<domain>/og/codx-junior-og.png`
- [ ] Hero video (if any) has a poster image and captions

Infra

- [ ] DNS: apex `A/AAAA` or CNAME correct; `www` CNAME → apex
- [ ] TLS certificate issued and auto-renewing
- [ ] `http://` → `https://` redirect (301) works
- [ ] `www.` → apex redirect (301) works
- [ ] Security headers set: `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy`, HSTS (after TLS is stable)
- [ ] Cache policy: HTML no-cache/short, `/assets/*` immutable long cache
- [ ] Uptime monitor on `/` and `/getting-started`
- [ ] Analytics script loaded once, no console errors

## 2. Deploy

```bash
git checkout main && git pull
git tag -a v1.3.0 -m "codx-junior v1.3.0 — first public website"
git push origin main --tags
```

- [ ] CI green: build, guard tests, deploy
- [ ] Deployment URL recorded in the launch channel
- [ ] Previous deployment ID recorded for rollback

## 3. Post-deploy verification (within 15 minutes)

```bash
D=https://codx-junior.ai
for p in / /getting-started /features/ /features/computer-use /demo /404.html /sitemap.xml /robots.txt /og/codx-junior-og.png; do
  printf "%-40s %s\n" "$p" "$(curl -s -o /dev/null -w '%{http_code} %{time_total}s' "$D$p")"
done
curl -sI "$D" | grep -iE "strict-transport|content-type|referrer-policy"
curl -s "$D" | grep -o '<meta property="og:[^>]*>' | head
```

- [ ] All routes return 200 (404.html returns 404 — expected)
- [ ] Home < 1.5 s TTFB from your region
- [ ] LinkedIn Post Inspector: title, description, image correct
- [ ] X Card Validator: `summary_large_image` renders
- [ ] Slack/Discord/WhatsApp paste: card renders, no broken image
- [ ] Google Rich Results test: `SoftwareApplication` parsed
- [ ] Mobile Safari + Chrome: nav, sidebar, code blocks scroll correctly
- [ ] "Edit this page" link points to the `main` branch
- [ ] Search box returns results for "workspaces", "milvus", "ollama"
- [ ] Install command on `/getting-started` works when pasted into a fresh shell

## 4. Rollback

- [ ] Cloudflare Pages → Deployments → previous deployment → **Rollback** (or
      `wrangler pages deployment rollback`), verified once in staging.
- [ ] If DNS is the problem: revert the record, TTL was set to 300 s before launch.
- [ ] Announce rollback in `#launch` with the cause and ETA; do not delete the post.
- [ ] Post-mortem within 48 h: what failed, what test would have caught it.

## 5. Launch-day extras

- [ ] Status line on the site if a known issue is live ("workspaces are beta — see roadmap")
- [ ] Demo instance health-checked at T-1 h and T+2 h
- [ ] Support inbox monitored every 30 min for the first 8 h
- [ ] GitHub issues labelled `launch` and triaged within 24 h
- [ ] Analytics dashboard open on a second screen
- [ ] A pre-written reply for the top 10 expected questions (see `content/COPY_BANK.md`)

## 6. Sign-off

| Check | Owner | Time | Result |
| --- | --- | --- | --- |
| Content truth | | | |
| Build + links | | | |
| DNS/TLS/headers | | | |
| Unfurls + analytics | | | |
| Install verified | | | |
| Rollback verified | | | |
