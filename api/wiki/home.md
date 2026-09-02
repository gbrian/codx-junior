# Codx Junior API - Complete Reference Guide

Welcome to the Codx Junior API documentation. This wiki serves as your comprehensive reference for understanding the architecture, components, and functionality of the CODX API system.

## Project Overview

Codx Junior API is a sophisticated backend system that combines FastAPI for robust HTTP handling with real-time Socket.IO communication, comprehensive knowledge management, and intelligent agent orchestration. The system empowers developers with AI-driven development assistance capabilities, managing projects, sessions, and complex operations with seamless integration across multiple specialized agents and tools.

## Core Architecture

### Application Infrastructure

**App Module**: The FastAPI foundation that handles HTTP requests, configures middleware, manages real-time communication through Socket.IO, and orchestrates background task execution for asynchronous operations.

**Engine Module**: The operational backbone responsible for project creation, session management, and high-level business logic that powers all features exposed through the application layer. The Engine coordinates critical operations including analytics tracking, session recording, and token usage monitoring to ensure comprehensive observability across all chat interactions. The Engine Module implements systematic issue management with structured error tracking and analysis capabilities to identify root causes, prevent silent failures, and manage cascading effects across system operations through comprehensive error handling and failure prevention mechanisms.

**Database and Data Storage**: Persistent data management with intelligent database routing and configuration supporting comprehensive application requirements.

**Security and Authentication**: Implements GitHub OAuth integration, user management, and authentication protocols ensuring secure access across the platform.

**Session Management**: Handles the complete session lifecycle, channel communication, and state management for coordinated multi-user operations.

## AI and Intelligent Agents

The system features multiple specialized agents, each optimized for specific operational domains:

### Agent Capabilities

**Base Agent**: Foundation providing core agent functionality and integration patterns for all specialized agent implementations.

**DevOps Agent**: Manages infrastructure operations, deployment tasks, and operational workflows.

**Git Issues Agent**: Handles GitHub integration, issue tracking, and version control coordination.

**SmolAgent**: A streamlined, async-first agent engineered for efficient iterative tool execution with sophisticated modern architecture. SmolAgent represents a refined approach to agent orchestration prioritizing clarity, performance, and production-readiness through:

- **Async-Only Design**: Purpose-built for asynchronous operations with no legacy synchronous code paths, ensuring efficient resource utilization and responsive feedback through iterative loops.
- **Safety First**: Comprehensive error handling with graceful degradation ensuring system reliability. All exceptions during tool execution are caught and handled gracefully as error strings, with explicit exception types tracked for root cause analysis. Non-fatal issues are logged appropriately to aid diagnostics while maintaining continued operation.
- **Streaming Architecture**: Full response accumulation with progressive delivery throughout the entire request lifecycle, enabling real-time feedback while maintaining complete response state with crash-safe persistence guarantees.
- **Sophisticated Tool Organization**: Global, chat-scoped, and profile-specific tools are dynamically filtered and organized based on execution context and permissions through explicit scope metadata.
- **Session Context Injection**: Session context is intelligently injected into tool parameters, enabling tools to access and operate within proper execution context without explicit parameter passing.
- **Robust Tool Result Handling**: Comprehensive normalization of tool outputs with intelligent truncation to 256 characters for context efficiency while preserving full results internally. Tool results are exclusively used for iterative tool execution and never included in final user responses, ensuring clean separation between internal processing and user-facing content.
- **Tool Result Caching**: Caches results per conversation by function name and parameters, with comprehensive cache statistics tracking cache hits, misses, and hit rate metrics for observability. Cached results bypass loop guard checks entirely, enabling efficient iteration without consuming protection budget.
- **Loop Protection**: LoopGuard prevents infinite iteration loops through three protection mechanisms—model-based limits, provider-based limits, and fallback limits—with intelligent violation behavior and priority-ordered resolution ensuring predictable loop termination. Cached tool calls bypass limit enforcement entirely, enabling efficient reuse without protection overhead.
- **Cancellation Support**: Flexible cancellation mechanisms including pre-stream abort before streaming begins with immediate token cleanup and zero response delivery, and mid-stream abort during active streaming with exact-once guarantee preventing duplicate token consumption.
- **Event Emission**: Comprehensive event system emitting lifecycle, LLM, and tool events with detailed payloads for complete observability and system integration.
- **Analytics Tracking**: Built-in analytics recording token usage, tool execution logging, cache statistics, and session context with resilient graceful degradation patterns ensuring analytics failures never cascade into core service delivery.
- **Production-Ready Design**: Engineered as a practical, ready-to-use tool with clear initialization patterns and straightforward integration for developers.

