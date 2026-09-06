# CodX Junior API Documentation

## Welcome to CodX Junior API

CodX Junior is a comprehensive API framework built with FastAPI that powers intelligent project management and AI-driven development assistance. This documentation provides detailed information about the architecture, modules, and tools that make up the system.

## Project Architecture

The CodX Junior API is organized into several core modules that work together to deliver a unified platform:

### Core Modules

**App Module** – Initializes and manages the FastAPI application, including configuration, routes, middleware setup, and real-time communication via Socket.IO. It also orchestrates background tasks that keep the system responsive and efficient.

**Engine Module** – Handles essential backend operations such as project creation, session management, Git operations, and other high-level functionalities. The Engine provides the business logic necessary to support all features exposed by the App Module. It includes specialized components like the Git Engine for comprehensive version control operations, repository management, and file version tracking across repository history.

**AI and Knowledge Management** – Integrates artificial intelligence capabilities with robust knowledge processing systems. This includes intelligent agents for specialized tasks, language models for AI-driven features, and comprehensive knowledge indexing and retrieval systems. The system supports multiple language models (OpenAI, vLLM) and provides embeddings-based knowledge retrieval for intelligent decision-making.

**Database and Data Storage** – Manages persistent data storage with database routing and configuration, ensuring reliable data persistence across the application. Includes project settings management with versioning, history tracking, and configuration backup capabilities.

**Security and Authentication** – Implements secure authentication mechanisms including GitHub OAuth integration and user management to protect resources and manage access control.

**Session Management** – Handles user sessions, real-time communication channels, and session state management to support collaborative features.

**Utility Functions** – Provides helper functions and tools used throughout the project, including chat utilities, browser automation, and logging features.

## Key Features

### Intelligent Tool Ecosystem

The platform includes a sophisticated tool ecosystem organized by scope (chat-based and system-wide) with support for both single and bulk operations. Tools are designed to integrate seamlessly with AI agents while maintaining clear separation between immediate chat-context tools and broader system-level utilities. The tool system emphasizes efficiency through bulk operations, enabling developers to perform multiple actions simultaneously rather than sequentially.

### AI-Driven Capabilities

Multiple specialized agents handle different aspects of development tasks, from DevOps operations to Git issue management. The system supports various language models and provides embeddings-based knowledge retrieval for intelligent decision-making. Agents are designed with flexible scoping to handle both chat-based interactions and system-wide operations.

### Comprehensive Version Control Integration

The Git Engine is a specialized sub-engine within the Engine Module that handles all Git repository operations within the codx-junior ecosystem. It provides comprehensive version control management organized into five functional areas:

**1. Repository Information** – Access repository metadata, branch information, and commit history with structured outputs for seamless integration with other system components.

**2. Commit Operations** – Detailed tracking and analysis of commits with full context and change detection capabilities, including commit metadata, authorship, and temporal information using ISO 8601 timestamps.

**3. Change Detection** – Comprehensive analysis of code modifications across commits and branches, with detailed breakdown of additions, modifications, and deletions organized by file.

**4. File Operations** – Explore file states across commit history with depth-based precision, enabling developers to retrieve specific file versions at configurable depth levels (depth=0 for current state, depth=1 for previous commit, depth=2 for two commits ago, etc.).

**5. Repository Changes** – Structured analysis and tracking of modifications across the repository with detailed breakdown by file, including local uncommitted changes and comprehensive diff capabilities.

Key capabilities include:

- **Depth-based file retrieval** – Explore file states across commit history with precision using configurable depth levels and concrete data structure outputs
- **Code change summarization** – Comprehensive analysis of modifications, additions, and deletions across the repository with detailed breakdown by file, including local uncommitted changes in comparisons
- **Branch sanitization** – Automatic handling of branch names with special character validation and normalization for consistent operations
- **Git root resolution** – Intelligent detection and resolution of repository root directories for accurate path handling across nested projects
- **File tracking** – Precise file state tracking across multiple commits with configurable depth navigation for historical analysis
- **Subproject support** – Specialized handling for repositories containing subprojects with depth-based navigation
- **Error handling and validation** – Robust handling of edge cases and error scenarios throughout all Git operations with consistent error reporting and input sanitization
- **Standardized return formats** – Consistent dictionary and list structures with structured Python data for commits, file changes, and repository modifications
- **ISO 8601 timestamps** – All temporal data uses standardized timestamp formatting for consistency across all file operations and commit tracking
- **Multi-Git support** – Utilities for handling repositories with multiple Git instances and complex version control scenarios
- **Categorized method organization** – Methods are logically organized by functional category for improved discoverability and maintainability

The Git Engine integrates seamlessly with CODXJuniorSession and Project Settings to provide context-aware repository operations. This enables sophisticated features like version comparison, historical analysis, comprehensive code review workflows, and PR/review details retrieval while maintaining consistency with the Knowledge System.

### Project Settings Management

The Settings Manager provides robust configuration management for projects with built-in versioning, history tracking, and automated backups. Key capabilities include:

- **Automatic directory creation** – Directories are created automatically during initialization for seamless setup
- **Configuration backup** – Backups occur before every write operation, ensuring previous states are always recoverable
- **History tracking** – Complete audit trail of configuration changes with newest to oldest ordering
- **Pydantic model support** – Accepts Pydantic models alongside standard Python dictionaries for flexible data handling
- **UTF-8 encoding** – All configuration files use UTF-8 encoding with 2-space JSON indentation for consistency and readability
- **Comprehensive validation** – Multi-stage validation process with special handling for list items and model validation

### Knowledge Management

Advanced document processing, code analysis, and keyword extraction systems enable the platform to understand and work with large codebases. The knowledge system supports semantic search, code splitting, QA generation, and comprehensive document enrichment with structured data schemas for reliable API integration.

### Real-Time Communication

Built on Socket.IO, the platform enables real-time interactions between clients and the server, supporting live updates for sessions, progress tracking, and collaborative features.

## Navigation

Use the sidebar to explore specific modules and components. Each section contains detailed documentation about implementation, APIs, and usage patterns. Start with the relevant category based on what you're working with:

- **Project Overview** – High-level system architecture and design principles
- **Engine Module** – Core backend operations, Git management, and session handling
- **AI and Knowledge Management** – Agents, models, and knowledge processing systems
- **Database and Data Storage** – Data persistence, storage configuration, and settings management
- **Security and Authentication** – Authentication mechanisms and access control
- **Session Management** – Session handling and real-time communication
- **Utility Functions** – Helper tools and scripts

For specific implementation details, parameter documentation, and structured code examples showing return data formats, navigate to the relevant module section in the documentation.