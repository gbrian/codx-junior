import os
import logging
import re
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

from langchain.schema import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain.schema.document import Document

from gpt_engineer.utils import extract_code_blocks, extract_json_blocks 

from gpt_engineer.core.dbs import DBs
from gpt_engineer.core.ai import AI
from gpt_engineer.core.settings import GPTEngineerSettings
from gpt_engineer.core import build_dbs, build_ai
from gpt_engineer.core.utils import curr_fn, document_to_context
from gpt_engineer.core.step.chat import ai_chat

from gpt_engineer.core.chat_manager import ChatManager
from gpt_engineer.tasks.task_manager import TaskManager

from gpt_engineer.api.profile_manager import ProfileManager

from gpt_engineer.api.model import (
    Chat,
    Message,
    KnowledgeSearch,
    Document,
    Content,
    ImageUrl
)
from gpt_engineer.core.context import (
  find_relevant_documents,
  AI_CODE_VALIDATE_RESPONSE_PARSER,
  generate_markdown_tree,
  AI_CODE_GENERATOR_PARSER,
  AICodeGerator
)

from gpt_engineer.core.steps import setup_sys_prompt_existing_code
from gpt_engineer.core.chat_to_files import parse_edits, apply_edit

from gpt_engineer.knowledge.knowledge import Knowledge
from gpt_engineer.knowledge.knowledge_loader import KnowledgeLoader
from gpt_engineer.knowledge.knowledge_keywords import KnowledgeKeywords

from gpt_engineer.core.mention_manager import (
    extract_mentions,
    replace_mentions,
    notify_mentions_in_progress,
    notify_mentions_error,
    strip_mentions
)

logger = logging.getLogger(__name__)

def reload_knowledge(settings: GPTEngineerSettings, path: str = None):
    knowledge = Knowledge(settings=settings)
    logger.info(f"***** reload_knowledge: {path}")
    documents = None
    if path:
        documents = knowledge.reload_path(path)
        logger.info(f"reload_knowledge: {path} - Docs: {len(documents)}")
    else:    
        documents = knowledge.reload()
    all_files = set([doc.metadata["source"] for doc in documents])
    for file_path in all_files:
        try:
            update_wiki(settings=settings, file_path=file_path)
        except:
            pass
    return { "doc_count": len(documents) if documents else 0 }

def knowledge_search(settings: GPTEngineerSettings, knowledge_search: KnowledgeSearch):
    if knowledge_search.document_search_type:
        settings.knowledge_search_type = knowledge_search.document_search_type
    if knowledge_search.document_count:
        settings.knowledge_search_document_count = knowledge_search.document_count
    if knowledge_search.document_cutoff_score:
        settings.knowledge_context_cutoff_relevance_score = knowledge_search.document_cutoff_score
    
    dbs = build_dbs(settings=settings)
    ai = build_ai(settings=settings)
    documents = []
    if knowledge_search.search_type == "embeddings":
        documents, _ = select_afefcted_documents_from_knowledge(ai=ai, dbs=dbs, query=knowledge_search.search_term, settings=settings)
    if knowledge_search.search_type == "source":
        documents = Knowledge(settings=settings).search_in_source(knowledge_search.search_term)
    return { 
        "documents": documents, 
        "settings": {
            "knowledge_search_type": settings.knowledge_search_type,
            "knowledge_search_document_count": settings.knowledge_search_document_count,
            "knowledge_context_cutoff_relevance_score": settings.knowledge_context_cutoff_relevance_score 
        }
    }

def delete_knowledge_source(settings: GPTEngineerSettings, sources: [str]):
    Knowledge(settings=settings).delete_documents(sources=sources)
    return { "ok": 1 }

def on_project_changed(project_path: str, file_path: str):
    logger.info(f"Project changed {project_path} - {file_path}")

def create_project(settings=GPTEngineerSettings):
    logger.info(f"Create new project {settings.gpteng_path}")
    os.makedirs(settings.gpteng_path, exist_ok=True)
    settings.save_project()