### SmolAgent Core Architecture

**Conversation Flow**: SmolAgent orchestrates message processing and tool invocation through a systematic multi-phase pipeline progressing through initialization, message processing, iterative tool execution, response streaming, completion handling, event emission, and recovery and cleanup phases with careful attention to crash-safety and state management throughout.

**Tool Management**: SmolAgent provides sophisticated tool organization across multiple scope levels:
- **Global Tools** — Available across all contexts and conversations
- **Chat-Scoped Tools** — Limited to specific chat contexts with explicit scope metadata
- **Profile-Specific Tools** — Available only within user profiles with access control enforcement

Tools are dynamically filtered based on execution context and permissions, with tool definitions managed through a modular structure containing specification, settings, and callable references.

**Tool Execution Patterns**: SmolAgent executes tools with comprehensive error handling, intelligently parses arguments from LLM responses, normalizes results with intelligent truncation to 256 characters for context efficiency, and manages both single-response and dual-response tool patterns. Tool execution is fully cached by function name and parameters.

**Dual-Response Tools**: SmolAgent distinguishes between single-response tools returning simple values and dual-response tools implementing the `ToolResponse` model. The ToolResponse model enables tools to deliver tailored outputs to different audiences:
- **user_content** — User-facing output optimized for clarity and actionability
- **llm_feedback** — Technical context and detailed information optimized for iterative decision-making

**Response Accumulation Strategy**: Responses are accumulated progressively throughout the chat lifecycle with explicit separation between user-facing output and tool execution content. Tool results are exclusively used for iterative decision-making and never included in final user responses, ensuring clean separation between internal processing and user-facing content.

**System Instructions**: SmolAgent applies hardcoded file handling rules for specific file patterns, automatically managing binary files and system metadata. These rules ensure consistent handling of environment configurations, version control metadata, and compiled artifacts across all operations.

**Event Emission System**: Comprehensive event emission provides complete observability through lifecycle events (RUN_START, RUN_END, RUN_ERROR, RUN_CANCELLED), tool events (capturing tool invocation and execution context), and LLM events (documenting model interactions). Events include detailed payloads with execution context, parsed arguments, result previews, and processing metadata enabling external monitoring and integration.

**RuntimeContext**: The `AgentRunContext` serves as the unified runtime state container for SmolAgent execution, managing accumulated response content, tool execution results, event tracking, loop guard state, and cancellation signals throughout execution.

**Cancellation Mechanisms**: SmolAgent supports flexible cancellation enabling responsive user interactions through pre-stream cancellation (abort before streaming begins with immediate token cleanup), mid-stream cancellation (gracefully terminate during active streaming with exact-once guarantee), and token-based identification for precise client-side operation termination.

## Knowledge and Models

**Knowledge Processing**: Comprehensive system featuring code splitting, semantic analysis, document enrichment, keyword extraction, and AI model integration for building project-specific knowledge bases. The knowledge system is built on the **Knowledge Milvus** foundation, which provides core document management, semantic search capabilities, and knowledge base orchestration through a structured seven-stage document processing pipeline with Milvus as the underlying vector database.

**Knowledge Milvus Base**: The foundational knowledge management component implementing a sophisticated document lifecycle and comprehensive seven-stage processing pipeline designed to transform raw source code and documentation into semantically rich, queryable knowledge assets:

### Core Functionality

