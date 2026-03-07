This document provides utility functions for interacting with AI models and parsing logs.

### Utility Functions

#### `curr_fn()`

This function returns the name of the current function.

```python
import inspect

def curr_fn() -> str:
    return inspect.stack()[1].function
```

#### `document_to_context(doc)`

This function converts a document object into a context string suitable for AI processing. It includes the document's analysis, language, absolute source path, and page content.

```python
from pathlib import Path

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
```

#### `extract_blocks(content)`

This generator function extracts code blocks from a given content string. It identifies blocks based on triple backticks (```) and yields dictionaries containing the block type and its content.

```python
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
```