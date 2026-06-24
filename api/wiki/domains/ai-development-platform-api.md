# AI Development Platform API

## Overview

The AI Development Platform API serves as the central and comprehensive backend infrastructure for advanced intelligent coding, natural language interaction, and knowledge management within the codx-junior project suite. This domain acts as an abstraction layer, coordinating complex features such as chat interactions, code execution, and deployment of various Large Language Models (LLMs).

Beyond basic functionality, a core pillar of this API is its robust analytics framework. It manages intricate business logic required for tracking usage metrics, accurately counting tokens consumed per request, facilitating cost prediction, and maintaining comprehensive project workflow histories. This structure makes it ideal for any application requiring managed AI interactions and detailed resource consumption tracking.

**Key Capabilities:**
*   **Intelligent Interaction:** Facilitates stateful chat experiences and knowledge retrieval (Wiki).
*   **Code Intelligence:** Provides sandboxed code execution capabilities and rich development workflows.
*   **Model Abstraction:** Manages diverse LLM integrations via a unified API layer (`ai_model.py`, `vllm_cpu_ai`).
*   **Financial/Operational Tracking:** Implements detailed analytics tools for token counting, usage metering, and cost estimation.

## Files in Domain

The files within this domain can be categorized by their primary functionality: Core APIs, AI/LLM Management, Analytics & Cost Control, Engines, and Knowledge Bases.

### 📁 API Endpoints and Core Logic
These modules define the public-facing interface for various platform features.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/chat.py`: Handles chat session management and logic.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/workspaces.py`: Manages user project workspaces and state persistence.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/projects.py`: Handles project lifecycle and workflow logic.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/logs.py`: General API logging utilities.

### 🧠 AI Model Management & Interaction
These modules are responsible for interfacing with and running the actual large language models.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`: Implementation layer utilizing vLLM for API calls (specifically CPU optimized).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/ai_model.py`: Abstraction class for interacting with various AI backends.

### ⚙️ Engines and Specialized Processing
These modules handle complex, structured tasks beyond simple API calls.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/code_engine.py`: Executes code snippets securely and manages execution results.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/chat_engine_actions.py`: Contains specific actions and tool implementations for advanced chat flows (e.g., calling project APIs).

### 📊 Analytics, Logging, and Monitoring
The suite of modules dedicated to tracking usage, costs, and system events.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/analytics.py`: The main entry point for analytics logic.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`: Handles persistence and storage of usage data.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`: Defines the core data model structures for analytics records.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`: Dedicated logic for accurate token counting and cost prediction.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/raw_logger.py`: Low-level raw logging dedicated to AI interactions.
*   `/home/codx-junior-projects/codx-junior/api/codx-junior/api/raw_log_reader.py`: Tool for reading and analyzing raw AI usage logs.

### 📚 Knowledge Base & Utilities
These modules support internal knowledge retrieval and history management.
*   `/home/codx-junior-projects/codx-junior/wiki/wiki_index.py`: Manages the index and retrieval of structured knowledge base articles (Wiki).
*   `/home/codx-junior-projects/codx-junior/model/logs.py`: Handles general persistent logging records related to the model or system state.

## Dependencies

This domain does not declare any specific hard file dependencies on other local source files listed in the scope. However, its functional complexity implies dependence on:
*   A scalable database backend for persistence (Analytics storage).
*   External LLM APIs/Services (via `vllm_cpu_ai.py` and `ai_model.py`).

## Used By

This domain is expected to be consumed by the frontend application layer, any client-facing API gateway, or other microservices that require intelligent backend computation and feature orchestration.

## Entry Points

These files serve as the primary initialization points for internal systems or external consumers wishing to interact with this platform's core capabilities.

*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`: Used to initiate and configure the vLLM AI backend connection, abstracting model communication.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/analytics.py`: The central entry point for initializing all analytics tracking logic (token counting, usage recording) that must occur before every API call execution.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`: Serves as the main package constructor, making the core APIs discoverable and usable across the rest of the application.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`: Used programmatically to establish connections and methods for persistent storage operations vital for analytics continuity.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`: The initialization point for defining the core data structures used throughout the analytics system, ensuring consistent data handling.