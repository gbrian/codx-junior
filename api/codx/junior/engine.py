import os
import logging
import re
import json
import time
import subprocess
import shutil
import asyncio
from pathlib import Path
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

from codx.junior.profiling.profiler import profile_function

from codx.junior.ai import AI
from codx.junior.settings import (
    CODXJuniorSettings,
    read_global_settings
)

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
    GlobalSettings,
    Profile,
    AI_TASKS_RESPONSE_PARSER
)
from codx.junior.context import (
    find_relevant_documents,
    AI_CODE_VALIDATE_RESPONSE_PARSER,
    generate_markdown_tree,
    AI_CODE_GENERATOR_PARSER,
    AICodeGerator
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

from codx.junior.context import AICodePatch

from codx.junior.sio.session_channel import SessionChannel

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

def create_project(project_path: str):
    logger.info(f"Create new project {project_path}")
    projects_root_path = f"{os.environ['HOME']}/projects"
    os.makedirs(projects_root_path, exist_ok=True)
        
    if project_path.startswith("http"):
        url = project_path
        repo_name = url.split("/")[-1].split(".")[0]
        project_path = f"{projects_root_path}/{repo_name}"
        command = f"git clone --depth=1 {url} {project_path}"
        logger.info(f"Cloning repo {url} {repo_name} {project_path}")
        exec_command(command=command)
        open_readme = True
    
    settings = CODXJuniorSettings()
    settings.project_name = project_path.split("/")[-1]
    settings.codx_path = f"{project_path}/.codx"
    settings.watching = True
    settings.save_project()
    exec_command("git init", cwd=project_path)
    return CODXJuniorSettings.from_project_file(f"{project_path}/.codx/project.json")

def coder_open_file(settings: CODXJuniorSettings,  file_name: str):
    if not file_name.startswith(settings.project_path):
        file_name = f"{settings.project_path}{file_name}"
    logger.info(f"coder_open_file {file_name}")
    os.system(f"code-server -r {file_name}")


def find_project_from_file_path(file_path: str):
    """Given a file path, find the project parent"""
    all_projects = find_all_projects()
    matches = [p for p in all_projects if file_path.startswith(p.project_path)]
    if matches:
        return sorted(matches, key=lambda p: len(p.project_path))[-1]
    return None

def find_all_projects():
    all_projects = []
    project_path = "/"
    result = subprocess.run("find / -name .codx".split(" "), cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    all_codx_path = result.stdout.decode('utf-8').split("\n")
    paths = [p for p in all_codx_path if os.path.isfile(f"{p}/project.json")]
    #logger.info(f"[find_all_projects] paths: {paths}")
    for codx_path in paths:
        try:
            project_file_path = f"{codx_path}/project.json"
            settings = CODXJuniorSettings.from_project_file(project_file_path)
            all_projects.append(settings)
        except Exception as ex:
            logger.exception(f"Error loading project {str(codx_path)}")
    
    def update_projects_with_details():
        for project in all_projects:
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

    def log_info(self, msg):
        logger.info(f"[{self.settings.project_name}] {msg}")

    def get_channel(self):
        return self.channel

    async def send_event(self, message: str):
        await self.get_channel().send_event('codx-junior', { 'text': message })
        self.log_info(f"SEND MESSAGE {message}- SENT!")

    async def chat_event(self, chat: Chat, message: str):
        await self.get_channel().send_event('chat-event', { 'id': chat.id, 'text': message })
        self.log_info(f"SEND MESSAGE {message}- SENT!")

    def delete_project(self):
        shutil.rmtree(self.settings.codx_path)
        logger.error(f"PROJECT REMOVED {self.settings.codx_path}")

    def get_chat_manager(self):
        return ChatManager(settings=self.settings)

    def get_profile_manager(self):
        return ProfileManager(settings=self.settings)

    def get_ai(self):
        return AI(settings=self.settings)

    def get_knowledge(self):
        return Knowledge(settings=self.settings)

    def get_browser(self):
        from codx.junior.browser.browser import Browser
        return Browser(session=self)

    @profile_function
    def load_chat(self, board, chat_name):
        return self.get_chat_manager().load_chat(board=board, chat_name=chat_name)
    
    def list_chats(self):
        return self.get_chat_manager().list_chats()

    def save_chat(self, chat, chat_only=False):
        return self.get_chat_manager().save_chat(chat, chat_only)

    def delete_chat(self, file_path):
        self.get_chat_manager().delete_chat(file_path)

    @profile_function
    def list_profiles(self):
        return self.get_profile_manager().list_profiles()

    async def save_profile(self, profile):
        profile = self.get_profile_manager().save_profile(profile=profile)
        await self.check_file_for_mentions(file_path=profile.path)
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

    @profile_function
    async def knowledge_search(self, knowledge_search: KnowledgeSearch):
        self.settings.knowledge_search_type = knowledge_search.document_search_type
        self.settings.knowledge_search_document_count = knowledge_search.document_count
        self.settings.knowledge_context_cutoff_relevance_score = knowledge_search.document_cutoff_score
        
        documents = []
        response = ""
        if knowledge_search.search_type == "embeddings":
            documents, file_list = find_relevant_documents(query=knowledge_search.search_term,
                                                    settings=self.settings, 
                                                    ignore_documents=[],
                                                    ai_validate=False)
            
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
            chat, _ = await self.chat_with_project(chat=chat, use_knowledge=False)
            response = chat.messages[-1].content
        elif knowledge_search.search_type == "source":
            documents = Knowledge(settings=self.settings).search_in_source(knowledge_search.search_term)
        
        return {
            "response": response,
            "documents": documents,
            "settings": {
                "knowledge_search_type": self.settings.knowledge_search_type,
                "knowledge_search_document_count": self.settings.knowledge_search_document_count,
                "knowledge_context_cutoff_relevance_score": self.settings.knowledge_context_cutoff_relevance_score
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

    @profile_function
    def select_afefcted_documents_from_knowledge(self, ai: AI, query: str, ignore_documents=[]):
        all_projects = find_all_projects()
        
        mentions = re.findall(r'@[a-zA-Z0-9\-\_\.]+', query)
        self.log_info(f"Extracted mentions: {mentions}")
        
        settings_sub_projects = self.settings.get_sub_projects() if self.settings.knowledge_query_subprojects else []
        settings_sub_projects = [p.project_name for p in settings_sub_projects]
        project_dependencies = self.settings.get_project_dependencies()
        sub_projects = set(settings_sub_projects + [mention[1:] for mention in mentions] + project_dependencies)
        search_projects = [settings for settings in all_projects if settings.project_name in sub_projects]
        self.log_info(f"select_afefcted_documents_from_knowledge query subprojects {sub_projects} - {search_projects}")
        
        for search_project in search_projects:
            mention = [mention[1:] for mention in mentions if mention == search_project.project_name]
            query = query.replace(f"@{mention}", "")

        @profile_function
        def process_rag_query(rag_query):
            docs, file_list = find_relevant_documents(query=rag_query, settings=self.settings, ignore_documents=ignore_documents)
            if not docs:
                docs = []
                file_list = []
            self.log_info(f"select_afefcted_documents_from_knowledge doc length: {len(docs)} - cutoff score {self.settings.knowledge_context_cutoff_relevance_score}")
            if search_projects and self.settings.knowledge_query_subprojects:
                self.log_info(f"select_afefcted_documents_from_knowledge search subprojects: {rag_query} in {[p.project_name for p in search_projects]}")
                for sub_settings in search_projects:
                    sub_docs, sub_file_list = find_relevant_documents(query=rag_query, settings=sub_settings, ignore_documents=ignore_documents)
                    self.log_info(f"select_afefcted_documents_from_knowledge search subproject {sub_settings.project_name} docs: {len(sub_docs)}") 
                    if sub_docs:
                        docs = docs + sub_docs
                    if sub_file_list:
                        file_list = file_list + sub_file_list
            return docs, file_list
        return process_rag_query(rag_query=query)

    def select_afected_files_from_knowledge(self, ai: AI, query: str):
        relevant_documents, file_list = self.select_afefcted_documents_from_knowledge(ai=ai, query=query)
        file_list = [str(Path(doc.metadata["source"]).absolute())
                      for doc in relevant_documents]
        file_list = list(dict.fromkeys(file_list))  # Remove duplicates

        return file_list

    async def improve_existing_code_patch(self, code_generator: AICodeGerator):
        changes = code_generator.code_changes
        file_path = changes[0].file_path
        
        patch = code_generator.code_patches[0]
        ts = datetime.now().strftime('%H%M%S')
        patch_file = f"/tmp/{ts}.patch"
        with open(patch_file, 'w') as f:
            f.write(patch.patch)
        git_patch = f"git apply {patch_file}"
        stdout, stderr = exec_command(git_patch, cwd=self.settings.project_path)
        os.remove(patch_file)
        res = f"{stdout} {stderr}".lower()
        error = True if len(stderr or "") != 0 or "error" in res else False
        if error:
            await self.apply_improve_code_changes(code_generator=code_generator)
            stdout = "Changes applied"
            stderr = ""
        coder_open_file(self.settings, file_name=file_path)
        return stdout, stderr


    @profile_function
    async def improve_existing_code(self, chat: Chat, apply_changes: bool=None):
        await self.send_event(message=f"Code-gen: Prepring changes")

        knowledge = Knowledge(settings=self.settings)
        profile_manager = ProfileManager(settings=self.settings)
        if apply_changes is None:
            apply_changes = True if chat.mode == 'task' else False

        code_changes_request = [message for message in chat.messages if not message.hide][0]
        
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

        CHANGES:
        ```markdown
        { code_changes_request.content }
        ```

        Create a list of find&replace instructions for each change needed:
        INSTRUCTIONS:
          {AI_CODE_GENERATOR_PARSER.get_format_instructions()}
          
          * For new files create an absolute paths
          * Keep content indentation; It is crucial to find the content to replace and to make new content work
        """
        code_generator = None
        if not chat.messages[-1].hide and not chat.messages[-1].improvement:
            retry_count = 1
            request_msg = Message(role="user", content=request)
            chat.messages.append(request_msg)
            self.log_info(f"improve_existing_code prompt: {request_msg}")
            async def try_chat_code_changes(attempt: int, error: str=None) -> AICodeGerator:
                if error:
                    chat.messages.append(Message(role="user", content=f"There was an error last time:\n {error}"))
                await self.chat_with_project(chat=chat, use_knowledge=True, chat_mode='chat')
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
        else:
            code_generator = self.get_ai_code_generator_changes(response=chat.messages[-1].content)

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
            await self.send_event(message=f"Code-gen: change {change_type} - {file_path}")
            
            if change_type == "delete_file":
                del open_files[file_path]
                os.remove(file_path)
            else:
                content = ""
                if os.path.isfile(file_path):
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                instruction_list = [json.dumps(change.__dict__) for change in changes]
                self.log_info(f"Applying {len(changes)} changes to {file_path}")
                new_content = await self.change_file_with_instructions(instruction_list=instruction_list, file_path=file_path, content=content)
                if new_content and new_content != content:
                    await self.write_project_file(file_path=file_path, content=new_content)
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
        await self.chat_with_project(chat=chat, use_knowledge=False, append_references=False)
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
        new_files = knowledge.detect_changes()
        if not new_files:
            self.log_info(f"check_project_changes {self.settings.project_name} no changes")
            return False
        return True

    async def process_project_changes(self):
        if not self.settings.is_valid_project():
            return
        knowledge = Knowledge(settings=self.settings)
        knowledge.clean_deleted_documents()
        new_files, _ = knowledge.detect_changes()
        if not new_files:
            return    
            
        await self.send_event(message=f"{self.settings.project_name} changed")

        file_path = new_files[0] # one at a time
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
            chat = await self.chat_with_project(chat=chat, use_knowledge=False)
            response = chat.messages[-1].content.strip()
            parsed_response = AI_CODE_VALIDATE_RESPONSE_PARSER.invoke(response)
            return parsed_response.new_content
        except Exception as ex:
            chat.messages.append(Message(role="error", content=str(ex)))
            raise ex
        finally:
            if save_changes:
                self.save_chat(chat=chat)

    @profile_function
    async def check_file_for_mentions(self, file_path: str, content: str = None, silent: bool = False):
        profile_manager = ProfileManager(settings=self.settings)
        chat_manager = ChatManager(settings=self.settings)
        ai = AI(settings=self.settings)
        mentions = None
        file_profiles = self.get_profile_manager().get_file_profiles(file_path=file_path)
        
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

        await self.send_event(message=f"Processing {file_path.split('/')[-1]}...")
            
        self.log_info(f"{len(mentions)} mentions found for {file_path}")
        new_content = notify_mentions_in_progress(content)
        if not silent:
            write_file(file_path=file_path, content=new_content)

        image_mentions = [m for m in mentions if m.flags.image]
        if image_mentions:
            new_content = self.process_image_mention(image_mentions, file_path, content)
            return await self.check_file_for_mentions(file_path=file_path, content=new_content, silent=True)

        org_content = strip_mentions(content=content, mentions=mentions)

        use_knowledge = True
        
        using_chat = any(m.flags.chat_id for m in mentions)
        skip_knowledge_search = not any(m.flags.knowledge for m in mentions)
        
        run_code = any(m.flags.code for m in mentions)

        if using_chat or skip_knowledge_search:
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

        chat = Chat(name=f"changes_at_{file_path}", messages=
            [
                Message(role="user", content=f"""
                {profile_manager.read_profile("software_developer").content}
                Find all information needed to apply all changes to file: {file_path}
                Changes:
                {query}

                File content:
                {new_content}
                """)
            ])
            
        await self.chat_with_project(chat=chat, use_knowledge=use_knowledge)
        if run_code:
            await self.improve_existing_code(chat=chat, apply_changes=True)
        else:
            if file_profiles:
                file_profile_content = "\n".join([
                    profile.content for profile in file_profiles
                ])
                
                chat.messages.append(Message(role="user", content=f"""Best practices for this file:
                {file_profile_content}
                """))

            chat.messages.append(Message(role="user", content=f"""
            Rewrite full file content replacing codx instructions by required changes.
            Return only the file content without any further decoration or comments.
            Do not surround response with '```' marks, just content:
            {new_content}
            """))
            
            await self.chat_with_project(chat=chat, use_knowledge=False, append_references=False)
            response = chat.messages[-1].content
            await self.write_project_file(file_path=file_path, content=response)

        return "done"

    def process_image_mention(self, image_mentions, file_path: str, content: str):
        ai = self.get_ai()
        for image_mention in image_mentions:
            image_mention.new_content = ai.image(image_mention.content)
        return replace_mentions(content, image_mentions)

    @profile_function
    def generate_tasks(self, chat: Chat):
        ai = self.get_ai()
        last_message = chat.messages[-1]

        prompt = f"""
        Generate subtasks from this epic:
        {last_message.content}

        INSTRUCTIONS:
        Each task must have a clear name and an intial descriptive message with instructions on what has to be done.
        In the intial message all references needed from the epic like files, keywords, ...
        {AI_TASKS_RESPONSE_PARSER.get_format_instructions()}
        """

        messages = ai.chat(prompt=prompt)
        response = messages[-1].content

        ai_tasks = AI_TASKS_RESPONSE_PARSER.invoke(response)
        chat_manager = self.get_chat_manager()
        for sub_task in ai_tasks.tasks:
            sub_task.parent_id = chat.id
            chat_manager.save_chat(sub_task)
    
    @profile_function
    async def chat_with_project(self, chat: Chat, use_knowledge: bool=True, callback=None, append_references: bool=True, chat_mode: str=None):
        chat_mode = chat_mode or chat.mode or 'chat'
        if chat_mode == 'browser':
            self.log_info(f"chat_with_project browser mode")
            await self.chat_event(chat=chat, message=f"connecting with browser...")
            return self.get_browser().chat_with_browser(chat)

        await self.chat_event(chat=chat, message=f"Process chat")
        
        is_refine = chat_mode == 'task'
        ai_messages = [m for m in chat.messages if not m.hide and not m.improvement and m.role == "assistant"]
        last_ai_message = ai_messages[-1] if ai_messages else None
            
        user_message = chat.messages[-1]
        query = user_message.content

        ai = AI(settings=self.settings)
        profile_manager = ProfileManager(settings=self.settings)
        chat_profiles_content = ""
        if chat.profiles:
            chat_profiles = [profile_manager.read_profile(profile) for profile in chat.profiles]
            chat_profiles_content = "\n".join([profile.content for profile in chat_profiles if profile])

        instructions = f"""BEGIN INSTRUCTIONS
        This is a conversation between you and the user about the project {self.settings.project_name}.
        {chat_profiles_content}
        END INSTRUCTIONS
        """
        messages = [
            SystemMessage(content=instructions)
        ]

        def convert_message(m):
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

                self.log_info(f"ImageMessage content: {content}")
                msg = BaseMessage(type="image", content=json.dumps(content))
            elif m.role == "user":
                msg = HumanMessage(content=m.content)
            else:
                msg = AIMessage(content=m.content)
      
            return msg

        for m in chat.messages[0:-1]:
            if m.hide or m.improvement:
                continue
            msg = convert_message(m)
            messages.append(msg)

        context = ""
        documents = []
        coding_profiles = []
        chat_files = chat.file_list or []
        ignore_documents = chat_files.copy()
        if chat.name:
            ignore_documents.append(f"/{chat.name}")

        await self.chat_event(chat=chat, message=f"Knowledge search")
        
        if use_knowledge:
            affected_documents, doc_file_list = self.select_afefcted_documents_from_knowledge(ai=ai, query=query, ignore_documents=ignore_documents)

            if chat_files:
                knowledge = Knowledge(settings=self.settings)
                chat_documents = [knowledge.doc_from_project_file(file_path) for file_path in chat_files]
                
                for doc in documents:
                    doc_context = document_to_context(doc)
                    context += f"{doc_context}\n"

            if affected_documents:
                documents = affected_documents
                file_list = doc_file_list
                for doc in documents:
                    doc_context = document_to_context(doc)
                    context += f"{doc_context}\n"

            doc_length = len(documents or [])
            self.log_info(f"chat_with_project found {doc_length} relevant documents")

        if context:
            messages.append(convert_message(
                Message(role="user", content=f"""
                  THIS INFORMATION IS COMING FROM PROJECT'S FILES.
                  HOPE IT HELPS TO ANSWER USER REQUEST.
                  KEEP FILE SOURCE WHEN WRITING CODE BLOCKS (EXISTING OR NEWS).
                  {context}
                  """)))

        if is_refine and last_ai_message:
            refine_message = Message(role="user", content=f"""
            UPDATE THIS DOCUMENT
            ```
            {last_ai_message.content}
            ```

            WITH USER COMMENTS:
            {user_message.content}
            """)
            messages.append(convert_message(refine_message))
        else:
            messages.append(convert_message(user_message))
        
        await self.chat_event(chat=chat, message=f"Invoking AI: {self.settings.ai_provider}")

        messages = ai.chat(messages, callback=callback)
        response = messages[-1].content
        sources = []
        if documents:
            sources = list(set([doc.metadata['source'].replace(self.settings.project_path, "") for doc in documents]))
            
        response_message = Message(role="assistant", content=response, files=sources)
        chat.messages.append(response_message)
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
        wiki_file = f"{project_wiki_path}{file_path}"
        try:
          with open(wiki_file, 'r', encoding='utf-8', errors='ignore') as f:
              return f.read()
        except:
          return f"{wiki_file} not found"

    def get_readme(self):
        project_path = self.settings.project_path
        readme_file = f"{project_path}/README.md"
        if os.path.isfile(readme_file):
          with open(readme_file, 'r', encoding='utf-8', errors='ignore') as f:
              return f.read()
        return ""

    async def update_wiki(self, file_path: str):
        return
        project_wiki_path = self.settings.get_project_wiki_path()
        if not self.settings.project_wiki or file_path.startswith(project_wiki_path):
            return

        project_wiki_home = f"{project_wiki_path}/home.md"

        home_content = f"# {self.settings.project_name}"
        if os.path.isfile(project_wiki_home):
            with open(project_wiki_home, 'r', encoding='utf-8', errors='ignore') as f:
                home_content = f.read()

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            file_content = f.read()
            self.log_info(f"update_wiki file_path: {file_path}, project_wiki: {project_wiki_path}")
            chat = Chat(messages=[
                Message(role="user", content=f"""Extract important parts from the content of {file_path} to be added to the wiki.
                {file_content}
                """)
            ])
            await self.chat_with_project(chat=chat, use_knowledge=True)
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
        await self.chat_with_project(chat=chat, use_knowledge=False)
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
        return stdout.split("\n")

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
            parent_branch = self.get_project_parent_branch()
            self.log_info(f"get_project_changes parent_branch {parent_branch}")
        stdout, _ = exec_command(f"git diff {parent_branch}...",
                      cwd=self.settings.project_path)
        return stdout

    def build_code_changes_summary(self, force = False):
        exec_command("git add .", cwd=self.settings.project_path)
        diff = self.get_project_changes()
        return self.get_knowledge().build_code_changes_summary(diff=diff, force=force)
    
