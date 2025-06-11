import os
import logging
import re
import json
import time
import subprocess
import shutil
import asyncio
import uuid
import requests
from datetime import datetime
from pathlib import Path
from threading import Thread

from slugify import slugify

from contextlib import contextmanager

from langchain.schema.document import Document
from langchain.schema import (
    AIMessage,
    HumanMessage,
    BaseMessage,
    SystemMessage
)

from codx.junior.utils import (
    document_to_context,
    extract_code_blocks,
    extract_json_blocks,
    exec_command,
    write_file
)

from codx.junior.profiling.profiler import profile_function

from codx.junior.ai import AI
from codx.junior.settings import (
    CODXJuniorSettings,
    read_global_settings
)

from codx.junior.chat_manager import ChatManager
from codx.junior.profiles.profile_manager import ProfileManager

from codx.junior.model.model import (
    KnowledgeSearch,
    Document,
    Content,
    ImageUrl,
    LiveEdit,
    GlobalSettings,
    Profile,
    CodxUser
)
from codx.junior.context import (
    find_relevant_documents,
    AI_CODE_VALIDATE_RESPONSE_PARSER,
    generate_markdown_tree,
    AI_CODE_GENERATOR_PARSER,
    AICodeGerator,
    AICodePatch
)

from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.knowledge.knowledge_loader import KnowledgeLoader
from codx.junior.knowledge.knowledge_keywords import KnowledgeKeywords

from codx.junior.mention_manager import (
    extract_mentions,
    replace_mentions,
    notify_mentions_in_progress,
    notify_mentions_error,
    strip_mentions,
    is_processing_mentions
)
from codx.junior.db import (
    Kanban,
    Chat,
    Message,
    MessageTaskItem
)

from codx.junior.sio.session_channel import SessionChannel
from codx.junior.security.user_management import UserSecurityManager


"""Changed files older than MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS won't be processed"""
MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS = 300

CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")

logger = logging.getLogger(__name__)

APPS = [
    {
        "name": "chrome",
        "icon": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e1/Google_Chrome_icon_%28February_2022%29.svg/768px-Google_Chrome_icon_%28February_2022%29.svg.png",
        "description": "Google chrome engine",
    }
]

APPS_COMMANDS = {
    "chrome": "google-chrome --no-sandbox --no-default-browser-check"
}

AGENT_DONE_WORD = "$$@@AGENT_DONE@@$$$"

def create_project(project_path: str, user: CodxUser):
    logger.info(f"Create new project {project_path}")
    global_settings = read_global_settings()
    projects_root_path = global_settings.projects_root_path or f"{os.environ['HOME']}/projects"
    os.makedirs(projects_root_path, exist_ok=True)
        
    if project_path.startswith("http"):
        url = project_path
        repo_name = url.split("/")[-1].split(".")[0]
        project_path = f"{projects_root_path}/{repo_name}"
        command = f"git clone --depth=1 {url} {project_path}"
        logger.info(f"Cloning repo {url} {repo_name} {project_path}")
        exec_command(command=command)
    
    existing_project = find_project_by_project_path(project_path=project_path)
    if existing_project:
        logger.info(f"Project already esists {url} {repo_name} {project_path}")
        return existing_project

    settings = CODXJuniorSettings()
    settings.project_name = project_path.split("/")[-1]
    settings.codx_path = f"{project_path}/.codx"
    settings.watching = True
    settings.save_project()
    _, stderr = exec_command("git branch")
    if stderr:
        exec_command("git init", cwd=project_path)
    new_project = CODXJuniorSettings.from_project_file(f"{project_path}/.codx/project.json")
    if user:
      UserSecurityManager().add_user_to_project(project_id=new_project.project_id, user=user, permissions='admin')
    return new_project

def coder_open_file(settings: CODXJuniorSettings,  file_name: str):
    logger.info(f"coder_open_file {file_name}")
    os.system(f"code-server -r {file_name}")


def find_project_from_file_path(file_path: str):
    """Given a file path, find the project parent"""
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if file_path.startswith(p.project_path)]
    if matches:
        logger.info(f"Find projects for file {file_path}: {[m.project_name for m in matches]}")
        return sorted(matches, key=lambda p: len(p.project_path))[-1]
    return None
  
