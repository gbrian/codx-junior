# Standalone wiki

This folder is also a deployable documentation website with a local AI
assistant.

## Build and run

```bash
# from the generated wiki folder
docker compose up --build
# open http://localhost:8080
```

Set the local OpenAI-compatible endpoint before starting:

```bash
WIKI_AI_BASE_URL=http://host.docker.internal:11434/v1 \
WIKI_AI_API_KEY=ollama \
WIKI_AI_MODEL=qwen2.5:7b \
docker compose up --build
```

Ollama bound to `127.0.0.1` on the host is reachable through
`host.docker.internal`; for other providers use their `/v1` base URL.

## Without Docker

```bash
npm install
npm run docs:build
pip install -r requirements.txt
WIKI_ROOT=. WIKI_DIST=.vitepress/dist uvicorn server:app --port 8080
```

## Endpoints

- `GET /api/health` — server and model status.
- `GET /api/site` — generated docs manifest.
- `GET /api/page?path=...` — one wiki page.
- `POST /api/assistant` — `{question, page, history}` → AI answer + citations.

The assistant reads the generated `docs.json` and markdown pages directly; it
does not need a running codx-junior instance.
