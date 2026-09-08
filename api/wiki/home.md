# CodX Junior API Documentation

## Welcome to CodX Junior API

CodX Junior is a comprehensive API framework built with FastAPI that powers intelligent project management and AI-driven development assistance. This documentation provides detailed information about the architecture, modules, and tools that make up the system.

## Project Architecture

The CodX Junior API is organized into several core modules that work together to deliver a unified platform:

### Key Components

**App Module** – The main FastAPI application entry point that orchestrates configuration, middleware setup, and real-time communication. Manages request routing, background task execution, and the complete application lifecycle. Implements security features with role-based access control, comprehensive logging with configurable control, session management with request state handling, and enforces a 280-second request timeout across all API operations as a fundamental architectural constraint. Supports HTTPS with adhoc SSL certificates for secure communication and serves static files for unified frontend-backend deployment.

**Engine Module** – The core backend service providing essential operations for project management, session handling, and file processing. Organizes endpoints into logical categories: Health & Diagnostics, Project Management (CRUD operations), Code Improvement & AI, File Operations, Settings & Profiles, Application & Workspace, System Control, and Socket.IO real-time communication. Implements role-based workspace access control with admin and regular user permission levels, handles file processing with secure MD5-based filename generation, provides comprehensive error handling with specific HTTP status codes, and supports dynamic router loading for extensible endpoint organization.

**Chat Engine** – The core conversational AI engine orchestrating sophisticated multi-mode chat interactions with language models. Implements four distinct chat modes optimized for different interaction patterns: **Task (Refine)** for document refinement and iterative task completion, **Chat** for standard conversational interactions, **Agent** for complex workflows with configurable iteration counts, and **Vibe** for contextual understanding with nuanced AI-driven reasoning. 

Delivers crash-safety through early metadata persistence (safeguarding response data before streaming begins), event bridge integration for distributed consistency, stream throttling with intelligent buffering, thinking content preservation for recovery and auditing, error state persistence for failure tracking, and duplicate prevention safeguards. Supports configurable knowledge inheritance through flags enabling selective knowledge propagation across related conversations, UUID-based cancellation with fine-grained token lifecycle management, comprehensive session analytics tracking timing metrics and token usage, and seamless hierarchical chat structures where child conversations inherit settings and context from parent conversations while respecting explicit inheritance controls.

Processes requests through a structured deterministic workflow: **Initialization** with validation and context setup, **History & Context** with parent chat knowledge and file inheritance, **Configuration** resolution from profiles and parameters, **Knowledge Retrieval** through Pre-Search (AI-driven semantic exploration) and RAG-based mechanisms with deduplication, **File Processing** with extraction and deduplication using deterministic ordering, **Prompt Assembly** with mode-specific transformations, **Response Metadata Persistence** before streaming begins for crash-safety, **Response Generation** with streaming integration, **Post-Processing** including chat description and auto-initialization, and **Finalization** with analytics persistence.

**SmolAgent** – An async-first streaming chat agent engineered for sophisticated, real-time interaction patterns with language models. Built with flow-centric architecture optimized for streaming responses, SmolAgent delivers high-performance conversational capabilities with structured agent loops, multi-turn conversation lifecycle management, intelligent tool management with scope systems, real-time streaming with buffer and flush mechanics, comprehensive event systems providing complete visibility into tool execution and operation flow, loop protection mechanisms preventing infinite loops, and detailed analytics for token usage and performance tracking. 

The agent initializes with comprehensive configuration management supporting flexible profiles and parameters with intelligent defaults. It processes requests through iterative execution loops with configurable iteration limits (Loop Guard Constraints enforcing maximum iteration counts and resource limits protecting system stability). Each iteration intelligently manages tools through both global and chat-specific scoping, executes sophisticated tool caching mechanisms tracking cache hits and misses, and incorporates results before proceeding to the next cycle. Supports two distinct cancellation approaches: UUID-based global cancellation tokens for external triggers with checkpoint verification at iteration boundaries, and context-based cancellation for graceful degradation when limits are reached. Implements comprehensive event emissions throughout execution including initialization events, iteration progress tracking, tool execution details, completion notifications, and error states. Tool Result Normalization ensures consistent handling of diverse tool outputs through standardized processing. Categorizes errors precisely with ToolLoopError for tool execution failures, CancelledError for cancellation-triggered exceptions, and AgentCancelled for graceful degradation, while preserving non-fatal warnings for observable errors without interruption.

