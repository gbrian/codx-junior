# Codx Junior API - Complete Reference Guide

Welcome to the Codx Junior API documentation. This wiki serves as your comprehensive reference for understanding the architecture, components, and functionality of the CODX API system.

## Project Overview

Codx Junior API is a sophisticated backend system that combines FastAPI for robust HTTP handling with real-time Socket.IO communication, comprehensive knowledge management, and intelligent agent orchestration. The system empowers developers with AI-driven development assistance capabilities, managing projects, sessions, and complex operations with seamless integration across multiple specialized agents and tools.

## Core Architecture

### Application Infrastructure

**App Module**: The FastAPI foundation that handles HTTP requests, configures middleware, manages real-time communication through Socket.IO, and orchestrates background task execution for asynchronous operations. The module implements a sophisticated middleware pipeline designed to enhance request processing with settings extraction, timeout management, and performance monitoring capabilities. Socket.IO integration enables real-time bidirectional communication through dedicated namespace architecture, supporting live chat updates, status notifications, and collaborative features.

**Session Management**: Establishes `CODXJuniorSession` instances through a dedicated middleware chain with three distinct layers—Settings extraction, Timeout management, and Process Time tracking—ensuring comprehensive request context management and performance observability. Session initialization occurs automatically via middleware, making sessions seamlessly available throughout the request lifecycle.

**Engine Module**: The operational backbone responsible for project creation, session management, and high-level business logic that powers all features exposed through the application layer. The Engine coordinates critical operations including analytics tracking, session recording, and token usage monitoring to ensure comprehensive observability across all chat interactions. The Engine Module implements systematic issue management with structured error tracking and analysis capabilities to identify root causes, prevent silent failures, and manage cascading effects across system operations through comprehensive error handling and failure prevention mechanisms.

**Database and Data Storage**: Persistent data management with intelligent database routing and configuration supporting comprehensive application requirements.

**Security and Authentication**: Implements GitHub OAuth integration, user management, and authentication protocols ensuring secure access across the platform.

## AI and Intelligent Agents

The system features multiple specialized agents, each optimized for specific operational domains:

### Agent Capabilities

**Base Agent**: Foundation providing core agent functionality and integration patterns for all specialized agent implementations.

**DevOps Agent**: Manages infrastructure operations, deployment tasks, and operational workflows.

**Git Issues Agent**: Handles GitHub integration, issue tracking, and version control coordination.

**SmolAgent**: A streamlined, async-first agent engineered for efficient iterative tool execution with sophisticated modern architecture. SmolAgent represents a refined approach to agent orchestration prioritizing clarity, performance, and production-readiness through:

- **Async-Only Design**: Purpose-built for asynchronous operations with no legacy synchronous code paths, ensuring efficient resource utilization and responsive feedback through iterative loops

- **Safety First**: Comprehensive error handling with graceful degradation ensuring system reliability. All exceptions during tool execution are caught and handled gracefully as error strings, with explicit exception types tracked for root cause analysis. Non-fatal issues are logged appropriately to aid diagnostics while maintaining continued operation

- **Streaming Architecture**: Full response accumulation with progressive delivery throughout the entire request lifecycle, enabling real-time feedback while maintaining complete response state with crash-safe persistence guarantees

- **Iterative Execution Pattern**: SmolAgent executes a sophisticated iterative pattern coordinating message processing, tool invocation, result normalization, and loop guard evaluation with intelligent state management between iterations. Specific cancellation checkpoints are integrated throughout the execution flow for responsive user interactions

- **Tool Organization and Discovery**: Sophisticated organization of global, chat-scoped, and profile-specific tools with dynamic filtering based on execution context and permissions. Tools are discovered through explicit scope metadata and module-level TOOLS registry, enabling precise availability control

- **Session Context Injection**: Session context is intelligently injected into tool parameters, enabling tools to access and operate within proper execution context without explicit parameter passing

- **Tool Events and Observability**: Comprehensive event system emitting `TOOL_START`, `TOOL_END`, and `TOOL_ERROR` events with detailed payloads for complete observability and system integration

- **Robust Tool Result Handling**: Comprehensive normalization of tool outputs with intelligent truncation to 256 characters for context efficiency while preserving full results internally. Tool results are exclusively used for iterative tool execution and never included in final user responses, ensuring clean separation between internal processing and user-facing content