def select_afefcted_documents_from_knowledge(ai: AI, dbs: DBs, query: str, settings: GPTEngineerSettings, ignore_documents=[]):
    # Extract mentions from the query
    mentions = re.findall(r'@\S+', query)
    logger.info(f"Extracted mentions: {mentions}")
    settings_sub_projects = settings.get_sub_projects()
    sub_projects = set(settings_sub_projects + [mention[1:].lower() for mention in mentions])
    all_projects = find_all_projects()
    search_projects = [settings for settings in all_projects if settings.project_name.lower() in sub_projects]
    logger.info(f"select_afefcted_documents_from_knowledge query subprojects {sub_projects} - {search_projects}")
    for search_project in search_projects:
        mention = [mention[1:] for mention in mentions if mention.lower() == search_project.project_name.lower()]
        query = query.replace(f"@{mention}", "")

    def process_rag_query(rag_query):
        docs, file_list = find_relevant_documents(query=rag_query, settings=settings, ignore_documents=ignore_documents)
        if not docs:
            docs = []
            file_list = []
        logger.info(f"select_afefcted_documents_from_knowledge doc length: {len(docs)}")
        if search_projects and settings.knowledge_query_subprojects:
            logger.info(f"select_afefcted_documents_from_knowledge search subprojects: {rag_query} in {[p.project_name for p in search_projects]}")
            for sub_settings in search_projects:
                sub_docs, sub_file_list = find_relevant_documents(query=rag_query, settings=sub_settings, ignore_documents=ignore_documents)
                if sub_docs:
                    docs = docs + sub_docs
                if sub_file_list:
                    file_list = file_list + sub_file_list
        return docs, file_list
    return process_rag_query(rag_query=query)

    # Disables muti query improvement

    rag_queries = "\n".join([
        "Extract up to 3 search queries from the user request.",
        "Each search query will be used to search relevant documents to enrich user's request.",
        "It's important to be able able to find relevant documents to enrich user's request.",
        "Return only the queries one by one on their on line",
        "QUERY:",
        query
    ])
    query_messages = ai.next(messages=[HumanMessage(content=rag_queries, role="user")], step_name="select_afefcted_documents_from_knowledge_split_query")
    response = query_messages[-1].content
    logger.info(f"select_afefcted_documents_from_knowledge RAG queries: {response}")
    all_docs = {}
    for rag_query in [query for query in response.split("\n") if query]:
        docs, _ = process_rag_query(rag_query)
        if docs:
            for doc in docs:
                key = f"{doc.metadata['source']}-{doc.metadata.get('index') or 0}"
                all_docs[key] = doc
    all_docs = [doc for doc in all_docs.values()]
    all_files = list(set(([doc.metadata["source"] for doc in all_docs])))
    return all_docs, all_files 
      

def select_afected_files_from_knowledge(ai: AI, dbs: DBs, query: str, settings: GPTEngineerSettings):
    relevant_documents, file_list = select_afefcted_documents_from_knowledge(ai=ai, dbs=dbs, query=query, settings=settings)
    file_list = [str(Path(doc.metadata["source"]).absolute())
                  for doc in relevant_documents]
    file_list = list(dict.fromkeys(file_list))  # Remove duplicates

    return file_list


def improve_existing_code(settings: GPTEngineerSettings, chat: Chat, apply_changes: bool=None):
    knowledge = Knowledge(settings=settings)
    profile_manager = ProfileManager(settings=settings)
    if apply_changes is None:
        apply_changes = True if chat.mode == 'task' else False

    request = \
    f"""
    {profile_manager.read_profile("software_developer").content}
    Project name: {settings.project_name}
    Root path: {settings.project_path}
    Files tree view: {generate_markdown_tree(knowledge.get_all_sources())}
    
    Create a list of find&replace intructions for each change needed:
    INSTRUCTIONS:
      { AI_CODE_GENERATOR_PARSER.get_format_instructions() }
      
      * For new files create a file name following best practices of the project coding language
      * Keep content identation; is crucial to find the content to replace and to make new content work
    """
    logger.info(f"improve_existing_code prompt: {request}")
    code_generator = None
    if not chat.messages[-1].improvement:
        retry_count = 1
        request_msg = Message(role="user", content=request)
        chat.messages.append(request_msg)
        def try_chat_code_changes(attempt: int) -> AICodeGerator:
            chat_with_project(settings=settings, chat=chat, use_knowledge=False)
            chat.messages = [msg for msg in chat.messages if msg != request_msg]
            chat.messages[-1].improvement = True
            if chat.mode == 'task':
                chat.messages[-1].hide = True
            response = chat.messages[-1].content.strip()
            try:
                return AI_CODE_GENERATOR_PARSER.invoke(response)
            except Exception as ex:
                logger.error(f"Error parsing response: {response}")
                attempt = attempt - 1
                if attempt:
                    chat.messages.pop()
                    return try_chat_code_changes(attempt)
                raise ex
        code_generator = try_chat_code_changes(retry_count)
        if not apply_changes:
            return code_generator
    else:
        code_generator = AI_CODE_GENERATOR_PARSER.invoke(response)

    apply_improve_code_changes(settings=settings, code_generator=code_generator)
    return code_generator