**Tools Engine** – A comprehensive toolkit system serving as the central hub for specialized capabilities organized into logical categories: Web & Content Utilities (browser automation, web scraping, content fetching), Project Management Tools (repository management, file operations, structure analysis), Code & Development Tools (analysis, generation, refactoring), Image & Vision Tools (vision analysis, image processing, generation), and Utility Tools (testing and maintenance). Tools operate within a centralized aggregation system supporting both synchronous and asynchronous execution, enable dual-response patterns for complex workflows, and integrate seamlessly with agent systems. The tools ecosystem emphasizes bulk operations, search-replace functionality with validation, comprehensive error handling, and complete parameter specifications including data types, defaults, and constraints for reliable automation across development workflows. Tools are scoped at global, chat-specific, or profile levels with configurable availability.

**Image Engine** – Manages comprehensive image operations including generation from text prompts using DALL-E models (supporting sizes from 256x256 to 1792x1024 with quality levels and style options), vision-based analysis using GPT-4 Vision, local storage and file management, OCR text extraction using Tesseract, and detailed metadata tracking. Supports complete image lifecycle management with organized directory structures, atomic metadata persistence in JSON format, and streamlined image deletion with automatic file and metadata cleanup.

**Advanced Features** – Provides fine-grained cancellation support using a UUID-based global registry with ISO-8601 timestamp tracking and comprehensive session analytics including timing metrics, token usage tracking, tool execution tracking, and error states. Supports parent chat knowledge and file inheritance through configurable flags, enabling selective knowledge reuse and context propagation across related conversations. Implements crash-safe persistence mechanisms protecting against data loss through early metadata creation, event bridge integration, and duplicate prevention safeguards.

**AI and Knowledge Management** – Integrates artificial intelligence capabilities with robust knowledge processing systems. The system features a comprehensive registry of Pydantic-based data models organized by functional domain, providing comprehensive validation and type safety. Includes support for multiple language models and providers with configurable defaults, providing embeddings-based knowledge retrieval organized across a three-tier architecture (Milvus for vector storage, AISearch for advanced search capabilities, and ChatKnowledge for conversation-specific indexing). Implements intelligent agents for specialized tasks and comprehensive knowledge indexing and retrieval systems with support for semantic search through both Pre-Search (AI-driven exploration) and RAG Search (document-grounded retrieval) mechanisms organized with deterministic file ordering and deduplication safeguards.

### Core Architecture

The application implements a structured request processing pipeline with the following layers:

| Layer | Purpose |
|-------|---------|
| **Settings Injection** | Configures global settings and request parameters |
| **Timeout Management** | Enforces 280-second request timeout across all operations with 504 HTTP status on timeout |
| **HTTP Process Time Tracking** | Monitors request processing duration and performance metrics |
| **Session Initialization** | Creates and manages user sessions with request state handling |
| **Authentication** | Validates user credentials and API keys |
| **Workspace Validation** | Ensures workspace access control and filtering |
| **Request Processing** | Routes requests to appropriate handlers |
| **Exception Handling** | Captures and processes errors with meaningful responses |
| **Response Serialization** | Formats responses with comprehensive debugging information |

### Session Management

User sessions are created during request processing and attached to the request state for access throughout the request lifecycle. Session context is initialized early in the middleware pipeline, enabling authentication, workspace filtering, and request-specific operations to leverage session data. Sessions maintain comprehensive metadata including user identity, workspace assignments, role-based permissions, and request timing information. This architecture ensures consistent session handling across all endpoints and background operations.

### Background Services

The application manages asynchronous task processing and background services for system responsiveness without blocking primary request handlers. Background service execution is controlled through the `CODX_JUNIOR_API_BACKGROUND` environment variable:

- **Knowledge Indexing** – Asynchronous indexing of knowledge bases and document processing
- **File Processing** – Background file handling and media operations
- **Long-Running Operations** – Non-blocking execution of extended tasks
- **Session Maintenance** – Automatic session cleanup and lifecycle management

Application lifecycle events handle startup and shutdown with proper resource initialization and cleanup:

