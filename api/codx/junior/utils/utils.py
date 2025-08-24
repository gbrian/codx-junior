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
    def is_fence_line(line):
        return line.strip().startswith("```")

    for line in content.split("\n"):
      if is_fence_line(line=line):
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
    doc = {
      "content": doc.metadata.get('summary', doc.page_content),
      "keywords": doc.metadata.get('keywords'),
      "category": doc.metadata.get('category'),
      "source": str(Path(doc.metadata['source']).absolute()),
      "language": doc.metadata.get('language')
    }
    return json.dumps(doc) 

def remove_starting_block(content):
    if content.startswith("```"):
        return "\n".join(content.split("\n")[1:-1])
    return content

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
    
def read_file(file_path: str, project_path: str = ""):
    if project_path and not file_path.startswith(project_path):
        file_path = path_join(project_path, file_path)
    with open(file_path, 'r') as f:
        return f.read()

def path_join(path, *paths):
  paths = [p[1:] if p[0] == '/' else p for p in paths]
  return "/".join([path] + paths)