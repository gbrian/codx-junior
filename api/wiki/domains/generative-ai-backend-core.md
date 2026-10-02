# Generative AI Backend Core

## Overview
This domain represents the core backend API layer responsible for integrating advanced generative AI functionalities. It provides a cohesive system for managing user workflows related to artificial intelligence development and usage. Key areas of functionality include managing conceptual **workspaces** and specific **projects**, facilitating conversational chat interactions, and providing a dedicated code engine execution environment.

Crucially, the domain incorporates comprehensive **analytics** tracking, allowing it to monitor resource consumption (like token counts) and predict potential API costs. The architecture is designed to abstract AI model interaction (e.g., through `ai_model.py`) while maintaining robust logging using raw log readers and storage mechanisms. This setup ensures that every AI request, whether a chat message or code completion call, is managed, tracked, and billed efficiently.

**Key Capabilities:**
*   **AI Functionality:** Chat handling (`chat.py`), Code Completion/Generation.
*   **Resource Management:** Tracking workspaces and projects for modular organization.
*   **Billing & Analytics:** Detailed logging of usage, token counting, and implementing cost prediction models.
*   **Execution:** Hosting a dedicated code execution engine (`code_engine.py`).

## Files in Domain
The following files constitute the operational logic, data handling, and API endpoints for this domain:

**API Endpoints & Core Logic:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py` (Core API initialization)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/chat.py` (Chat workflow handler)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/workspaces.py` (Workspace management endpoints)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/projects.py` (Project lifecycle management)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/logs.py` (Generic logging service endpoint)

**AI & Model Interaction:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py` (Implementation for AI model serving, potentially using vLLM in CPU mode)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/ai_model.py` (Abstract representation and wrapper for various generative models)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/code_engine.py` (Code execution sandbox and engine logic)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/engine/chat_engine_actions.py` (Actions executed within the chat workflow)

**Analytics & Logging:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/analytics.py` (Core analytics calculation and logic)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py` (Persistent storage layer for usage metrics and data)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py` (Data modeling structures for analytics)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py` (Utilities specifically designed to count input/output tokens for billing)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/raw_logger.py` (Low-level logging utility)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/raw_log_reader.py` (Utility for reading raw log data)

**Domain Specific Utilities:**
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/views/model.py` (Potential view models or request data structuring)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/model/logs.py` (Data structures for centralized log tracking)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/wiki/wiki_index.py` (Wiki or documentation index, suggesting content generation capabilities)

## Dependencies
This domain layer is highly self-contained but relies heavily on internal packages for functionality:

*   **External Dependencies:** *None specified in the local files.*
*   **Internal Logic Dependency:** Requires robust implementations of data modeling and storage services to manage usage metrics and API state. Features like cost prediction (`analytics/model.py`) are critical dependencies built upon accurate logging.
*   **Core Functions Utilized:** Authentication, Authorization, Asynchronous Programming (implied by the nature of AI processing).

## Used By
No consuming modules or downstream systems were specified in `used_by_files`. This indicates that this domain is intended to be a robust service layer, potentially consumed directly by an upstream API Gateway or front-end application layer for all advanced generative functionalities.

## Entry Points
The following files serve as primary entry points into the core functionality of the Generative AI Backend:

*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py` (Primary AI model interface)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/analytics.py` (Core KPI and usage calculation entry point)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py` (Domain initialization and API routing)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py` (Access point for persistent metric storage)
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py` (Data model instantiation for analytics)