- **Startup Events** – Service initialization, database connections, cache warming, and resource preparation
- **Shutdown Events** – Graceful cleanup, connection closure, and resource release

### Dynamic Router Loading

The Engine Module supports dynamic endpoint loading through a router discovery system, allowing flexible addition and management of API routes. This architecture enables modular endpoint organization and simplifies extension of API functionality without requiring core module modifications.

## API Endpoints

The Engine Module organizes API endpoints into logical categories for intuitive access and clear responsibility boundaries:

| Category | Purpose | Key Operations |
|----------|---------|-----------------|
| **Health & Diagnostics** | System status and health monitoring | Health checks, system information, service diagnostics |
| **Project Management** | Project CRUD operations and discovery | Create, read, update, delete projects with metadata management |
| **Code Improvement & AI** | Code analysis and AI-driven enhancements | Refine code, analyze patterns, suggest improvements |
| **File Operations** | File upload and management | Upload files with MD5 verification, retrieve, delete files |
| **Settings & Profiles** | Configuration and user profile management | Get/update settings and profiles, manage user preferences |
| **Application & Workspace** | Application and workspace management | Create and manage applications, workspace configuration |
| **System Control** | System-wide operations and monitoring | Logs, screen management, system restart and shutdown |
| **Socket.IO** | Real-time WebSocket communication | Bidirectional real-time updates, session channels, progress tracking |

## Chat Engine Architecture

### Overview

The Chat Engine is the core conversational AI component of the CodX Junior project, providing sophisticated multi-mode chat interactions with language models through a streamlined and crash-safe architecture. Built with persistent event tracking as its core principle, the engine processes requests through a deterministic pipeline of logical phases designed for comprehensive reliability and context management.

### Key Features

**Multi-Mode Interaction Architecture** – Implements four distinct modes optimized for different use patterns: Task (Refine) mode for document refinement and iterative task completion with focused output; Chat mode for standard conversational interactions with complete message history; Agent mode for complex workflows with configurable iteration counts and recursive logic; and Vibe mode for contextual understanding with nuanced AI-driven reasoning and sophisticated analysis.

**Crash-Safety Architecture** – Implements robust protection against data loss through multiple critical layers: early metadata persistence ensuring response metadata is created and persisted before content streaming begins, enabling recovery even if streaming fails midway; event bridge integration providing multi-step persistence through distributed consistency mechanisms with automatic state tracking across system failures; stream throttling and protection with intelligent buffering against rapid data loss during network issues; thinking content preservation for recovery, audit trails, and detailed failure analysis; error state persistence for immediate recording with full context enabling precise failure recovery; and duplicate prevention through sophisticated deduplication mechanisms maintaining data integrity.

**UUID-Based Cancellation Support** – Fine-grained request cancellation with global cancellation token registry featuring ISO-8601 UTC timestamp tracking, four-step flow from creation through cancellation verification with immediate persistence of cancellation state, comprehensive state tracking providing complete visibility into cancellation status and request lifecycle, and graceful degradation with proper cleanup and resource release upon cancellation while preserving state.

**Knowledge & File Inheritance System** – Supports intelligent knowledge management through parent-child relationships enabling child chats to selectively inherit knowledge and files from parent conversations. Configurable inheritance flags (`ignore_parent_knowledge` and `ignore_parent_files`) enable fine-grained control over knowledge propagation with recursive behavior across chat hierarchies. Knowledge search modes combine Pre-Search for AI-driven semantic exploration and RAG Search for document-grounded retrieval organized with deterministic file ordering. Selective reuse enables flexible knowledge management supporting partial inheritance and customized knowledge sets with deduplication and relevance ranking.

**Session Analytics** – Provides comprehensive session tracking including timing metrics (request duration, processing phase timing), token usage tracking (input/output token counts), tool execution tracking (invocation counts, execution duration), error states (exception tracking, error types), model & provider metrics (model used, provider, configuration tracking), and metadata accumulation (session metadata, message counts).

**Event Streaming** – Emits events throughout the request processing pipeline providing complete visibility into operation flow. Events are generated during initialization, history retrieval, knowledge processing, prompt assembly, response generation, and finalization phases, enabling real-time progress tracking and comprehensive operation auditing.