def apply_improve_code_changes(settings: GPTEngineerSettings, code_generator: AICodeGerator):
    changes = code_generator.code_changes
    logger.info(f"improve_existing_code total changes: {len(changes)}")
    changes_by_file_path = {}
    for change in changes:
      file_path = change.file_path
      if file_path not in changes_by_file_path:
          changes_by_file_path[file_path] = []
      changes_by_file_path[file_path].append(change)
    
    for file_path, changes in changes_by_file_path.items(): 
      change_type = change.change_type
      existing_content = change.existing_content
      new_content = change.new_content
      logger.info(f"improve_existing_code change: {change_type} - {file_path}")
      
      if change_type == "delete_file":
          del open_files[file_path]
          os.remove(file_path)
      else:
        content = ""
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
        instruction_list = [json.dumps(change.__dict__) for change in changes]
        logger.info(f"Applying {len(changes)} changes to {file_path}")
        new_content = change_file_with_instructions(settings=settings, instruction_list=instruction_list, file_path=file_path, content=content)
        if new_content and new_content != content:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(new_content)
        else:
            logger.error(f"Error applying changes to {file_path}. New content: {new_content}")

def change_file_with_instructions(settings: GPTEngineerSettings, instruction_list: [str], file_path: str, content: str):
    chat = Chat(name=f"changes_at_{file_path}",messages=[])

    content_instructions = f"EXISTING CONTENT:\n{content}" if content else ""
    chat.messages.append(Message(role="user", content=f""""
    Rewrite full file content replacing codx instructions by requiered changes.
    Return only the file content without any further decoration or comments.
    Do not sorround response with '```' marks, just content.
    Always respect current file content formatting.

    INSTRUCTIONS:
    { "- ".join(instruction_list) }

    {content_instructions}
    """))
    chat_with_project(settings=settings, chat=chat, use_knowledge=False, append_references=False)
    return chat.messages[-1].content

def improve_existing_code_gpt_blocks(settings: GPTEngineerSettings, chat: Chat):
    request = \
    """Create a list of files to be modified with this structure:
      <GPT_CODE_CHANGE>
      FILE: file_path
      CHANGES: Explain which changed do we need to apply to this file
      </GPT_CODE_CHANGE>
      <GPT_CODE_CHANGE>
      FILE: file_path
      CHANGES: Explain which changed do we need to apply to this file
      </GPT_CODE_CHANGE>
      Repeat for as many files we have to change
    """
    if not chat.messages[-1].improvement:
        request_chat = Chat(messages=chat.messages + [
          Message(role="user", content=request)
        ])
        request_chat = chat_with_project(settings=settings, chat=request_chat, use_knowledge=True)
        chat.messages.append(request_chat.messages[-1])
        chat.messages[-1].improvement = True
        return
    response = chat.messages[-1].content
    instructions = list(split_blocks_by_gt_lt(response))
    logger.info(f"improve_existing_code: {instructions}")
    if not instructions:
        logger.error(f"improve_existing_code ERROR no instrucctions at: {response} {chat.messages[-1]}")
    for instruction in instructions:
        file_path = instruction[0].split(":")[1].strip()
        changes = "\n".join(instruction[1:])
        logger.info(f"improve_existing_code instruction file: {file_path}")
        logger.info(f"improve_existing_code instruction changes: {changes}")
        chat.messages.append(Message(role="assistant", content="\n".join(instruction)))
        with open(file_path) as f:
          content = f.read()
        new_content = change_file(context_documents=[], query=changes, file_path=file_path, org_content=content, settings=settings)
        with open(file_path, 'w') as f:
          content = f.write(new_content)


