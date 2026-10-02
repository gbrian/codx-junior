# AI Service & Analytics Engine
## Overview

The AI Service & Analytics Engine is a comprehensive backend module cluster designed to standardize and streamline interactions with advanced Artificial Intelligence models. It serves as the primary API gateway for integrating complex generative functionalities, including conversational chat, sophisticated code generation capabilities, and structured project workflow execution.

This domain implements a powerful abstraction layer that manages model communication details, ensuring modularity regardless of the underlying AI provider or implementation (e.g., using vLLM). Critically, it provides robust, granular analytics features essential for production-grade APIs. These analytics include detailed logging components (tracking all requests and interactions), comprehensive usage tracking, and specific cost management functionalities such as token counting, allowing developers to accurately monitor API performance and predict operational costs.

**Key Functions:**
*   **AI Abstraction:** Providing a unified interface (`ai_model.py`, `vllm_cpu_ai.py`) for diverse AI models.
*   **Core APIs:** Handling chat sessions and managing complex project workspaces/logic retrieval.
*   **Analytics & Billing:** Implementing detailed logging systems (raw logs, structured logs) and advanced token counting (`token_counter.py`, `storage.py`).
*   **Workflow Management:** Powering execution logic through dedicated engines (`code_engine.py`, `chat_engine_actions.py`) to facilitate structured workflows.

## Files in Domain

The following files constitute the AI Service & Analytics Engine module:

*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/chat.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/workspaces.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/code_engine.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/chat_engine_actions.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/ai_model.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/raw_logger.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/views/model.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/raw_log_reader.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/projects.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/logs.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/logs.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_index.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/analytics.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/analytics.py`

## Dependencies

No formal dependencies are specified for this domain cluster.

## Used By

No files are listed as using components from the AI Service & Analytics Engine.

## Entry Points

The following paths serve as primary entry points or initialization modules for this service:

*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`