**File Content Integration** – Integrates file content at multiple points in the processing pipeline. Files are extracted from requests, deduplicated against existing context, parsed for content extraction, prepared with deterministic ordering for prompt inclusion, and tracked throughout processing for comprehensive context management.

**Performance Optimization** – Incorporates performance optimization strategies including intelligent deduplication mechanisms reducing redundant content processing, stream throttling preventing buffer overflow and network issues, lazy loading deferring expensive operations until necessary, and deterministic ordering ensuring consistent and reproducible behavior across processing phases.

### Chat Modes

The Chat Engine implements four distinct modes optimized for different interaction patterns:

| Mode | Purpose | Characteristics |
|------|---------|-----------------|
| **Task (Refine)** | Document refinement and iterative task completion | Non-answer messages hidden, focused output |
| **Chat** | Standard conversational interactions | Complete message history, general discussions |
| **Agent** | Complex workflows with multi-step automation | Configurable iteration counts, recursive logic |
| **Vibe** | Contextual understanding with nuanced reasoning | AI-driven perspective, sophisticated analysis |

### Processing Pipeline

The Chat Engine processes requests through a deterministic structured workflow ensuring reliability and consistency:

1. **Initialization Phase** – Validate incoming chat request and extract core parameters, register cancellation tokens with UUID tracking and ISO-8601 timestamps, initialize request context and session state, establish event tracking and analytics baseline, set up crash-safety checkpoints for recovery.

2. **History & Context Phase** – Retrieve full message history with deterministic ordering for consistency, apply parent chat knowledge and file inheritance rules based on configuration flags, construct conversation context from applicable messages with parent message inclusion logic, validate message consistency and integrity.

3. **Configuration Phase** – Resolve user profile settings and configurations with priority ordering, merge AI model parameters from multiple sources, apply mode-specific configuration overrides, finalize effective configuration for request.

4. **Knowledge Retrieval Phase** – Execute Pre-Search knowledge retrieval mechanism (AI-driven semantic exploration) when knowledge is not disabled, execute RAG-based knowledge search (document-grounded retrieval) with document-grounded deduplication, merge and deduplicate knowledge results across both search mechanisms, rank knowledge by relevance scores, apply knowledge context limits.

5. **File Processing Phase** – Extract and parse files from request and collect from parent chats using deterministic ordering, deduplicate files against existing context and knowledge, resolve file content with streaming and caching support, prepare files for prompt inclusion with deterministic ordering and formatting.

6. **Prompt Assembly Phase** – Build AI prompt message sequence with parent message integration, integrate knowledge context into prompt with formatting, integrate file content with markdown code block extraction, apply mode-specific prompt transformations and hiding rules.

7. **Response Metadata Phase** – Create and persist response metadata early before streaming begins (crash-safe checkpoint), establish baseline for streaming response with event tracking, prepare analytics baseline for session tracking.

8. **Response Generation Phase** – Execute AI response generation with streaming support and real-time buffering, handle streaming events and intelligent buffering, preserve thinking content throughout streaming for recovery and auditing, track token usage throughout generation, maintain crash-safety state during streaming.

9. **Post-Processing Phase** – Generate chat description based on response and context, execute auto-initialization if configured with knowledge and file inclusion, apply message hiding rules based on chat mode (Task mode hides non-answer messages), finalize response structure.

10. **Finalization Phase** – Persist analytics and session data with comprehensive metrics, persist error states if exceptions occurred with full context, clean up temporary resources and close file handles, record operation completion with final state tracking.

## SmolAgent Overview

SmolAgent is an advanced conversational agent designed for sophisticated real-time interactions with language models. It implements a streaming-first architecture that emphasizes real-time feedback and efficient resource utilization.

### Core Architecture & Design

SmolAgent employs an iterative loop design centered around the `AgentRunContext` which delegates core responsibilities across specialized handlers. The architecture follows an event-driven perspective with complete visibility through comprehensive event systems. Each iteration processes tool calls, executes tools with intelligent caching mechanisms, and incorporates results before proceeding to the next cycle.

**Tool Cache System** – Implements sophisticated caching for tool execution with detailed analytics including cache hits, cache misses, and cache hit rate metrics. Tool responses are cached at execution time, preventing redundant computations and accelerating multi-step workflows. Cache statistics are tracked throughout execution for performance monitoring and optimization.

