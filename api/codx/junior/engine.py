import os
import logging
import re
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from threading import Thread

from langchain.schema import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain.schema.document import Document

from codx.junior.utils import (
    document_to_context,
    extract_code_blocks,
    extract_json_blocks,
    exec_command,
    write_file
)

from codx.junior.ai import AI
from codx.junior.settings import CODXJuniorSettings

from codx.junior.chat_manager import ChatManager

from codx.junior.profiles.profile_manager import ProfileManager

from codx.junior.model import (
    Chat,
    Message,
    KnowledgeSearch,
    Document,
    Content,
    ImageUrl,
    LiveEdit,
    GlobalSettings
)
from codx.junior.context import (
  find_relevant_documents,
  AI_CODE_VALIDATE_RESPONSE_PARSER,
  generate_markdown_tree,
  AI_CODE_GENERATOR_PARSER,
  AICodeGerator
)


from codx.junior.knowledge.knowledge import Knowledge
from codx.junior.knowledge.knowledge_loader import KnowledgeLoader
from codx.junior.knowledge.knowledge_keywords import KnowledgeKeywords

from codx.junior.mention_manager import (
    extract_mentions,
    replace_mentions,
    notify_mentions_in_progress,
    notify_mentions_error,
    strip_mentions
)

logger = logging.getLogger(__name__)

def reload_knowledge(settings: CODXJuniorSettings, path: str = None):
    knowledge = Knowledge(settings=settings)
    logger.info(f"***** reload_knowledge: {path}")
    documents = None
    if path:
        documents = knowledge.reload_path(path)
        logger.info(f"reload_knowledge: {path} - Docs: {len(documents)}")
    else:    
        documents = knowledge.reload()
    all_files = set([doc.metadata["source"] for doc in documents])
    return { "doc_count": len(documents) if documents else 0 }

def knowledge_search(settings: CODXJuniorSettings, knowledge_search: KnowledgeSearch):
    if knowledge_search.document_search_type:
        settings.knowledge_search_type = knowledge_search.document_search_type
    if knowledge_search.document_count:
        settings.knowledge_search_document_count = knowledge_search.document_count
    if knowledge_search.document_cutoff_score:
        settings.knowledge_context_cutoff_relevance_score = knowledge_search.document_cutoff_score
    
    documents = []
    response = ""
    if knowledge_search.search_type == "embeddings":
        chat = Chat(messages=[
            Message(
                role="user",
                content=f"Please give me really short answer about: {knowledge_search.search_term}"
            )
        ])
        chat, chat_docs = chat_with_project(settings=settings, chat=chat, use_knowledge=True)
        documents = chat_docs
        response = chat.messages[-1].content
    if knowledge_search.search_type == "source":
        documents = Knowledge(settings=settings).search_in_source(knowledge_search.search_term)
    

    return { 
        "response": response,
        "documents": documents, 
        "settings": {
            "knowledge_search_type": settings.knowledge_search_type,
            "knowledge_search_document_count": settings.knowledge_search_document_count,
            "knowledge_context_cutoff_relevance_score": settings.knowledge_context_cutoff_relevance_score 
        }
    }

def delete_knowledge_source(settings: CODXJuniorSettings, sources: [str]):
    Knowledge(settings=settings).delete_documents(sources=sources)
    settings.watching = False
    settings.save_project()
    return { "ok": 1 }

def delete_knowledge(settings: CODXJuniorSettings):
    Knowledge(settings=settings).reset()
    return { "ok": 1 }

def on_project_changed(project_path: str, file_path: str):
    logger.info(f"Project changed {project_path} - {file_path}")

def create_project(project_path: str):
    logger.info(f"Create new project {project_path}")
    open_readme = False
    if project_path.startswith("http"):
        # Clone git repo into global settings
        global_settings = read_global_settings()
        os.makedirs(global_settings.projects_root_path, exist_ok=True)
        url = project_path
        repo_name = url.split("/")[-1].split(".")[0]
        project_path = f"{global_settings.projects_root_path}/{repo_name}"
        command = f"git clone --depth=1 {url} {project_path}"
        logger.info(f"Cloning repo {url} {repo_name} {project_path}")
        exec_command(command=command)
        open_readme = True
            
    os.makedirs(project_path, exist_ok=True)
     
    settings = CODXJuniorSettings()
    settings.project_path = project_path
    settings.project_name = settings.project_path.split("/")[-1] 
    settings.codx_path = f"{settings.project_path}/.codx"
    settings.save_project()
    coder_open_file(settings=settings, file_name=f"{settings.project_path}/README.md")
    return settings

