# AI Intelligence Core Engine

## Overview
The AI Intelligence Core Engine is a critical backend domain that provides the foundational logic layer for an advanced, AI-powered development platform. Its primary responsibility is managing complex user workflows involving interaction with various Large Language Models (LLMs) and specialized execution environments.

This engine handles the entire lifecycle of AI interactions, from initiating chat sessions to running executed code via dedicated code engines. Crucially, it incorporates robust utilities for system health and financial tracking. Core functionalities include specialized API wrappers for LLM communication (`ai_model.py`), comprehensive resource management (particularly token counting), detailed logging mechanisms (logging raw logs and managing historical records), and advanced usage analytics to support billing and performance monitoring.

It serves as the central orchestration point, coordinating inputs from user requests while abstracting away the complexity of interacting with multiple external AI services.

## Files in Domain
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
None identified.

## Used By
None identified.

## Entry Points
These modules are exposed as core entry points, making their functionality available to other services or components within the platform.

*   `/home/codx-junior-projects/codx-junior/api/codx/junior/ai/vllm_cpu_ai.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/api/__init__.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/storage.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/model.py`
*   `/home/codx-junior-projects/codx-junior/api/codx/junior/analytics/token_counter.py`