**Cancellation Mechanisms** – Supports two distinct cancellation approaches: UUID-based global cancellation tokens for external cancellation triggers with checkpoint verification at iteration boundaries, and context cancellation for graceful degradation when processing limits are reached. Checkpoints are established at loop boundaries and between phases for clean interruption points.

**Tool Result Normalization** – Standardizes diverse tool outputs through consistent processing ensuring uniform handling regardless of tool type or response format. Normalizes results for reliable downstream consumption and consistent behavior across different tool implementations.

### Core Capabilities

**Streaming Architecture** – Provides native streaming support with real-time response generation and buffered output delivery. The agent processes model responses as they arrive, enabling immediate user feedback and progressive result refinement.

**Tool Integration** – Seamlessly integrates with the Tools Engine for executing specialized capabilities. Tools are scoped (global, chat-specific, profile-level) and support both synchronous and asynchronous execution with dual-response patterns for complex workflows.

**Agent Loops** – Implements configurable iteration-based execution with loop protection mechanisms preventing infinite execution. Each iteration processes tool calls, executes tools, and incorporates results before proceeding to the next cycle. **Loop Guard Constraints** enforce maximum iteration counts and resource limits protecting system stability. Only uncached tool executions count toward iteration limits, allowing efficient use of cached results without consuming loop budget.

**Event System** – Provides comprehensive event emissions throughout execution with operational clarity. Events include initialization events, iteration progress events, tool execution details with event tables documenting tool call flows, completion events, and error states. Event-driven architecture enables real-time monitoring and integration with external systems.

**Configuration Management** – Supports flexible configuration through profiles and parameters with intelligent defaults. Configuration includes model selection, iteration limits, tool availability, and behavioral parameters.

**Analytics & Tracking** – Captures detailed metrics including token usage (input/output counts), execution timing (phase durations, total runtime), tool invocation counts and execution times, tool cache analytics (hits, misses, and hit rate percentages), and error tracking with full context preservation.

### Exception Handling

SmolAgent categorizes errors into specific types for precise failure recovery:

- **ToolLoopError** – Errors occurring during tool execution within the agent loop with full context preservation
- **CancelledError** – Errors resulting from cancellation requests with clean resource cleanup
- **AgentCancelled** – Cancellation state exceptions for graceful degradation

**Non-Fatal Failures** – Warnings that do not interrupt execution including tool timeout warnings, partial response recoveries, and degraded operation scenarios. These warnings are logged and tracked for observability without interrupting the agent workflow.

### System Rules

SmolAgent enforces explicit hardcoded file-handling rules ensuring consistent code output:

- **Code Block Formatting** – All code content is wrapped in markdown code blocks with language specification
- **File Path Handling** – Absolute or relative file paths used based on project and conversation context
- **Original Formatting Preservation** – New file changes maintain original file formatting and indentation
- **Minimal Changes** – Unnecessary changes, format alterations, or cleanup avoided unless explicitly requested
- **Complete File Content** – Full file content generated with changes for comprehensive review

## Security Features

**Authentication & Authorization** – Role-based access control with workspace filtering, ensuring users only access resources within their authorization scope. Supports role-based permission levels (admin and regular users) with workspace-specific assignments and project-level associations. Integrates both API key and OAuth-based authentication mechanisms including GitHub OAuth integration for secure user authentication and resource protection.

**Access Control** – Implements comprehensive access control through:
- User authentication validating credentials and managing secure session establishment
- Workspace access rules enforcing workspace-level permissions ensuring users can only interact with resources in their authorized workspaces
- Granular permission enforcement at the project and resource levels with admin privileges for administrative operations

**Request Processing Pipeline** – Each middleware layer executes in order through the core architecture, adding specific functionality to the request lifecycle with timeout enforcement (280 seconds) and process time tracking for performance monitoring.

**Exception Handling** – Centralized error handling strategy providing consistent error responses with timeout behavior, detailed error tracking, and graceful degradation with meaningful error messages for client troubleshooting.

## Request Flow

Each API request follows a structured lifecycle through the application:

