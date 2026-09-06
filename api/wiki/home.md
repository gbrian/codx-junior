# CodX Junior API Documentation

## Welcome to CodX Junior API

CodX Junior is a comprehensive API framework built with FastAPI that powers intelligent project management and AI-driven development assistance. This documentation provides detailed information about the architecture, modules, and tools that make up the system.

## Project Architecture

The CodX Junior API is organized into several core modules that work together to deliver a unified platform:

### Core Modules

**App Module** – Initializes and manages the FastAPI application, including configuration, routes, middleware setup, and real-time communication via Socket.IO. It also orchestrates background tasks that keep the system responsive and efficient.

**Engine Module** – Handles essential backend operations such as project creation, session management, Git operations, and other high-level functionalities. The Engine provides the business logic necessary to support all features exposed by the App Module. It includes specialized components like the Git Engine for comprehensive version control operations, repository management, and file version tracking across repository history.

**Chat Engine** – The intelligent orchestrator for crash-safe, multi-mode chat interactions with AI models through event-driven persistence. Supports four distinct conversation modes (chat, task, agent, vibe), each optimized for specific interaction patterns. Implements systematic data protection through early metadata creation, persistent event logging with atomic operations, and efficient streaming persistence. Features include multi-level chat hierarchy support for knowledge inheritance, comprehensive session analytics with timing and token tracking, and a global cancellation token system with ISO-8601 timestamp tracking for fine-grained request control.

**Crash-Safe Architecture** – Implements systematic data protection through three layered mechanisms: early chat metadata creation enables recovery from interruptions, persistent event logging with atomic operations prevents data loss, and throttled streaming persistence efficiently manages high-frequency updates. Immediate error state preservation captures diagnostics for troubleshooting, minimizing data loss windows through atomic operations and ensuring hidden reasoning is persisted before streaming begins.

**Advanced Features** – Provides fine-grained cancellation support using a UUID-based global registry with ISO-8601 timestamp tracking and comprehensive session analytics including timing metrics, token usage tracking, tool execution tracking, and error states. Supports parent chat knowledge and file inheritance through configurable flags, enabling selective knowledge reuse and context propagation across related conversations. Enables hierarchical chat structures where child conversations inherit settings and context from parent conversations while respecting explicit inheritance controls.

**AI and Knowledge Management** – Integrates artificial intelligence capabilities with robust knowledge processing systems. This includes intelligent agents for specialized tasks, language models for AI-driven features, and comprehensive knowledge indexing and retrieval systems. The system supports multiple language models (OpenAI, vLLM) and provides embeddings-based knowledge retrieval for intelligent decision-making organized across a three-tier architecture (Milvus for vector storage, AISearch for advanced search capabilities, and ChatKnowledge for conversation-specific indexing).

**Database and Data Storage** – Manages persistent data storage with database routing and configuration, ensuring reliable data persistence across the application. Includes project settings management with versioning, history tracking, and configuration backup capabilities.

**Security and Authentication** – Implements secure authentication mechanisms including GitHub OAuth integration and user management to protect resources and manage access control.

**Session Management** – Handles user sessions, real-time communication channels, and session state management to support collaborative features.

**Utility Functions** – Provides helper functions and tools used throughout the project, including chat utilities, browser automation, and logging features.

## Key Features

### Intelligent Chat Engine

The Chat Engine orchestrates sophisticated chat interactions with AI models featuring advanced reliability, control, and observability through crash-safe event-driven persistence:

**Chat Modes** – Four distinct modes optimized for different interaction patterns:

| Mode | Identifier | Purpose |
|------|-----------|---------|
| **task** | task | Document refinement and iterative task completion |
| **chat** | chat | Standard conversational mode for general discussions |
| **agent** | agent | Complex workflows with configurable iteration counts |
| **vibe** | vibe | Contextual understanding with AI-driven nuanced interactions |

**Core Workflow** – The Chat Engine manages a systematic ten-step processing pipeline:

1. Message reception and parsing with multimodal content support
2. Format conversion and embedded file extraction
3. Recursive message history construction combining message and parent context
4. Profile-based system prompt assembly tailored to conversation mode
5. User context integration respecting inheritance configuration flags
6. Pre-Search for quick context identification
7. RAG Search for semantic matching with configurable disable conditions
8. AI-powered response generation with model resolution
9. Result persistence with crash-safety mechanisms
10. Analytics recording with timing metrics and token usage data

**Crash-Safe Persistence** – Systematic data protection throughout the conversation lifecycle ensuring reliability and recoverability:

1. Early chat metadata creation enables recovery from interruptions
2. Persistent event logging with atomic operations prevents data loss
3. Throttled streaming persistence manages high-frequency updates efficiently
4. Hidden reasoning is persisted before streaming begins

