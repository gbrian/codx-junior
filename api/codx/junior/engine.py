import json
import logging
import os
import re
import shutil
import subprocess
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from langchain.schema import (
    AIMessage,
    HumanMessage,
    BaseMessage
)

from codx.junior.ai import AI
from codx.junior.chat.chat_engine import ChatEngine
from codx.junior.chat_manager import ChatManager
from codx.junior.context import (
    find_relevant_documents,
    AI_CODE_VALIDATE_RESPONSE_PARSER,
    generate_markdown_tree,
    AI_CODE_GENERATOR_PARSER,
    AICodeGerator
)
from codx.junior.db import (
    Chat,
    Message,
    MessageTaskItem
)
from codx.junior.events.event_manager import EventManager
from codx.junior.globals import (
    MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS,
    CODX_JUNIOR_API_BACKGROUND,
    APPS,
    APPS_COMMANDS,
    coder_open_file,
    find_project_by_id,
    find_project_by_name,
    find_all_projects
)
from codx.junior.knowledge.knowledge_keywords import KnowledgeKeywords
from codx.junior.knowledge.knowledge_loader import KnowledgeLoader
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.mentions.mention_manager import MentionManager
from codx.junior.model.model import (
    KnowledgeSearch,
    Profile
)
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.profiling.profiler import profile_function
from codx.junior.settings import (
    CODXJuniorSettings
)
from codx.junior.sio.session_channel import SessionChannel
from codx.junior.utils.chat_utils import ChatUtils
from codx.junior.utils.utils import (
    extract_json_blocks,
    exec_command,
    write_file
)

logger = logging.getLogger(__name__)