1. **Incoming Request** – Client sends request to the API endpoint
2. **Settings Injection** – Global settings and request context are configured
3. **Timeout Enforcement** – Request timeout limit (280 seconds) is established
4. **Process Time Tracking** – Request timing begins with HTTP header preparation
5. **Session Initialization** – User session is created or retrieved from request state
6. **Authentication Validation** – User credentials and API keys are verified
7. **Workspace Filtering** – Access control ensures user can access requested resources
8. **Route Dispatch** – Request is routed to the appropriate endpoint handler
9. **Endpoint Processing** – Business logic executes and generates response
10. **Exception Handling** – Any errors are caught and formatted consistently
11. **Response Serialization** – Response is formatted with debugging information
12. **Client Response** – Response is returned with process time header

## Logging & Monitoring

Comprehensive logging throughout the application with configurable logger control via `enable_logs()` and `disable_logs()` functions:

**Disabled Loggers** – The following loggers are disabled by default for reduced noise in standard operations:
- uvicorn.access
- uvicorn
- httpx
- openai._base_client

**Request Logging** – Detailed request and operation tracking for observability and debugging with support for multiple logger instances organized by functional domain. Log streams can be captured from Docker container logs or local file storage depending on deployment configuration. Disabled log streams can be re-enabled through configuration settings to provide granular control over logging output and system observability. Request tracking integrates with the middleware pipeline to capture timing metrics and performance indicators.

## Core Models

The model layer encompasses comprehensive data structures organized to reflect the actual codebase organization:

**Chat and Communication Models** – Message and content structures supporting chat sessions with ChatMessage and Content models for different content types, ImageUrl for image reference handling, and conversation session organization with comprehensive metadata.

**Project Organization Models** – Data structures for workspace organization, team management, and workspace-level settings with hierarchical permission structures enabling collaborative multi-team environments.

**Knowledge Management Models** – Schemas for organizing and retrieving knowledge including knowledge search with semantic capabilities, document management for indexed content, embeddings for vector-based knowledge representation, and knowledge operations for reload and deletion.

**Tool and Agent Models** – Comprehensive tool specifications with full type annotations for tool organization. Tool definitions include complete parameter specifications (type, required flag, defaults) and response type indicators. Supports intelligent tool scoping distinguishing between global and chat-specific availability.

**User Models** – Core data structures for user management including authentication, workspace assignments, role-based permissions, and user-specific settings.

**AI Models** – Comprehensive language model configurations with support for multiple AI providers (OpenAI, Anthropic, Mistral, Ollama). Features include provider-specific settings and model-specific parameters with configurable defaults.

**Profile Models** – User profile and role configurations organizing profile-specific settings and AI behavior parameters for different interaction modes.

**Image Models** – Complete image management schemas including generation parameters, vision analysis requests, storage metadata, response structures, and image lifecycle tracking.

**Configuration Models** – Data structures for system configuration including project settings, Git integration parameters, agent configurations, feature flags, and display customization.

**GlobalSettings** – Centralized system configuration providing comprehensive organization of AI Models, system settings, project & workspace configuration, user management options, workspace settings and collaboration, integration parameters, chat communication settings, logging configuration, and display customization.

## Key Features

### Image Operations

The Image Engine provides a centralized hub for all image operations:

- **Image Generation** – Create images from text prompts using DALL-E 3 and DALL-E 2 with support for multiple sizes and quality levels
- **Vision Analysis** – Analyze images using GPT-4 Vision to answer questions and describe content
- **Image Explanation Analysis** – Comprehensive multi-perspective understanding of image content
- **Storage Management** – Organized image storage with automatic directory creation and metadata indexing
- **OCR Text Extraction** – Extract text from images using Tesseract
- **Metadata Tracking** – Comprehensive tracking of generation parameters, creation timestamps, and operation status

### Intelligent Tool Ecosystem

Tools operate at multiple scope levels and support both single and bulk operations:

| Scope | Description | Availability |
|-------|-------------|--------------|
| **Global Scope** | System-level tools available across all chat sessions | Always accessible to all agents and operations |
| **Chat Scope** | Chat-specific tools scoped to individual conversations | Available within specific chat context |
| **Profile Scope** | Profile-specific tools customized for user profiles | Available based on profile settings and permissions |

**Tool Categories:**

