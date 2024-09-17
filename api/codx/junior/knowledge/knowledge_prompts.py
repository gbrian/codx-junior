
from gpt_engineer.core.db import DB
from gpt_engineer.core.settings import GPTEngineerSettings

class KnowledgePrompts:
  db: DB
  settings: GPTEngineerSettings

  def __init__(self, settings: GPTEngineerSettings):
    self.settings = settings
    self.db = settings.get_dbs().preprompts

  def template_replace(self, template: str, values: dict):
    for key in values.keys():
      template = template.replace("{{ %s }}" % key, values[key])
    return template

  def enrich_document_prompt(self, doc):
    template = self.db["enrich_document"]
    system = ""
    values = { 
                "page_content": doc.page_content,
                "language": doc.metadata.get('language', ''),
              }
    return self.template_replace(template, values), system

  def code_to_chunks_prompt(self, doc):
    template = self.db["code_to_chunks"]
    system = ""
    values = { 
              "page_content": doc.page_content,
              "language": doc.metadata.get('language', ''),
              "source": doc.metadata.get('source', ''),
            }
    return self.template_replace(template, values), system

  
  def extract_document_tags(self, doc):
    template = self.db["extract_document_tags"]
    system = ""
    values = { 
              "page_content": doc.page_content,
              "language": doc.metadata.get('language', ''),
              "source": doc.metadata.get('source', '')
              }
    return self.template_replace(template, values), system

  def extract_query_tags(self, query):
    template = self.db["extract_query_tags"]
    system = ""
    values = { 
              "query": query
              }
    return self.template_replace(template, values), system