**Loading Operations**: Initialize and load documents into the knowledge base with comprehensive source tracking and change detection capabilities. The system supports both individual document loading with automatic change detection and repository-level synchronization for bulk updates.

**Reloading and Updates**: Refresh document content and metadata with incremental update mechanisms supporting efficient knowledge base maintenance without complete regeneration.

**Enrichment Fields**: AI-powered document enhancement through multiple metadata layers including summaries for concise content overviews, keywords for semantic topic tags, categories for hierarchical classification, and content graphs for relationship mapping between documents and concepts.

**Training Data Generation**: Optional fine-tuning pair creation enabling model optimization and custom model development based on project-specific knowledge patterns.

**Indexing Pipeline**: Systematic seven-stage workflow transforming raw documents into queryable knowledge:
1. **Source Management** — Document ingestion with change detection
2. **Indexing** — Document organization and storage
3. **Document Enrichment** — AI-powered metadata generation and semantic analysis
4. **Search Integration** — Dual-mode semantic and lexical search capabilities
5. **Project Summarization** — Dynamic project-level intelligence generation

**Project Summary Management**: Dynamic and incremental project summarization providing comprehensive project documentation and LLM context with support for optional training dataset generation. The system uses AI-powered merging strategies for incremental updates, enabling efficient handling of evolving project structures.

**Search Capabilities**: Dual-mode search combining semantic and lexical patterns for comprehensive retrieval with advanced ranking, filtering, and source deduplication.

**Progress Callback System**: Event-based monitoring providing real-time visibility into knowledge base operations with detailed processing insights capturing enrichment milestones and operational stages.

**Database Integration**: Complete lifecycle management for knowledge base maintenance including reset operations, cleanup of deleted documents, and refresh of update timestamps with Milvus vector database capabilities.

**Status and Monitoring**: Comprehensive status tracking and indexing observability providing clear insight into knowledge base operations and processing progress.

**Pydantic Data Models**: Comprehensive, professionally organized model definitions spanning 50+ data structures across multiple functional domains providing a foundation for all data structures and configurations throughout the platform. Models are organized into logical categories including communication models, board and column models, knowledge management models, provider configuration models, development and automation models, UI and navigation models, user models, AI models, project configuration models, system configuration models, plugin system models, and agent and OAuth models.

**AI Models and Provider Configuration**: The system supports seamless integration with multiple AI providers through dedicated configuration models including built-in provider support with OLLAMA_PROVIDER and default embeddings for resource-efficient local deployment, provider-specific settings for OpenAI, Anthropic, and Mistral with customizable parameters, configurable embedding models for semantic analysis and knowledge retrieval, and flexible provider selection enabling optimal performance across different deployment scenarios.

**Model Configuration**: System-wide configuration through GlobalSettings which manages AI provider selection, embedding configuration, user access controls, feature flags, and API keys across all model categories. Settings are logically organized into domains with clearly defined subsections. Global instructions are loaded fresh from GlobalSettings on each chat to ensure consistency across operations.

## Profile Management

**Profile Manager**: Comprehensive system for managing user profiles and profile-related configurations with sophisticated profile discovery, operations, and lifecycle management across the platform.

### Core Components

**Initialization**: The ProfileManager establishes multiple paths for profile discovery across the system:
1. **Project profiles** — Located within `project_path/.codx/profiles/` with highest priority
2. **Base profiles** — Located within the system base profiles directory with secondary priority
3. **External provider profiles** — Profiles from external provider integrations with fallback access

**Profile Discovery and Listing**: Profiles are discovered through a hierarchical three-tier priority system:
- **Project Profiles** — Highest priority, profiles within specific project directories enabling project-specific customization
- **Base Profiles** — Secondary priority, system and default profiles available across the platform
- **External Provider Profiles** — Fallback access for profiles from external providers

The `list_profiles()` method retrieves profiles from the current project context, while `list_all_profiles()` returns profiles from all configured sources for comprehensive discovery.