- **Tool Result Caching**: Caches results per conversation by function name and parameters with comprehensive cache statistics tracking cache hits, misses, and hit rate metrics for observability. Cached results bypass loop guard checks entirely, enabling efficient iteration without consuming protection budget

- **Loop Protection**: LoopGuard prevents infinite iteration loops through three protection mechanisms—model-based limits, provider-based limits, and fallback limits—with intelligent violation behavior and priority-ordered resolution ensuring predictable loop termination. Cached tool calls bypass limit enforcement entirely, enabling efficient reuse without protection overhead

- **Dual-Response Tools**: Tools can implement the ToolResponse pattern to deliver distinct user-facing outputs (`user_response`) and technical context (`llm_response`) for language models within a single response, optimizing content for different audiences

- **Cancellation Support**: Flexible cancellation mechanisms including pre-stream abort before streaming begins with immediate token cleanup and zero response delivery, and mid-stream abort during active streaming with exact-once guarantee preventing duplicate token consumption

- **Analytics Tracking**: Built-in analytics recording token usage, tool execution logging, cache statistics, and session context with resilient graceful degradation patterns ensuring analytics failures never cascade into core service delivery

- **Wallet and Preflight Checks**: Validation of wallet state before execution to ensure cost management and token availability

- **Session Injection**: Automatic injection of `_active_session` and `_current_chat` context into tool parameters for seamless access to execution context

- **Production-Ready Design**: Engineered as a practical, ready-to-use tool with clear initialization patterns and straightforward integration for developers

## Knowledge and Models

**Knowledge Processing**: Comprehensive system featuring code splitting, semantic analysis, document enrichment, keyword extraction, and AI model integration for building project-specific knowledge bases. The knowledge system is built on the **Knowledge Milvus** foundation, which provides core document management, semantic search capabilities, and knowledge base orchestration through a structured seven-stage document processing pipeline with Milvus as the underlying vector database.

**Knowledge Milvus Base**: The foundational knowledge management component implementing a sophisticated document lifecycle and comprehensive seven-stage processing pipeline designed to transform raw source code and documentation into semantically rich, queryable knowledge assets:

### Knowledge Processing Core Functionality

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

**Pydantic Data Models**: Comprehensive, professionally organized model definitions spanning 50+ data structures across multiple functional domains providing a foundation for all data structures and configurations throughout the platform. Models are organized into logical categories including communication models, board and column models, knowledge management models, provider configuration models, development and automation models, UI and navigation models, user models, AI models, project configuration models, system configuration models, plugin system models, and agent and OAuth models.

**AI Models and Provider Configuration**: The system supports seamless integration with multiple AI providers through dedicated configuration models including built-in provider support with OLLAMA_PROVIDER and default embeddings for resource-efficient local deployment, provider-specific settings for OpenAI, Anthropic, and Mistral with customizable parameters, configurable embedding models for semantic analysis and knowledge retrieval, and flexible provider selection enabling optimal performance across different deployment scenarios.

**Model Configuration**: System-wide configuration through GlobalSettings which manages AI provider selection, embedding configuration, user access controls, feature flags, and API keys across all model categories. Settings are logically organized into domains with clearly defined subsections. Global instructions are loaded fresh from GlobalSettings on each chat to ensure consistency across operations.

## Project Tools and Utilities

The **Project Tools** module provides essential utility functions for file management, AI operations, and project-level interactions within the CODX Junior framework, serving as a comprehensive bridge between the AI system and project resources.

### Key Features

- **AI Initialization**: Configure AI instances with project settings and user context through the `get_ai()` utility function
- **Code Block Processing**: Convert and format code blocks with the `code_block()` function providing flexible output routing and comprehensive language support
- **Path Resolution**: Convert and validate file paths with boundary protection to ensure secure file operations
- **File Operations**: Read and write files with UTF-8 encoding support and comprehensive validation
- **Bulk File Reading**: Process up to 10 files per operation with automatic language detection through `project_read_file()`
- **Search and Knowledge Base**: Query project resources with `project_search()` supporting optional AI-powered filtering and automatic result deduplication by source file
- **Bulk Search Operations**: Execute up to 5 queries per operation with `project_search()` returning comprehensive results with automatic deduplication
- **Project Structure Exploration**: Understand project organization with visual representation through `project_structure()`

### Configuration

| Feature | Limit | Purpose |
|---------|-------|---------|
| **Bulk File Reading** | 10 files per call | Efficient multi-file processing |
| **Bulk Search Operations** | 5 queries per call | Comprehensive knowledge base searches |

