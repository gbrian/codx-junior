# [[{"id": "ea9e3cf1-150b-43bc-9303-87cb3ea69ec0", "doc_id": null, "project_id": null, "parent_id": null, "status": "", "tags": [], "file_list": ["/shared/codx-junior/api/codx/junior/engine.py", "/shared/codx-junior/api/codx/junior/events/event_manager.py"], "profiles": [], "users": ["admin"], "name": "Add event manager to engine", "description": "The conversation involved the task of reorganizing Python code from a given script into a `globals.py` file, ensuring only necessary imports and variables remained. It covered steps for creating projects, managing project settings, and handling project-related tasks using functions like `create_project`, `find_project_*`, and `update_engine`. The discussion emphasized best practices in coding, such as providing clear file paths in code blocks and maintaining the integrity of file names without trimming.", "created_at": "2025-07-13 11:08:48.364361", "updated_at": "2025-07-13T11:30:15.278437", "mode": "chat", "kanban_id": "", "column_id": "", "board": "Events", "column": "In Progress", "chat_index": 0, "url": "", "branch": "", "file_path": "/shared/codx-junior/api/.codx/tasks/Events/In Progress/add-event-manager-to-engine.ea9e3cf1-150b-43bc-9303-87cb3ea69ec0.md", "model": "", "visibility": "", "remote_url": "", "knowledge_topics": []}]]
## [[{"doc_id": "e94da6fe-dba6-4427-9e97-f024ed5ff380", "role": "user", "task_item": "", "think": "", "hide": true, "improvement": false, "created_at": "2025-07-13 11:10:57.832185", "updated_at": "2025-07-13 11:10:57.832215", "images": [], "files": ["/shared/codx-junior/api/codx/junior/engine.py", "/shared/codx-junior/api/codx/junior/engine.py", "/shared/codx-junior/api/codx/junior/events/event_manager.py"], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true}]]
@file://event_manager.py Add missing imports in EventManager. Extract missing imports from egine file @file://engine.py
## [[{"doc_id": "56f0a0fb-6f6b-4bd9-a73f-f822a97c0b68", "role": "assistant", "task_item": "", "think": null, "hide": true, "improvement": false, "created_at": "2025-07-13 11:10:57.832185", "updated_at": "2025-07-13 11:10:57.832215", "images": [], "files": [], "meta_data": {"time_taken": 12.457412004470825, "first_chunk_time_taken": 0.00028204917907714844, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false}]]
Certainly! Based on the provided context from the `engine.py` file, here are the missing imports for `event_manager.py`. I'll include the necessary imports and update the file accordingly.

```python /shared/codx-junior/api/codx/junior/events/event_manager.py
from codx.junior.sio.session_channel import SessionChannel
from codx.junior.db import Chat, Message
```

These imports are based on the usage of `SessionChannel`, `Chat`, and `Message` classes in the EventManager.
## [[{"doc_id": "b7ef9738-9cba-414e-b22f-b54864eb0bfe", "role": "user", "task_item": "", "think": "", "hide": true, "improvement": false, "created_at": "2025-07-13 11:17:43.667291", "updated_at": "2025-07-13T11:18:14.051Z", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true}]]
Change CODXJuniorSession channel by a event_manger instance.


Remove these methods from CODXJuniorSession and replace all calls to these methods using self.event_manger like:
`self.chat_event(...` will be `self.event_manager.chat_event(...`


List of methods to replace:
```python
    def event_data(self, data: dict):
        data['codx_path'] = self.settings.codx_path
        return data


    def send_notification(self, **kwargs):
        if not kwargs.get("type"):
            kwargs["type"] = "notification"
        self.get_channel().send_event('codx-junior', self.event_data(kwargs))


    def send_event(self, message: str):
        self.get_channel().send_event('codx-junior', self.event_data({ 'text': message, "type": "event" }))
        # self.log_info(f"Sending event {message}- SENT!")
    def send_knowled_event(self, **kwargs):
        self.get_channel().send_event('knowledge-event', self.event_data(kwargs))


    def chat_event(self, chat: Chat, message: str = None, event_type: str = None):
        self.get_channel().send_event('chat-event', self.event_data({ 'chat': { 'id': chat.id }, 'text': message, 'type': event_type }))
        # self.log_info(f"SEND MESSAGE {message}- SENT!")


    def message_event(self, chat: Chat, message: Message):
        self.get_channel().send_event('message-event', self.event_data({ 'chat': { 'id': chat.id }, 'message': message.model_dump() }))
        # self.log_info(f"SEND MESSAGE {message.role} {message.doc_id}- SENT!")
```
## [[{"doc_id": "164764b5-205c-4f52-aa25-0eaf5a33a924", "role": "assistant", "task_item": "", "think": null, "hide": true, "improvement": false, "created_at": "2025-07-13 11:17:43.667291", "updated_at": "2025-07-13 11:17:43.667395", "images": [], "files": [], "meta_data": {"time_taken": 159.80600953102112, "first_chunk_time_taken": 0.0002655982971191406, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false}]]
")
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
              self.event_manager.chat_event(chat=chat, message=f"Agent iteration {iteration + 1}")
              return self.chat_with_project(chat=chat,
                    disable_knowledge=disable_knowledge,
                    callback=callback,
                    append_references=append_references,
                    chat_mode=chat_mode,
                    iteration=iteration + 1)
            else:    
              self.event_manager.chat_event(chat=chat, message="done")
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

```

## [[{"doc_id": "744e3518-219d-454a-b639-e0eecf396e4c", "role": "user", "task_item": "", "think": "", "hide": false, "improvement": false, "created_at": "2025-07-13 11:29:00.338906", "updated_at": "2025-07-13 11:29:00.338938", "images": [], "files": [], "meta_data": {}, "profiles": [], "user": "admin", "knowledge_topics": [], "done": true, "is_thinking": false, "disable_knowledge": true}]]
Create a globals.py file from this piece of code remove all unedded imports and variables:


```python

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