def check_knowledge_status(settings: GPTEngineerSettings):
    knowledge = Knowledge(settings=settings)
    last_update = knowledge.last_update
    status = knowledge.status()
    pending_files = knowledge.detect_changes()
    return {
      "last_update": str(last_update),
      "pending_files": pending_files[0:2000],
      "total_pending_changes": len(pending_files),
      **status
    }

def run_edits(settings: GPTEngineerSettings, chat: Chat):
    dbs = build_dbs(settings=settings)
    ai = build_ai(settings=settings)
    
    errors = []
    total_edits = []
    for message in chat.messages:
      if hasattr(message, "hide"):
        continue
      try:
        edits = parse_edits(message.content)
        total_edits = total_edits + edits
        for edit in edits:
          success, error = apply_edit(edit=edit, workspace=dbs.workspace)
          errors.append(f"{edit.filename} error: {error}")
      except Exception as ex:
        errors.append(str(ex))
    return f"{len(total_edits)} edits, {len(errors)} errors", errors

def save_chat(chat: Chat, settings: GPTEngineerSettings):
    ChatManager(settings=settings).save_chat(chat)

def check_project_changes(settings: GPTEngineerSettings):
    knowledge = Knowledge(settings=settings)
    knowledge.clean_deleted_documents()
    new_files = knowledge.detect_changes()
    if not new_files:
        return
    logger.info(f"check_file_for_mentions {new_files}")
    file_path = new_files[0]
    try:
        check_file_for_mentions(settings=settings, file_path=file_path)
    except:
        logger.exception(f"Error checking changes in file {file_path}")

    logger.info(f"Reload knowledge files {new_files}")
    reload_knowledge(settings=settings)

    for file_path in new_files:
        try:
            update_wiki(settings=settings, file_path=file_path)
            logger.info(f"Update wiki done for {file_path}")
        except:
            logger.exception(f"Update wiki ERROR for {file_path}")

def extract_changes(content):
    for block in extract_json_blocks(content):
        try:
            for change in block:
                yield change["change"]
        except:
            pass

def split_blocks_by_gt_lt(content):
    add_line = False
    content_lines = []
    for line in content.split("\n"):
      if line == "<GPT_CODE_CHANGE>":
          add_line = True
          continue
      if line == "</GPT_CODE_CHANGE>":
          yield content_lines
          add_line = False
          content_lines = []
      if add_line:
          content_lines.append(line)
          continue

def get_line_changes(content):
    line_change = None
    for line in content.split("\n"):
      if line.startswith("<GPT_"):
          line_change = {
            "type": re.match(r'<GPT_([^_]+)_LINE', line),
            "start": line.split("start_line=")[1]
          }
          continue
      if line.startswith("</GPT"):
          yield content_lines
          add_line = False
          content_lines = []
      if add_line:
          content_lines.append(line)
          continue
          
def change_file_by_blocks(context_documents, query, file_path, org_content, settings, save_changes=False, profile=None):
    profile_manager = ProfileManager(settings=settings)
    tasks = "\n *".join(
            context_documents + [
            query,
            'To ADD line(s) use: <GPT_ADD_LINE start_line="10"></GPT_ADD_LINE>',
            'To REMOVE line(s) use: <GPT_REMOVE_LINE start_line="10" end_line="11"></GPT_ADD_LINE> Lines from 10 to 11 will be deleted, both included',
            'To CHANGE line(s) use: <GPT_CHANGE_LINE start_line="10" end_line="11">New content</GPT_ADD_LINE> New content will replace lines 10 to 11',
            'Make sure identantion for new content is consistent'
          ]
    )
    request = \
    f"""Given this CONTENT, generate line changes.
    ##CONTENT:
    {org_content}
    ##TASKS:
    {tasks}
    """

    chat_name = '-'.join(file_path.split('/')[-2:])
    chat_time = datetime.now().strftime('%H%M%S')
    chat = Chat(name=f"{chat_name}_{chat_time}", 
        messages=[
            Message(role="user", content=request)
        ])
    try:
        if profile:
            profile_content = profile_manager.read_profile(profile).content
            if profile_content:
                chat.messages = [
                  Message(role="system", content=profile_content),
                ] + chat.messages

        chat = chat_with_project(settings=settings, chat=chat, use_knowledge=False)
        new_content = chat.messages[-1].content
        
        return "\n".join(next(split_blocks_by_gt_lt(new_content)))
    except Exception as ex:
        chat.messages.append(Message(role="error", content=str(ex)))
        raise ex
    finally:
        if save_changes:
            save_chat(chat=chat, settings=settings)

