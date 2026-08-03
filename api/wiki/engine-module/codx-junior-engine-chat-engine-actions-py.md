# Chat Engine Actions Module Documentation

## Overview

The Chat Engine Actions module is a core component of the codx-junior engine that handles chat interactions, task generation, summarization, and AI messaging. It serves as the primary orchestrator for managing conversations with AI and the project knowledge base.

## Architecture

The module is structured around the `ChatEngineActions` class, which coordinates multiple operations:

- **chat_with_project**: Core method for orchestrating chat with AI and knowledge
- **chat_search**: Search functionality within chat context
- **api_chat_with_project**: API-based chat interface
- **summarize_chat**: Conversation summarization using AI
- **generate_tasks**: Automated sub-task generation and parallel processing
- **init_chat_from_url**: Initialize chats from URL content
- **convert_message**: Message conversion for LangChain compatibility

## Core Components

### ChatEngineActions Class

The main class that handles all chat-related operations. It maintains a reference to the parent `CODXJuniorSession` and provides shortcuts to session settings and event management.

**Key Properties:**
- `settings`: Direct access to session configuration
- `event_manager`: Event broadcasting mechanism

### Status Tracking Data Classes

#### SubTaskStatus

Tracks individual sub-task execution state with the following attributes:

- `name`: Task identifier
- `status`: Current state (pending | creating | done | error)
- `time_taken`: Execution duration in seconds
- `error`: Error message if applicable

#### TaskGenerationStatus

Tracks the overall task generation process with lifecycle phases and real-time status rendering:

- `phase`: Process state (starting | analyzing | creating | done | error)
- `total`: Total number of tasks
- `sub_tasks`: List of individual task statuses
- `start_time` / `end_time`: Temporal tracking

The `render()` method provides human-readable markdown status blocks with emoji indicators and progress tables, updated throughout execution.

## Core Methods

### chat_with_project()

The primary orchestration method for chat processing.

**Parameters:**
- `chat`: Chat object to process
- `disable_knowledge`: Skip knowledge retrieval when True
- `callback`: Optional streaming callback for real-time updates
- `append_references`: Include document references in response
- `chat_mode`: Override default chat mode
- `iteration`: Recursion depth tracking

**Process Flow:**
1. Creates a ChatEngine instance
2. Delegates to ChatEngine for actual processing
3. Saves the updated chat to persistence
4. Returns tuple of (updated_chat, documents)

### generate_tasks()

Converts a chat conversation into structured sub-tasks with parallel processing.

**Parameters:**
- `chat`: Parent chat to decompose
- `instructions`: Additional AI instructions

**Execution Phases:**

1. **Starting Phase**: Initialize status tracking and messaging
2. **Analyzing Phase**: Use AI to parse chat content into structured tasks
   - Sends content summary through AI prompt
   - Extracts JSON task list with retry logic (up to 2 attempts)
3. **Creating Phase**: Process sub-tasks in parallel
   - Each sub-task becomes an independent chat linked to parent via `parent_id`
   - Sub-tasks inherit board, column, project_id, and mode from parent
   - Initial message enhances task description using context
   - Results are saved and broadcast via event manager
4. **Done Phase**: Finalize and broadcast completion status

**Output:**
- Original chat contains JSON task list from AI
- Live status message updated throughout execution
- New chat objects created for each sub-task with parent relationship

### summarize_chat()

Generates AI-powered summaries of conversations.

**Parameters:**
- `chat`: Chat to summarize
- `instructions`: Custom summarization instructions

**Behavior:**
- Returns cached summary if most recent message is already a summary
- Appends summary prompt to chat messages
- Marks response as hidden and tagged with SUMMARY task item
- Preserves original message chain

### chat_search()

Enables semantic search within chat context.

**Process:**
1. Extracts chat description as context
2. Uses AI to convert user query into optimized search terms
3. Performs project knowledge search with generated query
4. Augments chat with search context
5. Processes through chat_with_project

### api_chat_with_project()

Provides API-compatible chat interface with named profiles.

**Parameters:**
- `profile_name`: Profile identifier
- `messages`: List of dicts with 'role' and 'content'

**Returns:** Updated Chat object

### init_chat_from_url()

Initializes chat from URL content.

**Process:**
1. Downloads content from chat.url
2. Uses AI to extract title and content from HTML
3. Parses JSON response from AI
4. Sets chat name and initial message

### get_chat_analysis_parents()

Traverses parent chat hierarchy to collect contextual information.

**Returns:** Concatenated visible messages from all parent chats

### convert_message()

Converts database Message objects to LangChain-compatible formats.

**Supported Conversions:**
- Messages with images: Structured format with image URLs
- User messages: HumanMessage objects
- Assistant messages: AIMessage objects

## Key Features

### Real-time Status Rendering

The `TaskGenerationStatus.render()` method provides live progress updates with:
- Phase-specific messaging with emoji indicators
- Task completion counters
- Individual task status table with timing information
- Elapsed time tracking

### Parallel Sub-task Processing

The `generate_tasks()` method uses Python's `asyncio.gather()` to process multiple sub-tasks concurrently, with error handling for individual failures while maintaining overall progress.

### Context Preservation

Sub-tasks maintain connection to parent chats through `parent_id` relationships, enabling hierarchical task decomposition and context traversal.

### Event Broadcasting

All operations broadcast events through `event_manager` for real-time UI updates:
- Message events for streaming responses
- Chat events for task creation
- Status updates throughout processing phases

## Error Handling

The module implements comprehensive error handling:
- Exception logging and propagation
- Graceful degradation in task generation (retry logic)
- Per-task error tracking with user feedback
- Overall process error phase with status reporting

## Dependencies
**Imports from:** codx/junior/chat/chat_engine.py, codx/junior/db.py, codx/junior/profiling/profiler.py, codx/junior/utils/utils.py, codx/junior/engine/session.py
**Imported by:** codx/junior/engine/session.py