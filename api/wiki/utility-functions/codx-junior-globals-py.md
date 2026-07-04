# Global Utility Configuration

This documentation covers the global settings and utility configurations for the Codx-Junior API.

## Environment Variables and Paths
The system utilizes several environment variables to define core paths and operational parameters:

*   **Host Identification**: The `HOST_USER` is determined by the `HOST_USER` environment variable, defaulting to the system `USER`.
*   **Logs**: Log files are stored in the path specified by `CODX_JUNIOR_API_LOGS`, which defaults to `/tmp/codx-junior-logs`.
*   **Analytics**: Global analytics data is managed via `ANALYTICS_DATA_PATH` (default: `/home/codx-junior/analytics`). Raw AI log data is stored in `CODX_JUNIOR_AI_RAW_LOG_PATH` (default: `/home/codx-junior/analytics/chats`).
*   **Workspaces**: 
    *   `CODX_JUNIOR_WORKSPACES_FOLDER` defines where workspace configurations and files are kept (default: `/home/codx-junior/codx-junior-global-settings.json/workspaces`).
    *   `CODX_JUNIOR_DEFAULT_WORKSPACE_PATH` defines the directory for workspace templates used during creation (default: `/home/codx-junior-projects/codx-junior/workspace-templates`).

## Processing Time Constraints
The system enforces time limits for processing file changes and mentions:
*   **File Changes**: Changes older than `MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS` (60 minutes) are skipped.
*   **File Mentions**: Mentions older than `MAX_OUTDATED_TIME_TO_PROVESS_FILE_MENTIONS_IN_SECS` (3 minutes) are ignored.

## Application Integration
The system includes configuration for external applications, specifically Google Chrome.
*   **Available Apps**: The `APPS` list provides metadata, including names, icons, and descriptions (e.g., Google Chrome engine).
*   **Execution Commands**: `APPS_COMMANDS` defines the launch arguments for integrated applications. The command for chrome is: `google-chrome --no-sandbox --no-default-browser-check`.

## AI and Language Parsing
*   **Agent Communication**: The constant `AGENT_DONE_WORD` (`$$@@AGENT_DONE@@$$$`) serves as the signal for task completion.
*   **Language Parsing**: Supported languages are derived from `langchain_text_splitters`. Custom mapping for specific extensions is handled in `LANGUAGE_PARSER_MAPPING`:
    *   `ts` maps to `js`
    *   `cs` maps to `csharp`

***

**References**
* [codx/junior/globals.py](codx/junior/globals.py)

## Dependencies
**Imported by:** codx/junior/ai/raw_log_reader.py, codx/junior/ai/raw_logger.py, codx/junior/analytics/analytics.py, codx/junior/api/analytics.py, codx/junior/api/users.py, codx/junior/app.py, codx/junior/background.py, codx/junior/changes/change_manager.py, codx/junior/chat/chat_engine.py, codx/junior/engine/knowledge_engine.py, codx/junior/engine/session.py, codx/junior/knowledge/knowledge_code_splitter.py, codx/junior/utils/utils.py