def change_file(context_documents, query, file_path, org_content, settings, save_changes=False):
    profile_manager = ProfileManager(settings=settings)
    tasks = "\n *".join(
            context_documents + [
            query
          ]
    )
    request = f"""Please produce a full version of this ##CONTENT applying the changes requested in the ##TASKS section.
    The output will replace existing file so write all unchanged lines as well.
    ##CONTENT:
    {org_content}
    
    ##TASKS:
    {tasks}

    OUPUT INSTRUCTIONS:
    {AI_CODE_VALIDATE_RESPONSE_PARSER.get_format_instructions()}
    """

    chat_name = '-'.join(file_path.split('/')[-2:])
    chat_time = datetime.now().strftime('%H%M%S')
    chat = Chat(name=f"{chat_name}_{chat_time}", 
        messages=[
          Message(role="user", content=profile_manager.read_profile("software_developer").content),
          Message(role="user", content=request)
        ])
    try:
        chat = chat_with_project(settings=settings, chat=chat, use_knowledge=False)
        response = chat.messages[-1].content.strip()
        parsed_response = AI_CODE_VALIDATE_RESPONSE_PARSER.invoke(response)
        return parsed_response.new_content
    except Exception as ex:
        chat.messages.append(Message(role="error", content=str(ex)))
        raise ex
    finally:
        if save_changes:
            save_chat(chat=chat, settings=settings)


def check_file_for_mentions(settings: GPTEngineerSettings, file_path: str):
    chat_manager = ChatManager(settings=settings)
    content = None
    with open(file_path, 'r') as f:
        content = f.read()

    def save_file (new_content):
        with open(file_path, 'w') as f:
            f.write(new_content)

    mentions = extract_mentions(content)
    #logger.info(f"EXTRACT MENTIONS: {mentions[0]}")
    
    if not mentions:
        return
    new_content = notify_mentions_in_progress(content)
    save_file(new_content=new_content)

    org_content = strip_mentions(content=content, mentions=mentions)
    
    def mention_info(mention):
      chat = chat_manager.find_by_id(mention.flags.chat_id) if mention.flags.chat_id else None
      if chat:
        logger.info(f"using CHAT for processing ention: {mention.mention}")
        return f"""Based on this conversation:
        ```markdown
        {chat_manager.serialize_chat(chat)}
        ```
        User commented in line {mention.start_line}: {mention.mention}
        """
      return f"User commented in line {mention.start_line}: {mention.mention}"
    
    query = "\n  *".join([mention_info(mention) for mention in mentions])

    chat = Chat(name=f"changes_at_{file_path}",messages=[
      Message(role="user", content=f"""
      Find all information needed to apply all changes to file: {file_path}
      Changes:
        {query}

      File content:
      {new_content}
      """)
    ])
    use_knowledge = True
    
    using_chat = True if [m for m in mentions if m.flags.chat_id] else False
    skip_knowledge_search = False if [m for m in mentions if m.flags.knowledge] else True
    
    if using_chat or skip_knowledge_search:
      use_knowledge = False       
      logger.info(f"Skip KNOWLEDGE seach for processing, using_chat={using_chat}: {query}")
    
    chat_with_project(settings=settings, chat=chat, use_knowledge=use_knowledge)
    chat.messages.append(Message(role="user", content=f""""
    Rewrite full file content replacing codx instructions by requiered changes.
    Return only the file content without any further decoration or comments.
    Do not sorround response with '```' marks, just content:
    {new_content}
    """))
    chat_with_project(settings=settings, chat=chat, use_knowledge=False, append_references=False)
    response = chat.messages[-1].content
    save_file(new_content=response)
    
    """
    context_documents = []
    use_knowledge = False if "--codx-no-knowledge" in query else True
    if use_knowledge:
      query = query.replace("--codx-knowledge", "")
      ai = build_ai(settings)
      dbs = build_dbs(settings)
      documents, _ = select_afefcted_documents_from_knowledge(ai=ai,
                                                    dbs=dbs,
                                                    query=query,
                                                    settings=settings,
                                                    ignore_documents=[f"/{file_path}"])
      if documents:
          for doc in documents:
              doc_context = document_to_context(doc)
              context_documents.append(doc_context)

    save_changes = True if "--codx-save" in query else False
    new_content = change_file(
        context_documents=context_documents,
        query=query,
        file_path=file_path,
        org_content=org_content,
        settings=settings,
        save_changes=save_changes)
    
    if content != new_content:
        save_file(new_content=new_content)        
    """



