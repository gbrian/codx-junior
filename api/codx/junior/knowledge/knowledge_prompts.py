import os
from codx.junior.settings import GPTEngineerSettings

class KnowledgePrompts:
  def __init__(self, settings: GPTEngineerSettings):
    self.settings = settings
    self.preprompts_path = f"{os.path.dirname(__file__)}/prepromts"
    
  def get_prepromt(self, name):
    with open(f"{name}.md", "r") as f:
      return f.read()

  def template_replace(self, template: str, values: dict):
    for key in values.keys():
      template = template.replace("{{ %s }}" % key, values[key])
    return template

  def enrich_document_prompt(self, doc):
    template = self.get_prepromt("enrich_document")
    system = ""
    values = { 
                "page_content": doc.page_content,
                "language": doc.metadata.get('language', ''),
              }
    return self.template_replace(template, values), system

  def code_to_chunks_prompt(self, doc):
    template = self.get_prepromt("code_to_chunks")
    system = ""
    values = { 
              "page_content": doc.page_content,
              "language": doc.metadata.get('language', ''),
              "source": doc.metadata.get('source', ''),
            }
    return self.template_replace(template, values), system

  
  def extract_document_tags(self, doc):
    template = self.get_prepromt("extract_document_tags")
    system = ""
    values = { 
              "page_content": doc.page_content,
              "language": doc.metadata.get('language', ''),
              "source": doc.metadata.get('source', '')
              }
    return self.template_replace(template, values), system

  def extract_query_tags(self, query):
    template = self.get_prepromt("extract_query_tags")
    system = ""
    values = { 
              "query": query
              }
    return self.template_replace(template, values), system