def find_project_by_id(project_id: str):
    """Given a project id, find the project"""
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if p.project_id == project_id]
    return matches[0] if matches else None

def find_project_by_project_path(project_path: str):
    """Given a project id, find the project"""
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if p.project_path == project_path]
    return matches[0] if matches else None

def find_project_by_name(project_name: str):
    """Given a project project_name, find the project"""
    all_projects = find_all_projects().values()
    matches = [p for p in all_projects if p.project_name == project_name]
    return matches[0] if matches else None

def find_all_user_projects(user: CodxUser):
    user_security_manager = UserSecurityManager()
    for settings in find_all_projects().values():
        permissions = user_security_manager.get_user_project_access(user=user, settings=settings)
        if permissions:
            yield {
                **settings.__dict__,
                "permissions": permissions
            }

def find_all_projects():
    all_projects = {}
    project_path = "/"
    result = subprocess.run("find / -name .codx".split(" "), cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    all_codx_path = result.stdout.decode('utf-8').split("\n")
    paths = [p for p in all_codx_path if os.path.isfile(f"{p}/project.json")]
    #logger.info(f"[find_all_projects] paths: {paths}")
    def is_valid_project(settings):
        if not settings or not settings.project_name:
            return False
        if [p for p in all_projects.values() if p.project_name == settings.project_name]:
            return False
        return True

    for codx_path in paths:
        try:
            project_file_path = f"{codx_path}/project.json"
            settings = CODXJuniorSettings.from_project_file(project_file_path)
            if is_valid_project(settings): 
                all_projects[settings.project_id] = settings
            else:
                # logger.error(f"Error duplicate project at: {settings.project_path} at {project_exists[0].project_path}")
                pass 
        except Exception as ex:
            logger.exception(f"Error loading project {str(codx_path)} : {ex}")
    
    def update_projects_with_details():
        for project in all_projects.values():
            try:
                command = ["git", "branch", "--show-current"]
                result = subprocess.run(command, cwd=project.project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                project.__dict__["_current_git_branch"] = result.stdout.decode('utf-8')
            except Exception as ex:
                project.__dict__["_current_git_branch"] = f"Error: {ex}"
            project.__dict__["_metrics"] = CODXJuniorSession(settings=project).get_project_metrics()
            project.__dict__["_sub_projects"] = [sp.project_name for sp in project.get_sub_projects()]
    return all_projects

def update_engine():
    try:
        command = ["git", "pull"]
        subprocess.run(command)
    except Exception as ex:
        logger.exception(ex)
        return ex


class CODXJuniorSession:
    def __init__(self,
            settings: CODXJuniorSettings = None,
            codx_path: str = None,
            channel: SessionChannel = None):
        self.settings = settings or CODXJuniorSettings.from_project_file(f"{codx_path}/project.json")
        self.channel = channel
        
        if not channel:
            from codx.junior.sio.sio import sio
            self.channel = SessionChannel(sio=sio)

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

    def get_channel(self):
        return self.channel

    def event_data(self, data: dict):
        data['codx_path'] = self.settings.codx_path
        return data

    def send_notification(self, **kwargs):
        self.get_channel().send_event('codx-junior', self.event_data({ **kwargs, "type": "notification" }))

    def send_event(self, message: str):
        self.get_channel().send_event('codx-junior', self.event_data({ 'text': message, "type": "event" }))
        # self.log_info(f"SEND MESSAGE {message}- SENT!")

    def chat_event(self, chat: Chat, message: str = None, event_type: str = None):
        self.get_channel().send_event('chat-event', self.event_data({ 'chat': { 'id': chat.id }, 'text': message, 'type': event_type }))
        # self.log_info(f"SEND MESSAGE {message}- SENT!")

    def message_event(self, chat: Chat, message: Message):
        self.get_channel().send_event('message-event', self.event_data({ 'chat': { 'id': chat.id }, 'message': message.model_dump() }))
        # self.log_info(f"SEND MESSAGE {message.role} {message.doc_id}- SENT!")

    @contextmanager
    def chat_action(self, chat: Chat, event: str):
        self.chat_event(chat=chat, message=f"{event} starting")
        self.log_info(f"Start chat {chat.name}")
        try:
            yield
        except Exception as ex:
            self.chat_event(chat=chat, message=f"{event} error: {ex}", event_type="error")
            self.log_exception(f"Chat {chat.name} {event} error: {ex}")
        finally:
            self.chat_event(chat=chat, message=f"{event} done")
            self.log_info(f"Chat done {chat.name}")

    
    def delete_project(self):
        shutil.rmtree(self.settings.codx_path)
        logger.error(f"PROJECT REMOVED {self.settings.codx_path}")

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
        return WikiManager(session=self)

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
        self.chat_event(chat=chat, event_type="changed")
        return chat

    def delete_chat(self, chat_id):
        self.get_chat_manager().delete_chat(chat_id=chat_id)

    @profile_function
    def list_profiles(self):
        return self.get_profile_manager().list_profiles()

    async def save_profile(self, profile):
        profile = self.get_profile_manager().save_profile(profile=profile)
        await self.check_file_for_mentions(file_path=profile.content_path)
        return self.read_profile(profile_name=profile.name)

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
        elif knowledge_search.search_type == "source":
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

    def delete_knowledge(self):
        Knowledge(settings=self.settings).reset()
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
        mentions = re.findall(r'@[a-zA-Z0-9\-\_\.]+', query)
        self.log_info(f"Extracted mentions: {mentions}")
        return mentions

    def find_projects_by_mentions(self, mentions: [str]):
        return [project for project in [find_project_by_name(mention[1:]) for mention in mentions] if project]

    def get_profiles_and_parents(self, profiles: []):
        """
        Return all inmediate parent profiles from a profile list
        """
        profile_manager = self.get_profile_manager()
        project_profiles = profile_manager.list_profiles()

        all_profiles = list(profiles)
        def add_profile(profile_name):
            profile = next((p for p in project_profiles if p.name == profile_name), None)
            if profile and profile not in all_profiles:
                all_profiles.append(profile)

        for profile in profiles:
            for profile_name in profile.profiles:
                add_profile(profile_name)
        
        return all_profiles
    
    def find_profiles_by_mentions(self, mentions: [str]):
        profile_manager = self.get_profile_manager()
        profiles = profile_manager.list_profiles()
        mention_profiles = [p for p in profiles if p.name in mentions]
        return self.get_profiles_and_parents(mention_profiles)

    def get_query_mentions(self, query: str):
        mentions = self.extract_query_mentions(query=query)
        projects = self.find_projects_by_mentions(mentions=mentions)
        profiles = self.find_profiles_by_mentions(mentions=mentions)
        return {
          "projects": projects,
          "profiles": profiles
        }

    @profile_function
    def find_project_documents(self, query: str):
        documents, _ = self.select_afefcted_documents_from_knowledge(chat=None, ai=self.get_ai(), query=query, search_projects=[])
        return documents
    
    @profile_function
    def select_afefcted_documents_from_knowledge(self, chat: Chat, ai: AI, query: str, ignore_documents=[], search_projects = []):
        for search_project in search_projects:
            query = query.replace(f"@{search_project.project_name}", "")

        @profile_function
        def process_rag_query(rag_query):
            docs = []
            file_list = []

            self.log_info(f"select_afefcted_documents_from_knowledge search subprojects: {rag_query} in {[p.project_name for p in search_projects]}")
            for search_project in search_projects:
                if chat:    
                    self.chat_event(chat=chat, message=f"Search knowledge in {search_project.project_name}: {search_project.project_path}")
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
            self.chat_event(chat=chat, message="Executing bash script")
            stdout, stderr = exec_command(code, cwd=self.settings.project_path)
            chat.messages.append(Message(role="user", content=f"""
            Executing bash script
            ```{language}
            {code}
            ```
            stdout: {stdout}
            stderr: {stderr}
            """))
            self.chat_event(chat=chat, message="Applying patch done.")
            await self.save_chat(chat=chat)
        except Exception as ex:
            self.chat_event(chat=chat, message=f"Error applying patch: {ex}", event_type="error")
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
            self.chat_event(chat=chat, message="Applying patch")
            await self.improve_existing_code(chat=chat, apply_changes=True)
            self.chat_event(chat=chat, message="Applying patch done.")
        except Exception as ex:
            self.chat_event(chat=chat, message=f"Error applying patch: {ex}", event_type="error")
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
        self.send_event(message=f"Code changes")

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
            self.send_event(message=f"Code-gen: change {change_type} - {file_path}")
            
            if change_type == "delete_file":
                del open_files[file_path]
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

    @profile_function
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

    def check_project_changes(self):
        if not self.settings.is_valid_project():
            # logger.error(f"check_project_changes invalid project {self.settings}")
            return False
        knowledge = Knowledge(settings=self.settings)
        knowledge.clean_deleted_documents()
        new_files = knowledge.detect_changes()
        if not new_files:
            self.log_info(f"check_project_changes {self.settings.project_name} no changes")
            return False
        return True

    @profile_function
    async def check_file(self, file_path: str, force: bool = False):
        res = await self.check_file_for_mentions(file_path=file_path)
        self.log_info(f"Check file {file_path} for mentions: {res}")
        # Reload knowledge 
        if CODX_JUNIOR_API_BACKGROUND:
            if res != "processing" and (force or self.settings.watching):
                knowledge = self.get_knowledge()
                knowledge.reload_path(path=file_path)

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

        res = await self.check_file_for_mentions(file_path=file_path)
        if res == "processing":
            return

        if self.settings.watching:
            self.log_info(f"Reload knowledge files {new_files}")
            knowledge.reload_path(path=file_path)

    def extract_changes(self, content):
        for block in extract_json_blocks(content):
            try:
                for change in block:
                    yield change["change"]
            except:
                pass

    def split_blocks_by_gt_lt(self, content):
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

    def get_line_changes(self, content):
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

    @profile_function
    async def check_file_for_mentions(self, file_path: str, content: str = None, silent: bool = False):

        async def check_file_for_mentions_inner(file_path: str, content: str = None, silent: bool = False):
            profile_manager = self.get_profile_manager()
            chat_manager = self.get_chat_manager()
            mentions = None
            file_profiles = profile_manager.get_file_profiles(file_path=file_path)
            file_profiles = self.get_profiles_and_parents(file_profiles)
            profile_names = [p.name for p in file_profiles]

            def read_file():
                def prepare_ipynb_for_llm():
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                        notebook_data = json.loads(file.read())
                    
                        # Remove outputs from each cell
                        for cell in notebook_data.get('cells', []):
                            if 'outputs' in cell:
                                del cell['outputs']
                    
                        return json.dumps(notebook_data)

                if  file_path.endswith(".ipynb"):
                    return prepare_ipynb_for_llm()
            
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()

            if not content:
                content = read_file()
            
            if is_processing_mentions(content=content):
                return "processing"

            mentions = extract_mentions(content)
            
            if not mentions:
                return ""

            # Don't process in background, mentions will be taken by main API module
            if CODX_JUNIOR_API_BACKGROUND:
                return "processing"

            self.send_notification(text=f"@codx {len(mentions)} mentions in {file_path.split('/')[-1]} profiles: {profile_names}")    
            self.log_info(f"{len(mentions)} mentions found for {file_path} profiles: {profile_names}")

            new_content = notify_mentions_in_progress(content)
            if not silent:
                write_file(file_path=file_path, content=new_content)

            image_mentions = [m for m in mentions if m.flags.image]
            if image_mentions:
                new_content = self.process_image_mention(image_mentions, file_path, content)
                return await self.check_file_for_mentions(file_path=file_path, content=new_content, silent=True)

            use_knowledge = any(m.flags.knowledge for m in mentions)
            using_chat = any(m.flags.chat_id for m in mentions)
            run_code = any(m.flags.code for m in mentions)

            save_mentions = self.settings.save_mentions

            if using_chat:
                use_knowledge = False       
                self.log_info(f"Skip KNOWLEDGE search for processing, using_chat={using_chat}")
            
            def mention_info(mention):
                chat = chat_manager.find_by_id(mention.flags.chat_id) if mention.flags.chat_id else None
                if chat:
                    self.log_info(f"using CHAT for processing mention: {mention.mention}")
                    return f"""Based on this conversation:
                    ```markdown
                    {chat_manager.serialize_chat(chat)}
                    ```
                    User commented in line {mention.start_line}: {mention.mention}
                    """
                return f"User commented in line {mention.start_line}: {mention.mention}"
            
            query = "\n  *".join([mention_info(mention) for mention in mentions])
            query_mentions = self.get_query_mentions(query=query)

            file_chat_name = "-".join(file_path.split("/")[-2:])
            
            self.log_info(f"Create mention chat {file_chat_name}")
            analysis_chat = None
            if use_knowledge:
                analysis_chat = Chat(name=slugify(f"analysis_at_{file_chat_name}-{datetime.now()}"), 
                    board="mentions",
                    column="analysis",
                    mode="chat",
                    tags=["use_knowledge" if use_knowledge else "skip_knowledge"],
                    messages=
                    [
                        Message(role="user", content="\n".join([
                        f"Find at @{self.settings.project_name} all information needed to apply all changes to file: {file_path}",
                        "",
                        f"Changes:",
                        query,
                        "",
                        "File content:",
                        new_content
                        ]))
                    ])
                self.log_info(f"Chat with project analysis {analysis_chat.name}")
                await self.chat_with_project(chat=analysis_chat)
                if save_mentions:
                    analysis_chat = chat_manager.save_chat(analysis_chat)

            if run_code:
                self.log_info(f"Mentions running code {file_path}")
                await self.improve_existing_code(chat=chat, apply_changes=True)
            else:
                changes_chat = Chat(name=slugify(f"changes_at_{file_chat_name}-{datetime.now()}"), 
                    board="mentions",
                    column="changes",
                    parent_chat=analysis_chat.id if analysis_chat else None,
                    tags=["use_knowledge" if use_knowledge else "skip_knowledge"],
                    profiles=[p.name for p in query_mentions["profiles"]],
                    messages=[])
                
                if analysis_chat:
                    changes_chat.messages.append(analysis_chat.messages[-1])

                file_profile_content = ""
                if file_profiles:
                    file_profile_content = "\n".join([
                        profile.content for profile in file_profiles
                    ])
                    
                    file_profile_content=f"""Best practices for this file:
                    {file_profile_content}
                    """

                changes_chat.messages.append(Message(role="user", content=f"""
                Apply codx comments and rewrite full content.
                Return only the content without any further decoration or comments.
                Do not surround response with '```' marks, just content.
                Remove codx comments from the final version. 
                Do not return the <document> tags.
                """))


                changes_chat.messages.append(
                        Message(
                            role="user",
                            profiles=[profile.name for profile in file_profiles],
                            files=[file_path],
                            content=f"""
                                Given this document:
                                <document>
                                
                                {new_content}
                                
                                </document>
                                
                                User has added these comments:
                                <comments>
                                @{self.settings.project_name} {query}
                                </comments>

                                {file_profile_content}
                                """)
                    )
                
                self.log_info(f"Mentions generate changes {file_path}")
                
                await self.chat_with_project(chat=changes_chat, disable_knowledge=True, append_references=False)
                if save_mentions:
                    chat_manager.save_chat(changes_chat)
                response = changes_chat.messages[-1].content
                
                self.log_info(f"Mentions save file changes {file_path}")
                write_file(file_path=file_path, content=response)
            
            self.send_notification(text=f"@codx done for {file_path.split('/')[-1]}")
        
            return "done"
        try:
            res = await check_file_for_mentions_inner(file_path=file_path, content=content, silent=silent)
            self.log_info(f"[{self.settings.project_name}] Mentions manager done for {file_path}")
            return res
        except Exception as ex:
            self.log_exception(f"Error processing mentions at {file_path}: {ex}")

    def process_image_mention(self, image_mentions, file_path: str, content: str):
        ai = self.get_ai()
        for image_mention in image_mentions:
            image_mention.new_content = ai.image(image_mention.content)
        return replace_mentions(content, image_mentions)

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

            def format_project_info(project):
                logger.info(f"format_project_info: {project.__dict__}")
                return f"""<project name="{project.settings.project_name}" id="{project.settings.project_id}">
                { project.get_project_profile().content }
                </project>
                """

            def get_format_instructions():
                return """
                {
                  "tasks": [
                    {
                      "name": "Design the `project_departments` Junction Table Schema",
                      "tags": ["ux", "to-do", "whatever"],
                      "messages": [
                        { 
                          "role": "assistent",
                          "content":"Define the schema for the `project_departments` junction table.  It should have columns for `project_id` (foreign key referencing the Project table) and `department_id` (foreign key referencing the Department table). Consider adding a timestamp column for tracking assignment history."
                        }
                      ],
                    }
                  ]
                }
                """

            project_child_projects, project_dependencies = self.get_project_dependencies()
            logger.info(f"project_child_projects: {[p.__dict__ for p in project_child_projects]}")
            logger.info(f"project_dependencies: {[p.__dict__ for p in project_dependencies]}")
            all_projects = [self] + [CODXJuniorSession(settings=settings) for settings in project_child_projects + project_dependencies]
            projects_section = "\n".join([format_project_info(project=project) for project in all_projects])

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
                self.message_event(chat=chat, message=response_message)
            
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
            
            self.chat_event(chat=chat, message=f"Generating {len(ai_tasks)} sub tasks")

            chat_manager = self.get_chat_manager()
            for task in ai_tasks:
                sub_task = Chat(**task)
                sub_task.parent_id = chat.id
                sub_task.board = chat.board
                sub_task.column = chat.column
                sub_task.project_id = chat.project_id
                sub_task.messages = [Message(role="user", content=f""" 
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
                """
                )]
                await self.chat_with_project(chat=sub_task)
                sub_task.messages[0].hide = True
                sub_task = chat_manager.save_chat(sub_task)
                self.chat_event(chat=sub_task, message=f"Saving subtask {sub_task.name}", event_type="created")

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
        timing_info = {
            "start_time": time.time(),
            "first_response": None
        }

        # Invoke project based on project_id
        self = self.switch_project(chat.project_id)

        with self.chat_action(chat=chat, event=f"Processing AI request {chat.name}"):
            chat_mode = chat_mode or chat.mode or "chat"
            if chat_mode == "browser":
                self.log_info(f"chat_with_project browser mode")
                self.chat_event(chat=chat, message=f"connecting with browser...")
                return self.get_browser().chat_with_browser(chat)

            documents = []
            task_item = ""

            parent_chat = None
            if chat.parent_id:
                chat_manager = self.get_chat_manager()
                parent_chat = chat_manager.find_by_id(chat.parent_id)


            max_iterations = self.settings.get_agent_max_iterations()
            iterations_left = max_iterations - iteration

            response_message = Message(role="assistant",
                                      doc_id=str(uuid.uuid4()))
            def send_message_event(content, done):
                if not response_message.is_thinking:
                    response_message.is_thinking = True if "<think>" in content else None
                elif response_message.is_thinking and \
                    "</think>" in content:
                        response_message.is_thinking = False
                
                content = content.replace("<think>", "").replace("</think>", "")

                if not timing_info.get("first_response"):
                    timing_info["first_response"] = time.time() - timing_info["start_time"]

                if response_message.is_thinking:
                    response_message.think = content
                else:
                    response_message.content = content
                sources =  []
                if documents:
                    sources = list(set([doc.metadata["source"].replace(self.settings.project_path, "") for doc in documents]))
                response_message.files = sources
                response_message.task_item = task_item
                response_message.done = done
                self.message_event(chat=chat, message=response_message)

            send_message_event("", False)

            valid_messages = [m for m in chat.messages if not m.hide and not m.improvement]
            ai_messages = [m for m in valid_messages if m.role == "assistant"]
            last_ai_message = ai_messages[-1] if ai_messages else None
                
            user_message = valid_messages[-1] if valid_messages else HumanMessage(content="")
            query = user_message.content

            query_mentions = self.get_query_mentions(query=query)
            
            profile_manager = ProfileManager(settings=self.settings)
            def load_profiles():
                query_profiles = query_mentions["profiles"]
                chat_profiles = [profile_manager.read_profile(profile_name) \
                                    for profile_name \
                                    in chat.profiles + (user_message.profiles or [])]
                all_profiles = [p for p in chat_profiles + query_profiles if p]
                all_profiles = self.get_profiles_and_parents(all_profiles)
                profile_names = [p.name for p in all_profiles]
                self.log_info(f"Loading profiles: {profile_names}")
                return all_profiles

            is_refine = chat_mode == "task"
            is_agent = chat_mode  == "agent"
            
            chat_profiles = load_profiles()
            
            chat_profiles_content = ""
            chat_profile_names = []
            chat_model = chat.model
            profiles_with_knowledge = []
            messages = []

            if chat_profiles:
                valid_profiles = [profile for profile in chat_profiles if profile]
                chat_profiles_content = chat_profiles_content + "\n".join([profile.content for profile in valid_profiles])
                chat_profile_names = [profile.name for profile in valid_profiles]
                if not chat_model:
                    chat_models = list(set([profile.llm_model for profile in valid_profiles if profile.llm_model]))
                    chat_model = chat_models[0] if chat_models else None
                if valid_profiles[0].chat_mode:
                    chat_mode = valid_profiles[0].chat_mode
                # None profile uses knowledge, disable knowledge
                if not disable_knowledge:
                    profiles_with_knowledge = [p for p in valid_profiles if p.use_knowledge]
                if next((p for p in valid_profiles if p.chat_mode == 'task'), None):
                    is_refine = True

            if is_refine:
                task_item = "analysis"
          
            self.log_info(f"chat_with_project {chat.name} settings ready")
            for m in chat.messages[0:-1]:
                if m.hide or m.improvement:
                    continue
                msg = self.convert_message(m)
                messages.append(msg)

            context = ""
            documents = []
            chat_files = chat.file_list or []
            if parent_chat and parent_chat.file_list:
                chat_files = chat_files + parent_chat.file_list

            ignore_documents = chat_files.copy()
            if chat.name:
                ignore_documents.append(f"/{chat.name}")

            if chat_profile_names:
                self.chat_event(chat=chat, message=f"Chat profiles: {chat_profile_names}")

            for chat_file in chat_files:
                chat_file_full_path = chat_file
                if self.settings.project_path not in chat_file_full_path:
                    if chat_file[0] == '/':
                        chat_file = chat_file[1:]
                    chat_file_full_path = f"{self.settings.project_path}/{chat_file}"
                try:
                  with open(chat_file_full_path, 'r') as f:
                      doc_context = document_to_context(
                        Document(page_content=f.read(), metadata={ "source": chat_file })
                      )
                      messages.append(HumanMessage(content=f"""
                      * To change existing file '{chat_file_full_path}' generate a diff patch block
                      
                      {doc_context}
                      """))
                except Exception as ex:
                    logger.error(f"Error adding context file to chat {ex}")

            # Prepare AI
            ai_settings = self.settings.get_llm_settings()
            if chat_model:
                ai_settings.model = chat_model
            ai = self.get_ai(llm_model=ai_settings.model)

            # Read knowledge
            search_projects = ({
                    settings.codx_path:settings for settings in (query_mentions["projects"] + self.get_all_search_projects())
                }).values()
            
            if not disable_knowledge and self.settings.use_knowledge and search_projects:
                self.log_info(f"chat_with_project start project search {search_projects}")
                try:
                    doc_length = 0
                    if query:
                        query_context = "\n".join([m.content for m in messages])
                        search_query = self.create_knowledge_search_query(query=f"{query_context}\n{query}")
          
                        self.chat_event(chat=chat, message=f"Knowledge searching for: {search_query}")
                        
                        documents, file_list = self.select_afefcted_documents_from_knowledge(ai=ai, chat=chat, query=search_query, ignore_documents=ignore_documents, search_projects=search_projects)
                        for doc in documents:
                            doc_context = document_to_context(doc)
                            context += f"{doc_context}\n"
                    
                        response_message.files = file_list
                        doc_length = len(documents)
                    self.chat_event(chat=chat, message=f"Knowledge search found {doc_length} relevant documents")
                except Exception as ex:
                    self.chat_event(chat=chat, message=f"!!Error searching in knowledge {ex}", event_type="error")
                    self.log_exception(f"!!Error searching in knowledge {ex}")
            else:
                self.chat_event(chat=chat, message="! Knowledge search is disabled !")
            if context:
                messages.append(self.convert_message(
                    Message(role="user", content=f"""
                      THIS INFORMATION IS COMING FROM PROJECT'S FILES.
                      HOPE IT HELPS TO ANSWER USER REQUEST.
                      KEEP FILE SOURCE WHEN WRITING CODE BLOCKS (EXISTING OR NEWS).
                      {context}
                      """)))

            if is_refine:
                existing_document = last_ai_message.content if last_ai_message else "" 
                refine_request = user_message.content
                parent_task = self.get_chat_analysis_parents(chat=chat)
                task_content = user_message.content

                if parent_task:
                    task_content = f"""
                    You are writting a child document.
                    This information comes from the parent document for your information:
                    <parent_document>
                    {parent_task}
                    </parent_document>
                    """
                
                if existing_document:
                    task_content += f"""
                    Update the document with user comments:
                    <document>
                    {existing_document}
                    </document>
                    User comments:
                    {user_message.content}
                    """
                else:
                    task_content += f"""
                    Create new document based on user comments.
                    User comments:
                    {user_message.content}
                    """

                task_content += f"""
                Important: Always return the mardown document without any comments before or after, to keep it clean."""

                refine_message = Message(role="user", content=task_content)
                messages.append(self.convert_message(refine_message))
            elif is_agent:
                refine_message = Message(role="user", content=f"""
                You are responsible to end this task.
                Follow instructions and try to solve it with the minimun iterations needed.
                <task>
                { chat.name }
                </task>

                <parent_context>
                {self.get_chat_analysis_parents(chat=chat)}
                </parent_context>

                <user_request>
                Refine document with this comments:
                {user_message.content}
                </user_request>
                
                You still have { iterations_left } attemps more to finish the task. 
                Return { AGENT_DONE_WORD } when the task is done.
                """)
                messages.append(self.convert_message(refine_message))
            else:
                messages.append(self.convert_message(user_message))

            if chat_profiles_content:
                messages[-1].content += f"\nInstructions:\n{chat_profiles_content}"
            self.chat_event(chat=chat, message=f"Chatting with {ai_settings.model}")

            if not callback:
                callback = lambda content: send_message_event(content=content, done=False)
            try:
                messages = ai.chat(messages, callback=callback)
                message_parts = messages[-1].content.replace("<think>", "").split("</think>")
                is_thinking = len(message_parts) == 2
                response_message.think = message_parts[0] if is_thinking else None
                response_message.content = message_parts[-1]
                response_message.is_thinking = False
                send_message_event(content=response_message.content, done=True)
            except Exception as ex:
                logger.exception(f"Error chating with project: {ex} {chat.id}")
                response_message.content = f"Ops, sorry! There was an error with latest request: {ex}"

            response_message.meta_data["time_taken"] = time.time() - timing_info["start_time"]
            response_message.meta_data["first_chunk_time_taken"] = timing_info["first_response"]
            response_message.meta_data["model"] = ai_settings.model
            response_message.profiles = chat_profile_names
            
            chat.messages.append(response_message)

            # Chat description
            try:
                description_message = ai.chat(messages=messages.copy(),
                                              prompt="Create a 5 lines summary of the conversation")[-1]
                chat.description = description_message.content
            except Exception as ex:
                logger.exception(f"Error chating with project: {ex} {chat.id}")
                response_message.content = f"Ops, sorry! There was an error with latest request: {ex}"

            if chat_mode == 'task':
                for message in chat.messages[:-1]:
                    message.hide = True

            is_agent_done = AGENT_DONE_WORD in response_message.content
            if is_agent and not is_agent_done and iterations_left:
              self.chat_event(chat=chat, message=f"Agent iteration {iteration + 1}")
              return self.chat_with_project(chat=chat,
                    disable_knowledge=disable_knowledge,
                    callback=callback,
                    append_references=append_references,
                    chat_mode=chat_mode,
                    iteration=iteration + 1)
            else:    
              self.chat_event(chat=chat, message="done")
            return chat, documents
            
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
        knowledge = Knowledge(settings=self.settings)
        # pending_files, last_update = knowledge.detect_changes(last_update=)
        
      
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

    async def write_project_file(self, file_path: str, content: str):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
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