**Hierarchical Profile Lookup**: The system implements a sophisticated four-level lookup hierarchy ensuring optimal profile resolution:
1. **Project-level profiles** — Project-specific customizations with highest precedence
2. **Parent project profiles** — Inherited configurations from parent projects
3. **CODX Junior project level** — System-wide profiles as fallback
4. **External provider profiles** — External integrations as final fallback

**Content Processing**: The `get_profile_with_content()` method handles complete profile retrieval with content parsing and template resolution. Profile content supports template variables with explicit regex pattern syntax: `{{variable_name}}` for dynamic content substitution. Undefined variables preserve their original `{{var}}` syntax, enabling graceful handling of missing context.

**Template Resolution**: Template variables are resolved lazily through lambda functions in the execution context. This approach enables efficient processing of profile content with deferred evaluation until context becomes available.

**Profile File Structure**: Profiles are organized as dual-file pairs where `.profile` files contain JSON metadata and configuration, while `.md.profile` files contain associated markdown content and documentation. This separation enables efficient metadata queries alongside rich content storage.

**Profile Context Variables**: Profile metadata includes essential context variables for LLM integration: `project_path` and `project_name`, enabling seamless integration into AI processing workflows.

**Profile Matching**: Intelligent profile identification logic enables flexible profile discovery based on criteria and requirements.

**Profile Operations**: The system provides comprehensive CRUD operations:
- **Loading**: Retrieve specific profiles by reference with full content parsing and context variable resolution
- **Saving**: Persist profile configurations with automatic content deduplication and exclusion from JSON metadata
- **Deleting**: Remove profiles with complete lifecycle management
- **Bulk Operations**: Process multiple profiles simultaneously for efficiency

**Profile Inheritance**: Profiles support inheritance across projects, enabling configuration reuse and centralized management while maintaining project-specific customizations.

**Linked Profile Management**: Specialized management of profiles linked across project boundaries with sophisticated filtering and file-based organization for efficient profile discovery and access control.

**Graceful Degradation**: The system supports minimal valid profiles that contain essential metadata even when full configuration is unavailable, ensuring operational continuity through error handling with graceful degradation.

**Deduplication**: The system intelligently manages linked profiles with sophisticated deduplication logic, preventing duplicate profile processing while maintaining access to all unique configurations.

**Tree Generation**: Profiles support tree generation for visual structure representation with disabled file output by default and configurable filtering for efficient exploration.

## Project Tools and Utilities

The **Project Tools** module provides essential utility functions for file management, AI operations, and project-level interactions within the CODX Junior framework, serving as a comprehensive bridge between the AI system and project resources.

### Core Functions

**AI Management**: Initialize and return AI instances configured with project settings and user context through integrated configuration management.

**Code Processing**: Process and format code to ensure it follows project standards, generating properly formatted markdown code blocks with syntax highlighting and file path annotations.

**File Path Resolution**: Convert relative or absolute file paths into absolute project paths with comprehensive validation and recursive glob search for flexible file discovery within project boundaries.

### File Operations

**File Reading**: Access project files with comprehensive error documentation and graceful handling of missing resources. Automatically detects file extensions, handles UTF-8 encoding transparently, and returns content in structured markdown code blocks with language specification and file path metadata.

**File Writing**: Write and create files within project structures with complete validation and UTF-8 encoding support. Security features include path boundary validation preventing unauthorized file access with automatic parent directory creation.

**File Searching**: Search project knowledge bases for documents matching query strings with optional AI-powered content filtering, automatic result deduplication by source file, and graceful handling of missing resources.

### Additional Capabilities

**Project Structure**: Provides utilities for exploring and understanding the organization of a project's files and folders. Returns a tree-like ASCII representation featuring visual file indicators, optional metadata display, and configurable maximum folder depth traversal.

### Error Handling and Security

All functions implement explicit exception handling with comprehensive documentation of error scenarios. Path validation prevents access to files outside the intended project scope, and write operations include comprehensive security measures with path boundary enforcement.

## Tools and Utilities

The platform provides a flexible tool ecosystem organized across multiple scope levels, enabling precise tool availability and security. Tools follow a modular architecture pattern designed to maximize flexibility, maintain backward compatibility, and preserve operational context across interactions.