class CODXJuniorSession:
    def __init__(self,
            settings: CODXJuniorSettings = None,
            codx_path: str = None,
            channel: SessionChannel = None):
        self.settings = settings or CODXJuniorSettings.from_project_file(f"{codx_path}/project.json")
        self.channel = channel
        self.event_manager = EventManager(
                                codx_path=codx_path,         
                                channel=channel)

    def switch_project(self, project_id: str):
        if not project_id or project_id == self.settings.project_id:
            return self
        settings = find_project_by_id(project_id=project_id)
        return CODXJuniorSession(settings=settings, channel=self.channel) \
                if settings else self

    def log_info(self, msg):
        logger.info(f"[{self.settings.project_name}] {msg}")

    def log_error(self, msg):
        logger.error(f"[{self.settings.project_name}] {msg}")
    
    def log_exception(self, msg):
        logger.exception(f"[{self.settings.project_name}] {msg}")

    def coder_open_file(self, file_name: str):
        if not file_name.startswith(self.settings.project_path):
            file_name = f"{self.settings.project_path}/{file_name}".replace("//", "/")
        os.system(f"code-server -r {file_name}")
        return [self.settings.project_path, file_name, file_name.startswith(self.settings.project_path)]
      
    @contextmanager
    def chat_action(self, chat: Chat, event: str):
        self.event_manager.chat_event(chat=chat, message=f"{event} starting")
        self.log_info(f"Start chat {chat.name}")
        try:
            yield
        except Exception as ex:
            self.event_manager.chat_event(chat=chat, message=f"{event} error: {ex}", event_type="error")
            self.log_exception(f"Chat {chat.name} {event} error: {ex}")
        finally:
            self.event_manager.chat_event(chat=chat, message=f"{event} done")
            self.log_info(f"Chat done {chat.name}")

    
    def delete_project(self):
        shutil.rmtree(self.settings.codx_path)
        logger.error(f"PROJECT REMOVED {self.settings.codx_path}")

    def get_mention_manager(self):
        return MentionManager(settings=self.settings, 
                              event_manager=self.event_manager)

    def get_chat_manager(self):
        return ChatManager(settings=self.settings)

    def get_profile_manager(self):
        return ProfileManager(settings=self.settings)

    def get_ai(self, llm_model: str = None):
        return AI(settings=self.settings, llm_model=llm_model)

    def get_knowledge(self):
        return Knowledge(settings=self.settings)

    def get_wiki(self):
        from codx.junior.wiki.wiki_manager import WikiManager
        return pwiwki(settings=self.settings)

    def get_browser(self):
        from codx.junior.browser.browser import Browser
        return Browser(session=self)

    @profile_function
    def load_chat(self, board, chat_name):
        return self.get_chat_manager().load_chat(board=board, chat_name=chat_name)
    
    def list_chats(self):
        return self.get_chat_manager().list_chats()

    async def save_chat(self, chat: Chat, chat_only=False):
        chat = self.get_chat_manager().save_chat(chat, chat_only)
        self.event_manager.chat_event(chat=chat, event_type="changed")
        return chat

    def delete_chat(self, chat_id):
        self.get_chat_manager().delete_chat(chat_id=chat_id)

    @profile_function
    def list_profiles(self):
        return self.get_profile_manager().list_profiles()

    async def save_profile(self, profile):
        profile = self.get_profile_manager().save_profile(profile=profile)
        await self.get_mention_manager().check_file_for_mentions(file_path=profile.content_path)
        return self.read_profile(profile_name=profile.name)

    def watch_project(self, watching):
        self.settings.watching = watching
        self.settings.save_project()

    def read_profile(self, profile_name):
        return self.get_profile_manager().read_profile(profile_name)

    def delete_profile(self, profile_name):
        return self.get_profile_manager().delete_profile(profile_name)

    def reload_knowledge(self, path: str = None):
        knowledge = self.get_knowledge()
        self.log_info(f"***** reload_knowledge: {path}")
        documents = None
        if path:
            documents = knowledge.reload_path(path)
            self.log_info(f"reload_knowledge: {path} - Docs: {len(documents)}")
        else:
            documents = knowledge.reload()
        return {"doc_count": len(documents) if documents else 0}

    def init_chat_from_url(self, chat: Chat):
        ai_content = None
        try:
            # Step 1: Download the content from the chat URL
            response = requests.get(chat.url)
            response.raise_for_status()  # This will raise an error for bad responses (4XX or 5XX)

            # Ensure the response is text-based
            downloaded_content = response.text

            # Step 2: Use AI to parse the downloaded content
            ai = self.get_ai()

            # Step 3: Create a prompt to extract a title and content
            prompt = f"""
            Extract a concise title and all content from the following issue html page:
            {downloaded_content}

            Return the response in JSON format:
            {{
                "title": "Extracted title",
                "content": "Extracted content"
            }}
            """
            # Use AI to get the response
            ai_responses = ai.chat(prompt=prompt)
            ai_content = ai_responses[0].content
            response_json = next(extract_json_blocks(ai_content))
    
            # Step 4: Set the extracted title as the name and the content as the first message of the chat
            chat.name = response_json.get('title', 'Untitled Chat')  # Default to 'Untitled Chat' if no title is found
            chat.messages.append(Message(role='user', content=response_json.get('content', '')))
                
        except Exception as e:
            self.log_exception(f"Error initializing chat from URL {chat.url}: {e} - {ai_content}")
            raise e
    
    @profile_function
    async def knowledge_search(self, knowledge_search: KnowledgeSearch):
        self.settings.knowledge_search_type = knowledge_search.document_search_type
        self.settings.knowledge_search_document_count = knowledge_search.document_count
        self.settings.knowledge_context_cutoff_relevance_score = knowledge_search.document_cutoff_score
        self.settings.knowledge_context_rag_distance = knowledge_search.document_cutoff_rag

        logger.info(f"""knowledge_search: 
        knowledge_search_type: {self.settings.knowledge_search_type}
        knowledge_search_document_count: {self.settings.knowledge_search_document_count}
        knowledge_context_cutoff_relevance_score: {self.settings.knowledge_context_cutoff_relevance_score}
        knowledge_context_rag_distance: {self.settings.knowledge_context_rag_distance}
        """)
        
        documents = []
        response = ""
        if knowledge_search.search_type == "fulltext":
            documents = Knowledge(settings=self.settings).full_text_search(knowledge_search.search_term)
        
        if knowledge_search.search_type == "embeddings":
            documents, file_list = find_relevant_documents(query=knowledge_search.search_term,
                                                    settings=self.settings, 
                                                    ignore_documents=[],
                                                    ai_validate=True)
            
            chat = Chat(messages=
                [
                    Message(
                        role="user",
                        content=doc.page_content)
                    for doc in documents] +  
                [
                    Message(
                        role="user",
                        content=f"Based on previos messages, give me really short answer about: {knowledge_search.search_term}"
                )
            ])
            chat, _ = await self.chat_with_project(chat=chat, disable_knowledge=True)
            response = chat.messages[-1].content

        if knowledge_search.search_type == "source":
            documents = Knowledge(settings=self.settings).search_in_source(knowledge_search.search_term)
        
        return {
            "response": response,
            "documents": documents,
            "settings": {
                "knowledge_search_type": self.settings.knowledge_search_type,
                "knowledge_search_document_count": self.settings.knowledge_search_document_count,
                "knowledge_context_cutoff_relevance_score": self.settings.knowledge_context_cutoff_relevance_score,
                "knowledge_context_rag_distance": self.settings.knowledge_context_rag_distance
            }
        }

    def delete_knowledge_source(self, sources: [str]):
        Knowledge(settings=self.settings).delete_documents(sources=sources)
        self.settings.watching = False
        self.settings.save_project()
        find_all_projects()
        return {"ok": 1}

    def delete_knowledge(self, index: str):
        Knowledge(settings=self.settings).reset(index=index)
        return {"ok": 1}

    def get_project_dependencies(self):
        """Returns all projects related with this project, including child projects and links"""
        project_child_projects = self.settings.get_sub_projects()
        project_dependencies = [find_project_by_name(project_name) for project_name in self.settings.get_project_dependencies()]
        return project_child_projects, project_dependencies

    def get_all_search_projects(self):
        project_child_projects, project_dependencies = self.get_project_dependencies()
        all_projects = [self.settings] + project_child_projects + project_dependencies
        return all_projects
        
    def extract_query_mentions(self, query: str):
        chat_utils = ChatUtils(profile_manager=self.get_profile_manager())
        return chat_utils.extract_query_mentions(query=query)

    def find_projects_by_mentions(self, mentions: [str]):
        chat_utils = ChatUtils(profile_manager=self.get_profile_manager())
        return chat_utils.find_projects_by_mentions(mentions=mentions)

    def find_profiles_by_mentions(self, mentions: [str]):
        chat_utils = ChatUtils(profile_manager=self.get_profile_manager())
        return chat_utils.find_profiles_by_mentions(mentions=mentions)

    def get_query_mentions(self, query: str):
        chat_utils = ChatUtils(profile_manager=self.get_profile_manager())
        return chat_utils.get_query_mentions(query=query)

    @profile_function
    def find_project_documents(self, query: str):
        documents, _ = self.select_afefcted_documents_from_knowledge(chat=None, ai=self.get_ai(), query=query, search_projects=[])
        return documents
    
    @profile_function
    def select_afefcted_documents_from_knowledge(self, chat: Optional[Chat], ai: AI, query: str, ignore_documents=[], search_projects = []):
        for search_project in search_projects:
            query = query.replace(f"@{search_project.project_name}", "")

        @profile_function
        def process_rag_query(rag_query):
            docs = []
            file_list = []

            self.log_info(f"select_afefcted_documents_from_knowledge search subprojects: {rag_query} in {[p.project_name for p in search_projects]}")
            for search_project in search_projects:
                if chat:    
                    self.event_manager.chat_event(chat=chat, message=f"Search knowledge in {search_project.project_name}: {search_project.project_path}")
                project_docs, project_file_list = find_relevant_documents(query=rag_query, settings=search_project, ignore_documents=ignore_documents)
                project_file_list = [os.path.join(search_project.project_path, file_path) for file_path in project_file_list]
                if project_docs:
                    docs = docs + project_docs
                if project_file_list:
                    file_list = file_list + project_file_list
            
            self.log_info(f"select_afefcted_documents_from_knowledge doc length: {len(docs)} - cutoff score {self.settings.knowledge_context_cutoff_relevance_score}")  
            return docs, file_list
        return process_rag_query(rag_query=query)

    async def excute_bash_code(self, chat: Chat, code_block_info: dict):
        # Invoke project based on project_id
        self = self.switch_project(chat.project_id)
        
        language = code_block_info["language"]
        code = code_block_info["code"]
        try:
            self.event_manager.chat_event(chat=chat, message="Executing bash script")
            stdout, stderr = exec_command(code, cwd=self.settings.project_path)
            chat.messages.append(Message(role="user", content=f"""
            Executing bash script
            ```{language}
            {code}
            ```
            stdout: {stdout}
            stderr: {stderr}
            """))
            self.event_manager.chat_event(chat=chat, message="Applying patch done.")
            await self.save_chat(chat=chat)
        except Exception as ex:
            self.event_manager.chat_event(chat=chat, message=f"Error applying patch: {ex}", event_type="error")
            raise ex

    async def generate_code(self, chat: Chat, code_block_info: dict):
        # Invoke project based on project_id
        self = self.switch_project(chat.project_id)

        language = code_block_info["language"]
        code = code_block_info["code"]
        ai = self.get_ai()
        messages = ai.chat(prompt=f"Answer only (YES or NO). Is this something I can execute in a terminal?:\nScript:\n{code}")
        
        is_bash = "YES" in messages[-1].content
        if is_bash:
            return await self.excute_bash_code(chat=chat, code_block_info=code_block_info)
        
        try:
            chat.messages.append(Message(role="user", content=f"""
            Apply this code
            ```{language}
            {code}
            ```
            """))
            self.event_manager.chat_event(chat=chat, message="Applying patch")
            await self.improve_existing_code(chat=chat, apply_changes=True)
            self.event_manager.chat_event(chat=chat, message="Applying patch done.")
        except Exception as ex:
            self.event_manager.chat_event(chat=chat, message=f"Error applying patch: {ex}", event_type="error")
            raise ex
                      
    async def improve_existing_code_patch(self, chat:Chat, code_generator: AICodeGerator):
        # Invoke project based on project_id
        self = self.switch_project(chat.project_id)

        patch = code_generator.code_patches[0]
        ts = datetime.now().strftime('%H%M%S')
        patch_file = f"{self.settings.project_path}/{ts}.patch"
        with open(patch_file, 'w') as f:
            f.write(patch.patch)
        git_patch = f"git apply {patch_file}"
        stdout, stderr = exec_command(git_patch, cwd=self.settings.project_path)
        os.remove(patch_file)
        res = f"{stdout} {stderr}".lower()
        error = True if len(stderr or "") != 0 or "error" in res else False
        
        changes = code_generator.code_changes            
        if error and changes:
            file_path = changes[0].file_path
            await self.apply_improve_code_changes(chat=chat, code_generator=code_generator)
            stdout = "Changes applied"
            stderr = ""
            if file_path not in chat.file_list:
                chat.file_list.append(file_path) 
                coder_open_file(self.settings, file_name=file_path)
        return stdout, stderr


    @profile_function
    async def improve_existing_code(self, chat: Chat, apply_changes: bool=None):
        # Invoke project based on project_id
        self = self.switch_project(chat.project_id)
        self.event_manager.send_event(message=f"Code changes")

        valid_messages = [message for message in chat.messages if not message.hide]
        if valid_messages[-1].improvement:
            code_generator = self.get_ai_code_generator_changes(response=valid_messages[-1].content)
            return await self.apply_improve_code_changes(chat=chat, code_generator=code_generator)

        knowledge = Knowledge(settings=self.settings)
        profile_manager = ProfileManager(settings=self.settings)
        if apply_changes is None:
            apply_changes = True if chat.mode == 'task' else False

        request = f"""
        Assist the user on generating file changes for the project "{self.settings.project_name}" based on the comments below.
        Make sure that all proposed changes follow strictly the best practices.
        
        Best practices:
        ```markdown
        {profile_manager.read_profile("software_developer").content}
        ```
        Info about the project:
        - Root path: {self.settings.project_path}
        - Files tree view: {generate_markdown_tree(knowledge.get_all_sources())}
        Use this information for generating file paths and understanding the project's folder structure.

        Create a list of find&replace instructions for each change needed:
        INSTRUCTIONS:
          {AI_CODE_GENERATOR_PARSER.get_format_instructions()}
          
          * For new files create an absolute paths
          * Only update files that exists in the project's files
          * Keep content indentation; It is crucial to find the content to replace and to make new content work
        """
        code_generator = None
        retry_count = 1
        request_msg = Message(role="user", content=request)
        chat.messages.append(request_msg)
        async def try_chat_code_changes(attempt: int, error: str=None) -> AICodeGerator:
            if error:
                chat.messages.append(Message(role="user", content=f"There was an error last time:\n {error}"))
            
            await self.chat_with_project(chat=chat, disable_knowledge=True, chat_mode='chat')
            chat.messages[-1].improvement = True
            
            request_msg.improvement = True
            request_msg.hide = True
            if chat.mode == 'task':
                chat.messages[-2].hide = False
                chat.messages[-1].hide = True
            response = chat.messages[-1].content.strip()
            try:
                return self.get_ai_code_generator_changes(response=response)
            except Exception as ex:
                logger.error(f"Error parsing response: {response}")
                attempt -= 1
                if attempt:
                    chat.messages.pop()
                    return await try_chat_code_changes(attempt, error=str(ex))
                raise ex
        code_generator = await try_chat_code_changes(retry_count)
        if not apply_changes:
            return code_generator

        await self.apply_improve_code_changes(chat=chat, code_generator=code_generator)
        return code_generator

    def get_ai_code_generator_changes(self, response: str):
        code_generator = AI_CODE_GENERATOR_PARSER.invoke(response)
        for change in code_generator.code_changes:
            file_path = change.file_path
            if not file_path.startswith(self.settings.project_path):
                change.file_path = os.path.join(self.settings.project_path, file_path)        
        return code_generator

    def project_script_test(self):
        self.log_info(f"project_script_test, test: {self.settings.script_test} - {self.settings.script_test_check_regex}")
        if not self.settings.script_test:
            return

        command = self.settings.script_test.split(" ")
        result = subprocess.run(command, cwd=self.settings.project_path,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True)
        console_out = result.stdout
        
        self.log_info(f"project_script_test: {console_out} \nOUTPUT DONE")

        test_regex = self.settings.script_test_check_regex if self.settings.script_test_check_regex else 'error' 
        if re.search(test_regex, console_out):
            return console_out
        return ""

    @profile_function
    async def apply_improve_code_changes(self, code_generator: AICodeGerator, chat: Chat = None):
        # Invoke project based on project_id
        self = self.switch_project(chat.project_id)
        
        changes = code_generator.code_changes
        self.log_info(f"improve_existing_code total changes: {len(changes)}")
        changes_by_file_path = {}
        for change in changes:
            file_path = change.file_path
            if file_path not in changes_by_file_path:
                changes_by_file_path[file_path] = []
            changes_by_file_path[file_path].append(change)
        
        for file_path, changes in changes_by_file_path.items():
            change_type = changes[0].change_type
            self.log_info(f"improve_existing_code change: {change_type} - {file_path}")
            self.event_manager.send_event(message=f"Code-gen: change {change_type} - {file_path}")
            
            if change_type == "delete_file":
                os.remove(file_path)
                if file_path in chat.file_list:
                    chat.file_list = [f for f in chat.file_list if f != file_path]
            else:
                content = ""
                if os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                instruction_list = [json.dumps(change.__dict__) for change in changes]
                self.log_info(f"Applying {len(changes)} changes to {file_path}")
                new_content = await self.change_file_with_instructions(instruction_list=instruction_list, file_path=file_path, content=content)
                if new_content and new_content != content:
                    write_file(file_path=file_path, content=new_content)
                    if file_path not in chat.file_list:
                        chat.file_list.append(file_path)
                else:
                    logger.error(f"Error applying changes to {file_path}. New content: {new_content}")

        if chat:
            file_paths = " ".join(changes_by_file_path.keys())
            git_diff, _ = exec_command(f"git diff {file_paths}", cwd=self.settings.project_path)
            chat.messages.append(Message(role="assistant", content=f"```diff\n{git_diff}\n```"))

    async def change_file_with_instructions(self, instruction_list: [str], file_path: str, content: str):
        profile_manager = ProfileManager(settings=self.settings)
        chat = Chat(name=f"changes_at_{file_path}", messages=[])

        content_instructions = f"EXISTING CONTENT:\n{content}" if content else ""
        chat.messages.append(Message(role="user", content=f"""
        {profile_manager.read_profile("software_developer").content}

        Rewrite full file content replacing codx instructions by required changes.
        Return only the file content without any further decoration or comments.
        Do not surround response with '```' marks, just content.
        Always respect current file content formatting.

        INSTRUCTIONS:
        { "- ".join(instruction_list) }

        { content_instructions }
        """))
        await self.chat_with_project(chat=chat, disable_knowledge=True, append_references=False)
        return chat.messages[-1].content

    def check_knowledge_status(self):
        knowledge = Knowledge(settings=self.settings)
        status = knowledge.status()
        pending_files, last_update = knowledge.detect_changes()
        return {
            "last_update": str(last_update),
            "pending_files": pending_files[0:2000],
            "total_pending_changes": len(pending_files),
            **status
        }

    def apply_patch(self, patch: str):
        # Extract the file path from the diff
        file_diff_lines = patch.split('\n')
        file_path = None

        for line in file_diff_lines:
            if line.startswith('+++ b/'):
                file_path = line[6:]  # Removes '+++ b/' to get the file path
                break

        if not file_path:
            logger.error("No file path found in patch.")
            return
        
        # Determine the full path.
        if not file_path.startswith(self.settings.project_path):
            file_path = os.path.join(self.settings.project_path, file_path)

        # Read the existing content of the file if it exists
        existing_content = ""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                existing_content = f.read()

        # Prepare the new content by appending the patch in the required format
        new_content = existing_content + f"""
        """

        # Create directories if they do not exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save the updated content back to the file
        with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
            f.write(new_content)

        logger.info(f"Patch applied and saved to {file_path}")

    async def process_project_changes(self):
        if not self.settings.is_valid_project():
            return

        knowledge = Knowledge(settings=self.settings)
        knowledge.clean_deleted_documents()
        new_files, _ = knowledge.detect_changes()
        if not new_files:
            return    

        def changed_file():
            for file_path in new_files:
                if (int(time.time()) - int(os.stat(file_path).st_mtime) < MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS):
                    return file_path
            return None

        file_path = changed_file() # one at a time by modified time
        if not file_path:
            return

        mention_manager = self.get_mention_manager()
        if not CODX_JUNIOR_API_BACKGROUND:
            return await self.get_mention_manager().check_file_for_mentions(file_path=file_path)

        if not self.settings.watching:
            return

        file_has_mentions = mention_manager.check_if_file_has_mentions(file_path=file_path)  
        if file_has_mentions:
            return
        self.log_info(f"Reload knowledge files {file_path}")
        knowledge.reload_path(path=file_path)
        self.event_manager.send_knowled_event(type="loaded", file_path=file_path)

        self.get_wiki().process_file_change(file_path=file_path)

    def extract_changes(self, content):
        for block in extract_json_blocks(content):
            try:
                for change in block:
                    yield change["change"]
            except:
                pass

    async def change_file(self, context_documents, query, file_path, org_content, save_changes=False):
        profile_manager = ProfileManager(settings=self.settings)
        tasks = "\n *".join(context_documents + [query])
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
        chat = Chat(name=f"{chat_name}_{chat_time}", messages=[
            Message(role="user", content=profile_manager.read_profile("software_developer").content),
            Message(role="user", content=request)
        ])
        try:
            chat = await self.chat_with_project(chat=chat, disable_knowledge=True)
            response = chat.messages[-1].content.strip()
            parsed_response = AI_CODE_VALIDATE_RESPONSE_PARSER.invoke(response)
            return parsed_response.new_content
        except Exception as ex:
            chat.messages.append(Message(role="error", content=str(ex)))
            raise ex
        finally:
            if save_changes:
                await self.save_chat(chat=chat)

    def get_project_profile(self):
        return self.get_profile_manager().read_profile("project")

    @profile_function
    async def summarize_chat(self, chat: Chat, instructions: str = ""):
        if chat.messages[-1].task_item == MessageTaskItem.SUMMARY:
            return chat.messages[-1]

        org_messages = chat.messages
        summary_prompt = f"""
        Create a summary of the conversarion.
        Make sure to do not loose any important detail.
        Syntetize text, no need for verbosity
        Add keywords at the end
        { instructions }
        """
        chat.messages = chat.messages.copy() + [Message(role="user", content=summary_prompt)]
        await self.chat_with_project(chat=chat)
        response_message = chat.messages[-1]
        response_message.task_item = MessageTaskItem.SUMMARY
        response_message.hide = True
        chat.messages = org_messages + [response_message]
        return response_message
          
    @profile_function
    async def generate_tasks(self, chat: Chat, instructions: str = ""):
        with self.chat_action(chat=chat, event="Creating sub-tasks"):

            ai = self.get_ai()
            
            summary = await self.summarize_chat(chat=chat)
            content = summary.content
            last_message = chat.messages[-1]

            project_child_projects, project_dependencies = self.get_project_dependencies()
            logger.info(f"project_child_projects: {[p.__dict__ for p in project_child_projects]}")
            logger.info(f"project_dependencies: {[p.__dict__ for p in project_dependencies]}")

            output_example = """
            [
              { 
                "name": "Task1. Subtask name ",
                "description": "A detailed description with clear instructions about what to do"
              },
              { 
                "name": "Task2. Second task name ",
                "description": "This is  the task description with clear instructions about what to do",
                "tags": ["ui", "angular"]
              }
            ]
            """
            prompt = f"""
            Split into subtasks:

            <content>
            { self.get_chat_analysis_parents(chat=chat) }
            { content }
            </content>

            <main_task>
            { last_message.content }
            </main_task>
            
            <instructions>
              * Take the name of the task from the content if present
              * Take the description from the content
              * The name of the task must indicate the priority like: "Task 1: Perform analysis"
              * Description must be super detailed, explaing all the actions to take, things to change,
              * Make sure to add any relevant information and have instructions for all that needs to be done.
              * Don't forget to enclose the subtasks JSON object with "```json" as the first line, and "```" at the end
              * { instructions }
            </instructions>

            <output_format>
              * Return a single JSON block like the one in the example below without further decoration or comments
                ```json
                { output_example }
                ```
              </output_format>
            """

            response_message = Message(role="assistant",
                                        doc_id=str(uuid.uuid4()))
            chat.messages.append(response_message)
            
            def send_message_event(content):
                if not response_message.is_thinking:
                    response_message.is_thinking = True if "<think>" in content else None
                elif response_message.is_thinking and \
                    "</think>" in content:
                    response_message.is_thinking = False
                
                content = content.replace("<think>", "").replace("</think>", "")

                if response_message.is_thinking:
                    response_message.think = content
                else:
                    response_message.content = content
                self.event_manager.message_event(chat=chat, message=response_message)
            
            retry_count = 2
            ai_tasks = None
            while retry_count:
                retry_count = retry_count - 1
                messages = ai.chat(prompt=prompt, callback=send_message_event)

                response = messages[-1].content

                ai_tasks = next(extract_json_blocks(response), None)
                if ai_tasks:
                    break
                
            if not ai_tasks:
                raise Exception(f"Not valid response from AI")

            response_message.hide = True
            self.save_chat(chat=chat)
            
            self.event_manager.chat_event(chat=chat, message=f"Generating {len(ai_tasks)} sub tasks")

            chat_manager = self.get_chat_manager()
            for task in ai_tasks:
                sub_task = Chat(**task)
                sub_task.parent_id = chat.id
                sub_task.board = chat.board
                sub_task.column = chat.column
                sub_task.project_id = chat.project_id
                sub_task.messages = [
                    Message(role="user",
                    content=f""" 
                    ```xml
                    <context>
                    { content }
                    </context>

                    <task>
                    { sub_task.description }
                    </task>
                    ```
                    
                    Given the "context" improve the "task" description.
                    Return a detailed task description
                    Add all important information
                    Generate a clear and easy redeable description 
                    """,
                    profiles=last_message.profiles,
                    files=last_message.files,
                    user=last_message.user
                )]
                await self.chat_with_project(chat=sub_task)
                sub_task.messages[0].hide = True
                sub_task = chat_manager.save_chat(sub_task)
                self.event_manager.chat_event(chat=sub_task, message=f"Saving subtask {sub_task.name}", event_type="created")

    def get_chat_analysis_parents(self, chat: Chat):
        """Given a chat, traverse all parents and return all analysis"""
        parent_content = []
        chat_manager = self.get_chat_manager()
        parent_chat = chat_manager.find_by_id(chat.parent_id)
        while parent_chat:
            messages = [m.content for m in parent_chat.messages if not m.hide]
            if messages:
                parent_content.append("\n".join(messages))
            parent_chat = chat_manager.find_by_id(parent_chat.parent_id)
        return "\n".join(parent_content)


    def create_knowledge_search_query(self, query: str):
        ai = self.get_ai()
        return ai.chat(prompt=f"""
        <text>
        {query}
        </text>

        Extract keywords from the text to help searching in the knowledge base.
        Return just the search string without further decoration or comments.
        """)[-1].content
    
    @profile_function
    async def api_chat_with_project(self, profile_name: str, messages: []):
        chat = Chat(name="api-chat", profiles=[profile_name], messages=[Message(role=m["role"], content=m["content"]) \
                                                          for m in messages])
        await self.chat_with_project(chat=chat)
        return chat

    def convert_message(self, m):
        msg = None
        def parse_image(image):
            try:
                return json.loads(image)
            except:
                return {"src": image, "alt": ""}
        if m.images:
            images = [parse_image(image) for image in m.images]
            text_content = {
                "type": "text",
                "text": m.content
            }
            content = [text_content] + [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image["src"]
                    }
                } for image in images]

            # self.log_info(f"ImageMessage content: {content}")
            msg = BaseMessage(type="image", content=json.dumps(content))
        elif m.role == "user":
            msg = HumanMessage(content=m.content)
        else:
            msg = AIMessage(content=m.content)
    
        return msg


    @profile_function
    async def chat_with_project(self, chat: Chat, disable_knowledge: bool = False, callback=None, append_references: bool=True, chat_mode: str=None, iteration: int = 0):
        
        chat_engine = ChatEngine(settings=self.settings,
                                event_manager=self.event_manager)
        return await chat_engine.chat_with_project(
                            chat=chat,
                            disable_knowledge=disable_knowledge,
                            callback=callback,
                            append_references=append_references,
                            chat_mode=chat_mode,
                            iteration=iteration
                          )
    

    def check_project(self):
        try:
            self.log_info(f"check_project")
            loader = KnowledgeLoader(settings=self.settings)
            loader.fix_repo()
        except Exception as ex:
            logger.exception(str(ex))

    def extract_tags(self, doc):
        knowledge = Knowledge(settings=self.settings)
        knowledge.extract_doc_keywords(doc)
        return doc

    def get_keywords(self, query):
        return KnowledgeKeywords(settings=self.settings).get_keywords(query)

    def get_wiki_file(self, file_path:str):
        project_wiki_path = self.settings.get_project_wiki_path()
        if project_wiki_path:
            if project_wiki_path[-1] != '/' and file_path[0] != '/':
                file_path = f"/{file_path}"
            wiki_file = f"{project_wiki_path}{file_path}"
            try:
                logger.info(f"Reading wiki file: {wiki_file}")
                with open(wiki_file, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except:
                pass
        return f"> {wiki_file} not found"

    def get_readme(self):
        project_path = self.settings.project_path
        readme_file = f"{project_path}/README.md"
        if os.path.isfile(readme_file):
            with open(readme_file, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        return ""


    async def process_wiki_changes(self):
        pass        
      
    async def update_wiki(self, file_path: str):
        project_wiki_path = self.settings.get_project_wiki_path()
        if not self.settings.project_wiki or file_path.startswith(project_wiki_path):
            return

        project_wiki_home = f"{project_wiki_path}/home.md"

        home_content = f"# {self.settings.project_name}"
        if os.path.isfile(project_wiki_home):
            with open(project_wiki_home, 'r', encoding='utf-8', errors='ignore') as f:
                home_content = f.read()
        else:
            with open(project_wiki_home, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(home_content)

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
            self.log_info(f"update_wiki file_path: {file_path}, project_wiki: {project_wiki_path}")
            chat = Chat(profiles=["wiki"], 
                        messages=[
                            Message(role="user", content=f"""Extract important parts from the content of {file_path} to be added to the wiki.
                            {file_content}
                            """)
            ])
            await self.chat_with_project(chat=chat)
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
            code_generator = await self.improve_existing_code(chat=chat, apply_changes=False)
            self.log_info(f"update_wiki file_path: {file_path}, changes: {code_generator}")
            if code_generator:
                wiki_changes = [change for change in code_generator.code_changes if project_wiki_path in change.file_path]
                self.log_info(f"update_wiki file_path: {file_path}, wiki changes: {wiki_changes}")
                if wiki_changes:
                    await self.apply_improve_code_changes(code_generator=AICodeGerator(code_changes=wiki_changes))

    def update_project_profile(self, file_path: str):
        return  # deprecated

    def get_project_metrics(self):
        chat_manager = ChatManager(settings=self.settings)

        number_of_chats = chat_manager.chat_count()
        chat_changed_last = chat_manager.last_chats()
        
        status = self.check_knowledge_status()
        
        return {
            "number_of_chats": number_of_chats,
            "chats_changed_last": chat_changed_last,
            **status
        }

    def api_image_to_text(self, image_bytes):
        from PIL import Image
        import pytesseract
        import io

        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        
        return text
    
    def parse_file_line(self, file, base_path):
        file_path = os.path.join(base_path, file)
        if not file_path.startswith(self.settings.project_path):
            file_path = f"{self.settings.project_path}/{file_path}"
        is_dir = os.path.isdir(file_path)
        return {
          "name": file.split("/")[-1],
          "file_path": file_path,
          "is_dir": is_dir,
          "children": [] if is_dir else None
        }
    
    def read_directory(self, path: str):
        base_path = path
        files = os.listdir(base_path)
        return {
          "path": path,
          "full_path": base_path,
          "files": [self.parse_file_line(file, base_path) for file in sorted(files)]
        }

    def read_file(self, path: str):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def diff_file(self, path: str, content: str):
        git_command = f"""
        cat << EOF | git --no-pager diff --no-index -- - {path}
        {content}
        EOF
        """

        return os.popen(git_command).read()
      
    @profile_function
    async def process_project_file_before_saving(self, file_path: str, content: str):
        file_profiles = self.get_profile_manager().get_file_profiles(file_path=file_path)
        self.log_info(f"Applying file profiles {[p.name for p in file_profiles]} to {file_path}")
        if file_profiles:
            for profile in file_profiles:
                content = await self.apply_file_profile(file_path=file_path, content=content, profile=profile)
        return content
    
    async def apply_file_profile(self, file_path: str, content: str, profile: Profile):
        file_profile_prompt = f"""
        You are given a section of code that requires improvement by applying best practices. Your task is to refactor the code while ensuring that it adheres to the specified best practices. Please follow the instructions below:

        ### File Content:
        ```
        {content}
        ```

        ### Instructions:
        ```
        {profile.content}
        ```
        Return the final content without any kind of decoration or extra comments. 
        Avoid surronding your response with fences (```), just return the final content.
        """

        content_message = Message(role="user", content=file_profile_prompt)

        chat = Chat(name=f"Improve file with profile {profile.name}", messages=[content_message])
        await self.chat_with_project(chat=chat, disable_knowledge=True)
        return chat.messages[-1].content

    async def write_project_file(self, file_path: str, content: str, process: bool = True):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        if process:
            content = await self.process_project_file_before_saving(file_path=file_path, content=content)
        write_file(file_path=file_path, content=content)

    def search_files(self, search: str):
        all_sources = [s for s in self.get_knowledge().get_all_sources().keys() if search in s]
        base_path = self.settings.project_path
        return [self.parse_file_line(file, base_path) for file in sorted(all_sources)]

    def run_app(self, app_name: str):
        command = APPS_COMMANDS[app_name]
        exec_command(command)

    def get_project_apps(self):
        return APPS

    def get_project_branches(self):
        stdout, _ = exec_command("git branch",
            cwd=self.settings.project_path)
        branches = [s.strip() for s in stdout.split("\n") if s.strip()]
        current_branch = [b for b in branches if b.startswith('* ')]
        if current_branch:
            current_branch = current_branch[0].replace('* ', '')
        else:
            current_branch = ""

        branches = [b.replace('* ', '') for b in branches]

        branch_details = self.get_branch_details(current_branch)
        parent_branch = branch_details["parent_branch"]

        git_diff = ""
        if current_branch and parent_branch:
            head_ix = len(branch_details["commits"]) - 1
            stdout, _ = exec_command(f"git diff HEAD~{head_ix}",
              cwd=self.settings.project_path)
            git_diff = stdout


        return {
          "branches": branches,
          "current_branch": current_branch.strip(),
          "parent_branch": parent_branch,
          "git_diff": git_diff,
          "branch_details": branch_details
        }

    def get_branch_details(self, branch_name: str):
        """
        Extracts commit details from a specified branch without checking it out.

        Args:
            branch_name (str): The name of the branch to extract commits from.

        Returns:
            list: A list of dictionaries containing commit information.
        """
        # Command to get commit details from the specified branch
        log_command = f"git log -g --format=%H|%an|%cI|%s {branch_name}"
        stdout, _ = exec_command(log_command, cwd=self.settings.project_path)

        log_lines = stdout.split('\n')

        commits = []
        for entry in log_lines:
            if entry.strip():
                commit_hash, author, date, message = entry.split('|', 3)

                # Command to get files changed in each commit
                file_changes_command = \
                    f'git show --name-only --pretty=format:{commit_hash}'
                stdout, _ = exec_command(file_changes_command, cwd=self.settings.project_path)
                file_changes = stdout.strip().split('\n')
                commits.append({
                    'entry_line': entry,
                    'commit_hash': commit_hash,
                    'author': author,
                    'date': date,
                    'message': message,
                    'files': [file for file in file_changes if file][1:]
                })

        return {
          "commits": commits,
          "parent_branch": commits[-1]["commit_hash"]
        }

    def get_project_current_branch(self):
        stdout, _ = exec_command("git branch --show-current")
        return stdout

    def get_project_parent_branch(self):
        current_branch = self.get_project_current_branch()
        stdout, _ = exec_command(f"git reflog {current_branch}",
                              cwd=self.settings.project_path)
        self.log_info(f"get_project_parent_branch reflog: {stdout} cwd: {self.settings.project_path}")
        creation_line = [l for l in stdout.split("\n") if "Created from" in l][0]
        # 808a14a v1.0-hello-codx-junior@{53}: branch: Created from refs/remotes/origin/v1.0-hello-codx-junior
        if "refs/remotes/" in creation_line:
            ref_branch = creation_line.split(" ")[-1].remove("refs/remotes/", "")
            # origin/v1.0-hello-codx-junior
            return ref_branch

        # 5f3e0bdd (origin/main, origin/task-two) tsk-task-1@{4}: branch: Created from 5f3e0bddbc466967f1a2eedc731eec980978b184
        ref_branch  = creation_line.split(" (")[1].split(",")[0]
        return ref_branch

    def get_project_changes(self, parent_branch: str = None):
        if not parent_branch:
            #parent_branch = self.get_project_parent_branch()
            parent_branch = parent_branch or "HEAD@{1}"
            self.log_info(f"get_project_changes parent_branch {parent_branch}")
        stdout, _ = exec_command(f"git diff {parent_branch}",
                      cwd=self.settings.project_path)
        return stdout

    def build_code_changes_summary(self, force = False):
        project_branches = self.get_project_branches()
        diff = project_branches["git_diff"]
        return self.get_knowledge().build_code_changes_summary(diff=diff, force=force)
