# Codx Junior API - Complete Reference Guide

Welcome to the Codx Junior API documentation. This wiki serves as your comprehensive reference for understanding the architecture, components, and functionality of the CODX API system.

## Project Overview

Codx Junior API is a sophisticated backend system that combines FastAPI for robust HTTP handling with real-time Socket.IO communication, comprehensive knowledge management, and intelligent agent orchestration. The system empowers developers with AI-driven development assistance capabilities, managing projects, sessions, and complex operations with seamless integration across multiple specialized agents and tools.

## Core Architecture

### Application Infrastructure

**App Module**: The main FastAPI entry point that initializes the application, configures middleware, manages real-time communication through Socket.IO, and orchestrates background task execution. The module implements a sophisticated three-layer middleware pipeline—Settings extraction, Timeout management, and Process Time tracking—ensuring comprehensive request context management and performance observability. Requests are transparently limited to 280 seconds through timeout middleware, preventing resource exhaustion while allowing complex operations to complete. Socket.IO integration enables real-time bidirectional communication at `/api/socket.io` through dedicated namespace architecture, supporting live chat updates, status notifications, and collaborative features.

**FastAPI Initialization**: The application configures FastAPI with comprehensive middleware integration:

```python
app = FastAPI(
    title="CODX Junior API",
    description="AI-powered development assistance backend",
    version="1.0.0"
)

# Three-layer middleware pipeline
app.add_middleware(SettingsMiddleware)      # Extract request context
app.add_middleware(TimeoutMiddleware)       # Enforce 280-second limit
app.add_middleware(ProcessTimeMiddleware)   # Track request duration

# Socket.IO integration
sio = socketio.AsyncServer(async_mode='asgi')
app = socketio.ASGIApp(sio, app)
```

**Session Management**: Establishes `CODXJuniorSession` instances automatically through the middleware chain, ensuring comprehensive request context management. Sessions are seamlessly available throughout the request lifecycle, eliminating manual initialization requirements and providing consistent context across all operations.

```python
def get_codx_junior_session() -> CODXJuniorSession:
    """Retrieve the current request's session context.
    
    Returns the session established by middleware during request initialization,
    providing access to user context, authentication state, and request metadata.
    """
    return request.state.session
```

**Engine Module**: The operational backbone responsible for project creation, session management, and high-level business logic that powers all features exposed through the application layer. The Engine coordinates critical operations including analytics tracking, session recording, and token usage monitoring to ensure comprehensive observability across all chat interactions. The Engine Module implements systematic issue management with structured error tracking and analysis capabilities to identify root causes, prevent silent failures, and manage cascading effects through comprehensive error handling.

**Database and Data Storage**: Persistent data management with intelligent database routing and configuration supporting comprehensive application requirements.

**Security and Authentication**: Implements GitHub OAuth integration, user management, and authentication protocols ensuring secure access across the platform.

**Settings Management**: The system provides comprehensive configuration management through `CODXJuniorSettings` for global system configuration and `CODXJuniorProject` for project-specific settings. Configuration is persisted as JSON with intelligent path resolution and fallback mechanisms for property retrieval. New methods support efficient project configuration access including `get_project_settings_file()` for accessing the full path to project.json and `get_sub_projects_paths()` for retrieving absolute paths to subprojects. The settings system features intelligent loading and initialization with computed properties alongside persisted configuration, enabling flexible and maintainable configuration management.

## Request Processing Chain

The middleware pipeline coordinates comprehensive request handling through sequential processing:

1. **Settings Extraction** — Middleware extracts and injects request context (user, authentication, configuration) into session state
2. **Timeout Management** — Enforces 280-second timeout preventing resource exhaustion
3. **Process Time Tracking** — Records request duration for performance observability
4. **Session Initialization** — Establishes CODXJuniorSession with full context for request lifecycle
5. **Validation Error Handling** — Middleware catches validation errors and returns structured error responses

## AI and Intelligent Agents

The system features multiple specialized agents, each optimized for specific operational domains:

### Agent Capabilities

**Base Agent**: Foundation providing core agent functionality and integration patterns for all specialized agent implementations.

**DevOps Agent**: Manages infrastructure operations, deployment tasks, and operational workflows.