### Tool Architecture and Design

**Centralized Aggregation System**: The tools module serves as a centralized aggregation point for all tool implementations, organizing them into a cohesive ecosystem while maintaining clean separation between tool definitions, configurations, and execution logic.

**Three-Level Scoping**: Tools are organized at global, chat-level, and profile-specific scopes, providing flexible tool availability while maintaining security boundaries. Tools are dynamically filtered based on scope metadata via explicit scope values:
- **Global Tools**: Available across all contexts
- **Chat-Scoped Tools**: Limited to specific chat contexts
- **Profile-Specific Tools**: Available only within user profiles

The system evaluates global and chat-specific availability independently to determine the final set of executable tools for each context.

**Tool Configuration**: Each tool is defined through a JSON structure containing the tool definition (name, description, parameters), associated settings, and a callable reference for execution. This modular structure enables tools to be easily registered, configured, and managed across different scopes.

### Tool Response Model

The `ToolResponse` model provides a structured approach for tools to implement sophisticated response patterns. This model enables tools to deliver tailored outputs to different audiences within a single response, optimizing content for both end users and language models.

**ToolResponse Model Structure**:
- **user_content**: User-facing output optimized for clarity, actionability, and readability
- **llm_feedback**: Technical context and detailed information optimized for language model processing

### Available Tools

The platform includes specialized tools for critical operations:

- **Code Block Generator**: A versatile tool for converting and formatting code blocks with flexible output routing and comprehensive language support
- **Webpage Fetching**: Fetch a webpage and convert it to markdown for integration with knowledge base and reference material processing
- **Project Search**: Efficiently locate project resources, files, and documentation with optional AI-powered filtering and automatic result deduplication by source file
- **Project Read File**: Reads and accesses project files for analysis and processing with comprehensive error documentation
- **Project Structure**: Provides utilities for exploring and understanding project organization with visual indicators and metadata display
- **Project Write File**: Write and create files within project structures with complete validation and UTF-8 encoding support
- **Generate Tasks Tool**: Transforms a chat conversation into actionable sub-tasks, automatically analyzing context and splitting complex discussions into manageable tasks

### Tool Organization and Best Practices

**Bulk Operations**: Tools supporting bulk operations provide performance optimization for processing multiple items efficiently through single requests.

**Dual Response Tools**: Tools implementing the `ToolResponse` pattern deliver enhanced value by providing distinct user-facing summaries and technical context for language models.

**Search Result Validation**: When using search tools, validate results match your actual needs—optional AI-powered filtering helps refine results but manual verification ensures accuracy for critical operations.

## Chat Management and API

The Chat API provides a comprehensive set of endpoints for managing conversations, with sophisticated operations designed for robust and reliable message handling. All endpoints are designed with crash-safety mechanisms and comprehensive state management to ensure reliable operation even during system interruptions.

### Chat Engine Architecture

The ChatEngine serves as the central orchestration hub for all chat interactions, coordinating message processing, knowledge retrieval, and response generation. It manages the complete lifecycle of chat operations from query reception through message persistence with sophisticated crash-safety mechanisms ensuring reliable operation even during system interruptions.

#### Key Responsibilities

**Chat Processing**:
- Accept and validate incoming chat requests with comprehensive token management
- Extract and process user messages with full context awareness
- Build system prompts adapted to specific chat modes (Chat, Task, Agent, Vibe, Search)
- Assemble user prompts with knowledge context and metadata enrichment
- Coordinate complete message lifecycle from initial processing through final persistence

**Knowledge Integration**:
- Perform semantic search against project knowledge bases with configurable result limits
- Apply optional filters to refine search results based on criteria
- Load parent chat context when applicable with inheritance control flags
- Integrate knowledge context seamlessly into conversation flow
- Manage parent message filtering through ignore_parent_knowledge flag
- Handle file inheritance through ignore_parent_files flag

