import inspect
import re
from pathlib import Path

#: Markers a model uses when it emits a tool call INSIDE its text because the
#: provider (or the gateway) did not translate it into structured ``tool_calls``
#: deltas. DeepSeek V3.2 uses ``<｜｜DSML｜｜invoke …>`` (with full-width bars).
_TOOL_CALL_MARKERS = (
    "<｜｜DSML｜｜",
    "<||DSML||",
    "<|DSML|",
    "<tool_calls>",
    "<tool_call>",
    "<function=",
    "<|python_tag|>",
    "<|tool▁calls▁begin|>",
)

#: Stray per-token markup that may survive before the block.
_TOOL_CALL_TOKEN_RE = re.compile(
    r"<[^<>]{0,120}(?:DSML|tool_calls?|function=)[^<>]{0,120}>",
    re.IGNORECASE,
)


def strip_tool_call_markup(content: str) -> str:
    """
    Remove inline tool-call markup that a model emitted as plain text.

    Some providers stream tool calls as literal markup instead of structured
    ``tool_calls`` deltas (DeepSeek emits ``<｜｜DSML｜｜invoke …>``). When the
    markup is not translated it ends up in the assistant answer and the reader
    sees machine syntax instead of prose.

    Everything from the first marker on is dropped: an inline call is emitted
    after (or instead of) the prose and the block itself is never readable
    content.

    :param content: Assistant text as returned by the provider.
    :return: The readable part of the text (may be empty).
    """
    if not content:
        return ""
    cut = len(content)
    for marker in _TOOL_CALL_MARKERS:
        index = content.find(marker)
        if index != -1:
            cut = min(cut, index)
    cleaned = content[:cut] if cut < len(content) else content
    cleaned = _TOOL_CALL_TOKEN_RE.sub("", cleaned)
    return cleaned.strip()

def curr_fn() -> str:
    return inspect.stack()[1].function

def document_to_context(doc):
    analysis = doc.metadata.get('analysis') or ""
    raw_lines = [
                analysis,
                f"```{doc.metadata.get('language')}",
                f"{Path(doc.metadata['source']).absolute()}",
                doc.page_content,
                "```"
              ]
    lines = [line for line in raw_lines if line]
    return "\n".join(lines)

def extract_blocks(content):
    add_line = False
    block_type = None
    content_lines = []
    for line in content.split("\n"):
      if line.startswith("```"):
          if add_line:
              yield {
                      "type": block_type,
                      "content": "\n".join(content_lines)
                    }
              add_line = False
              block_type = None
              content_lines = []
          else:
              add_line = True
              block_type = line.replace('```', '')
          continue
      if add_line:
          content_lines.append(line)
          continue
