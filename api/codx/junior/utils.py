import os
import logging
import inspect
import subprocess
from pathlib import Path
import json, re
import hashlib

HOST_USER = os.environ.get("HOST_USER")
logger = logging.getLogger(__name__)


def extract_code_blocks(content):
    in_fence = False
    content_lines = []
    def is_fence_start(line):
        return True if re.match('^```[a-zA-Z]*$', line.strip()) else False

    for line in content.split("\n"):
      if is_fence_start(line=line):
          if in_fence:
              yield "\n".join(content_lines)
              in_fence = False
              content_lines = []
          else:  
            in_fence = True
          continue
      if in_fence:
          content_lines.append(line)

def extract_json_blocks(content):
    for block in extract_code_blocks(content=content):
        try:
            yield json.loads(block)
        except:
            pass

def calculate_md5(file_path):
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

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

def exec_command(command: str, cwd: str=None, env: dict=None):
    # logger.info(f"exec_command# {command}")
    result = subprocess.run(command.split(" "),
                                    cwd=cwd,
                                    env=os.environ | (env or {}),
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True)
    return result.stdout, result.stderr

def set_file_permissions(file_path: str):
    if HOST_USER:
        exec_command(f"chown {HOST_USER} {file_path}")

def write_file(file_path: str, content: str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        f.write(content)
    set_file_permissions(file_path)
    