**AI Interaction**:
- Stream language model responses with full content accumulation
- Progressively deliver streamed content to callbacks with controlled throttling
- Detect and parse tool invocations from model responses
- Execute tools iteratively with comprehensive error handling and result normalization
- Maintain loop protection mechanisms preventing infinite iteration
- Persist state between iterations for crash recovery and resilience

#### Core Workflow

The ChatEngine processes each chat through a sophisticated multi-phase pipeline coordinating token management, message extraction, profile resolution, model configuration, knowledge retrieval, system prompt construction, tool preparation, user prompt assembly, AI execution with streaming, tool invocation detection and execution, result integration, loop guard evaluation, state persistence, and analytics recording with careful attention to crash-safety and recovery mechanisms throughout.

#### Context Manager: `chat_action`

The `chat_action` context manager provides centralized lifecycle management for chat operations, handling initialization, state persistence, error tracking, and cleanup with structured responsibility management.

#### Main Entry Point

The `chat_with_project()` method is the primary interface for initiating chat operations with comprehensive project context:

| Parameter | Type | Description |
|-----------|------|-------------|
| `project` | Project | Project context and configuration |
| `user` | User | User context and authentication state |
| `token_id` | str | Unique token identifier for the chat session |
| `chat_id` | str | Unique chat identifier |
| `messages` | list[ChatMessage] | Conversation history and current query |
| `mode` | ChatMode | Chat mode (Chat, Task, Agent, Vibe, Search) |
| `search_limit` | int | Maximum results from knowledge base search |
| `search_filters` | dict | Optional filters for knowledge base queries |
| `callback` | Callable | Streaming callback for response delivery |
| `ignore_parent_knowledge` | bool | Exclude parent chat messages |
| `ignore_parent_files` | bool | Exclude parent chat files |

**Returns**: Tuple[list[ChatMessage], str] - Updated message list and system state summary

#### Key Features and Mechanisms

**Crash-Safety System**: ChatEngine implements multi-layered crash-safety mechanisms to handle unexpected interruptions with minimal data loss. The system provides four primary persistence checkpoints:

- **Immediate Error/Cancellation Persistence**: Errors and cancellations are recorded instantly to prevent loss
- **Tool/Lifecycle Events via ChatEventBridge**: Tool execution and lifecycle events are persisted through the event bridge when registered
- **Throttled Streaming Content**: Progressive content delivery with controlled flush points creates recoverable checkpoints
- **Hidden Reasoning Messages**: Internal reasoning and intermediate states are preserved for complete recovery capability

This multi-layer approach ensures crash-safe operation with recovery possible within seconds of any system interruption.

**Message Deduplication**: The system prevents duplicate message insertion when ChatEventBridge has already registered a response message. This ensures idempotent operations even if the same message is processed multiple times due to retry logic or recovery mechanisms.

**Cancellation System**: Flexible cancellation mechanisms provide responsive user interactions:

- **Registration**: Cancellation tokens are registered at chat start with metadata stamping for tracking
- **Pre-Stream Cancellation**: Abort before streaming begins with immediate token cleanup and zero response delivery
- **Mid-Stream Cancellation**: Gracefully terminate during active streaming with exact-once guarantee and immediate token ID stamping
- **Token-Based Identification**: Cancellation by token ID enables precise client-side operation termination
- **Explicit Cancellation Flow**: Token ID is stamped immediately, and cancelled_at timestamp is recorded for audit purposes

**Parent Chat Context**: ChatEngine supports structured conversation hierarchies with sophisticated inheritance:

- **Message Inheritance**: Child chats include or exclude parent messages via `ignore_parent_knowledge` flag
- **File Inheritance**: Child chats include or exclude parent files via `ignore_parent_files` flag
- **Recursive Traversal**: Automatic parent chain traversal builds complete context lineage
- **History Integration**: Parent messages seamlessly integrate into conversation history
- **Refinement Integration**: Supports specialized refinement use cases with complete contextual awareness

#### Chat Modes

The system supports five distinct chat modes, each optimized for specific interaction patterns:

