# Magnitude — Docker test harness

A self-contained folder to **build, run and test [Magnitude](https://github.com/magnitudedev/magnitude)** inside Docker, and to verify that it can download and serve a **small model that fits the machine it runs on**.

> Magnitude is an open-source inference engine that tunes its kernels on your hardware to find the fastest way to run each model. It works on Apple Silicon, NVIDIA, AMD or CPU-only machines and exposes an OpenAI-compatible API.

---

## Table of contents

1. [What this folder does](#what-this-folder-does)
2. [Folder layout](#folder-layout)
3. [Requirements](#requirements)
4. [Quick start](#quick-start)
5. [What the test does](#what-the-test-does)
6. [Choosing a model](#choosing-a-model)
7. [Hardware](#hardware)
8. [Using the API from another container or agent](#using-the-api-from-another-container-or-agent)
9. [GPU (NVIDIA)](#gpu-nvidia)
10. [Troubleshooting](#troubleshooting)
11. [Cleanup](#cleanup)
12. [References](#references)

---

## What this folder does

Instead of installing Magnitude on the host, the engine runs **inside a container**. That keeps the machine clean and makes the test reproducible.

```text
┌───────────────────────────── docker compose project: magnitude ─────────────────────────────┐
│                                                                                             │
│   service: magnitude                        service: magnitude-test  (profile: test)        │
│   ┌──────────────────────────┐              ┌──────────────────────────┐                    │
│   │ debian:12-slim           │              │ same image               │                    │
│   │  magnitude serve         │              │  magnitude serve (bg)    │                    │
│   │  :10100  ────────────────┼── host ──────┤  run-test.sh             │                    │
│   │  /home/magnitude/.magni… ├── volume ────┤  0. health               │                    │
│   └──────────────────────────┘  magnitude-  │  1. hardware             │                    │
│                                 data        │  2. catalog              │                    │
│                                             │  3. recommendations      │                    │
│                                             │  4. pull + load model    │                    │
│                                             │  5. chat completion      │                    │
│                                             └──────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

Two things to remember:

* **The server** (`magnitude`) is long-running and is what an agent or browser talks to.
* **The test** (`magnitude-test`) is a one-shot container that starts its own temporary server, downloads a small model and runs one prompt.

---

## Folder layout

| File | Purpose |
| :--- | :--- |
| `Dockerfile` | `debian:12-slim` + the Linux Magnitude `.deb` + a non-root user and the helper scripts. |
| `docker-compose.yml` | Defines the `magnitude` (server) and `magnitude-test` (one-shot test) services. |
| `docker-compose.gpu.yml` | Override that exposes NVIDIA GPUs to both services. |
| `.env.example` | All tunables; copy it to `.env`. |
| `Makefile` | Shortcuts for every common command. |
| `scripts/entrypoint.sh` | Writes `~/.magnitude/config.json` and dispatches `serve` / `test` / `<cmd>`. |
| `scripts/run-test.sh` | Starts a background server and runs the smoke test. |
| `scripts/test-model.sh` | The actual model test (hardware → recommendations → pull → load → completion). |
| `scripts/lib.sh` | Shared helpers (`resolve_magnitude`, `wait_for_health`). |
| `.gitignore` | Ignores `.env` and local data. |

---

## Requirements

| Requirement | Notes |
| :--- | :--- |
| Docker Engine + Compose v2 | The harness uses `docker compose`. |
| ~4 GB free disk | The image (desktop libs) plus a small model download. |
| Internet access (first run) | To fetch the `.deb` and to pull the model. |
| CPU-only is fine | Magnitude runs on CPU; a GPU only changes the speed and the model it recommends. |

<details>
<summary><strong>Why Debian 12 and not Alpine?</strong></summary>

Magnitude needs **glibc ≥ 2.34**. Alpine uses musl and has no Magnitude package, so the image is deliberately based on `debian:12-slim` (glibc 2.36) with a `.deb` install.

</details>

---

## Quick start

```bash
cd magnitude
cp .env.example .env          # adjust if needed (port, API key, model)

# 1. build the image (downloads and installs the Magnitude .deb)
make build

# 2. run the one-shot test: hardware → recommendations → download → prompt
make test
```

Start the persistent server (web UI + API on <http://localhost:10100>):

```bash
make up          # start in the background
make logs        # follow the logs
make down        # stop
```

<details>
<summary><strong>Same commands without make</strong></summary>

```bash
cp .env.example .env
docker compose build
docker compose run --rm magnitude-test
docker compose up -d magnitude
docker compose logs -f magnitude
docker compose down
```

</details>

---

## What the test does

`scripts/test-model.sh` performs six steps and prints a labelled section for each:

| Step | What happens | Upstream command / endpoint |
| :--- | :--- | :--- |
| 1/6 | Waits for the engine to be ready | `GET /health` |
| 2/6 | Prints the **detected hardware** | `magnitude hardware` |
| 3/6 | Waits for the hardware assessment / catalog | `magnitude catalog status` |
| 4/6 | Shows **recommendations** and picks a small model | `magnitude catalog recommendations --preference fastest` |
| 5/6 | Downloads and loads the model | `magnitude catalog pull <id>` / `magnitude models load <id>` |
| 6/6 | Sends one prompt and reports throughput | `POST /inference/v1/chat/completions` |

Example of the interesting tail of the output:

```text
=== 4/6 Model recommendations (--preference fastest) ===
    <recommendation list printed by the CLI>
    selected model: <owner/model-id>

=== 6/6 Chat completion ===

--- answer ---
An inference engine runs a trained model to turn input tokens into generated output.

--- usage ---
{"prompt_tokens":24,"completion_tokens":19,"total_tokens":43}

wall clock: 2.71s
approx. 7.01 output tokens/s

=== Done ===
    model '<owner/model-id>' was downloaded and served successfully.
```

> **First run is slow.** Downloading the model is the long part; the second run reuses the `magnitude-data` volume and jumps straight to the prompt.

---

## Choosing a model

The harness never hard-codes a model id — catalog ids change over time. It reads them from the CLI.

| Goal | What to do |
| :--- | :--- |
| Smallest / fastest model | Default: `MAGNITUDE_PREFERENCE=fastest` |
| Slightly smarter, still small | `MAGNITUDE_PREFERENCE=faster` or `balanced` |
| Force an exact model | `MAGNITUDE_MODEL=<catalog-id>` in `.env` |
| Force it for one run only | `MODEL_ID=<catalog-id> make test` |
| See everything available | `docker compose run --rm magnitude bash`, then `magnitude catalog list` |

```bash
# browse the catalog interactively
make shell
$ magnitude hardware
$ magnitude catalog list
$ magnitude catalog show "owner/model-id"
$ magnitude catalog recommendations --preference balanced --limit 10
```

---

## Hardware

Magnitude adapts to the machine it runs on, so the test asks it directly rather than assuming:

```bash
make test        # step 2/6 prints `magnitude hardware`
```

| Machine | Inference support |
| :--- | :--- |
| Linux x64 / ARM64, no GPU | CPU (system RAM) |
| Linux + NVIDIA (Ampere or newer) | CUDA — use `docker-compose.gpu.yml` |
| Linux + AMD / Vulkan GPU | Vulkan (requires the driver + Vulkan runtime in the container) |

<details>
<summary><strong>What "small model" mean on a CPU-only host?</strong></summary>

On CPU-only machines the bottleneck is memory bandwidth, so the practical choice is a **small parameter count with a low-bit quantization**. That is exactly what `--preference fastest` returns. Start there, confirm the pipeline works, and only then move to `balanced`/`smarter` models.

</details>

<details>
<summary><strong>Detecting the GPU before you start</strong></summary>

```bash
nvidia-smi        # NVIDIA driver present?
lspci | grep -i vga
ls -l /dev/dri    # AMD / Intel render nodes
```

If `nvidia-smi` works on the host, enable the GPU override below.

</details>

---

## Using the API from another container or agent

The server exposes an OpenAI-compatible API on port **10100**:

| Setting | Value (inside the compose network) | Value (from the host) |
| :--- | :--- | :--- |
| Base URL | `http://magnitude:10100/inference/v1` | `http://localhost:10100/inference/v1` |
| API key | `MAGNITUDE_API_KEY` (default `mag_local_dev_key`) | same |
| Model | the id returned by `GET /models` | same |

```bash
# list models (from the host)
curl -H "Authorization: Bearer mag_local_dev_key" \
     http://localhost:10100/inference/v1/models

# chat completion
curl http://localhost:10100/inference/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer mag_local_dev_key" \
  -d '{
        "model": "MODEL_ID",
        "messages": [{"role": "user", "content": "Say hello in one sentence."}],
        "max_tokens": 64
      }'
```

The web UI is at <http://localhost:10100> (sign in with the same key).

> The compose service name `magnitude` is added to `network.allowedHosts` by the entrypoint so requests that use it as the HTTP `Host` header are not rejected with `421 Invalid Host header`.

---

## GPU (NVIDIA)

```bash
# host prerequisites
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi

# run the harness with the GPU override
docker compose -f docker-compose.yml -f docker-compose.gpu.yml build
docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm magnitude-test
```

Then compare step 2/6 and step 6/6 with a CPU run — the same model should generate noticeably faster.

---

## Troubleshooting

| Symptom | Likely cause / fix |
| :--- | :--- |
| `ERROR: no model id could be determined automatically` | The recommendation output uses an unexpected format. Read it, then run `MODEL_ID=<id> make test`. |
| Build fails at the `.deb` download | No internet access, or `MAGNITUDE_ARCH` does not match the host (`x86_64` → `x64`, `aarch64` → `arm64`). |
| `magnitude: command not found` | The package layout differs; set `MAGNITUDE_HOME`/check `/opt`. The entrypoint already probes common paths. |
| Chromium/Electron sandbox errors on start | Add `MAGNITUDE_SERVE_ARGS="--no-sandbox"` to `.env`, or run the service with `security_opt: [seccomp=unconfined]`. |
| `401 Unauthorized` | The key in the request differs from `MAGNITUDE_API_KEY` in `.env`. |
| `421 Invalid Host header` | You reached the API through a hostname that is not in `network.allowedHosts`. |
| Container is `unhealthy` for a long time | The first model load takes a while; check `make logs`. |
| `Connection refused` on port 10100 | The server is not started yet (`make up`) or the port is already in use on the host. |
| Model download slow / stuck | Watch progress with `docker compose run --rm magnitude bash` → `magnitude models status`. |

<details>
<summary><strong>Useful diagnostics inside the container</strong></summary>

```bash
make shell
$ magnitude --version
$ magnitude status
$ magnitude hardware
$ magnitude catalog status
$ magnitude models status
$ cat ~/.magnitude/config.json
```

</details>

---

## Cleanup

```bash
make down     # stop and remove containers (models are kept in the volume)
make clean    # stop everything AND delete the downloaded models
make prune    # remove the built image
```

---

## References

* Upstream repository: <https://github.com/magnitudedev/magnitude>
* Documentation: <https://docs.magnitude.dev>
  * Linux install: <https://docs.magnitude.dev/installation/linux>
  * Hardware: <https://docs.magnitude.dev/hardware>
  * Remote server / headless: <https://docs.magnitude.dev/remote-server>
  * API endpoints: <https://docs.magnitude.dev/api/endpoints>
  * CLI reference: <https://docs.magnitude.dev/reference>
* Model list: <https://magnitude.dev/models>