**Git Issues Agent**: Handles GitHub integration, issue tracking, and version control coordination.

**SmolAgent**: A streamlined, async-first agent engineered for efficient iterative tool execution with sophisticated modern architecture. SmolAgent represents a refined approach to agent orchestration prioritizing clarity, performance, and production-readiness through comprehensive state management, intelligent tool caching, and robust error handling.

#### SmolAgent Architecture Overview

**Design Philosophy**: SmolAgent implements async-first design with no legacy synchronous code paths, ensuring efficient resource utilization and responsive feedback through iterative loops. The agent structures messages with clear separation between user queries and tool execution context, maintaining full message history with accumulated responses throughout the request lifecycle.

**Core Operating Principles**: SmolAgent operates through three fundamental organizing principles: **iterative execution** of tool calls with intelligent caching to avoid redundant work, **scope-based tool management** organizing tools at global, chat, and profile levels with precise availability control, and **crash-safe operations** with multi-layered persistence checkpoints ensuring reliability even during system interruptions.

**Conversation Flow**: SmolAgent follows a complete 7-step flow from initialization through message generation:
1. Initialize agent with session context and tool registry
2. Build system prompt from parameters, chat mode instructions, and current tool schemas
3. Send user query to language model for initial response
4. Identify and validate tool calls from model output
5. Execute tools iteratively with sophisticated caching and loop protection
6. Accumulate results with normalized responses
7. Return final response with complete message history

**Tool Execution Pipeline**: SmolAgent executes through a sophisticated iterative cycle designed for efficiency and reliability:

1. Process model responses to identify tool calls
2. Check execution cache for previously computed results (bypassing loop guard checks)
3. Validate against loop protection mechanisms
4. Execute tools with provided parameters
5. Normalize results with intelligent truncation
6. Store results in cache for future iterations
7. Loop until completion or protection limit reached

Cached tool calls bypass loop guard checks entirely and don't count toward iteration limits, enabling efficient repeated operations without consuming protection budget.

**Tool Scoping and Discovery**: Tools are organized at three distinct scopes—global tools available across all contexts, chat-scoped tools limited to specific conversations, and profile-specific tools restricted to user profiles. Dynamic filtering based on scope metadata ensures precise availability control. Tool discovery leverages the TOOLS registry with automatic loading based on scope, ensuring instructions are always current and properly sandboxed to their execution context.

**Tool Caching Strategy**: SmolAgent implements sophisticated tool result caching organized per conversation by function name and parameters:
- Eliminates redundant computations through result reuse
- Reduces iterative loop complexity by avoiding recalculation
- Improves response times for common operations
- Tracks cache hits, misses, and overall hit rates for comprehensive observability

**Tool Call Processing**: SmolAgent implements a two-phase processing model for tool execution:
- **Cached Phase**: Previously computed results are retrieved and applied immediately, bypassing all loop protection checks and iteration counting
- **Uncached Phase**: New tool executions proceed through standard loop protection validation and iteration accounting

**Tool Response Types**: Tools deliver responses through two distinct patterns:
- **Traditional Tools**: Return single responses optimized for either user presentation or LLM processing
- **Dual-Response Tools**: Implement the `ToolResponse` model to deliver both user-facing outputs and technical context within a single response, optimizing content for distinct audiences

**Loop Protection**: SmolAgent implements LoopGuard safeguards preventing infinite iteration loops through multiple protection mechanisms with intelligent violation behavior. The system maintains iteration state and manages loop lifecycle with comprehensive safeguards, while cached operations bypass protection checks entirely for optimal efficiency.

**Stuck Loop Detection**: SmolAgent incorporates dedicated mechanisms to detect and prevent scenarios where the agent becomes trapped repeating similar operations. Detection considers iteration patterns, tool execution sequences, and response consistency to identify stalled progress.

**Streaming and Callbacks**: SmolAgent supports callback-based streaming with comprehensive safeguards. The streaming mechanism guards against concurrent operations through synchronization, ensuring safe multi-threaded access during active streaming. Callbacks receive accumulated full responses at controlled intervals to avoid buffering delays, with crash-safety guarantees ensuring response delivery even during system interruptions.

