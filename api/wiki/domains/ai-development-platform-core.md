# AI Development Platform Core

## Overview

The AI Development Platform Core serves as the central backend API for a comprehensive Generative Artificial Intelligence (GenAI) development environment. This domain is critical infrastructure, managing and coordinating multiple core functionalities necessary for advanced ML workflows, including interaction with various models, execution of code, user state management, and detailed tracking of resource usage.

Its primary responsibilities include:
1. **LLM Interaction:** Providing structured endpoints for chatting and model-based inferences (leveraging technologies like vLLM).
2. **Code Execution Engine:** Orchestrating code execution logic through dedicated engines (`code_engine`).
3. **Project Management:** Managing user workspaces, projects, and chat session contexts (`workspaces`, `api/chat.py`).
4. **Monitoring & Billing:** Implementing advanced analytics modules to track AI usage, count tokens, log interactions, and manage cost prediction metrics for billing purposes.
5. **Logging Pipeline:** Handling detailed logging of raw API calls, model inputs, and outputs across the entire system lifecycle.

This core module acts as an abstraction layer, ensuring modularity, scalability, and robust observability for all GenAI-related activities within the platform.

## Files in Domain

The files within this domain manage the operational logic, state, and specialized processing modules required for AI workflow management:

*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`: Primary module for integrating and handling interactions with large language models (LLMs) using vLLM, specifically targeting CPU optimization.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`: Initializes the core API package and defines base API endpoints.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`: Handles persistent storage mechanisms for collected usage metrics and analytics data.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`: Contains the data structure and logic definition for storing models and related performance metrics within the analytics system.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`: Dedicated module for accurately counting tokens used during AI inference, crucial for cost calculation.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/chat.py`: Manages the state and logic flow for multi-turn chat sessions and conversations.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/workspaces.py`: Provides functionality to create, retrieve, and manage user workspaces and project contexts.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/code_engine.py`: Executes complex code snippets provided by users or LLMs in a controlled environment (sandboxing).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/chat_engine_actions.py`: Contains specialized logic and actions for enhancing the chat engine's capabilities (e.g., tool use, action calls).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/ai_model.py`: Defines the interface and handling logic for connecting and interacting with various underlying AI models.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/raw_logger.py`: Captures raw, unprocessed logs of system interactions for deep analysis and auditing.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/logs.py`: Manages the recording and retrieval of high-level API usage logs.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/projects.py`: Core endpoints for creating, managing, and listing user projects within the platform.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/logs.py`: Defines log data models and management functions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/analytics.py`: Houses the main entry point for executing analytical tasks and generating reports (e.g., cost prediction).
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/views/model.py`: Contains view-related models, likely used in the presentation layer interactions with the API core.

## Dependencies

Given its role as a central orchestration and logic domain, this module has high dependencies on foundational services:

*   **Database Services:** Required for persistent storage of user state (workspaces, projects), usage metrics (`storage.py`), and logging data (`model/logs.py`).
*   **Execution Environment:** Depends heavily on isolated environments to safely execute code (managed by `code_engine`).
*   **AI Infrastructure:** Relies on external or internal services providing LLM inference capabilities (e.g., vLLM backend).
*   **Time/Utility Services:** Utilizes standard date, time, and utility libraries for logging timestamps and calculating elapsed times.

## Used By

Due to its fundamental nature, this domain serves several critical areas of the platform:

*   **Frontend/Client Applications (GraphQL/REST):** All presentation layers accessing AI functionalities (chat, code execution, project views) consume endpoints exposed by this core.
*   **Monitoring Services:** System health monitoring and usage dashboards query the analytical modules (`analytics/*`).
*   **Billing Service:** The cost prediction logic heavily depends on `token_counter.py` and logging data to calculate accurate user billing aggregates.

## Entry Points

The following files represent primary, top-level entry points for interacting with core domain functionalities:

*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`: The main entry point for initiating LLM interactions and resource allocation via vLLM.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`: Provides the standard namespace access for API consumers, bundling all core endpoints together.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`: Entry point for data persistence and retrieval of analytics metrics.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`: Entry point for initializing or validating analytical models used for reporting.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`: Dedicated entry point service for calculating token consumption across different model inputs and outputs.