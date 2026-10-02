# GuideModels - Lightweight Project Resource Finder

## Overview

**GuideModels** is a Python-based microservice that uses small, efficient language models (smol models) to serve as intelligent project resource finders. Each model instance is pre-loaded with a fixed project guide document, enabling fast, context-aware question answering about project resources, structure, and documentation — without the overhead of large LLMs.

The core idea is simple: **load once, query forever**. The guide document is processed and its KV cache state is persisted to disk, making subsequent queries blazingly fast even on CPU-only hardware.

---

## Key Features

- 🧠 **Smol model focused** — designed for small GGUF-format models via `llama-cpp-python`
- 📄 **Fixed guide context** — each instance holds a project's guide document in memory
- 💾 **KV cache persistence** — model state is saved to disk after first load, avoiding reprocessing
- 🐳 **Docker-first** — fully containerized, ready to run anywhere
- ⚡ **CPU optimized** — auto-detects available CPU threads for optimal performance
- 🔄 **Guide hot-reload** — update the guide document at runtime with `reload_guide()`

---

## Project Structure

```
/home/codx-junior-projects/codx-junior
├── codx/
│   └── junior/
│       ├── globals.py              # Global constants (e.g., CODX_JUNIOR_MODELS_PATH)
│       ├── guide_model.py          # ProjectResourceFinder core class
│       └── __init__.py
├── models/                         # GGUF model files and cached states
├── guides/                         # Project guide documents (.md, .txt)
├── tests/
│   └── test_guide_model.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## Requirements

- Python **3.10+**
- Docker & Docker Compose
- A GGUF-format smol model (e.g., [Qwen2.5-0.5B](https://huggingface.co/), [SmolLM](https://huggingface.co/HuggingFaceTB/SmolLM-135M-Instruct-GGUF))

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-org/codx-junior.git
cd codx-junior
```

### 2. Add your model

Place your `.gguf` model file inside the `models/` directory:

```bash
models/
└── smollm-135m-instruct.Q4_K_M.gguf
```

### 3. Configure environment

```bash
cp .env.example .env
```

```ini /home/codx-junior-projects/codx-junior/.env.example
# Path where GGUF models are stored (mapped via Docker volume)
CODX_JUNIOR_MODELS_PATH=/app/models

# Default model filename
CODX_JUNIOR_MODEL_NAME=smollm-135m-instruct.Q4_K_M.gguf

# Context window size
CODX_JUNIOR_N_CTX=4096
```

### 4. Build and run with Docker

```bash
docker-compose up --build
```

---

## Docker Setup

```dockerfile /home/codx-junior-projects/codx-junior/Dockerfile
FROM python:3.11-slim

# Install build dependencies for llama-cpp-python
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories for models and guides
RUN mkdir -p /app/models /app/guides

CMD ["python", "-m", "codx.junior"]
```

```yaml /home/codx-junior-projects/codx-junior/docker-compose.yml
version: "3.9"

services:
  guide-model:
    build: .
    container_name: codx-junior-guide
    env_file: .env
    volumes:
      - ./models:/app/models       # Persist model files and cached states
      - ./guides:/app/guides       # Mount guide documents
    restart: unless-stopped
```

---

## Usage Example

```python /home/codx-junior-projects/codx-junior/codx/junior/guide_model.py
from codx.junior.guide_model import ProjectResourceFinder

# Initialize with your smol model
finder = ProjectResourceFinder(model_name="smollm-135m-instruct.Q4_K_M.gguf")

# Load your project guide (cached to disk automatically)
with open("guides/my_project_guide.md", "r") as f:
    guide = f.read()

finder.load_guide(guide)

# Ask questions about your project
answer = finder.ask("Where is the authentication module located?")
print(answer)
# >> "The authentication module is located in src/auth/auth_service.py"

# Reload guide when documentation changes
finder.reload_guide(updated_guide_text)
```

---

## How It Works

```
┌─────────────────────────────────────────────┐
│              First Run                       │
│                                             │
│  Guide Text ──► Tokenize ──► KV Cache       │
│                                  │           │
│                             Save to Disk     │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│           Subsequent Runs                   │
│                                             │
│  Load State from Disk ──► KV Cache Ready    │
│                                  │           │
│  Question ──► Append to Prompt ──► Answer   │
└─────────────────────────────────────────────┘
```

1. On first load, the guide document is tokenized and processed by the model
2. The resulting KV cache state is serialized and saved as a `.state` file alongside the model
3. On subsequent starts, the state is restored from disk — **skipping reprocessing entirely**
4. Queries are answered by appending the question to the guide context and sampling the model

---

## Dependencies

```txt /home/codx-junior-projects/codx-junior/requirements.txt
llama-cpp-python==0.2.90
python-dotenv==1.0.1
```

> **Note:** `llama-cpp-python` will compile from source during the Docker build. This is expected and ensures CPU-optimized binaries.

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `CODX_JUNIOR_MODELS_PATH` | `/app/models` | Directory where `.gguf` models and `.state` files are stored |
| `CODX_JUNIOR_MODEL_NAME` | *(required)* | Filename of the GGUF model to load |
| `CODX_JUNIOR_N_CTX` | `4096` | Context window size in tokens |

---

## Recommended Models

| Model | Size | Notes |
|---|---|---|
| SmolLM-135M-Instruct | ~90MB | Ultra-fast, best for simple lookups |
| Qwen2.5-0.5B-Instruct | ~400MB | Better reasoning, still CPU-friendly |
| Phi-3-mini-4k-instruct | ~2.2GB | High quality, moderate CPU load |

---

## License

MIT © codx-junior contributors