| Category | Purpose | Key Capabilities |
|----------|---------|-----------------|
| **Web & Content** | Web content retrieval and processing | Browser automation, web scraping, HTTP requests |
| **Project Management** | Repository and project management | Git operations, project search, structure analysis |
| **Code & Development** | Code analysis and creation | Code writing, analysis, refactoring |
| **Image & Vision** | Image processing and analysis | Vision analysis, image processing, generation |
| **File Operations** | File reading and modification | File management, search-replace with validation |
| **Task Management** | Workflow orchestration | Bulk operations, batch processing, task execution |

### Git Integration

Comprehensive version control management through a structured API providing repository operations, branch management, commit tracking, file history exploration, pull request workflows, and code change summarization. Key capabilities include depth-based file retrieval, structured code change analysis, subproject support, and standardized return formats.

### Project Settings Management

Robust configuration management for projects through automatic directory creation, configuration backup before every write operation, complete audit trail with history tracking, Pydantic model support, and comprehensive validation. Supports MCP Server management for extended integrations and automatic initialization with UUID generation.

### Knowledge Management

Advanced document processing and code analysis systems enabling the platform to understand and work with large codebases. The knowledge system supports semantic search through both Pre-Search (AI-driven exploration) and RAG Search (document-grounded retrieval) mechanisms organized across a three-tier architecture (Milvus for vector storage, AISearch for advanced search capabilities, and ChatKnowledge for conversation-specific indexing), intelligent code splitting, QA generation, and comprehensive document enrichment with structured data schemas.

### Socket.IO Integration

Real-time communication built on Socket.IO, enabling dynamic bidirectional communication between clients and the server through SessionChannel integration. The integration wraps FastAPI with an ASGIApp for seamless integration, supports live session updates, progress tracking for long-running operations, and collaborative features with responsive user experiences and event-driven architecture.

## Static Files & Deployment

The application serves static frontend assets alongside the API, supporting unified deployment scenarios with SPA (Single Page Application) support. Static files are served from the directory specified by the `CODX_JUNIOR_STATIC_FOLDER` environment variable. HTML fallback is automatically configured for client-side routing, enabling seamless integration of modern frontend frameworks with the backend API.

## Environment Configuration

The system is configured through environment variables that control various aspects of the application including AI provider settings, database connections, authentication credentials, logging levels, and feature flags. Key environment variables include:

- `CODX_JUNIOR_STATIC_FOLDER` – Path to static frontend assets for unified deployment
- `CODX_JUNIOR_API_BACKGROUND` – Controls background service execution and asynchronous task processing
- Model configurations, workspace settings, logging options, integration credentials, and storage paths

Configuration supports multiple deployment scenarios from local development to production environments with Docker containerization.

## Navigation

Use the sidebar to explore specific modules and components. Each section contains detailed documentation about implementation, APIs, and usage patterns. Start with the relevant category based on what you're working with:

- **Project Overview** – High-level system architecture and design principles
- **App Module** – FastAPI application initialization, configuration, request processing pipeline, middleware implementations, session management, and lifecycle management
- **Engine Module** – Core backend operations, endpoint organization, Git management, session handling, file upload processing with MD5 verification, and access control
- **AI and Knowledge Management** – AI and LLM model configurations with provider settings, comprehensive data models organized by functional domain, agents for specialized tasks, knowledge processing with semantic search through Pre-Search and RAG mechanisms, Chat Engine with advanced features and crash-safe architecture supporting deterministic processing with deduplication and file ordering safeguards, comprehensive processing pipeline with logical phases, SmolAgent for streaming interactions with real-time event systems and sophisticated tool caching analytics, tool integration with intelligent caching mechanisms and cache statistics tracking, error handling with exception categorization and non-fatal failure tracking, tool result normalization for consistent output handling, hardcoded file-handling rules for consistent code output, comprehensive image operations, and guidance for Chat Engine and SmolAgent usage
- **Database and Data Storage** – Data persistence, storage configuration, and settings management
- **Security and Authentication** – Authentication mechanisms, authorization enforcement, and access control
- **Session Management** – Session handling, session creation, Socket.IO integration through SessionChannel, and real-time communication
- **Utility Functions** – Helper tools and scripts

For specific implementation details, method signatures, parameter documentation, model field specifications, complete parameter specifications for tools (including data types, defaults, and constraints), structured code examples showing return data formats, and detailed SmolAgent behavior including tool cache analytics with hit rate metrics, loop guard iteration counting mechanisms, and cancellation checkpoints, navigate to the relevant module section in the documentation.