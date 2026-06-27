# AI Interaction & Analytics Backend

## Overview
This module cluster provides the critical backend layer responsible for abstracting, managing, and analyzing interactions with advanced generative Artificial Intelligence models (e.g., LLMs). It serves as the central API gateway for features like conversational chat functionality and code completion across various workspaces and projects.

Functionally, it handles communication with underlying model endpoints (such as VLLM), facilitating complex business logic that utilizes AI capabilities. A core component of this domain is its robust analytics suite, which meticulously tracks usage metrics, analyzes token consumption, manages API costs, and provides overall performance monitoring necessary for billing, optimization, and accountability.

This backend acts as a sophisticated wrapper, insulating the core application logic from the complexities and heterogeneity of external model APIs while providing standardized methods for rate limiting, logging, and data processing. Key concerns include:
*   **AI Integration & Abstraction:** Providing unified interfaces for diverse AI models.
*   **Analytics & Cost Management:** Detailed tracking of token usage and API calls ($ cost prediction).
*   **Workflow Logic:** Managing the execution flow for complex tasks (e.g., code generation within a specific project context, or multi-turn chat sessions).

## Files in Domain
The following files constitute the core logic and components of the AI Interaction & Analytics Backend:

```bash
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py             # Primary vLLM interaction layer for CPU deployment.
/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py         # API package initialization.
/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py     # Persistent storage for usage metrics.
/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py       # Data structure definition for analytics models and schemas.
/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py # Logic for accurately counting input and output tokens.
/home/codx-junior-projects/codx-junior/api/codx/junior/api/chat.py              # Core API logic for chat interactions.
/home/codx-junior-projects/codx-junior/api/codx/junior/api/workspaces.py       # Logic related to grouping and managing AI use within workspaces.
/home/codx-junior-projects/codx-junior/api/codx/junior/engine/code_engine.py   # Executes code generation or completion tasks using AI models.
/home/codx-junior-projects/codx-junior/api/codx/junior/engine/chat_engine_actions.py # Defines specific actions and logic for chat interactions within the engine.
/home/codx-junior-projects/codx-junior/api/codx/junior/model/ai_model.py       # Abstraction layer representing various AI model configurations and access points.
/home/codx-junior-projects/codx-junior/api/codx/junior/ai/raw_logger.py        # Low-level logging utility for raw AI interaction logging.
/home/codx-junior-projects/codx-junior/api/codx/junior/api/raw_log_reader.py    # Utility to process and read unstructured raw AI logs.
/home/codx-junior-projects/codx-junior/api/codx/junior/api/analytics.py         # Main API endpoint for initiating analytics logging and querying usage data.
/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/analytics.py   # Core service layer implementing analytic calculations (e.g., aggregation, cost prediction).
```

## Dependencies
*No explicit dependencies were specified using the provided metadata structure.*

(Note: Functionally, this module depends heavily on core data models (`codx-junior/model/*`) and general utility libraries for storage access.)

## Used By
*No consumers were specified using the provided metadata structure.*

(Note: This backend serves as a foundational service. It is expected to be integrated by higher-level application services, such as a main API router or a core workspace management module, which request AI features for execution.)

## Entry Points
These files are configured as primary access points, representing key operational components of the domain:

*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`: The active entry point for running AI via the vLLM engine on CPU infrastructure.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`: General API initialization access.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`: Entry point for data persistence related to usage metrics.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`: Defines the structure and usage patterns of analytics reporting.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`: Dedicated entry point for calculating token consumption in real time.