def chat_with_project(settings: GPTEngineerSettings, chat: Chat, use_knowledge: bool=True, callback=None, append_references: bool=True):
    chat_mode = chat.mode
    is_refine = True if chat_mode == 'task' and len(chat.messages) > 1 else False
    ai_messages = [m for m in chat.messages if not m.hide and not m.improvement and m.role == "assistant"]
    last_ai_message = ai_messages[-1] if ai_messages else None
        
    user_message = chat.messages[-1]
    query = user_message.content
    if "@codx-code" in query:
        return improve_existing_code(chat=chat, settings=settings)

    ai = build_ai(settings)
    dbs = build_dbs(settings)
    profile_manager = ProfileManager(settings=settings)

    instructions = f"""BEGIN INSTRUCTIONS
    This is a converation between you and the user about the project {settings.project_name}.
    Please always keep your answers short and simple unless a more detailed answer has been requested.
    {profile_manager.read_profile("project").content}

    END INSTRUCTIONS
    """
    
    if chat_mode == 'task':
        task = last_ai_message.content if is_refine and last_ai_message else ""
        if is_refine:
            query = f"{chat.messages[0].content}\n{query}"
        instructions = f"""Help me writting a coding task.
    Here you have details about the project:
    ```md
    {profile_manager.read_profile("project").content}
    ```

    Details about writting code:
    ```md
    {profile_manager.read_profile("software_developer").content}
    ```

    And this is what we have written so far:
    ```md
    {task}
    ```
    """
    messages = [
      SystemMessage(content=instructions)
    ]

    def convert_message(m):
        msg = None
        if m.images:
            text_content = {
                  "type": "text",
                  "text": m.content 
                }
            content = [ text_content ] + \
                [
                  {
                    "type": "image_url",
                    "image_url": {
                      "url": url
                    }
                  } for url in m.images]

            logger.info(f"ImageMEssage content: {content}")
            msg = BaseMessage(type="image", content=json.dumps(content))
        elif m.role == "user":
            msg = HumanMessage(content=m.content)
        else:
            msg = AIMessage(content=m.content)
  
        logger.info(f"convert_message {m} - {msg}")  
        return msg

    if is_refine:
        msg = convert_message(chat.messages[0])
        messages.append(msg)
    else:
        for m in chat.messages[0:-1]:
            if m.hide or m.improvement:
                continue
            msg = convert_message(m)
            messages.append(msg)

    context = ""
    documents = []
    coding_profiles = []
    if use_knowledge:
        affected_documents, doc_file_list = select_afefcted_documents_from_knowledge(ai=ai,
                                                        dbs=dbs,
                                                        query=query,
                                                        settings=settings,
                                                        ignore_documents=[f"/{chat.name}"])
        if affected_documents:
            documents = affected_documents
            file_list = doc_file_list
            documents = affected_documents
            for doc in documents:
                doc_context = document_to_context(doc)
                context = context + f"{doc_context}\n"

            coding_profiles = profile_manager.get_coding_profiles(doc_file_list)
            logger.info(f"Coding profgiles: {coding_profiles} - files: {doc_file_list}")
            for profile in coding_profiles:
                context = context + f"coding profile {profile['content']}\n"

        doc_length = len(documents) if documents else 0
        logger.info(f"chat_with_project found {doc_length} relevant documents")

    
    messages.append(AIMessage(
      content=f"""THIS INFORMATION IS COMING FROM PROJECT'S FILES.
                  HOPE IT HELPS TO ANSWER USER REQUEST.
                  KEEP FILE SOURCE WHEN WRITTING CODE BLOCKS (EXISTING OR NEWS).
                  {context}"""))

    messages.append(convert_message(user_message))
    
    messages = ai.next(messages, step_name=curr_fn(), callback=callback)
    response = messages[-1].content
    if documents and append_references:
        sources = list(set([doc.metadata['source'].replace(settings.project_path, "") \
                        for doc in documents]))
        sources = '\n'.join([f'- {source}' for source in sources])
        response = f"{messages[-1].content}\n\nRESOURCES:\n{sources}"
        if coding_profiles:
            profiles = ""
            for profile in coding_profiles:
                profiles = f"* {profile['type']}\n"
            response = f"{response}\n\nPROFILES:\n{profiles}"

    response_message = Message(role="assistant", content=response)
    if chat_mode == 'task':
        for msg in chat.messages[1:]:
          msg.hide = True
    chat.messages.append(response_message)
    return chat

