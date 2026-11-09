# Quickstart rewrite (draft for `docs/getting-started.md`)

Replace the current page with this. Every command must be copy-pasted into a fresh terminal on
a clean host before publishing — the timings are placeholders until then.

**Success criterion:** a person who has never seen the repo reaches a first agent chat in
**≤ 15 minutes**, measured with a stopwatch, and knows what to do if it fails.

> **Depends on PUBLISH_PLAN Phase 1:** this draft assumes `docker-compose.release.yaml` exists
> (pull-only, pinned image tags) and that `v1.3.0` images are published. Do not publish it
> before both are true. On macOS, `sed -i` needs an empty backup argument (`sed -i '' …`).

---

# Install codx-junior

codx-junior is a self-hosted stack: a web app, an API, a background worker, Traefik and Milvus,
wrapped in one Docker Compose file. This page takes you from zero to a first agent chat.

> **Active beta.** The core loop — board, agents, diffs, review, budgets — is used daily.
> Workspaces (dev containers) are behind a flag while the runtime is finished. See the
> [roadmap](/roadmap).

## Before you start (5 minutes)

| Requirement | Minimum | Comfortable |
| --- | --- | --- |
| OS | Linux, macOS, or Windows with WSL2 | Ubuntu 24.04 |
| Docker | 24+ with Compose v2 | latest |
| CPU | 2 cores | 4 cores |
| RAM | 8 GB (API-hosted models) | 16 GB |
| Disk | 20 GB free | 50 GB |
| Models | One OpenAI-compatible API key | + local models (Ollama/LocalAI) |

* Ports **80** and **443** must be free.
* For HTTPS you need a domain pointing at the machine. For a local test, `localhost` works over
  plain HTTP.
* Local models need much more RAM/VRAM; start with a hosted API key.

Check Docker:

```bash
docker --version          # >= 24
docker compose version    # >= v2
```

## 1. Get the stack (1 minute)

```bash
mkdir codx-junior && cd codx-junior
curl -fsSLO https://raw.githubusercontent.com/gbrian/codx-junior/main/codx-junior-installer/codx-junior/docker-compose.release.yaml
curl -fsSLO https://raw.githubusercontent.com/gbrian/codx-junior/main/codx-junior-installer/codx-junior/.env.example
```

> **Contributors** who want to build from source: follow [Build from source](/contributing#build)
> instead — it takes 20+ minutes and needs more disk.

## 2. Configure (2 minutes)

```bash
mv .env.example .env
# Generate real secrets instead of the placeholders
sed -i "s|^LITELLM_MASTER_KEY=.*|LITELLM_MASTER_KEY=\"sk-$(openssl rand -hex 24)\"|" .env
sed -i "s|^LITELLM_SALT_KEY=.*|LITELLM_SALT_KEY=\"sk-$(openssl rand -hex 24)\"|" .env
```

Set these in `.env`:

| Variable | What to put |
| --- | --- |
| `CODX_JUNIOR_DOMAIN` | `localhost` for a local test, or your domain |
| `ACME_EMAIL` | your email, used only for Let's Encrypt |
| `USER_ID` / `GROUP_ID` | `id -u` / `id -g` from the host |

::: warning Before exposing this to the internet
The example file ships **placeholder keys**. Change them (commands above), keep `.env` out of
git, and put the stack behind HTTPS before using it on a public network.
:::

## 3. Pull and start (3–5 minutes)

```bash
docker compose -f docker-compose.release.yaml pull
docker compose -f docker-compose.release.yaml up -d
docker compose -f docker-compose.release.yaml ps
```

Expected services: `traefik-codx-junior`, `codx-junior-client`, `codx-junior-api`,
`codx-junior-api-background`, `milvus-codx-junior`.

Watch the API until it is ready:

```bash
docker compose -f docker-compose.release.yaml logs -f codx-junior-api
# wait for "Application startup complete" and the port 19980 line, then Ctrl+C
```

## 4. Open the app and log in (1 minute)

Open `http://localhost` (or `https://<CODX_JUNIOR_DOMAIN>`).

Log in as **admin**. The first password you type becomes the admin password. Change it in
**Settings → User account**.

## 5. Add a model (2 minutes)

**Settings → Global settings → AI Models**

1. Add a provider: name, OpenAI-compatible base URL, API key. OpenAI, Ollama, LiteLLM, vLLM and
   LocalAI all work.
2. Add the models you want.
3. Pick a default for each purpose — at minimum **LLM** and **Embeddings**.

Wait, embeddings? Yes: without an embeddings model the knowledge index is empty, and agents
will answer without looking at your code. See [AI providers](/features/ai-providers).

## 6. Add a project and index it (3 minutes)

From the projects menu, paste a Git URL or a folder path on the server, then press `+`.

Then **Settings → Knowledge settings → Start indexing**. A small repository indexes in a minute
or two; watch the progress.

## 7. First agent chat (1 minute)

Open **Home**, pick the project, pick a developer profile and a model, and ask something that
requires reading the code:

> Find where the API authenticates requests, and explain the flow in five bullet points.

If you get a grounded answer with file references, the install is complete.

## Verify the install

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/          # 200
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/api/docs  # 200
docker compose -f docker-compose.release.yaml ps --format '{{.Name}} {{.Status}}'
```

- [ ] All five services `Up` (Milvus may show `healthy`)
- [ ] Login works
- [ ] A provider and an embeddings model are configured
- [ ] A project is indexed
- [ ] An agent answer cites files from the repo

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Page loads, "API disconnected!" | API not up or Traefik cannot reach it | `docker compose logs codx-junior-api`; check ports 80/443 |
| `bind: address already in use` | something else owns 80/443 | stop it, or change the published ports |
| Milvus unhealthy | low memory or corrupted volume | `docker compose logs milvus-codx-junior`; 16 GB recommended |
| Knowledge search returns nothing | no embeddings model, or indexing never ran | configure embeddings; re-index |
| Agent answers without reading code | project not indexed / wrong project selected | check knowledge status |
| Login loop or 401 | cookies blocked, or clock skew | use the same host name; check system time |
| Permission denied on project files | wrong `USER_ID`/`GROUP_ID` | fix `.env`, recreate the containers |
| Workspaces do not start | known beta limitation | see [roadmap](/roadmap); not required for the core loop |
| Out of disk | Milvus + images + models | `docker system df`, prune unused images |

Logs, in order of usefulness:

```bash
docker compose logs -f codx-junior-api
docker compose logs -f codx-junior-api-background
docker compose logs -f traefik-codx-junior
```

Still stuck? Open an issue with the output of `docker compose ps` and the API log tail:
<https://github.com/gbrian/codx-junior/issues>.

## Next steps

* [Initial setup](/initial-setup) — users, permissions, wallets, workspaces.
* [Features](/features/) — what each part does.
* [Operations](/operations) — backup, upgrade, uninstall.
* [Configuration](/configuration) — every environment variable.