| Mode | Purpose | Key Characteristics |
|------|---------|-------------------|
| **Chat** | Standard conversational interaction | General discussion and question answering |
| **Task** | Complex problem decomposition | Automatic task generation and linking |
| **Agent** | Autonomous agent operation | Extended tool access and decision-making |
| **Vibe** | Creative and exploratory interaction | Specialized creative mode engagement |
| **Search** | Knowledge base querying | Comprehensive semantic search capabilities |

### Chat Manager Features

The ChatManager module provides specialized functionality for managing chat files, message persistence, and chat state across projects with merge-safe operations prioritized as a core feature:

- **File Organization**: Chat files are systematically organized with predictable naming patterns following `board/column/name/id` format
- **Merge-Safe Persistence**: Implements last-writer-wins conflict resolution per-message by `doc_id` and `updated_at` timestamp
- **Fast-Path Optimization**: Efficient hot-path loading through specialized operations for frequently-called granular access
- **Chat Discovery**: Specialized methods for discovering chats by search criteria and retrieving recent conversations
- **Multi-Project Support**: Explicit support for chats owned by projects other than those requesting them
- **Full-Text Search**: Comprehensive search functionality across chat content, messages, files, and metadata
- **Granular Message Operations**: Full CRUD operations for message management with merge-safe conflict resolution
- **Chat Export**: Multiple format options (markdown, DOCX, PDF, Excel) for structured documentation
- **Kanban Integration**: Chat-to-board assignment enabling task organization within project structures
- **Metadata Management**: Dedicated metadata operations enable efficient updates to chat metadata

### Chat API Endpoints

The Chat API is organized into logical groups supporting the complete conversation lifecycle:

#### Cancellation Management
- **POST /chat/cancel** — Abort in-progress chat operations with graceful fallback mechanisms

#### Message Management
- **POST /chat/message** — Append messages to conversations in a merge-safe, idempotent manner
- **PUT /chats/message** — Update existing messages with merge-safe operations
- **DELETE /chats/message** — Remove messages from chats with safe deletion

#### Metadata Management
- **POST /chats/metadata** — Update chat metadata separately from message operations

#### Retrieval and Search
- **GET /chats** — Retrieve conversations with optional filtering and pagination
- **POST /chat/search** — Discover conversations using flexible search with filter flags and relevance scoring

#### Chat Operations
- **POST /chat/from-url** — Generate new chats by loading content from URLs
- **POST /chat** — Initiate conversation with a project
- **PUT /chat/{chat_id}** — Persist chat state and message updates
- **DELETE /chat/{chat_id}** — Remove conversations and associated data

#### Kanban Board Management
- **GET /chat/kanban** — Retrieve kanban board assignments
- **POST /chat/kanban** — Persist kanban board state
- **DELETE /chat/kanban** — Remove kanban board assignments

## System Reliability and Observability

### Analytics Integration

The platform implements comprehensive analytics tracking throughout critical system operations. The analytics system records session start events capturing initialization context and baseline metrics, as well as session end events documenting completion metrics including token usage, tool execution patterns, and cache statistics. Analytics recording occurs at iteration boundaries to avoid duplicates and ensure clean observability traces. Wallet checks are explicitly integrated to track cost management and token usage across operations.

The analytics integration operates with built-in resilience: when analytics operations encounter issues, they are caught and logged appropriately rather than disrupting core service delivery. This graceful degradation pattern ensures that analytics failures never cascade into broader system failures.

### Crash-Safety Mechanisms

The system implements multi-layered crash-safety mechanisms designed to handle unexpected interruptions with minimal data loss. Through structured event attachment, regular state persistence, and intelligent recovery mechanisms, the platform ensures reliable operation with loss tolerance measured in seconds even during hard system failures.

### Error Handling and Resilience

The system implements comprehensive error handling across multiple dimensions with graceful degradation as a core principle. Errors encountered during tool execution, argument parsing, validation, analytics operations, cancellation handling, and loop protection are managed without disrupting primary service delivery. Non-fatal issues are logged appropriately to aid diagnostics while maintaining continued operation, ensuring that system reliability is preserved across diverse failure scenarios.

