# AI Backend Service Core

## Overview
The AI Backend Service Core is a comprehensive, high-fidelity backend framework designed to power sophisticated, AI-driven applications. This module provides structured APIs and deep integration points for managing complex operational workflows, including advanced chat interfaces, customizable project management lifecycles (workspaces), and dynamic knowledge base implementations (wikis).

At its heart, the core manages multiple levels of intelligence: from utilizing dedicated `vllm` endpoints for efficient AI model serving to orchestrating interactions between specialized internal engines.

A key architectural focus is observability. The module includes sophisticated, structured logging mechanisms (`raw_logger`, logging services) and a robust analytics pipeline (tracking token usage, request metrics, and service performance). This ensures deep, granular insight into system interactions, making it ideal for billing prediction, cost management, and operational monitoring of demanding AI workloads.

**Key Features:**
*   **LLM Abstraction:** Handles interaction with various Large Language Models via abstraction layers (`ai_model`, `vllm`).
*   **Workflow Management:** Provides APIs for managing project states and persistent chat sessions.
*   **Code Execution & Reasoning:** Includes a dedicated code engine for sandboxed execution and reasoning capabilities.
*   **Deep Observability:** Dedicated modules for analytics tracking, logging (structured logs), and token usage counting for accurate cost modeling.

## Files in Domain

The following files constitute the implementation and logic of the AI Backend Service Core:

**Core API & Logic:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`: Initialization file for the core API namespace.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/chat.py`: Logic handling chat-related APIs and endpoints.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/workspaces.py`: API wrapper and logic for managing user workspaces (projects).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/projects.py`: Manages project-specific API endpoints and data persistence.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/analytics.py`: Primary aggregation point for analytics services.

**AI Engine & Model Integration:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`: Implementation utilizing vLLM for running AI models on CPU resources.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/ai_model.py`: Abstraction layer for interacting with various AI model providers (LLMs).
*   `/home/codx-junior-projects/codx-junior/engine/code_engine.py`: Dedicated engine for safe, sandboxed code execution and computational tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/chat_engine_actions.py`: Actions and logic specific to enhancing chat interactions using the core engines.

**Observability & Logging:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`: Handles the persisting storage of analytics data (metrics, usage).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`: Defines the data model used for storing and querying utilization statistics.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`: Dedicated module to accurately count input/output tokens for pricing models.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/raw_logger.py`: Low-level utility for capturing raw, structured logging events.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/raw_log_reader.py`: Utility for reading and parsing complex raw log formats.

**Knowledge & Data Management:**
*   `/home/codx-junior-projects/codx-junior/wiki/wiki_index.py`: Handles the indexing and retrieval of knowledge base documents (wikis).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/logs.py`: Defines the data model for structured system logs.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/views/model.py`: Contains view-related models used across different API endpoints (e.g., listing chats, projects).

## Dependencies
The provided manifest does not list external or internal file dependencies (`<depends_on_files>`). This implies that the framework relies on core Python standard libraries and established database connectors for persistence layers, abstracting service coupling within the module itself. Inter-module communication is managed through well-defined object models (like `analytics/model.py` or `model/logs.py`).

## Used By
The provided manifest does not list modules that consume or depend on this core domain (`<used_by_files>`). This suggests the AI Backend Service Core acts as a foundational, infrastructural layer utilized by other applications within the platform ecosystem (e.g., a user-facing frontend API Gateway or a dedicated billing service).

## Entry Points
Entry points define accessible utility classes and models that are crucial for initializing components, especially for external services or testing environments.

*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`: The primary access point for vLLM-based AI inference.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`: General entry point for the API wrapper.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`: Entry point for managing analytics data storage interactions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`: Entry point defining the structure and state of tracked metrics/models used in analytics.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`: Dedicated entry point for token counting logic, critical for cost API prediction.