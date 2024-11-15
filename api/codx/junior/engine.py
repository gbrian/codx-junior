import os
import logging
import re
import json
import time
import subprocess
import shutil
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
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
    Profile
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

def create_project(project_path: str):
    logger.info(f"Create new project {project_path}")
    open_readme = False
    if project_path.startswith("http"):
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

def coder_open_file(settings: CODXJuniorSettings,  file_name: str):
    if not file_name.startswith(settings.project_path):
        file_name = f"{settings.project_path}{file_name}"
    logger.info(f"coder_open_file {file_name}")
    os.system(f"code-server -r {file_name}")

def find_all_projects(detailed: bool=False):
    all_projects = []
    project_path = "/"
    result = subprocess.run("find / -name .codx".split(" "), cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    all_codx_path = result.stdout.decode('utf-8').split("\n")
    paths = [p for p in all_codx_path if os.path.isfile(f"{p}/project.json")]
    for project_path in paths:
        try:
            settings = CODXJuniorSettings.from_project(str(project_path))
            if settings.codx_path not in all_projects \
                  and project_path == settings.codx_path:
                all_projects.append(settings)
        except Exception as ex:
            logger.exception(f"Error loading project {str(project_path)}")
    def projects_with_details():
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

    return projects_with_details() if detailed else all_projects

def update_engine():
    try:
        command = ["git", "pull"]
        subprocess.run(command)
    except Exception as ex:
        logger.exception(ex)
        return ex
                

async def send_io_message(sio, sid, event, data):
    logger.info("SENDING MESSAGE BY SIO!")
    await sio.emit(event, data)
    logger.info("MESSAGE SENT BY SIO!")

class SessionChannel:
    def __init__(self, sid=None, sio=None):
        self.sid = sid
        self.sio = sio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    def send_event(self, event, data):
        return # Disabled, not working
        args = (self.sio, self.sid, event, data)
        # Thread(target=send_io_message, args=args).start()
        asyncio.get_event_loop().create_task(
          send_io_message(self.sio, self.sid, event, data)
        )

    def chat_event(self, message: str):
        self.send_event('chat-event', { 'text': message })
        logger.info(f"SEND MESSAGE {message}- SENT!")


class CODXJuniorSession:
    def __init__(self,
        settings: CODXJuniorSettings = None,
        codx_path: str = None,
        app=None,
        channel: SessionChannel = SessionChannel()):
        self.app = app
        self.settings = settings or CODXJuniorSettings.from_project(codx_path)
        self.channel = channel

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
        from codx.junior.browser import Browser
        return Browser(session=self)

    def load_chat(self, board, chat_name):
        return self.get_chat_manager().load_chat(board=board, chat_name=chat_name)
    
    def list_chats(self):
        return self.get_chat_manager().list_chats()

    def save_chat(self, chat):
        self.channel.chat_event(f'Saving {chat.name}')
        return self.get_chat_manager().save_chat(chat)

    def delete_chat(self, board, chat_name):
        self.get_chat_manager().delete_chat(board, chat_name)


    def list_profiles(self):
        return self.get_profile_manager().list_profiles()

    def save_profile(self, profile):
        return self.get_profile_manager().save_profile(profile=profile)

    def read_profile(self, profile_name):
        return self.get_profile_manager().read_profile(profile_name)

    def delete_profile(self, profile_name):
        return self.get_profile_manager().delete_profile(profile_name)

    def reload_knowledge(self, path: str = None):
        knowledge = self.get_knowledge()
        logger.info(f"***** reload_knowledge: {path}")
        documents = None
        if path:
            documents = knowledge.reload_path(path)
            logger.info(f"reload_knowledge: {path} - Docs: {len(documents)}")
        else:
            documents = knowledge.reload()
        return {"doc_count": len(documents) if documents else 0}

    def knowledge_search(self, knowledge_search: KnowledgeSearch):
        self.settings.knowledge_search_type = knowledge_search.document_search_type
        self.settings.knowledge_search_document_count = knowledge_search.document_count
        self.settings.knowledge_context_cutoff_relevance_score = knowledge_search.document_cutoff_score
        
        documents = []
        response = ""
        if knowledge_search.search_type == "embeddings":
            chat = Chat(messages=[
                Message(
                    role="user",
                    content=f"Please give me really short answer about: {knowledge_search.search_term}"
                )
            ])
            chat, chat_docs = self.chat_with_project(chat=chat, use_knowledge=True)
            documents = chat_docs
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
        return {"ok": 1}

    def delete_knowledge(self):
        Knowledge(settings=self.settings).reset()
        return {"ok": 1}

    def select_afefcted_documents_from_knowledge(self, ai: AI, query: str, ignore_documents=[]):
        all_projects = find_all_projects()
        
        mentions = re.findall(r'@\S+', query)
        logger.info(f"Extracted mentions: {mentions}")
        
        settings_sub_projects = self.settings.get_sub_projects() if self.settings.knowledge_query_subprojects else []
        settings_sub_projects = [p.project_name for p in settings_sub_projects]
        project_dependencies = self.settings.get_project_dependencies()
        sub_projects = set(settings_sub_projects + [mention[1:] for mention in mentions] + project_dependencies)
        search_projects = [settings for settings in all_projects if settings.project_name in sub_projects]
        logger.info(f"select_afefcted_documents_from_knowledge query subprojects {sub_projects} - {search_projects}")
        
        for search_project in search_projects:
            mention = [mention[1:] for mention in mentions if mention == search_project.project_name]
            query = query.replace(f"@{mention}", "")

        def process_rag_query(rag_query):
            docs, file_list = find_relevant_documents(query=rag_query, settings=self.settings, ignore_documents=ignore_documents)
            if not docs:
                docs = []
                file_list = []
            logger.info(f"select_afefcted_documents_from_knowledge doc length: {len(docs)} - cutoff score {self.settings.knowledge_context_cutoff_relevance_score}")
            if search_projects and self.settings.knowledge_query_subprojects:
                logger.info(f"select_afefcted_documents_from_knowledge search subprojects: {rag_query} in {[p.project_name for p in search_projects]}")
                for sub_settings in search_projects:
                    sub_docs, sub_file_list = find_relevant_documents(query=rag_query, settings=sub_settings, ignore_documents=ignore_documents)
                    logger.info(f"select_afefcted_documents_from_knowledge search subproject {sub_settings.project_name} docs: {len(sub_docs)}") 
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

    def improve_existing_code(self, chat: Chat, apply_changes: bool=None):
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
          * Keep content indentation; It is crucial to find the content to replace and to make new content work
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
                self.chat_with_project(chat=chat, use_knowledge=False, chat_mode='chat')
                chat.messages = [msg for msg in chat.messages if msg != request_msg]
                chat.messages[-1].improvement = True
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
                        return try_chat_code_changes(attempt, error=str(ex))
                    raise ex
            code_generator = try_chat_code_changes(retry_count)
            if not apply_changes:
                return code_generator
        else:
            code_generator = self.get_ai_code_generator_changes(response=chat.messages[-1].content)

        self.apply_improve_code_changes(code_generator=code_generator)
        return code_generator

    def get_ai_code_generator_changes(self, response: str):
        code_generator = AI_CODE_GENERATOR_PARSER.invoke(response)
        for change in code_generator.code_changes:
            file_path = change.file_path
            if not file_path.startswith(self.settings.project_path):
                change.file_path = os.path.join(self.settings.project_path, file_path)
        return code_generator

    def project_script_test(self):
        logger.info(f"project_script_test, test: {self.settings.script_test} - {self.settings.script_test_check_regex}")
        if not self.settings.script_test:
            return

        command = self.settings.script_test.split(" ")
        result = subprocess.run(command, cwd=self.settings.project_path,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True)
        console_out = result.stdout
        
        logger.info(f"project_script_test: {console_out} \nOUTPUT DONE")

        test_regex = self.settings.script_test_check_regex if self.settings.script_test_check_regex else 'error' 
        if re.search(test_regex, console_out):
            return console_out
        return ""

    def apply_improve_code_changes(self, code_generator: AICodeGerator):
        changes = code_generator.code_changes
        logger.info(f"improve_existing_code total changes: {len(changes)}")
        changes_by_file_path = {}
        for change in changes:
            file_path = change.file_path
            if file_path not in changes_by_file_path:
                changes_by_file_path[file_path] = []
            changes_by_file_path[file_path].append(change)
        
        for file_path, changes in changes_by_file_path.items():
            change_type = changes[0].change_type
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
                new_content = self.change_file_with_instructions(instruction_list=instruction_list, file_path=file_path, content=content)
                if new_content and new_content != content:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    write_file(file_path, new_content)
                else:
                    logger.error(f"Error applying changes to {file_path}. New content: {new_content}")

    def change_file_with_instructions(self, instruction_list: [str], file_path: str, content: str):
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
        self.chat_with_project(chat=chat, use_knowledge=False, append_references=False)
        return chat.messages[-1].content

    def improve_existing_code_gpt_blocks(self, chat: Chat):
        request = """Create a list of files to be modified with this structure:
          <GPT_CODE_CHANGE>
          FILE: file_path
          CHANGES: Explain which changes do we need to apply to this file
          </GPT_CODE_CHANGE>
          <GPT_CODE_CHANGE>
          FILE: file_path
          CHANGES: Explain which changes do we need to apply to this file
          </GPT_CODE_CHANGE>
          Repeat for as many files we have to change
        """
        if not chat.messages[-1].improvement:
            request_chat = Chat(messages=chat.messages + [Message(role="user", content=request)])
            request_chat = self.chat_with_project(chat=request_chat, use_knowledge=True)
            chat.messages.append(request_chat.messages[-1])
            chat.messages[-1].improvement = True
            return
        response = chat.messages[-1].content
        instructions = list(self.split_blocks_by_gt_lt(response))
        logger.info(f"improve_existing_code: {instructions}")
        if not instructions:
            logger.error(f"improve_existing_code ERROR no instructions at: {response} {chat.messages[-1]}")
        for instruction in instructions:
            file_path = instruction[0].split(":")[1].strip()
            changes = "\n".join(instruction[1:])
            logger.info(f"improve_existing_code instruction file: {file_path}")
            logger.info(f"improve_existing_code instruction changes: {changes}")
            chat.messages.append(Message(role="assistant", content="\n".join(instruction)))
            with open(file_path) as f:
                content = f.read()
            new_content = self.change_file(context_documents=[], query=changes, file_path=file_path, org_content=content)
            write_file(file_path, new_content)

    def check_knowledge_status(self):
        knowledge = Knowledge(settings=self.settings)
        last_update = knowledge.last_update
        status = knowledge.status()
        pending_files = knowledge.detect_changes()
        return {
            "last_update": str(last_update),
            "pending_files": pending_files[0:2000],
            "total_pending_changes": len(pending_files),
            **status
        }

    def check_project_changes(self):
        knowledge = Knowledge(settings=self.settings)
        knowledge.clean_deleted_documents()
        new_files = knowledge.detect_changes()
        if not new_files:
            return
        logger.info(f"check_file_for_mentions {new_files}")
        file_path = new_files[0]
        try:
            self.check_file_for_mentions(file_path=file_path)
        except:
            logger.exception(f"Error checking changes in file {file_path}")

        logger.info(f"Reload knowledge files {new_files}")
        self.reload_knowledge()

        for file_path in new_files:
            Thread(target=self.update_project_profile, args=(file_path,)).start()
            Thread(target=self.update_wiki, args=(file_path,)).start()

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

    def change_file_by_blocks(self, context_documents, query, file_path, org_content, save_changes=False, profile=None):
        profile_manager = ProfileManager(settings=self.settings)
        tasks = "\n *".join(
            context_documents + [
                query,
                'To ADD line(s) use: <GPT_ADD_LINE start_line="10"></GPT_ADD_LINE>',
                'To REMOVE line(s) use: <GPT_REMOVE_LINE start_line="10" end_line="11"></GPT_ADD_LINE> Lines from 10 to 11 will be deleted, both included',
                'To CHANGE line(s) use: <GPT_CHANGE_LINE start_line="10" end_line="11">New content</GPT_ADD_LINE> New content will replace lines 10 to 11',
                'Make sure indentation for new content is consistent'
            ]
        )
        request = f"""Given this CONTENT, generate line changes.
        ##CONTENT:
        {org_content}
        ##TASKS:
        {tasks}
        """

        chat_name = '-'.join(file_path.split('/')[-2:])
        chat_time = datetime.now().strftime('%H%M%S')
        chat = Chat(name=f"{chat_name}_{chat_time}", messages=[Message(role="user", content=request)])
        try:
            if profile:
                profile_content = profile_manager.read_profile(profile).content
                if profile_content:
                    chat.messages = [Message(role="system", content=profile_content)] + chat.messages

            chat = self.chat_with_project(chat=chat, use_knowledge=False)
            new_content = chat.messages[-1].content
            
            return "\n".join(next(self.split_blocks_by_gt_lt(new_content)))
        except Exception as ex:
            chat.messages.append(Message(role="error", content=str(ex)))
            raise ex
        finally:
            if save_changes:
                self.save_chat(chat=chat)

    def change_file(self, context_documents, query, file_path, org_content, save_changes=False):
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
            chat = self.chat_with_project(chat=chat, use_knowledge=False)
            response = chat.messages[-1].content.strip()
            parsed_response = AI_CODE_VALIDATE_RESPONSE_PARSER.invoke(response)
            return parsed_response.new_content
        except Exception as ex:
            chat.messages.append(Message(role="error", content=str(ex)))
            raise ex
        finally:
            if save_changes:
                self.save_chat(chat=chat)

    def check_file_for_mentions(self, file_path: str, content: str = None, silent: bool = False):
        profile_manager = ProfileManager(settings=self.settings)
        chat_manager = ChatManager(settings=self.settings)
        ai = AI(settings=self.settings)
        mentions = None
        def read_file():
            with open(file_path, 'r') as f:
                return f.read()

        def save_file(new_content):
            write_file(file_path, new_content)

        if not content:
            content = read_file()
        mentions = extract_mentions(content)
        
        if not mentions:
            return False
            
        new_content = notify_mentions_in_progress(content)
        if not silent:
            save_file(new_content=new_content)

        image_mentions = [m for m in mentions if m.flags.image]
        if image_mentions:
            new_content = self.process_image_mention(image_mentions, file_path, content)
            return self.check_file_for_mentions(file_path=file_path, content=new_content, silent=True)

        org_content = strip_mentions(content=content, mentions=mentions)

        use_knowledge = True
        
        using_chat = any(m.flags.chat_id for m in mentions)
        skip_knowledge_search = not any(m.flags.knowledge for m in mentions)
        

        if using_chat or skip_knowledge_search:
            use_knowledge = False       
            logger.info(f"Skip KNOWLEDGE search for processing, using_chat={using_chat}")
        
        def mention_info(mention):
            chat = chat_manager.find_by_id(mention.flags.chat_id) if mention.flags.chat_id else None
            if chat:
                logger.info(f"using CHAT for processing mention: {mention.mention}")
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

        chat = Chat(name=f"changes_at_{file_path}", messages=[
            Message(role="user", content=f"""
            {profile_manager.read_profile("software_developer").content}
            Find all information needed to apply all changes to file: {file_path}
            Changes:
              {query}

            File content:
            {new_content}
            """)
        ])
            
        self.chat_with_project(chat=chat, use_knowledge=use_knowledge)
        chat.messages.append(Message(role="user", content=f"""
        Rewrite full file content replacing codx instructions by required changes.
        Return only the file content without any further decoration or comments.
        Do not surround response with '```' marks, just content:
        {new_content}
        """))
        self.chat_with_project(chat=chat, use_knowledge=False, append_references=False)
        response = chat.messages[-1].content
        save_file(new_content=response)

        return True

    def process_image_mention(self, image_mentions, file_path: str, content: str):
        ai = self.get_ai()
        for image_mention in image_mentions:
            image_mention.new_content = ai.image(image_mention.content)
        return replace_mentions(content, image_mentions)

        
    def chat_with_project(self, chat: Chat, use_knowledge: bool=True, callback=None, append_references: bool=True, chat_mode: str=None):
        chat_mode = chat_mode or chat.mode or 'chat'
        if chat_mode == 'browser':
            logger.info(f"chat_with_project browser mode")
            return self.get_browser().chat_with_browser(chat)

        is_refine = chat_mode == 'task'
        ai_messages = [m for m in chat.messages if not m.hide and not m.improvement and m.role == "assistant"]
        last_ai_message = ai_messages[-1] if ai_messages else None
            
        user_message = chat.messages[-1]
        query = user_message.content

        ai = AI(settings=self.settings)
        profile_manager = ProfileManager(settings=self.settings)

        instructions = f"""BEGIN INSTRUCTIONS
        This is a conversation between you and the user about the project {self.settings.project_name}.
        Please always keep your answers short and simple unless a more detailed answer has been requested.
        END INSTRUCTIONS
        """
        if chat_mode == 'task':
            task = last_ai_message.content if is_refine and last_ai_message else "No task defined yet, create it following the instructions"
            if is_refine:
                user_message = Message(role="user", content=f"""
                  UPDATE OR CREATE THE TASK:
                  {task}
                  
                  USER COMMENTS:
                  {query}
                  """)
            instructions = f"""
            {profile_manager.read_profile("analyst").content}
            """
        chat.messages.append(
            Message(role="system", hide=True, content=f"""# INSTRUCTIONS:
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

                logger.info(f"ImageMessage content: {content}")
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
        ignore_documents = chat_files.copy()
        if chat.name:
            ignore_documents.append(f"/{chat.name}")
        
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
            logger.info(f"chat_with_project found {doc_length} relevant documents")

        if context:
            user_message = Message(role="user", content=f"""{user_message.content}
            THIS INFORMATION IS COMING FROM PROJECT'S FILES.
            HOPE IT HELPS TO ANSWER USER REQUEST.
            KEEP FILE SOURCE WHEN WRITING CODE BLOCKS (EXISTING OR NEWS).
            {context}
            """)
        messages.append(convert_message(user_message))
        messages = ai.chat(messages, callback=callback)
        response = messages[-1].content
        sources = []
        if documents:
            sources = list(set([doc.metadata['source'].replace(self.settings.project_path, "") for doc in documents]))
            
        response_message = Message(role="assistant", content=response, files=sources)
        if chat_mode == 'task':
            for msg in chat.messages:
                msg.hide = True
        chat.messages.append(response_message)
        return chat, documents

    def check_project(self):
        try:
            logger.info(f"check_project")
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
          with open(wiki_file) as f:
              return f.read()
        except:
          return f"{wiki_file} not found"

    def update_wiki(self, file_path: str):
        project_wiki_path = self.settings.get_project_wiki_path()
        if not self.settings.project_wiki or file_path.startswith(project_wiki_path):
            return

        project_wiki_home = f"{project_wiki_path}/home.md"

        home_content = f"# {self.settings.project_name}"
        if os.path.isfile(project_wiki_home):
            with open(project_wiki_home, 'r') as f:
                home_content = f.read()

        with open(file_path, 'r') as f:
            file_content = f.read()
            logger.info(f"update_wiki file_path: {file_path}, project_wiki: {project_wiki_path}")
            chat = Chat(messages=[
                Message(role="user", content=f"""Extract important parts from the content of {file_path} to be added to the wiki.
                {file_content}
                """)
            ])
            self.chat_with_project(chat=chat, use_knowledge=True)
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
            code_generator = self.improve_existing_code(chat=chat, apply_changes=False)
            logger.info(f"update_wiki file_path: {file_path}, changes: {code_generator}")
            if code_generator:
                wiki_changes = [change for change in code_generator.code_changes if project_wiki_path in change.file_path]
                logger.info(f"update_wiki file_path: {file_path}, wiki changes: {wiki_changes}")
                if wiki_changes:
                    self.apply_improve_code_changes(code_generator=AICodeGerator(code_changes=wiki_changes))

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

    def save_profile(self, profile: Profile):
        if profile.user_comment:
            prompt = f"""Update this document applying user comments.
            Generate a markdown document. Below it's an XML with the information you need:
            ```xml
            <xml>
                <CURRENT_DOCUMENT>
                {profile.content}
                </CURRENT_DOCUMENT>
                <USER_COMMENT>
                {profile.user_comment}
                </USER_COMMENT>
            </xml>
            ```
            Return only the document without any further decoration or comments.
            Do not surround response with '```' marks, just content
            """
            ai = AI(settings=self.settings)
            profile.content = ai.chat(prompt=prompt)[-1].content

        profile_manager = ProfileManager(settings=self.settings)
        profile_manager.create_profile(profile)
        return profile_manager.read_profile(profile.name)
    
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
        with open(path) as f:
            return f.read()
      
    def write_file(self, path: str, content: str):
        if not self.check_file_for_mentions(file_path=path, content=content, silent=True):
            with open(path, 'w') as f:
                return f.write(content)

    def search_files(self, search: str):
        all_sources = [s for s in self.get_knowledge().get_all_sources().keys() if search in s]
        base_path = self.settings.project_path
        return [self.parse_file_line(file, base_path) for file in sorted(all_sources)]