### Error Handling and Validation

All functions implement explicit exception handling with comprehensive error management including path validation preventing unauthorized file access, safe file operations with verification, graceful handling of missing resources, and UTF-8 encoding with proper error handling for all file operations. Each function includes detailed exception documentation to aid in error diagnosis and handling.

### Best Practices

- Use bulk operations for processing multiple items to reduce tool invocations and improve efficiency
- Implement proper path handling strategies with validation to ensure security and prevent unauthorized access
- Apply search validation techniques to verify results match actual requirements before use
- Monitor file size and optimize operations for large-scale file processing
- Consider context efficiency when working with large file contents

## Custom Tools and Integration

**Custom Tools System**: A flexible and extensible framework for defining, registering, and executing specialized tools that extend the capabilities of the AI system. The custom tools module enables seamless integration of domain-specific functionality with comprehensive tool management and sophisticated execution patterns.

### Tool Architecture

**Tool Registration and Management**: Tools are registered within the custom tools module with comprehensive metadata including:
- Tool name and description for identification and documentation
- Input parameters with JSON schema validation
- Output format specifications
- Scope information (global, chat-level, or profile-specific)
- Execution context and permissions requirements

**Tool Discovery and Organization**: The system provides intelligent tool discovery through:
- Scope-based filtering enabling precise availability control
- Dynamic tool discovery based on execution context
- Module-level tool registry for centralized management
- Permission-based availability restricting tools to authorized users

**Tool Execution and Integration**: Tools are executed within a sophisticated execution framework providing:
- Parameter validation and schema enforcement
- Context injection for session and chat awareness
- Error handling with graceful degradation
- Result normalization and formatting
- Event emission for complete observability

**Custom Tool Development**: The framework enables developers to create custom tools with:
- Standardized tool definition patterns
- Clear parameter and output specifications
- Built-in error handling and validation
- Integration with session and chat context
- Support for dual-response patterns (user-facing and LLM context)

### Custom Tool Manager

The Custom Tool Manager provides comprehensive tool management capabilities with systematic handling of tool creation, retrieval, updates, and deletion. All operations maintain atomic consistency ensuring reliable tool lifecycle management.

**Create Tool**: Establish new custom tools through structured creation process with automatic metadata initialization and script file generation. The system manages tool registration with proper resource allocation and configuration setup.

**List Tools**: Retrieve custom tools with efficient filtering and comprehensive metadata representation. The system provides detailed tool information enabling complete tool discovery and capability assessment.

**Update Tool**: Modify existing custom tool configurations with preservation of creation metadata and consistent version tracking. Updates maintain tool integrity while enabling configuration refinement.

**Delete Tool**: Remove custom tools with recursive resource cleanup ensuring complete tool removal from the system. All associated scripts and metadata are properly cleaned up.

**File Management**: Sophisticated handling of tool-related files including script storage, metadata persistence, and automatic directory management with proper hierarchy maintenance.

**Metadata Files**: JSON structures maintaining comprehensive tool information including configuration, status, and operational metadata for complete tool state tracking.

**Script Files**: Storage and management of tool implementation scripts with support for multiple programming languages, automatic naming conventions, and organized directory structures.

**Error Handling**: Comprehensive error management with specific error types and behaviors for invalid operations, resource conflicts, and execution failures with detailed error reporting for diagnosis.

### API Endpoints

