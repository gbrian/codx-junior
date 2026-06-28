# AI Development Core Services

## Overview
This domain provides comprehensive API backend logic for an advanced, AI-powered coding and knowledge workspace. It serves as the central nervous system for interactions involving artificial intelligence, managing critical workflows such as user project lifecycles, real-time chat interactions, and complex analytical tasks (like code generation and execution). The service utilizes various proprietary engines (`code_engine`, `chat_engine`) to abstract expensive AI calls and provides robust infrastructure for performance monitoring, comprehensive analytics tracking, and granular logging of all developer activities. Key functionalities include API cost modeling, token counting, authentication handling, and secure state management across multiple endpoints.

## Files in Domain
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`: Handles core AI inference execution using vLLM on CPU.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`: API initialization and routing.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`: Manages the storage mechanisms for tracking metrics and usage data.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`: Defines the structure and models used by the analytics system.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`: Logic for tracking, calculating, and managing API tokens consumed during usage.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/chat.py`: Handles the specialized API logic for real-time chat interactions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/workspaces.py`: Manages user workspace state and project organization within the system.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/code_engine.py`: Executes complex code generation, sandbox execution, and related tasks.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/chat_engine_actions.py`: Defines specific actions or workflows triggered by the chat engine.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/ai_model.py`: Contains models and abstractions related to interacting with underlying AI services.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/raw_logger.py`: Utility for standardized, low-level logging of raw AI interaction data.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/views/model.py`: Contains reusable view models or structures for API request/response handling.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/projects.py`: Handles the creation, management, and retrieval of user projects.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/logs.py`: Defines models for structured activity logging across the platform.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/logs.py`: Primary API endpoint logic for viewing and managing audit logs.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_index.py`: Specialized handlers or APIs for knowledge base (Wiki) interactions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/analytics.py`: Core endpoint logic for submitting and querying usage analytics.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/analytics.py`: Orchestration layer for calculating and reporting usage metrics.

## Dependencies
None specified.

## Used By
None specified.

## Entry Points
The following files are primary entry points that expose the domain's critical functionality:

*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`: The main deployment point for AI inference services.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`: Initializes and exposes the core API routing definitions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`: Entry point for analytics data persistence layer interactions.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`: Exposes the structure and instantiation of core analytic models.
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`: Entry point for token calculation and usage tracking logic, crucial for billing.