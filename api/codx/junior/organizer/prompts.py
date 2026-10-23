"""
Prompts used by the LLM decision engine.

The prompt asks the model for a single JSON object and nothing else, so the
answer can be parsed with the project's existing ``extract_json_blocks`` helper
(the same "ask the LLM for JSON and parse it" approach already used across the
codebase, e.g. ``wiki_manager`` and ``chat_engine_actions``).
"""

import logging

from codx.junior.organizer.models import OrganizationContext

logger = logging.getLogger(__name__)


def _render_boards(context: OrganizationContext) -> str:
    """
    Render the catalogue as a compact, human readable list for the prompt.

    Deliberately *not* JSON: the model must not be tempted to echo the
    catalogue back (which would collide with parsing the answer block).
    """
    lines = []
    for board in context.boards:
        columns = ", ".join(board.column_titles()) or "(no columns)"
        description = f" — {board.description}" if board.description else ""
        lines.append(f'- "{board.name}"{description}. Columns: {columns}')
    return "\n".join(lines)


def build_organization_prompt(state: str, context: OrganizationContext) -> str:
    """
    Build the prompt asking the LLM to place a chat on a board + column.

    :param state: Textual description of the chat (see ``build_chat_state``).
    :param context: The project's board/column catalogue.
    :return: The prompt string. The model is asked to reply with a single
        JSON block containing ``board``, ``column`` and ``priority``.
    """
    return f"""Organize the following chat into a kanban board and column.

<boards>
{_render_boards(context)}
</boards>

<chat>
{state}
</chat>

<instructions>
  * Choose exactly one board from the list above.
  * Choose exactly one column from the chosen board's columns.
  * Choose a priority of "high", "medium" or "low".
  * Reply with ONLY a single JSON object. No explanations, no analysis.
  * Enclose the JSON object with ```json as the first line and ``` at the end.
</instructions>

<output_format>
```json
{{
  "board": "<board name>",
  "column": "<column title>",
  "priority": "<high|medium|low>"
}}
```
</output_format>
"""


# Made with ❤️ by codx-junior