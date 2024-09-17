import inspect
from pathlib import Path

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