## Documentation Organization and Approach

This wiki employs a refined documentation structure that prioritizes clarity and practical utility:

### Content Organization Principles

- **Endpoint-Centric API Documentation**: Chat API endpoints are organized with clear HTTP methods, paths, and operations for practical reference
- **Feature-Focused Sections**: Tool documentation emphasizes capabilities, use cases, and practical benefits
- **Professional Formatting**: Standardized tables, structured headings, and consistent section organization for improved scannability
- **Practical Integration Guidance**: Integration notes and configuration requirements are clearly separated from API specifications
- **Progressive Disclosure**: Users can understand high-level capabilities from this overview and navigate to detailed documentation for specific implementation guidance
- **Diagnostic-Focused Problem Analysis**: Error handling documentation emphasizes root cause analysis and problem diagnosis
- **High-Level Architecture Focus**: Core architecture and responsibilities are documented at the system level rather than implementation details
- **User-Focused Behavior Emphasis**: Documentation prioritizes understanding practical system behavior and capabilities over implementation complexity

### Navigation Structure

This wiki is organized into the following primary sections:

- **Project Overview**: High-level architecture understanding and system purpose
- **App Module**: FastAPI configuration, middleware setup, and Socket.IO integration
- **Engine Module**: Core backend logic, project operations, and session handling
- **AI and Knowledge Management**: Agents including SmolAgent with comprehensive documentation; Pydantic data models; and knowledge processing with sophisticated seven-stage document pipeline
- **Database and Data Storage**: Data persistence strategies and storage architecture
- **Security and Authentication**: Authentication mechanisms and security practices
- **Session Management**: Session lifecycle, channel coordination, and state management
- **Profile Management**: User profile management with sophisticated discovery, dual-file structure, hierarchical lookup with four-level priority system, and comprehensive lifecycle operations
- **Project Tools and Utilities**: File management operations, AI operations, and project-level interaction utilities
- **Tools and Utilities**: Tool implementations, response patterns, and helper modules with complete tool ecosystem documentation
- **Chat Engine and API**: Central orchestration hub with message lifecycle management and crash-safe operations
- **Utility Functions**: Reference helper modules and supporting functionality

### Using This Documentation

Each section in this wiki is designed for practical reference with clear architectural overviews, feature highlights, key responsibilities, design patterns, and integration context. Navigate to specific sections for detailed implementation guidance, or use the search functionality to locate information on particular components.

---

**Last Updated**: This documentation reflects the current state of the CODX API with comprehensive updates across all system components. Recent significant enhancements have been made to the Profile Management system with refined documentation reflecting feature-based organization that emphasizes what ProfileManager does and how its features work together rather than implementation details. The documentation now features an overview section introducing key capabilities, a directory structure section showing both old and new format visuals, a profile model section listing key properties, and key functionality grouping methods by logical purpose. Profile discovery has been consolidated to clarify the hierarchical explanation, profile linking emphasizes deduplication purpose, utility functions expand generated_llm_tree() description with sorting behavior details, and loading behavior clarifies graceful error handling for malformed JSON as a key feature. SmolAgent documentation maintains comprehensive coverage including detailed multi-phase conversation flow, Tool Result Normalization with intelligent truncation to 256 characters for context efficiency, LoopGuard with three protection mechanisms and intelligent violation behavior with cached bypass, Tool Result Caching with comprehensive hit/miss/rate metrics and per-conversation organization, Dual-Response Tool patterns for sophisticated output routing to different audiences, System Instructions for hardcoded file handling, Event Emission with comprehensive lifecycle and tool event tracking, AgentRunContext for unified execution state management, and comprehensive callback flush behavior documentation. All documentation continues to emphasize core concepts including tool caching optimization, loop protection through multiple strategies, comprehensive analytics with resilient graceful degradation, structured event types for complete observability, error handling philosophy prioritizing non-fatal issue logging and continued operation, and system limits with intelligent enforcement. Documentation maintains user-focused behavior emphasis and graceful error handling ensuring system reliability and performance across diverse operational scenarios.