def check_project(settings: GPTEngineerSettings):
    try:
        logger.info(f"check_project")
        loader = KnowledgeLoader(settings=settings)
        loader.fix_repo()
    except Exception as ex:
        logger.exception(str(ex))

def extract_tags(settings: GPTEngineerSettings, doc):
    knowledge = Knowledge(settings=settings)
    knowledge.extract_doc_keywords(doc)
    return doc

def get_keywords(settings: GPTEngineerSettings, query):
    return KnowledgeKeywords(settings=settings).get_keywords(query)

def find_all_projects(detailed: bool = False):
    all_projects = []
    project_path = "/"
    all_gpteng_path = [str(p) for p in Path(project_path).glob("**/.gpteng")]
    # logger.exception(f"all_gpteng_path {all_gpteng_path}")
    paths = [p for p in all_gpteng_path if os.path.isfile(f"{p}/project.json")]
    # logger.info(f"find_projects_to_watch: Scanning project paths: {project_path} - {paths}")
    for project_settings in paths:
        try:
            settings = GPTEngineerSettings.from_project(gpteng_path=str(project_settings))
            if settings.gpteng_path not in all_projects:
                all_projects.append(settings)
                # logger.info(f"find_projects_to_watch: project found {str(project_settings)}")
        except Exception as ex:
            logger.exception(f"Error loading project {str(project_settings)}")
    def projects_with_details():
        for project in all_projects:
            try:
              command = ["git", "branch", "--show-current"]
              result = subprocess.run(command, cwd=project.project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
              project.__dict__["current_git_branch"] = result.stdout.decode('utf-8')
            except Exception as ex:
                project.__dict__["current_git_branch"] = f"Error: {ex}"
                pass
        return all_projects
    return projects_with_details() if detailed else all_projects

def update_wiki(settings: GPTEngineerSettings, file_path: str):
    project_wiki_path = settings.get_project_wiki_path()
    if not settings.project_wiki or file_path.startswith(project_wiki_path):
        return

    project_wiki_home = f"{project_wiki_path}/home.md"

    home_content = f"# {settings.project_name}"
    if os.path.isfile(project_wiki_home):
        with open(project_wiki_home, 'r') as f:
            home_content = f.read()

    with open(file_path, 'r') as f:
        file_content = f.read()
        logger.info(f"update_wiki file_path: {file_path}, project_wiki: {project_wiki_path}")
        chat = Chat(messages=[
          Message(role="user", content=f"""Extract iportant parts from the content of {file_path} to be added to the wiki.
          {file_content}
          """)
        ])
        chat_with_project(settings=settings, chat=chat, use_knowledge=True)
        chat.messages.append(Message(role="user", content=f"""
        Improve our current wiki with the new knowledge extracted from {file_path},
        Highlight important parts and create mermaid diagrams to help user's understanding of the project.
        If information is not relevant for the whole project but for the file itself remove from home and create a new linked wiki page instead.
        
        Wiki directory structure:
        ```md
        {generate_markdown_tree(Path(project_wiki_path).glob("**"))}
        ```

        Wiki home content:
        ```{project_wiki_home}
        {home_content}
        ```
        """))
        code_generator = improve_existing_code(settings=settings, chat=chat, apply_changes=False)
        logger.info(f"update_wiki file_path: {file_path}, changes: {code_generator}")
        if code_generator:
            wiki_changes = [change for change in code_generator.code_changes if project_wiki_path in change.file_path]
            logger.info(f"update_wiki file_path: {file_path}, wiki changes: {wiki_changes}")
            if wiki_changes:
                apply_improve_code_changes(settings=settings, code_generator=AICodeGerator(code_changes=wiki_changes))