**Streaming Strategy**: SmolAgent implements an accumulation-based callback flushing approach:
- Collects response fragments during tool execution
- Dispatches accumulated content at strategic intervals
- Maintains synchronization to prevent concurrent callback conflicts
- Ensures delivery guarantees even during system failures

**Callback Batching**: SmolAgent implements intelligent callback batching, which accumulates responses and dispatches them at optimal intervals. This approach prevents callback overhead while maintaining responsiveness and ensuring reliable message delivery even during system failures.

**Cancellation Mechanisms**: Flexible cancellation provides responsive user interactions through distinct mechanisms:
- **Pre-stream Cancellation**: Abort before streaming begins with immediate cleanup at initialization checkpoint
- **Mid-stream Cancellation**: Gracefully terminate during active streaming with exact-once guarantee at execution checkpoint
- **Legacy Token Mechanism**: Compatibility layer for gradual migration paths
- **Runtime Token Mechanism**: Modern token-based cancellation for precise operation control

**System Message Building**: Constructed from three sources—system prompt parameter, chat mode-specific instructions, and fresh tool schema definitions—with guaranteed freshness for tool availability. The system message ensures tools reflect current state and instructions remain contextually appropriate.

**Tool Result Normalization**: Implements intelligent conversion rules normalizing diverse tool response formats into consistent structures with clear priority rules. The system truncates results to prevent excessive context bloat while preserving essential information, with explicit rationale for each conversion ensuring predictable behavior across tool implementations.

**Tool Arguments Parsing**: SmolAgent processes tool arguments through argument parsing, which parses model-generated arguments and validates them against tool schemas. This method ensures type correctness and parameter alignment while providing detailed error context for debugging.

**Dual-Response Pattern**: Tools implement dual-response patterns through the `ToolResponse` model, delivering user-facing outputs and technical context for language models within a single response, optimizing content for distinct audiences.

**Event Emission System**: SmolAgent provides comprehensive event-driven observability organized into three categories:
- **Request Lifecycle Events**: Chat initialization and completion tracking with session context
- **LLM Events**: Model interaction and token usage tracking with provider information
- **Tool Events**: `TOOL_START`, `TOOL_END`, and `TOOL_ERROR` events with execution metrics, cache indicators, and detailed payloads

**Error Handling**: Comprehensive error management with all exceptions during tool execution caught and handled gracefully. Explicit exception type tracking enables detailed error analysis and logging without disrupting primary service delivery. Errors are never propagated to the user but converted to informative strings for language model processing.

**Analytics and Usage Recording**: Multi-layered tracking across token usage with cache statistics and tool usage patterns. Analytics recording occurs at controlled intervals to prevent duplication while maintaining comprehensive observability. Wallet checks are explicitly integrated to track cost management and token usage across operations.

**Configuration**: SmolAgent initialization requires session context, AI provider configuration, tool registry with scope-based filtering, and optional cancellation token support.

**Public API**: The primary interface through the `chat()` method provides comprehensive chat interaction with iterative tool execution.

**Method Signature and Parameters**:
```python
async def chat(
    messages: List[ChatMessage],
    system: Optional[str] = None,
    model: Optional[str] = None,
    stream_callback: Optional[Callable[[str], Awaitable[None]]] = None,
    tools: Optional[List[Tool]] = None,
    cancel_token: Optional[CancelToken] = None
) -> ChatResponse
```

Key parameters include conversation history, custom system prompts, model selection, streaming callbacks for real-time response delivery, available tools for execution during iteration, and optional cancellation tokens for mid-operation termination.

**System Rules for File Operations**: SmolAgent enforces specific guidelines when working with files:
- Use code blocks with file names after the language identifier
- Maintain original file formatting and indentation
- Avoid unnecessary changes, format changes, or cleanup unless explicitly requested
- Validate file paths based on project context

## Chat Architecture and Management

**Chat Engine**: The central orchestration hub for all chat interactions, coordinating message processing, knowledge retrieval, and response generation. It manages the complete lifecycle of chat operations from query reception through message persistence with sophisticated crash-safety mechanisms ensuring reliable operation even during system interruptions.