def select_afefcted_documents_from_knowledge(ai: AI, query: str, settings: CODXJuniorSettings, ignore_documents=[]):
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
    query_messages = ai.chat(messages=[HumanMessage(content=rag_queries, role="user")])
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
      

def select_afected_files_from_knowledge(ai: AI, query: str, settings: CODXJuniorSettings):
    relevant_documents, file_list = select_afefcted_documents_from_knowledge(ai=ai, query=query, settings=settings)
    file_list = [str(Path(doc.metadata["source"]).absolute())
                  for doc in relevant_documents]
    file_list = list(dict.fromkeys(file_list))  # Remove duplicates

    return file_list


def improve_existing_code(settings: CODXJuniorSettings, chat: Chat, apply_changes: bool=None):
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
    code_generator = None
    if not chat.messages[-1].hide and not chat.messages[-1].improvement:
        retry_count = 1
        request_msg = Message(role="user", content=request)
        chat.messages.append(request_msg)
        logger.info(f"improve_existing_code prompt: {request_msg}")
        def try_chat_code_changes(attempt: int, error: str=None) -> AICodeGerator:
            if error:
                chat.messages.append(Message(role="user", content=f"There was an error last time:\n {error}"))
            chat_with_project(settings=settings, chat=chat, use_knowledge=False, chat_mode='chat')
            chat.messages = [msg for msg in chat.messages if msg != request_msg]
            chat.messages[-1].improvement = True
            if chat.mode == 'task':
                chat.messages[-2].hide = False
                chat.messages[-1].hide = True
            response = chat.messages[-1].content.strip()
            try:
                return AI_CODE_GENERATOR_PARSER.invoke(response)
            except Exception as ex:
                logger.error(f"Error parsing response: {response}")
                attempt = attempt - 1
                if attempt:
                    chat.messages.pop()
                    return try_chat_code_changes(attempt, error=str(ex))
                raise ex
        code_generator = try_chat_code_changes(retry_count)
        if not apply_changes:
            return code_generator
    else:
        code_generator = AI_CODE_GENERATOR_PARSER.invoke(chat.messages[-1].content)

    apply_improve_code_changes(settings=settings, code_generator=code_generator)
    return code_generator

def project_script_test(settings: CODXJuniorSettings):
    logger.info(f"project_script_test, test: {settings.script_test} - {settings.script_test_check_regex}")
    if not settings.script_test:
        return

    command = settings.script_test.split(" ")
    result = subprocess.run(command, cwd=settings.project_path,
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.STDOUT,
                                    text=True)
    console_out = result.stdout
    
    logger.info(f"project_script_test: {console_out} \nOUTPUT DONE")

    test_regex = settings.script_test_check_regex if settings.script_test_check_regex else 'error' 
    if re.search(test_regex, console_out):
        return console_out
    return ""

def apply_improve_code_changes(settings: CODXJuniorSettings, code_generator: AICodeGerator):
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
            write_file(file_path, new_content)
        else:
            logger.error(f"Error applying changes to {file_path}. New content: {new_content}")

def change_file_with_instructions(settings: CODXJuniorSettings, instruction_list: [str], file_path: str, content: str):
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

def improve_existing_code_gpt_blocks(settings: CODXJuniorSettings, chat: Chat):
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
        write_file(file_path, new_content)


def check_knowledge_status(settings: CODXJuniorSettings):
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

def save_chat(chat: Chat, settings: CODXJuniorSettings):
    ChatManager(settings=settings).save_chat(chat)

def check_project_changes(settings: CODXJuniorSettings):
    knowledge = Knowledge(settings=settings)
    knowledge.clean_deleted_documents()
    new_files = knowledge.detect_changes()
    # logger.info(f"[check_project_changes] project {settings.project_name} changed {len(new_files)}")
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
        Thread(target=update_project_profile, args=(settings, file_path)).start()
        Thread(target=update_wiki, args=(settings, file_path)).start()

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


