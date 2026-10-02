# Getting started

This page shows how to self-host codx-junior with Docker Compose. The engine is free and open source. If you would rather not run it yourself, see [Self-hosted or managed](/managed).

## Requirements

* A Linux server or workstation with **Docker** and **Docker Compose**.
* Enough resources for the stack: Milvus, the API and, if you run models locally, LocalAI. 4 CPUs and 16 GB of RAM is a comfortable start; local models need more.
* An API key for an OpenAI-compatible provider, or a local model server (LocalAI, Ollama, vLLM).
* Optionally, a domain name pointing to the server if you want HTTPS.

## 1. Clone the repository

```sh
git clone https://github.com/gbrian/codx-junior.git
cd codx-junior/codx-junior-installer/codx-junior
```

## 2. Configure the environment

Copy the example file and edit it:

```sh
cp .env.example .env
```

```ini
USER_ID=911
GROUP_ID=911

# Used by the LiteLLM model manager, if you enable it
LITELLM_MASTER_KEY="sk-change-me"
LITELLM_SALT_KEY="sk-change-me"

# Domain Traefik answers on. Use localhost for a local install.
CODX_JUNIOR_DOMAIN="localhost"

# Email used for Let's Encrypt certificates
ACME_EMAIL="you@example.com"
```

See [Configuration](/configuration) for the full list of variables.

## 3. Build or pull the images

The stack uses the `codxjunior/codx-junior:api`, `codxjunior/codx-junior:client` and `codxjunior/codx-junior:debian` images. Build them from source with:

```sh
bash build.sh
```

## 4. Start codx-junior

```sh
docker compose up -d
```

This starts:

| Service | Purpose |
| --- | --- |
| `traefik-codx-junior` | Reverse proxy on ports 80 and 443 |
| `codx-junior-client` | Web application |
| `codx-junior-api` | API |
| `codx-junior-api-background` | Background jobs (indexing, watchers, mentions) |
| `milvus-codx-junior` | Vector store for knowledge |
| `localai-codx-junior` | Optional local models |

Projects are stored on the host under `/home/codx-junior-projects`, and global settings are kept in the `codx-junior` Docker volume.

## 5. Open the app

Go to `http://localhost` (or `https://<CODX_JUNIOR_DOMAIN>`). Continue with the [Initial setup](/initial-setup).

## Troubleshooting

* **The page loads but says "API disconnected!"**: check `docker logs codx-junior-api`.
* **Knowledge search returns nothing**: make sure `milvus-codx-junior` is healthy and that an embeddings model is configured.
* **Workspaces do not start**: the API needs access to `/var/run/docker.sock`, which the compose file mounts by default.
* **API reference**: the OpenAPI documentation is served at `/api/docs`.