**Key Responsibilities**:
- Accept and validate incoming chat requests with comprehensive token management
- Extract and process user messages with full context awareness
- Build system prompts adapted to specific chat modes (Chat, Task, Agent, Vibe, Search)
- Perform semantic search against project knowledge bases with configurable result limits
- Coordinate complete message lifecycle with crash-safe persistence
- Detect and execute tools iteratively with comprehensive error handling
- Maintain loop protection mechanisms preventing infinite iteration

**Chat Modes**: The system supports five distinct chat modes optimized for specific interaction patterns:
- **Chat** — Standard conversational interaction
- **Task** — Complex problem decomposition with automatic task generation
- **Agent** — Autonomous agent operation with extended tool access
- **Vibe** — Creative and exploratory interaction
- **Search** — Knowledge base querying with comprehensive semantic search

**Crash-Safety System**: ChatEngine implements multi-layered crash-safety mechanisms with four primary persistence checkpoints:
- Immediate error and cancellation persistence
- Tool and lifecycle event recording through ChatEventBridge
- Throttled streaming content with controlled flush points
- Hidden reasoning message preservation for complete recovery

**Cancellation System**: Flexible cancellation mechanisms provide responsive user interactions:
- Pre-stream cancellation: Abort before streaming begins with immediate token cleanup
- Mid-stream cancellation: Gracefully terminate during active streaming with exact-once guarantee
- Token-based identification: Precise client-side operation termination

**Chat Manager**: Provides specialized functionality for managing chat files, message persistence, and chat state across projects:
- **File Organization**: Chats systematically organized with predictable naming patterns
- **Merge-Safe Persistence**: Last-writer-wins conflict resolution per-message by doc_id and updated_at timestamp
- **Fast-Path Optimization**: Efficient hot-path loading for frequently-called granular access
- **Full-Text Search**: Comprehensive search functionality across chat content and metadata
- **Chat Export**: Multiple format options (markdown, DOCX, PDF, Excel) for structured documentation

## Knowledge and Models

**Knowledge Processing**: Comprehensive system featuring code splitting, semantic analysis, document enrichment, keyword extraction, and AI model integration for building project-specific knowledge bases. The knowledge system is built on the **Knowledge Milvus** foundation, which provides core document management, semantic search capabilities, and knowledge base orchestration through a structured seven-stage document processing pipeline with Milvus as the underlying vector database.

**Knowledge Milvus Base**: The foundational knowledge management component implementing a sophisticated document lifecycle and comprehensive seven-stage processing pipeline designed to transform raw source code and documentation into semantically rich, queryable knowledge assets:

### Knowledge Processing Core Functionality

**Loading Operations**: Initialize and load documents into the knowledge base with comprehensive source tracking and change detection capabilities. The system supports both individual document loading with automatic change detection and repository-level synchronization for bulk updates.

**Enrichment Fields**: AI-powered document enhancement through multiple metadata layers including summaries for concise content overviews, keywords for semantic topic tags, categories for hierarchical classification, and content graphs for relationship mapping between documents and concepts.

**Indexing Pipeline**: Systematic seven-stage workflow transforming raw documents into queryable knowledge:
1. **Source Management** — Document ingestion with change detection
2. **Indexing** — Document organization and storage
3. **Document Enrichment** — AI-powered metadata generation and semantic analysis
4. **Search Integration** — Dual-mode semantic and lexical search capabilities
5. **Project Summarization** — Dynamic project-level intelligence generation

**Search Capabilities**: Dual-mode search combining semantic and lexical patterns for comprehensive retrieval with advanced ranking, filtering, and source deduplication.

**Database Integration**: Complete lifecycle management for knowledge base maintenance including reset operations, cleanup of deleted documents, and refresh of update timestamps with Milvus vector database capabilities.

### Pydantic Data Models

**Comprehensive Model Definitions**: The system utilizes 50+ professionally organized Pydantic data structures spanning multiple functional domains, providing a robust foundation for all data structures and configurations throughout the platform. Models are organized into logical, category-based groupings for improved clarity and navigation:

**Core Models**: Imported User and AI model subsystems providing foundational data structures and dependencies.

**Communication Models**: ChatMessage, Content, and ImageUrl structures for message handling and conversation flow, with support for rich message content and metadata.

**Project Management Models**: Board, Column, and Bookmark structures for project task management and organization.

**Knowledge Management Models**: Knowledge base and document management structures with semantic analysis support.