def check_file_for_mentions(settings: CODXJuniorSettings, file_path: str):
    chat_manager = ChatManager(settings=settings)
    ai = AI(settings=settings)

    content = None
    with open(file_path, 'r') as f:
        content = f.read()

    def save_file (new_content):
        write_file(file_path, new_content)

    mentions = extract_mentions(content)
    #logger.info(f"EXTRACT MENTIONS: {mentions[0]}")
    
    if not mentions:
        return
    new_content = notify_mentions_in_progress(content)
    save_file(new_content=new_content)

    org_content = strip_mentions(content=content, mentions=mentions)

    use_knowledge = True
    
    using_chat = True if [m for m in mentions if m.flags.chat_id] else False
    skip_knowledge_search = False if [m for m in mentions if m.flags.knowledge] else True

    if using_chat or skip_knowledge_search:
      use_knowledge = False       
      logger.info(f"Skip KNOWLEDGE seach for processing, using_chat={using_chat}")
    
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
        elif use_knowledge:
            return ai.chat(prompt=f"""Return a search query string from user's request using the context. 
            CONTEXT:
            ```{file_path}
            {org_content}
            ```

            User commented in line {mention.start_line}: {mention.mention}
            """)[-1].content

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



def chat_with_project(settings: CODXJuniorSettings, chat: Chat, use_knowledge: bool=True, callback=None, append_references: bool=True, chat_mode: str=None):
    chat_mode = chat_mode or chat.mode or 'chat'
    is_refine = True if chat_mode == 'task' else False
    ai_messages = [m for m in chat.messages if not m.hide and not m.improvement and m.role == "assistant"]
    last_ai_message = ai_messages[-1] if ai_messages else None
        
    user_message = chat.messages[-1]
    query = user_message.content
    if "@codx-code" in query:
        return improve_existing_code(chat=chat, settings=settings)

    ai = AI(settings=settings)
    profile_manager = ProfileManager(settings=settings)

    
    instructions = f"""BEGIN INSTRUCTIONS
    This is a converation between you and the user about the project {settings.project_name}.
    Please always keep your answers short and simple unless a more detailed answer has been requested.
    END INSTRUCTIONS
    """
    
    if chat_mode == 'task':
        task = last_ai_message.content if is_refine and last_ai_message \
                          else "No task defined yet, create it following the instructions"
        if is_refine:
            user_message = Message(role="user", content=
              f"""
              UPDATE OR CREATE THE TASK:
              {task}
              
              USER COMMENTS:
              {query}
              """)
        instructions = f"""
        {profile_manager.read_profile("analyst").content}
        
        """
    chat.messages.append(
      Message(role="system", 
              hide=True, 
              content=f"""# INSTRUCTIONS:
              
              {instructions}

              # REQUEST
              {user_message.content}
              """))
    messages = [
      SystemMessage(content=instructions)
    ]

    def convert_message(m):
        msg = None
        def parse_image(image):
            try:
                return json.loads(image)
            except:
                return  { "src": image, "alt": "" }
        if m.images:
            images = [parse_image(image) for image in m.images]
            text_content = {
                  "type": "text",
                  "text": m.content 
                }
            content = [ text_content ] + \
                [
                  {
                    "type": "image_url",
                    "image_url": {
                      "url": image["src"]
                    }
                  } for image in images]

            logger.info(f"ImageMEssage content: {content}")
            msg = BaseMessage(type="image", content=json.dumps(content))
        elif m.role == "user":
            msg = HumanMessage(content=m.content)
        else:
            msg = AIMessage(content=m.content)
  
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
    chat_files = chat.file_list or []
    ignore_documents = [] + chat_files
    if chat.name:
        ignore_documents.append(f"/{chat.name}")
    
    if use_knowledge:
        affected_documents, doc_file_list = select_afefcted_documents_from_knowledge(ai=ai,
                                                        query=query,
                                                        settings=settings,
                                                        ignore_documents=ignore_documents)

        if chat_files:
            knowledge = Knowledge(settings=settings)
            chat_documents = [knowledge.doc_from_project_file(file_path) for file_path in chat_files]
            
            for doc in documents:
                doc_context = document_to_context(doc)
                context = context + f"{doc_context}\n"

        if affected_documents:
            documents = affected_documents
            file_list = doc_file_list
            documents = affected_documents
            for doc in documents:
                doc_context = document_to_context(doc)
                context = context + f"{doc_context}\n"
            """
            coding_profiles = profile_manager.get_coding_profiles(doc_file_list)
            logger.info(f"Coding profgiles: {coding_profiles} - files: {doc_file_list}")
            for profile in coding_profiles:
                context = context + f"coding profile {profile['content']}\n"
            """

        doc_length = len(documents) if documents else 0
        logger.info(f"chat_with_project found {doc_length} relevant documents")

    
    if context:
        user_message = Message(role="user", content=f"""{user_message.content}
        
        THIS INFORMATION IS COMING FROM PROJECT'S FILES.
        HOPE IT HELPS TO ANSWER USER REQUEST.
        KEEP FILE SOURCE WHEN WRITTING CODE BLOCKS (EXISTING OR NEWS).
        {context}
        """)
    messages.append(convert_message(user_message))
    messages = ai.chat(messages, callback=callback)
    response = messages[-1].content
    sources = []
    if documents and append_references:
        sources = list(set([doc.metadata['source'].replace(settings.project_path, "") \
                        for doc in documents]))
        
    response_message = Message(role="assistant", content=response, files=sources)
    if chat_mode == 'task':
        for msg in chat.messages[1:]:
          msg.hide = True
    chat.messages.append(response_message)
    return chat, documents

