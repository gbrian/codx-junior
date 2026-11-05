# DSH as a Docker service behind Traefik

Run the DeepSeek Harness web UI as a single Docker container and publish it
through an existing Traefik instance with Docker labels. The DSH listener is
never published on the host; Traefik is the only client that can reach it.

The local `.env` in this workspace points at `dsh.demo.codxjunior.com`, whose
record should point at this host (`135.181.0.35`). Create that DNS record (or
change `DSH_DOMAIN` in `.env`) before expecting a browser to reach the service.

## Files

| Path | Purpose |
| --- | --- |
| `Dockerfile` | Node 22 image with `@deepseek-ai/dsh` installed globally, plus `git`, `ripgrep`, and OpenSSH for the agent's tools. |
| `docker-entrypoint.sh` | Resolves the container's concrete bind IP (DSH rejects `0.0.0.0`), then launches `dsh --profile web` with `--public-url` and `--trusted-host`. |
| `healthcheck.mjs` | Probes the listener over the container interface; an unauthenticated `401` counts as healthy. |
| `docker-compose.yml` | The service, the persistent `dsh-home` volume, the workspace bind mount, and all Traefik labels. |
| `compose.auth.yml` | Optional overlay that puts Traefik HTTP Basic auth in front of DSH. |
| `scripts/token-url.sh` | Prints the current tokenized login URL from the container logs. |
| `scripts/set-basic-auth.sh` | Adds a Basic auth bcrypt hash to `.env` for the optional overlay. |
| `.env.example` | Documented template for the local `.env`. |
| `workspace/` | Default project directory mounted at `/workspace`. |

## How access works

DSH has no user accounts and no configurable login token. Its web surface uses a
two-step exchange:

1. At startup DSH prints `dsh web: https://<DSH_DOMAIN>/?token=<random>`.
2. Opening that URL once returns `303` with `Set-Cookie: dsh-auth-<hash>...;
   Max-Age=2592000; HttpOnly; SameSite=Strict`.
3. Every later page load, API call, and WebSocket uses that signed cookie. The
   token is not needed again for that browser.

The cookie signing secret is stored in `$DSH_HOME/.credentials.yaml`, inside the
`dsh-home` volume. The process token changes on every restart, but the 30-day
cookie keeps working as long as the volume survives. Deleting the volume
invalidates every existing browser session and rotates the token.

Each browser that completes the exchange becomes the owner: DSH has no
per-user authorization. Treat the token URL and the session cookie as
credentials.

## Prerequisites

- Docker Engine with Compose v2+.
- A Traefik instance with the Docker provider enabled and an external network
  shared with the containers it routes.
- A DNS `A`/`AAAA` record for `DSH_DOMAIN` pointing at the Docker host.
- Ports 80 and 443 reachable if Traefik terminates TLS with ACME HTTP-01.
- A DeepSeek API key, either as `DEEPSEEK_API_KEY` in `.env` or entered later
  under **Settings -> Models** in the web UI.

The current host uses these values; adjust them for another installation:

| Setting | Current value |
| --- | --- |
| Traefik network | `codx-junior_default` |
| Traefik entrypoints | `web` (80) and `websecure` (443) |
| Traefik certificate resolver | `sslresolver` |
| DSH bind port | `3080` (internal only) |

## Configure

If `.env` does not exist yet:

```sh
cp .env.example .env
$EDITOR .env
```

Set at least:

- `DSH_DOMAIN` — the browser authority only, for example
  `dsh.example.com`. Do not include `https://`, a path, or `:443`. It becomes
  both the Traefik `Host()` rule and DSH's `--trusted-host`.
- `DSH_UID` / `DSH_GID` — the owner of `workspace/` and the container process.
  Use `id -u` and `id -g` from the host user who will edit the project files.
- `DEEPSEEK_API_KEY` — optional; leave blank to set the model key in the UI.
- `TRAEFIK_NETWORK`, `TRAEFIK_CERT_RESOLVER` — match the local Traefik setup.

Make the workspace writable by the container identity:

```sh
mkdir -p workspace
chown -R "$(id -u):$(id -g)" workspace
```

Keeping `DSH_UID`/`DSH_GID` equal to your host UID/GID avoids permission
problems on the bind mount. Changing them after the `dsh-home` volume already
exists requires fixing ownership of that volume, or removing it.

`workspace/` is intentionally isolated. To give the agent the current
`codx-junior` checkout instead, set `DSH_WORKSPACE=/home/codx-junior/codx-junior`
(or another host path) and keep `DSH_UID`/`DSH_GID` matching its owner. That
exposes those files to anyone who can use the UI.

## Deploy

```sh
docker compose up -d --build
docker compose ps
```

Wait for the health status to become `healthy`, then read the one-time URL:

```sh
./scripts/token-url.sh
# or
docker compose logs dsh | grep 'dsh web:'
```

Open the printed URL in a browser. It redirects to the same page without the
token and stores the session cookie, so that browser does not need the token
again. Do not bookmark the tokenized URL; bookmark `https://<DSH_DOMAIN>/`
instead.

If the API key was left blank, sign in and add it under **Settings -> Models**.
The key is then stored in the `dsh-home` volume.

### With optional Basic auth

```sh
./scripts/set-basic-auth.sh admin
docker compose -f docker-compose.yml -f compose.auth.yml up -d
```