import anyio


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


from codx.junior.mentions.mention_manager import MentionManager
from codx.junior.events.event_manager import EventManager


from codx.junior.db import (
    Kanban,
    Chat,
    Message,
    MessageTaskItem
)


from codx.junior.sio.session_channel import SessionChannel
from codx.junior.security.user_management import UserSecurityManager




"""Changed files older than MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS won't be processed"""
MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS = 60 * 60


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


    repo_url = None 
    if project_path.startswith("http"):
        repo_url = project_path
        repo_name = repo_url.split("/")[-1].split(".")[0]
        project_path = f"{projects_root_path}/{repo_name}"
        command = f"git clone --depth=1 {repo_url} {project_path}"
        logger.info(f"Cloning repo {repo_url} {repo_name} {project_path}")
        exec_command(command=command)
    
    existing_project = find_project_by_project_path(project_path=project_path)
    if existing_project:
        logger.info(f"Project already esists {repo_url} {repo_name} {project_path}")
        return existing_project


    settings = CODXJuniorSettings()
    settings.project_name = project_path.split("/")[-1]
    settings.codx_path = f"{project_path}/.codx"
    settings.watching = True
    settings.repo_url = repo_url
    settings.save_project()
    _, stderr = exec_command("git branch")
    if stderr:
        exec_command("git init", cwd=project_path)
    new_project = CODXJuniorSettings.from_project_file(f"{project_path}/.codx/project.json")
    if user:
      UserSecurityManager().add_user_to_project(project_id=new_project.project_id, user=user, permissions='admin')
    return new_project


def coder_open_file(settings: CODXJuniorSettings,  file_name: str):
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


def find_all_user_projects(user: CodxUser, with_metrics:bool = False):
    user_security_manager = UserSecurityManager()
    for settings in find_all_projects(with_metrics=with_metrics).values():
        permissions = user_security_manager.get_user_project_access(user=user, settings=settings)
        if permissions:
            yield {
                **settings.__dict__,
                "permissions": permissions
            }


def find_all_projects(with_metrics: bool = False):
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
                project.__dict__["_metrics"] = CODXJuniorSession(settings=project).get_project_metrics()
            except Exception as ex:
                project.__dict__["_error"] = str(ex)
        return all_projects
    return update_projects_with_details() if with_metrics else all_projects


def update_engine():
    try:
        command = ["git", "pull"]
        subprocess.run(command)
    except Exception as ex:
        logger.exception(ex)
        return ex


```
## [[{"doc_id": "e8bafa7a-7691-44d1-aa52-c891f9431838", "role": "assistant", "task_item": "", "think": null, "hide": false, "improvement": false, "created_at": "2025-07-13 11:29:43.241473", "updated_at": "2025-07-13 11:29:43.241500", "images": [], "files": [], "meta_data": {"time_taken": 21.154210567474365, "first_chunk_time_taken": 0.00014591217041015625, "model": "gpt-4o"}, "profiles": [], "user": null, "knowledge_topics": [], "done": true, "is_thinking": null, "disable_knowledge": false}]]
```python /shared/codx-junior/api/codx/junior/globals.py
import os
import subprocess
import logging

from codx.junior.settings import read_global_settings
from codx.junior.utils import exec_command
from codx.junior.security.user_management import UserSecurityManager
from codx.junior.model.model import CodxUser
from codx.junior.db import Chat

"""Changed files older than MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS won't be processed"""
MAX_OUTDATED_TIME_TO_PROCESS_FILE_CHANGE_IN_SECS = 60 * 60

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

    repo_url = None 
    if project_path.startswith("http"):
        repo_url = project_path
        repo_name = repo_url.split("/")[-1].split(".")[0]
        project_path = f"{projects_root_path}/{repo_name}"
        command = f"git clone --depth=1 {repo_url} {project_path}"
        logger.info(f"Cloning repo {repo_url} {repo_name} {project_path}")
        exec_command(command=command)
    
    existing_project = find_project_by_project_path(project_path=project_path)
    if existing_project:
        logger.info(f"Project already exists {repo_url} {repo_name} {project_path}")
        return existing_project

    settings = CODXJuniorSettings()
    settings.project_name = project_path.split("/")[-1]
    settings.codx_path = f"{project_path}/.codx"
    settings.watching = True
    settings.repo_url = repo_url
    settings.save_project()
    _, stderr = exec_command("git branch")
    if stderr:
        exec_command("git init", cwd=project_path)
    new_project = CODXJuniorSettings.from_project_file(f"{project_path}/.codx/project.json")
    if user:
        UserSecurityManager().add_user_to_project(project_id=new_project.project_id, user=user, permissions='admin')
    return new_project


def coder_open_file(settings: CODXJuniorSettings, file_name: str):
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

def find_all_user_projects(user: CodxUser, with_metrics: bool = False):
    user_security_manager = UserSecurityManager()
    for settings in find_all_projects(with_metrics=with_metrics).values():
        permissions = user_security_manager.get_user_project_access(user=user, settings=settings)
        if permissions:
            yield {
                **settings.__dict__,
                "permissions": permissions
            }

def find_all_projects(with_metrics: bool = False):
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
                project.__dict__["_metrics"] = CODXJuniorSession(settings=project).get_project_metrics()
            except Exception as ex:
                project.__dict__["_error"] = str(ex)
        return all_projects
    return update_projects_with_details() if with_metrics else all_projects

def update_engine():
    try:
        command = ["git", "pull"]
        subprocess.run(command)
    except Exception as ex:
        logger.exception(ex)
        return ex
```