**Tools and Extensions**: Tool definitions and tool-related structures for agent integration with sophisticated tool organization and role-based access control.

**Configuration Models**: Consolidated configuration for all system types including AI provider settings with built-in support for OpenAI, Anthropic, Mistral, and OLLAMA with defaults.

**Global Settings Models**: Comprehensive system-wide configuration organized into five logical subsections—AI configuration with provider selection, User/Access controls, Project/Workspace management, System Features, and System Maintenance.

**AI Models and Provider Configuration**: Seamless integration with multiple AI providers through dedicated configuration models with built-in provider support, provider-specific settings, configurable embedding models, and flexible provider selection.

## Project Tools and Utilities

The **Project Tools** module provides essential utility functions for file management, AI operations, and project-level interactions within the CODX Junior framework, serving as a comprehensive bridge between the AI system and project resources.

### Key Features

- **AI Initialization**: Configure AI instances with project settings and user context through the `get_ai()` utility function
- **Code Block Processing**: Convert and format code blocks with the `code_block()` function
- **Path Resolution**: Convert and validate file paths with boundary protection for secure file operations
- **File Operations**: Read and write files with UTF-8 encoding support and comprehensive validation
- **Bulk File Reading**: Process up to 10 files per operation with automatic language detection
- **Search and Knowledge Base**: Query project resources with optional AI-powered filtering and automatic result deduplication
- **Bulk Search Operations**: Execute up to 5 queries per operation with automatic deduplication
- **Project Structure Exploration**: Understand project organization with visual representation
- **Code Writer Tool**: Generate and manage code implementations with proper formatting and structure validation (scope: chat)
- **Code Block Generator**: Versatile tool for converting and formatting code blocks (scope: global)

### Working with Files

When working with files, always use code blocks and add the file name after the code block language. Maintain original file formatting and indentation when making changes. Avoid unnecessary changes, format changes, or cleanup unless explicitly requested. Validate file paths based on project context.

### Configuration

| Feature | Limit | Purpose |
|---------|-------|---------|
| **Bulk File Reading** | 10 files per call | Efficient multi-file processing |
| **Bulk Search Operations** | 5 queries per call | Comprehensive knowledge base searches |

## Custom Tools and Integration

**Custom Tools System**: A flexible and extensible framework for defining, registering, and executing specialized tools that extend the capabilities of the AI system. The custom tools module enables seamless integration of domain-specific functionality with comprehensive tool management and sophisticated execution patterns.

### Tool Architecture

**Tool Registration and Management**: Tools are registered with comprehensive metadata including tool name and description, input parameters with JSON schema validation, output format specifications, scope information, and execution context requirements.

**Tool Discovery and Organization**: Intelligent tool discovery through scope-based filtering enables precise availability control with dynamic tool discovery based on execution context.

**Tool Execution and Integration**: Tools execute within a sophisticated framework providing parameter validation, context injection, error handling with graceful degradation, result normalization, and event emission for observability.

### Custom Tool Manager

The Custom Tool Manager provides comprehensive tool management capabilities with systematic handling of tool creation, retrieval, updates, and deletion while maintaining atomic consistency.