The Custom Tools API provides a comprehensive set of endpoints for managing tools:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/projects/custom-tools` | GET | Retrieve all custom tools for a project |
| `/api/projects/custom-tools` | POST | Create a new custom tool |
| `/api/projects/custom-tools/{tool_id}` | GET | Retrieve a specific custom tool |
| `/api/projects/custom-tools/{tool_id}` | PUT | Update an existing custom tool |
| `/api/projects/custom-tools/{tool_id}` | DELETE | Delete a custom tool |
| `/api/projects/custom-tools/{tool_id}/execute` | POST | Execute a custom tool |

**Authentication**: All endpoints require authentication. The execute endpoint only requires authentication (not admin role).

**Authorization**: Create, update, and delete operations require admin authorization. The execute endpoint does not require admin authorization; it requires only authentication.

**Behavior**: The create endpoint automatically sets the `created_by` field to the authenticated user's username and initializes creation timestamps in UTC. The update endpoint preserves the original `created_by` value and creation timestamp while updating modification metadata. Timestamps are always recorded in UTC timezone.

**Validation**: The system validates that tool names are unique within a project and enforces required parameters in tool definitions. JSON schema validation ensures parameter definitions conform to standard JSON Schema specifications.

**Tool Activation**: Tools must be marked as active before they can be executed. Inactive tools are excluded from availability to agents and are not executable.

**Logging**: The system maintains comprehensive logging at multiple levels:
- **INFO**: Tool creation, updates, deletions, and successful executions
- **DEBUG**: Detailed parameter validation steps and execution context information
- **WARNING**: Attempts to execute inactive tools or tools with validation issues
- **ERROR**: Tool execution failures with exception details and root cause information

**Execution Response**: The execute endpoint returns a 200 status code with execution results. The response may contain errors in the result field even with a 200 status, indicating partial success or recoverable errors during execution.

## Tools and Utilities

The platform provides a flexible tool ecosystem organized across multiple scope levels, enabling precise tool availability and security. Tools follow a modular architecture pattern designed to maximize flexibility, maintain backward compatibility, and preserve operational context across interactions.

### Tool Organization and Design

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
- **user_response**: User-facing output optimized for clarity, actionability, and readability
- **llm_response**: Technical context and detailed information optimized for language model processing

### Available Tools

The platform includes specialized tools for critical operations:

- **Code Block Generator**: A versatile tool for converting and formatting code blocks with flexible output routing and comprehensive language support. Features include bulk operations, flexible output routing, and comprehensive language support
- **Webpage Fetching**: Fetch a webpage and convert it to markdown for integration with knowledge base and reference material processing
- **Project Search**: Efficiently locate project resources, files, and documentation with optional AI-powered filtering and automatic result deduplication by source file. Features include bulk operations (up to 5 queries per call), AI-powered filtering, and automatic deduplication
- **Project Read File**: Reads and accesses project files for analysis and processing with support for bulk operations reading multiple files (up to 10 per call) in a single call. Features include bulk operations, automatic language detection, and UTF-8 encoding support
- **Project Structure**: Provides utilities for exploring and understanding project organization with visual indicators and metadata display
- **Project Write File**: Write and create files within project structures with complete validation, UTF-8 encoding support, and automatic parent directory creation. Features include automatic parent directory creation, comprehensive validation, and error handling
- **Generate Tasks Tool**: Transforms a chat conversation into actionable sub-tasks, automatically analyzing context and splitting complex discussions into manageable tasks
- **Custom Tools**: Extensible framework enabling developers to create domain-specific tools with standardized patterns, parameter validation, and seamless AI system integration

### Tool Organization and Best Practices

**Bulk Operations**: Tools supporting bulk operations provide performance optimization for processing multiple items efficiently through single requests. Bulk operations include specific limits: file reading supports up to 10 files per call, while search supports up to 5 queries per call.

**Dual Response Tools**: Tools implementing the `ToolResponse` pattern deliver enhanced value by providing distinct user-facing summaries and technical context for language models.

**Search Result Validation**: When using search tools, validate results match your actual needs—optional AI-powered filtering helps refine results but manual verification ensures accuracy for critical operations.

## Profile Management

**Profile Manager**: Comprehensive system for managing user profiles and profile-related configurations with sophisticated profile discovery, operations, and lifecycle management across the platform.

### Key Features

**Hierarchical Profile Discovery**: The ProfileManager establishes multiple tiers for profile discovery:
1. **Project profiles** — Located within `project_path/.codx/profiles/` with highest priority
2. **Base profiles** — Located within the system base profiles directory with secondary priority
3. **External provider profiles** — Profiles from external provider integrations with fallback access

**Modern Folder-Based Structure**: Profiles are organized as dual-file pairs with improved clarity:
- `.profile` files contain JSON metadata and configuration
- `.md.profile` files contain associated markdown content and documentation

This structure replaces legacy flat-file approaches with a modern `[profile_name]/[profile_name].profile` organization.

**Profile Lookup Hierarchy**: The system implements a four-level lookup priority ensuring optimal profile resolution:
1. **Project-level profiles** — Project-specific customizations with highest precedence
2. **Parent project profiles** — Inherited configurations from parent projects
3. **CODX Junior project level** — System-wide profiles as fallback
4. **External provider profiles** — External integrations as final fallback

**Content Processing and Templates**: The `get_profile_with_content()` method handles complete profile retrieval with content parsing and template variable resolution. Profile content supports template variables through explicit syntax: `{{ variable_name }}` (with spaces) for dynamic content substitution. Template variables include `{{ project_path }}` and `{{ project_name }}` for seamless AI integration. Undefined variables are left unchanged, enabling graceful handling of missing context.

**Discovery Methods**: The ProfileManager provides specialized methods for profile discovery:
- **`base_profiles()`** — Returns profiles from the system base directory
- **`project_profile_paths()`** — Explicitly locates project-level profile paths

**Profile Operations**: The system provides comprehensive CRUD operations:
- **Loading**: Retrieve specific profiles by reference with full content parsing and context variable resolution
- **Saving**: Persist profile configurations with automatic content deduplication and exclusion from JSON metadata
- **Deleting**: Remove profiles with complete lifecycle management
- **Bulk Operations**: Process multiple profiles simultaneously for efficiency

**Profile Relationships**: Profiles support inheritance across projects, enabling configuration reuse and centralized management while maintaining project-specific customizations. The system manages linked profiles across project boundaries with sophisticated deduplication logic preventing duplicate profile processing while maintaining access to all unique configurations.

**Graceful Degradation**: The system supports minimal valid profiles containing essential metadata even when full configuration is unavailable, ensuring operational continuity through error handling with graceful degradation for malformed content.

## Wiki Management

**Wiki Manager**: Comprehensive system for creating and managing project wikis with sophisticated document organization, domain classification, and category management. The WikiManager handles the complete lifecycle of wiki creation and maintenance:

### Core Capabilities

**Wiki Tree Creation**: Automatically generates hierarchical wiki structures from repository files with intelligent organization into logical sections and subsections.

**Domain Building**: Orchestrates parallel document processing to build semantic domains that group related documentation and code concepts together.

**Index Creation**: Constructs comprehensive wiki indices enabling efficient search and navigation across the entire documentation structure.

**Category Management**: Manages hierarchical category structures with proper validation and organization of wiki content.

**File Organization**: Systematically organizes wiki files with predictable naming patterns and comprehensive validation of file paths.

**Settings Persistence**: Caches and persists wiki configuration with intelligent validation to ensure consistency across operations.

**Multi-Format Support**: Supports both VitePress and MkDocs documentation frameworks with flexible configuration.

**AI Integration**: Leverages AI models for intelligent document analysis, category assignment, and content summarization while maintaining concurrent processing efficiency through ThreadPoolExecutor for parallel operations.

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

## API Endpoints and Operations

The application exposes a comprehensive set of API endpoints organized into functional categories:

### Project Management
- Create, retrieve, update, and delete projects
- Manage project metadata and configuration
- Handle project-level settings and preferences

### Code Operations
- Execute code analysis and transformations
- Manage code repositories and version control
- Process code changes and generate diffs

### File Management
- Read and write project files
- Organize file structures
- Handle file uploads and media management
- Generate file diffs for change tracking

### Settings & Profiles
- Manage user and project settings
- Configure user profiles and preferences
- Handle global system settings

### System & Infrastructure
- Monitor system health and performance
- Access application logs
- Manage system configuration
- View infrastructure metrics

### Utility Operations
- Generate code blocks with formatting
- Fetch and process web content
- Search project knowledge bases
- Manage custom tools and extensions

### Static File Serving
The application serves static files including documentation, assets, and public resources with proper content-type handling and caching strategies. Uploads are served with MD5 hash naming conventions in subdirectory structures (`/images/message/`) for efficient organization and retrieval.

## App Module - Key Endpoints and Configuration

The App Module serves as the FastAPI foundation, providing critical endpoints organized into functional categories with comprehensive middleware and configuration support.

### Endpoint Organization

**Health & System**
- **GET /health** — System health status and availability checks
- **GET /logs** — Access application logs with filtering and retrieval

**Settings Management**
- **GET /settings** — Retrieve current system and user settings
- **POST /settings** — Update system configuration and preferences

**Project Operations**
- **GET /projects** — List projects with filtering and pagination
- **POST /projects** — Create new projects with configuration
- **GET /projects/{id}** — Retrieve specific project details
- **PUT /projects/{id}** — Update project configuration
- **DELETE /projects/{id}** — Remove projects

**File and Code Operations**
- **GET /projects/{id}/files** — List project files
- **POST /projects/{id}/files** — Upload and create files
- **GET /projects/{id}/files/{path}** — Read file contents
- **PUT /projects/{id}/files/{path}** — Modify file contents
- **DELETE /projects/{id}/files/{path}** — Remove files

**Logging Configuration**

The App Module implements selective logging to optimize performance and focus on critical operations. The following loggers are disabled to reduce noise:
- **httpx** — HTTP client logging suppressed
- **openai** — OpenAI client logging suppressed
- **watchfiles** — File monitoring logging suppressed
- **asyncio** — Async runtime logging suppressed

Critical loggers remain enabled to provide essential operational visibility while maintaining system performance.

## Documentation Organization and Approach

This wiki employs a refined documentation structure that prioritizes clarity and practical utility:

### Content Organization Principles

- **User-Focused Structure**: Documentation is organized around capabilities, use cases, and practical benefits rather than implementation details
- **API-Reference Format**: Chat API and custom tools documentation uses structured sections for quick-reference clarity
- **Feature-Focused Sections**: Tool documentation emphasizes capabilities, use cases, and practical benefits
- **Professional Formatting**: Standardized tables, structured headings, and consistent section organization for improved scannability
- **Practical Integration Guidance**: Integration notes and configuration requirements are clearly separated from API specifications
- **Progressive Disclosure**: Users can understand high-level capabilities from this overview and navigate to detailed documentation for specific implementation guidance
- **Diagnostic-Focused Problem Analysis**: Error handling documentation emphasizes root cause analysis and problem diagnosis
- **High-Level Architecture Focus**: Core architecture and responsibilities are documented at the system level rather than implementation details
- **Agent-Focused Documentation**: SmolAgent documentation emphasizes the iterative execution pattern with intelligent state management, comprehensive tool management with caching and loop protection, dual-response tool patterns, event emission systems for observability, and sophisticated crash-safety mechanisms

### Navigation Structure

This wiki is organized into the following primary sections:

- **Project Overview**: High-level architecture understanding and system purpose
- **App Module**: FastAPI configuration, middleware setup, Socket.IO integration, and key endpoints
- **Engine Module**: Core backend logic, project operations, and session handling
- **AI and Knowledge Management**: Agents including SmolAgent with comprehensive documentation; Pydantic data models; and knowledge processing with sophisticated seven-stage document pipeline
- **Database and Data Storage**: Data persistence strategies and storage architecture
- **Security and Authentication**: Authentication mechanisms and security practices
- **Session Management**: Session lifecycle, channel coordination, and state management
- **Profile Management**: User profile management with sophisticated hierarchical discovery, dual-file folder-based structure, four-level lookup priority, template variable support with explicit syntax, and comprehensive lifecycle operations
- **Wiki Management**: Wiki creation and maintenance with sophisticated document organization, domain classification, and category management
- **Custom Tools and Integration**: Flexible tool framework for extending AI system capabilities with domain-specific functionality, comprehensive tool management, and standardized API endpoints
- **Project Tools and Utilities**: File management operations, AI operations, and project-level interaction utilities with enhanced bulk operation support and performance considerations
- **Tools and Utilities**: Tool implementations, response patterns, and helper modules with complete tool ecosystem documentation including custom tools system
- **Chat Engine and API**: Central orchestration hub with message lifecycle management and crash-safe operations
- **Utility Functions**: Reference helper modules and supporting functionality

### Using This Documentation

Each section in this wiki is designed for practical reference with clear architectural overviews, feature highlights, key responsibilities, design patterns, and integration context. Navigate to specific sections for detailed implementation guidance, or use the search functionality to locate information on particular components.

---

**Last Updated**: This documentation reflects the current state of the CODX API with comprehensive updates across all system components. Recent improvements include enhanced presentation of App Module architecture with explicit Session Management middleware chain details and key endpoint specifications; expanded coverage of Knowledge Milvus integration and seven-stage document processing pipeline; enhanced custom tool manager documentation with structured operation descriptions; improved wiki management documentation with concurrent processing efficiency details; improved profile management documentation with explicit template variable syntax support and four-level lookup hierarchy; restructured custom tools API documentation with user-focused content emphasizing practical capabilities and use cases; comprehensive API endpoints organization by functional categories with clear HTTP method and route specifications. All documentation continues to emphasize core concepts including tool caching optimization for efficient iteration, comprehensive analytics with resilient graceful degradation, structured event types for complete observability, error handling philosophy prioritizing non-fatal issue logging and continued operation, and multi-layered crash-safety ensuring system reliability and performance across diverse operational scenarios.