Traefik now asks for the Basic auth credentials before forwarding any request
to DSH. The script stores a bcrypt hash in `.env` as `DSH_BASIC_AUTH_USERS`, so
the label works without mounting a file into the Traefik container. The DSH
token exchange still happens after that. To return to the plain deployment, run
`docker compose up -d` without the overlay (or `make auth-down` followed by
`make up`).

If the installation already defines a forward-auth middleware (for example
`codx-junior-auth`), chain it with the HSTS middleware instead of using the
Basic auth overlay:

```yaml
traefik.http.routers.dsh.middlewares: dsh-headers,codx-junior-auth
```

## Traefik details

The important labels in `docker-compose.yml` are:

```yaml
traefik.enable: "true"
traefik.docker.network: codx-junior_default
traefik.http.routers.dsh.rule: Host(`dsh.example.com`)
traefik.http.routers.dsh.entrypoints: websecure
traefik.http.routers.dsh.tls.certresolver: sslresolver
traefik.http.services.dsh.loadbalancer.server.port: "3080"
```

- Traefik forwards the browser's `Host` header unchanged. DSH's Host/Origin
  fence rejects every `/api` and WebSocket request whose authority is not listed
  in `--trusted-host`, so the hostname in `DSH_DOMAIN` must exactly match what
  the browser sees. Changing the Traefik rule therefore means changing
  `DSH_DOMAIN` and recreating the container.
- The port is only `expose`d, never `ports`-published. Do not add a host port
  mapping: the listener is plain HTTP and its fence is host-based.
- One container replica only. DSH keeps SQLite state and the cookie secret in
  `dsh-home`, and there is no shared-session layer for multiple replicas.
- The `web` router redirects to HTTPS; the secure router sends HSTS. Traefik
  handles ACME HTTP-01 challenges on the `web` entrypoint independently of
  that redirect.

## Operations

```sh
docker compose logs -f dsh        # startup, token URL, requests
docker compose restart dsh        # token rotates, cookies survive
docker compose down               # stop (dsh-home volume is kept)
docker compose up -d --build      # rebuild after changing DSH_VERSION
```

Upgrade DSH:

```sh
# edit DSH_VERSION in .env
docker compose build --pull
docker compose up -d
```

Back up `dsh-home` before upgrades. The volume is named
`dsh-service_dsh-home` (Compose project prefix):

```sh
docker run --rm \
  -v dsh-service_dsh-home:/data:ro \
  -v "$PWD":/backup \
  alpine tar czf /backup/dsh-home-$(date +%F).tar.gz -C /data .
```

Restore while the service is stopped, then start it again. The archive contains
the browser-cookie signing secret and any credentials stored through the UI, so
treat it as a secret.

### Token lost or session invalid

- The token is printed only once per process. Run `./scripts/token-url.sh` or
  `docker compose logs dsh | grep 'dsh web:'`.
- Existing cookies survive restarts; if a browser was signed out or the volume
  was recreated, open a fresh tokenized URL.
- A cookie minted for a different authority (for example after changing
  `DSH_DOMAIN`) is not valid for the new hostname.

## Security notes

- Anyone who obtains the tokenized URL can complete the exchange and becomes an
  owner with shell access to `/workspace` inside the container. Keep logs and
  terminal scrollback private.
- Use the Basic auth overlay, or an existing forward-auth middleware, if the
  hostname is reachable from an untrusted network.
- The container runs as a non-root user with `no-new-privileges` and all Linux
  capabilities dropped. It has no Docker socket; only the project workspace is
  bind-mounted from the host, plus the private `dsh-home` volume.
- DSH sees the Traefik leg as plain HTTP, so its session cookie is not marked
  `Secure`. The HTTP router redirects and the HTTPS router sends HSTS, but
  prefer HTTPS URLs and avoid a plain-HTTP first visit. Terminating TLS inside
  DSH would make the cookie `Secure`, but that is not this deployment's layout.
- The agent can run `git`, `ripgrep`, and arbitrary shell commands inside the
  container. Treat the workspace contents as accessible to anyone who can use
  the UI.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `401 dsh web authentication required` | No valid cookie yet. Open the tokenized URL for this exact hostname. |
| `403` on `/api` or WebSocket | `DSH_DOMAIN` does not match the `Host` Traefik forwards; fix `DSH_TRUSTED_HOSTS`/`--trusted-host`. |
| `404` from Traefik | DNS or router rule mismatch, or the container is not on `TRAEFIK_NETWORK`; check `docker compose config` and Traefik logs. |
| `502`/`503` | Container is starting or unhealthy; check `docker compose ps` and `docker compose logs dsh`. |
| TLS certificate error | DNS does not point at this host, or port 80 is not reachable for ACME; check the Traefik logs. |
| `permission denied` on `/workspace` | `DSH_UID`/`DSH_GID` do not match the owner of `workspace/`. |
| Token URL not found | DSH has not reached readiness, or the log line rotated out; `docker compose logs dsh`. |

## Why not disable the token?

DSH's launch token is generated with `randomBytes(32)` per process and is not
read from config, environment, or the credential store; there is no
`auth: false` or predefined-token setting. It is only the first-visit exchange,
and the resulting cookie is persistent, so the supported deployment is one
tokenized visit per browser plus a mounted `dsh-home`.

A blanket Traefik redirect to `?token=` does not work: DSH answers any request
carrying a valid token with a `303` to the clean URL, so the redirect loops. An
edge-side static `dsh-auth-*` cookie would have to mint DSH's internal signed
cookie and would make every visitor the owner; it is unsupported and must be
re-minted whenever the secret or DSH cookie format changes. Keep the tokenized
URL flow unless you have a specific need for zero-touch access.