**API Endpoints**:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/projects/custom-tools` | GET | Retrieve all custom tools for a project |
| `/api/projects/custom-tools` | POST | Create a new custom tool |
| `/api/projects/custom-tools/{tool_id}` | GET | Retrieve a specific custom tool |
| `/api/projects/custom-tools/{tool_id}` | PUT | Update an existing custom tool |
| `/api/projects/custom-tools/{tool_id}` | DELETE | Delete a custom tool |
| `/api/projects/custom-tools/{tool_id}/execute` | POST | Execute a custom tool |

**Authentication and Authorization**:
- All endpoints require authentication
- Create, update, and delete operations require admin authorization
- Execute endpoint requires only authentication without admin role
- Tool activation is required before execution

## Tools and Utilities

The platform provides a flexible tool ecosystem organized across multiple scope levels, enabling precise tool availability and security.

### Tool Organization and Design

**Centralized Aggregation System**: The tools module serves as a centralized aggregation point for all tool implementations, organizing them into a cohesive ecosystem.

**Three-Level Scoping**: Tools are organized at global, chat-level, and profile-specific scopes:
- **Global Tools**: Available across all contexts
- **Chat-Scoped Tools**: Limited to specific chat contexts
- **Profile-Specific Tools**: Available only within user profiles

**Tool Response Model**: The `ToolResponse` model enables tools to deliver tailored outputs to different audiences:
- **user_response**: User-facing output optimized for clarity and actionability
- **llm_response**: Technical context optimized for language model processing

### Available Tools

- **Code Block Generator**: Versatile tool for converting and formatting code blocks with flexible output routing
- **Code Writer**: Generate and manage code implementations with proper formatting and validation
- **Webpage Fetching**: Fetch and convert webpages to markdown for knowledge base integration
- **Project Search**: Efficiently locate project resources with optional AI-powered filtering
- **Project Read File**: Bulk file reading with automatic language detection and UTF-8 encoding support
- **Project Structure**: Explore and understand project organization with visual indicators
- **Project Write File**: Write and create files with validation and automatic parent directory creation
- **Generate Tasks Tool**: Transform chat conversations into actionable sub-tasks
- **Custom Tools**: Extensible framework for domain-specific tool development

## Profile Management

**Profile Manager**: Comprehensive system for managing user profiles and profile-related configurations with sophisticated profile discovery and lifecycle management.

### Key Features

**Hierarchical Profile Discovery**: Multiple tiers for profile discovery:
1. **Project profiles** — Located within `project_path/.codx/profiles/` with highest priority
2. **Base profiles** — Located within the system base profiles directory
3. **External provider profiles** — Profiles from external provider integrations

**Modern Folder-Based Structure**: Profiles are organized as dual-file pairs:
- `.profile` files contain JSON metadata and configuration
- `.md.profile` files contain associated markdown content

**Profile Lookup Hierarchy**: Four-level lookup priority ensuring optimal profile resolution:
1. **Project-level profiles** — Project-specific customizations with highest precedence
2. **Parent project profiles** — Inherited configurations from parent projects
3. **CODX Junior project level** — System-wide profiles as fallback
4. **External provider profiles** — External integrations as final fallback

**Content Processing and Templates**: Profile content supports template variables through explicit syntax: `{{ variable_name }}` (with spaces) for dynamic content substitution. Template variables include `{{ project_path }}` and `{{ project_name }}`.

**Profile Operations**: Comprehensive CRUD operations including loading, saving, deleting, and bulk processing of profiles across project boundaries.

## Wiki Management

**Wiki Manager**: Comprehensive system for creating and managing project wikis with sophisticated document organization, domain classification, and category management.

### Main Workflows

**Wiki Creation Process**: Orchestrates a complete workflow for generating comprehensive wikis:
1. **Repository Analysis** — Scan project files and extract source documentation
2. **Document Organization** — Automatically create hierarchical wiki structures
3. **Domain Building** — Group related documentation through semantic analysis
4. **Index Construction** — Build comprehensive search indices
5. **Category Management** — Organize content into logical hierarchical categories

### Key Components

**Document Processing**: Analyzes repository files with AI-powered categorization and content summarization for intelligent document organization. Documents are automatically categorized, with concise summaries generated and indexed keywords enabling efficient discovery.

**AI Integration**: Leverages cached AI instances for intelligent document categorization, automatic summary generation, relevance assessment, and content graph generation.

**Semantic Organization**: Creates domain structures that group related documentation together, enabling efficient knowledge discovery and cross-reference navigation.

**File Organization**: Systematically organizes wiki output with predictable naming patterns and comprehensive validation including hierarchical directory structures, automatic file naming conventions, and path validation.

### Notable Design Patterns

1. **Lazy Initialization** — Components initialize only when first accessed
2. **Concurrent Processing** — Parallel document processing for large repositories
3. **Prompt Engineering** — Sophisticated AI prompts for consistent categorization
4. **Event-Driven Architecture** — Progress callbacks for monitoring long-running operations
5. **Graceful Degradation** — Operations continue with reduced functionality when components become unavailable

## Chat Management and API

The Chat API provides a comprehensive set of endpoints for managing conversations with sophisticated operations designed for robust and reliable message handling.

### API Endpoints

**Cancellation Management**
- **POST /chat/cancel** — Abort in-progress chat operations

**Message Management**
- **POST /chat/message** — Append messages to conversations
- **PUT /chats/message** — Update existing messages
- **DELETE /chats/message** — Remove messages from chats

**Metadata Management**
- **POST /chats/metadata** — Update chat metadata separately from message operations

**Retrieval and Search**
- **GET /chats** — Retrieve conversations with optional filtering and pagination
- **POST /chat/search** — Discover conversations using flexible search

**Chat Operations**
- **POST /chat/from-url** — Generate new chats by loading content from URLs
- **POST /chat** — Initiate conversation with a project
- **PUT /chat/{chat_id}** — Persist chat state and message updates
- **DELETE /chat/{chat_id}** — Remove conversations and associated data

**Kanban Board Management**
- **GET /chat/kanban** — Retrieve kanban board assignments
- **POST /chat/kanban** — Persist kanban board state
- **DELETE /chat/kanban** — Remove kanban board assignments

## System Reliability and Observability

### Analytics Integration

The platform implements comprehensive analytics tracking throughout critical system operations. The analytics system records session start and end events capturing initialization context and completion metrics including token usage, tool execution patterns, and cache statistics. Analytics recording occurs at iteration boundaries to avoid duplicates and ensure clean observability traces. Wallet checks are explicitly integrated to track cost management and token usage across operations.

The analytics integration operates with built-in resilience: when analytics operations encounter issues, they are caught and logged appropriately rather than disrupting core service delivery.

### Crash-Safety Mechanisms

The system implements multi-layered crash-safety mechanisms designed to handle unexpected interruptions with minimal data loss. Through structured event attachment, regular state persistence, and intelligent recovery mechanisms, the platform ensures reliable operation with loss tolerance measured in seconds even during hard system failures.

### Error Handling and Resilience

The system implements comprehensive error handling across multiple dimensions with graceful degradation as a core principle. Errors encountered during tool execution, argument parsing, validation, analytics operations, cancellation handling, and loop protection are managed without disrupting primary service delivery.

## Lifecycle Management

**Startup Events**: The application initializes critical components during startup including FastAPI configuration with all middleware layers, Socket.IO server instantiation, database connection establishment and schema initialization, knowledge base initialization with Milvus connectivity verification, and AI provider configuration with credential validation.

**Shutdown Events**: The application implements graceful shutdown through coordinated teardown of all services including completion of in-flight chat operations with state persistence, database connection closure with transaction cleanup, and Socket.IO connection termination.

## User Authorization and Access Control

The platform implements role-based access control to manage user permissions:

**Authorization Rules**:
- **Authentication Required**: All API endpoints require user authentication
- **Admin Operations**: Custom tool creation, updates, and deletion require admin authorization
- **Execution Access**: Tool execution and most read operations require only authentication
- **Project Ownership**: Users access and modify their own projects with explicit cross-project authorization rules
- **Workspace Access Logic**: User access controlled at workspace level with sophisticated filtering

## Environment Configuration

The system supports flexible configuration through environment variables:

**Key Configuration Variables**:
- **Provider Settings**: Configure AI provider selection (OpenAI, Anthropic, Mistral, OLLAMA)
- **API Keys**: Store API credentials for external services
- **Database Configuration**: Set connection parameters for data persistence
- **Knowledge Base Settings**: Configure Milvus and embedding model parameters
- **Feature Flags**: Enable/disable specific platform features
- **Performance Settings**: Adjust timeout values and resource limits

## Real-Time Communication

**Socket.IO Integration**: The application leverages Socket.IO for real-time bidirectional communication:

- **Namespace Architecture**: Dedicated namespaces provide organized communication channels
- **Live Chat Updates**: Real-time message delivery and conversation synchronization
- **Status Notifications**: Immediate notification delivery for system status changes
- **Collaborative Features**: Support for live collaboration scenarios with synchronized state
- **Event-Driven Communication**: Structured event system for precise control

## API Routers and Endpoints

The application exposes a comprehensive set of API endpoints through registered routers, organized into functional categories and accessible under the `/api` prefix:

### Router Organization

All specialized routers are integrated into the FastAPI application with consistent endpoint organization:
- **Projects Router** — Project management and configuration
- **Files Router** — File operations and content management
- **Code Router** — Code analysis and transformations
- **Profiles Router** — User profile and settings management
- **Chat Router** — Conversation and message operations
- **Knowledge Router** — Knowledge base and semantic search
- **Custom Tools Router** — Custom tool management and execution

### Request Timeout Handling

The application enforces a 280-second timeout on all HTTP requests through middleware. This timeout is designed to prevent long-running requests from consuming resources indefinitely while providing sufficient time for complex operations to complete.

### Logging Configuration

The App Module implements selective logging to optimize performance and focus on critical operations. The following loggers are disabled to reduce noise:
- **httpx** — HTTP client logging suppressed
- **openai** — OpenAI client logging suppressed
- **watchfiles** — File monitoring logging suppressed
- **asyncio** — Async runtime logging suppressed

## Documentation Organization and Approach

This wiki employs a refined documentation structure that prioritizes clarity and practical utility:

### Content Organization Principles

- **User-Focused Structure**: Documentation organized around capabilities, use cases, and practical benefits
- **API-Reference Format**: Chat API and custom tools documentation uses structured sections for quick-reference clarity
- **Feature-Focused Sections**: Tool documentation emphasizes capabilities, use cases, and practical benefits
- **Professional Formatting**: Standardized tables, structured headings, and consistent section organization
- **Practical Integration Guidance**: Integration notes and configuration requirements clearly separated from API specifications
- **Progressive Disclosure**: Users understand high-level capabilities from this overview and navigate for detailed implementation guidance
- **Diagnostic-Focused Problem Analysis**: Error handling documentation emphasizes root cause analysis
- **High-Level Architecture Focus**: Core architecture and responsibilities documented at system level
- **SmolAgent Documentation**: Emphasizes the iterative execution pattern, intelligent state management, comprehensive tool management with caching and loop protection, event emission systems, crash-safe operations with multi-layered persistence checkpoints, tool call processing with cached vs. uncached phases, tool response types with traditional and dual-response patterns, streaming strategy with accumulation-based callback flushing, and cancellation handling with distinct legacy and runtime token mechanisms
- **Pydantic Data Models Organization**: Category-based structure grouping models into logical functional domains

### Navigation Structure

This wiki is organized into the following primary sections:

- **Project Overview**: High-level architecture understanding and system purpose
- **App Module**: FastAPI configuration, middleware setup, Socket.IO integration
- **Engine Module**: Core backend logic, project operations, and session handling
- **AI and Knowledge Management**: Agents including SmolAgent with comprehensive documentation; Pydantic data models organized into logical categories; and knowledge processing with sophisticated seven-stage document pipeline
- **Database and Data Storage**: Data persistence strategies and storage architecture
- **Security and Authentication**: Authentication mechanisms and security practices
- **Session Management**: Session lifecycle, channel coordination, and state management
- **Profile Management**: User profile management with hierarchical discovery and lifecycle operations
- **Wiki Management**: Wiki creation and maintenance with document organization and category management
- **Custom Tools and Integration**: Flexible tool framework with domain-specific functionality
- **Project Tools and Utilities**: File management, AI operations, and project-level interactions
- **Tools and Utilities**: Tool implementations, response patterns, and helper modules
- **Chat Engine and API**: Central orchestration hub with message lifecycle management and crash-safe operations
- **Utility Functions**: Reference helper modules and supporting functionality

### Using This Documentation

Each section in this wiki is designed for practical reference with clear architectural overviews, feature highlights, key responsibilities, design patterns, and integration context. Navigate to specific sections for detailed implementation guidance, or use the search functionality to locate information on particular components.

---

**Last Updated**: This documentation reflects the current state of the CODX Junior API with comprehensive organizational improvements enhancing clarity and practical utility. SmolAgent documentation has been reorganized to emphasize the iterative execution pattern, intelligent state management, comprehensive tool management with sophisticated caching and loop protection mechanisms, crash-safe operations with multi-layered persistence checkpoints, callback batching strategies, tool argument parsing capabilities, sophisticated event emission systems across request lifecycle, LLM interactions, and tool execution, with explicit emphasis on tool call processing phases, tool response types, and streaming strategy. The wiki now features streamlined content organization prioritizing user-facing functionality over implementation details while preserving all core technical accuracy.