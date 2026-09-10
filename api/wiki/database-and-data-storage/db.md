# Database and Data Storage

## Overview

This module provides data models and storage structures for the CODX Junior system, including chat management, recipe workflows, kanban boards, and associated metadata. All models are built using Pydantic for validation and serialization.

## Core Models

### Message

Represents a single chat message with support for attachments, tool events, and lifecycle tracking.

**Key Fields:**
- `doc_id`: Document identifier
- `role`: Message author role (user/assistant)
- `content`: Message text content
- `think`: Optional thinking/reasoning content
- `attachments`: List of ChatAttachment objects
- `tool_events`: Tool execution events associated with response messages
- `lifecycle_events`: Agent run lifecycle events
- `created_at` / `updated_at`: Timestamps
- `recipe_step_index`: Index when part of a recipe
- `recipe_step_action`: Action context ('instruction', 'hint', 'validation', 'result')
- `recipe_requires_acknowledgment`: Flag for explicit user acknowledgment

### Chat

Represents a chat session with messages, metadata, and kanban board associations.

**Key Features:**
- Support for standalone conversations or recipe-based chats
- Parent-child chat relationships via `parent_id` and `message_id`
- Linked chat references across projects
- File management with `file_list`
- Knowledge indexing via `knowledge_topics`
- Auto-initialization support for AI-assisted setup

**Notable Fields:**
- `project_id`: Working project reference
- `owner_project_id`: Project where chat was created
- `kanban_id` / `column_id`: Board organization
- `recipe_id`: Links to Recipe if part of a workflow
- `ignore_parent_knowledge`: Disconnect from parent context when True
- `ignore_parent_files`: Exclude parent file list when True

### Recipe

A reusable template or instance for accomplishing goals through ordered steps.

**Recipe Types:**
- `tutorial`: Interactive step-by-step learning
- `automation`: Unattended background jobs
- `workflow`: Multi-step manual procedures
- `playbook`: Structured troubleshooting

**Key Features:**
- Template/Instance distinction via `is_template`
- Version tracking with semantic versioning
- Execution metrics and progress tracking
- Scheduled automation support
- Related recipe linking

**Fields:**
- `steps`: Ordered list of RecipeStep objects
- `tags`: Categorization labels
- `metrics`: Progress tracking (instances only)
- `auto_execute`: Enable unattended execution
- `auto_execute_schedule`: Cron expression for automation
- `meta_data`: Custom extensibility

### RecipeStep

A single step within a recipe.

**Step Types:**
- `instruction`: Read-only guidance
- `exercise`: User performs action
- `validation`: Check/verification
- `action`: Automated execution

**Key Fields:**
- `step_index`: Execution order (0-based)
- `chat_id`: Reference to associated Chat
- `step_type`: Type of step
- `is_required`: Must complete to advance
- `success_criteria`: Completion requirements
- `estimated_duration_seconds`: Time estimate

## Supporting Models

### ChatAttachment

Represents images in chats with metadata and base64 encoding.

**Validation:**
- Max size: 50MB (configurable via `MAX_IMAGE_SIZE_MB`)
- Allowed types: PNG, JPEG, GIF, WebP, SVG

### ToolEvent

Tracks tool execution within agent runs.

**Status Values:**
- `running`: Tool currently executing
- `done`: Execution completed
- `error`: Execution failed

**Fields:**
- `tool`: Tool name
- `tool_call_id`: Unique call identifier
- `request`: Parsed arguments
- `response`: Result preview
- `duration_ms`: Execution time
- `error`: Error details when applicable

### LifeCycleEvent

Tracks agent run status and metrics.

**Status Values:**
- `running`: Run in progress
- `done`: Run completed
- `error`: Run failed

**Fields:**
- `run_id`: Unique run identifier
- `duration_ms`: Total execution time
- `error`: Error details when applicable

### Kanban

Represents a kanban board with columns and chats.

**Fields:**
- `title`: Board name
- `description`: Board purpose
- `columns`: List of KanbanColumn objects
- `created_at` / `updated_at`: Timestamps

### KanbanColumn

Represents a column within a kanban board.

**Fields:**
- `title`: Column name
- `color`: Visual indicator
- `index`: Column order
- `chats`: Associated chat IDs

### RecipeMetrics

Aggregated metrics for recipe execution tracking.

**Tracked Metrics:**
- `total_steps`: Step count
- `completed_steps`: Finished steps
- `skipped_steps`: Bypassed steps
- `failed_steps`: Failed steps
- `completion_percent`: Progress percentage
- `total_duration_seconds`: Total execution time
- `last_completed_step_index`: Latest completed step

### ChatHistoryEntry

Historical entry in a chat with summary and timestamps.

**Fields:**
- `timestamp`: Entry creation time
- `summary`: Entry summary
- `message_ids`: Associated message identifiers

### ChatId

Reference to a chat in another project.

**Fields:**
- `chat_id`: Chat identifier
- `project_id`: Owner project identifier

## Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `ROLE_USER` | "user" | Message author is user |
| `ROLE_ASSISTANT` | "assistant" | Message author is assistant |
| `MAX_IMAGE_SIZE_MB` | 50 | Maximum image file size |
| `MAX_IMAGE_SIZE_BYTES` | 52,428,800 | Maximum in bytes |

## Enumerations

### MessageTaskItem

Task item type enumeration.

**Values:**
- `SUMMARY`: Summary task

## Dependencies
**Imports from:** codx/junior/settings.py, codx/junior/model/model.py
**Imported by:** codx/junior/agents/git_issues_agent.py, codx/junior/api/chat.py, codx/junior/app.py, codx/junior/chat/chat_engine.py, codx/junior/chat/chat_export.py, codx/junior/chat/chat_knowledge.py, codx/junior/chat_manager.py, codx/junior/engine/chat_engine_actions.py, codx/junior/engine/code_engine.py, codx/junior/engine/file_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/engine/wiki_engine.py, codx/junior/events/event_manager.py, codx/junior/knowledge/knowledge_ai_search_message.py, codx/junior/mentions/mention_manager.py, codx/junior/sio/model.py, codx/junior/tools/code_writer.py, tests/db/test_db.py