# Globals Configuration

## Overview

This module defines global constants, environment variables, and configuration settings used throughout the `codx-api` project. It centralizes system-wide parameters related to file processing, application management, logging, analytics, and workspace management.

---

## Environment Variables

The following environment variables are read at startup to configure the system:

| Variable | Constant | Default Value | Description |
|---|---|---|---|
| `HOST_USER` / `USER` | `HOST_USER` | `None` | Resolves the current host user |
| `CODX_JUNIOR_API_BACKGROUND` | `CODX_JUNIOR_API_BACKGROUND` | `None` | Background API setting |
| `CODX_JUNIOR_PROJECTS_PATH` | `CODX_JUNIOR_PROJECTS_PATH` | `None` | Path to projects directory |
| `CODX_JUNIOR_API_LOGS` | `LOGS_FOLDER` | `/tmp/codx-junior-logs` | Directory for log files |
| `CODX_JUNIOR_API_ANALYTICS_DATA_PATH` | `ANALYTICS_DATA_PATH` | `/home/codx-junior/analytics` | Global analytics data path |
| `CODX_JUNIOR_AI_RAW_LOG_PATH` | `CODX_JUNIOR_AI_RAW_LOG_PATH` | `/home/codx-junior/analytics/chats` | Path for raw AI chat logs |
| `CODX_JUNIOR_WORKSPACES_FOLDER` | `CODX_JUNIOR_WORKSPACES_FOLDER` | `/home/codx-junior/codx-junior-global-settings.json/workspaces` | Workspace configuration and files folder |
| `CODX_JUNIOR_DEFAULT_WORKSPACE_PATH` | `CODX_JUNIOR_DEFAULT_WORKSPACE_PATH` | `/home/codx-junior-projects/codx-junior/workspace-templates` | Default workspace template path |

---

## Time Constants

These constants control how file changes and file mentions are processed based on their age:

- **`MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS`** — Set to `3600` seconds (1 hour). Changed files older than this threshold will **not** be processed for file change events.
- **`MAX_OUTDATED_TIME_TO_PROVESS_FILE_MENTIONS_IN_SECS`** — Set to `180` seconds (3 minutes). Controls the maximum age for processing file mentions.

---

## Application Registry

### `APPS`

A list of registered applications available in the system. Each entry includes:

- **`name`** — Identifier for the application (e.g., `"chrome"`)
- **`icon`** — URL to the application icon image
- **`description`** — Human-readable description of the application

Currently registered applications:

| Name | Description |
|---|---|
| `chrome` | Google Chrome browser engine |

### `APPS_COMMANDS`

A dictionary mapping application names to their launch commands:

| Application | Command |
|---|---|
| `chrome` | `google-chrome --no-sandbox --no-default-browser-check` |

---

## Agent Control

- **`AGENT_DONE_WORD`** — A special sentinel string (`$$@@AGENT_DONE@@$$$`) used to signal that an agent has completed its task.

---

## Language and Parsing Configuration

These constants support code parsing and text splitting functionality:

- **`CURRENT_SPLITTER_LANGUAGES`** — A dynamically generated list of supported language identifiers derived from `langchain_text_splitters.Language`, normalized to lowercase.
- **`LANGUAGE_PARSER_MAPPING`** — A dictionary that maps non-standard file extensions to their corresponding parser language:

| Extension | Maps To |
|---|---|
| `ts` | `js` |
| `cs` | `csharp` |

---

## Logging

A module-level logger is initialized using:

```python
logger = logging.getLogger(__name__)
```

This logger is available for use throughout the module and follows the standard Python logging hierarchy.

## Dependencies
**Imported by:** codx/junior/ai/raw_log_reader.py, codx/junior/ai/raw_logger.py, codx/junior/analytics/analytics.py, codx/junior/api/analytics.py, codx/junior/api/users.py, codx/junior/app.py, codx/junior/background.py, codx/junior/changes/change_manager.py, codx/junior/chat/chat_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/knowledge/knowledge_code_splitter.py, codx/junior/utils/utils.py