**Cancellation Support** – Fine-grained request cancellation through a global UUID-based registry:
- Tokens registered at initialization with ISO-8601 timestamp tracking
- Cancellation by ID or token reference enabling graceful shutdown
- Full lifecycle visibility and request interruption capabilities

**Parent Chat Integration** – Nested chat structures with hierarchical support:
- Child conversations inherit settings, context, and knowledge from parent conversations
- Multi-level relationships traversed automatically
- Explicit inheritance control flags for selective knowledge reuse

**Session Analytics** – Comprehensive monitoring including:
- Conversation timing metrics and performance measurement
- Token usage tracking and cost monitoring
- Tool execution tracking with execution metrics
- Error state recording for diagnostic purposes

### SmolAgent: Flow-Centric Streaming Chat Agent

**SmolAgent** is an async-first streaming chat agent engineered for sophisticated, real-time interaction patterns with language models:

- **Async-First Architecture** – Purpose-built for asynchronous operations enabling responsive, non-blocking chat interactions with full control over conversation lifecycle and real-time message streaming

- **Multi-Turn Conversation Lifecycle** – Structured execution spanning initialization, iterative chat loops, streaming completion, tool execution, and controlled cancellation

- **Intelligent Tool Management** – Tool scope system distinguishing between global and chat-scoped tools with configurable result caching to optimize repeated operations

- **Real-Time Streaming** – Enables continuous message streaming with full response accumulation and crash-safety through time-based and explicit flushing mechanisms

- **Comprehensive Event System** – Real-time event emission throughout the conversation lifecycle with visibility into tool calls, arguments, results, and execution duration

- **Robust Tool Execution Pipeline** – Configurable tool call processing with result normalization, cache management, and cancellation checkpoints

- **Cost Management** – User wallet validation and cost estimation ensure operations remain within budget constraints

- **Request Tracing** – Unique request identifiers enable comprehensive conversation tracing with token usage tracking and complete observability

### Intelligent Tool Ecosystem

The platform includes a sophisticated tool ecosystem organized by scope (chat-based and system-wide) with support for both single and bulk operations. Tools are designed to integrate seamlessly with AI agents while maintaining clear separation between immediate chat-context tools and broader system-level utilities.

### Advanced Streaming Agents

Multiple specialized agents handle different aspects of development tasks, from DevOps operations to Git issue management. These agents leverage the SmolAgent framework to deliver sophisticated, real-time capabilities tailored to specific use cases and workflows.

### Comprehensive Version Control Integration

The Git Engine provides comprehensive version control management through a structured, method-focused API with consistent parameter and return value specifications:

**Repository Operations** – Manage repository state, initialize repositories, and handle multi-Git scenarios for complex version control workflows.

**Branch Operations** – Complete branch management including creation, switching, deletion, and tracking across project branches.

**Commit Operations** – Detailed tracking and analysis of commits with full context and change detection capabilities.

**File History and Versioning** – Explore file states across commit history with depth-based precision, supporting both main project and subproject file navigation.

**Pull Request & Review Operations** – Comprehensive pull request management including creation, review, and status tracking.

**Code Change Summarization** – Comprehensive analysis of modifications, additions, and deletions across the repository with detailed breakdown by file.

Key capabilities include depth-based file retrieval, structured code change analysis, subproject support, robust error handling, standardized return formats, and multi-Git support for repositories containing multiple Git instances.

### Project Settings Management

The Settings Manager provides robust configuration management for projects with automatic directory creation, automatic configuration backup before every write operation, complete audit trail with history tracking, Pydantic model support, UTF-8 encoding with consistent JSON formatting, and comprehensive validation.

### Knowledge Management

Advanced document processing, code analysis, and keyword extraction systems enable the platform to understand and work with large codebases. The knowledge system supports semantic search through both Pre-Search and RAG Search mechanisms organized across a three-tier architecture (Milvus for vector storage, AISearch for advanced search capabilities, and ChatKnowledge for conversation-specific indexing), intelligent code splitting, QA generation, and comprehensive document enrichment with structured data schemas.

### Real-Time Communication

Built on Socket.IO, the platform enables real-time interactions between clients and the server, supporting live updates for sessions, progress tracking, and collaborative features.

## Navigation

Use the sidebar to explore specific modules and components. Each section contains detailed documentation about implementation, APIs, and usage patterns. Start with the relevant category based on what you're working with:

- **Project Overview** – High-level system architecture and design principles
- **App Module** – FastAPI application initialization, configuration, and routing
- **Engine Module** – Core backend operations, Git management, and session handling
- **AI and Knowledge Management** – Agents, models, knowledge processing, and the Chat Engine
- **Database and Data Storage** – Data persistence, storage configuration, and settings management
- **Security and Authentication** – Authentication mechanisms and access control
- **Session Management** – Session handling and real-time communication
- **Utility Functions** – Helper tools and scripts

For specific implementation details, method signatures, parameter documentation, and structured code examples showing return data formats, navigate to the relevant module section in the documentation.