def check_project(settings: CODXJuniorSettings):
    try:
        logger.info(f"check_project")
        loader = KnowledgeLoader(settings=settings)
        loader.fix_repo()
    except Exception as ex:
        logger.exception(str(ex))

def extract_tags(settings: CODXJuniorSettings, doc):
    knowledge = Knowledge(settings=settings)
    knowledge.extract_doc_keywords(doc)
    return doc

def get_keywords(settings: CODXJuniorSettings, query):
    return KnowledgeKeywords(settings=settings).get_keywords(query)

def find_all_projects(detailed: bool = False):
    all_projects = []
    project_path = "/"
    result = subprocess.run("find / -name .codx".split(" "), cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    all_codx_path = result.stdout.decode('utf-8').split("\n")
    # logger.exception(f"all_codx_path {all_codx_path}")
    paths = [p for p in all_codx_path if os.path.isfile(f"{p}/project.json")]
    # logger.info(f"find_projects_to_watch: Scanning project paths: {project_path} - {paths}")
    for project_settings in paths:
        try:
            settings = CODXJuniorSettings.from_project(codx_path=str(project_settings))
            if settings.codx_path not in all_projects:
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

def update_engine():
    try:
      command = ["git", "pull"]
      result = subprocess.run(command)
    except Exception as ex:
      logger.exception(ex)
      return ex

def run_live_edit(settings: CODXJuniorSettings, chat: Chat):
    return improve_existing_code(settings=settings, chat=chat, apply_changes=True)
            
def update_wiki(settings: CODXJuniorSettings, file_path: str):
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

def read_global_settings():
    try:
        with open(f"global_settings.json") as f:
            return GlobalSettings(**json.loads(f.read()))
    except:
        return GlobalSettings()

def write_global_settings(global_settings: GlobalSettings):
    try:
        with open(f"global_settings.json", 'w') as f:
            return f.write(json.dumps(global_settings.dict()))
    except:
        pass

def update_project_profile(settings: CODXJuniorSettings, file_path:str):
  ai = AI(settings=settings)
  file_content = None
  with open(file_path) as f:
    file_content = f.read()

  ai_messages = ai.chat(messages=[
              HumanMessage(content=f"""Summarize in a business way the content of this file.
              Keep it really small summary, avoid any text decoration or formality. Use telegraphic style.
              It will then be used to update the project's main document that serves as an overview of this project.
              Extract keywords and important concepts and explain in a business language but using real names for future reference and searches.
              !IMPORTAN: PROJECT CONTENT MUST BE BE LARGER THAN 64KB!
              FILE: 
              {file_content}
              """)
            ])
  file_summary = ai_messages[-1].content

  profile_manager = ProfileManager(settings=settings)
  project = profile_manager.read_profile("project")

  ai_messages = ai.chat(messages=[
              HumanMessage(content=f"""Update the project's main document that serves as an overview of this project with the new information.
              PROJECT:
              {project.content}



              NEW INFORMATION: 
              {file_summary}
              """)
            ])
  project.content = ai_messages[-1].content
  profile_manager.create_profile(project)
  
  
def coder_open_file(settings: CODXJuniorSettings, file_name: str):
    if not file_name.startswith(settings.project_path):
        file_name = f"{settings.project_path}{file_name}"
    os.system(f"code-server -r {file_name}")