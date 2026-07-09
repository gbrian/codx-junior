"""
Main session module for codx-junior engine.
CODXJuniorSession orchestrates all sub-engine modules.

Made with ❤️ by codx-junior
"""

import logging
import os
import shutil
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List

import requests

from codx.junior.ai import AI
from codx.junior.chat_manager import ChatManager
from codx.junior.context import (
    AI_CODE_GENERATOR_PARSER,
    AICodeGenerator
)
from codx.junior.db import Chat, Message
from codx.junior.events.event_manager import EventManager
from codx.junior.knowledge.knowledge_keywords import KnowledgeKeywords
from codx.junior.knowledge.knowledge_milvus import Knowledge
from codx.junior.mentions.mention_manager import MentionManager
from codx.junior.model.model import CodxUser, KnowledgeSearch, Profile
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.profiling.profiler import profile_function
from codx.junior.project.project_discover import (
    find_project_by_id,
    find_project_by_name,
)
from codx.junior.settings import CODXJuniorSettings
from codx.junior.sio.session_channel import SessionChannel
from codx.junior.utils.chat_utils import ChatUtils
from codx.junior.utils.utils import extract_json_blocks
from codx.junior.whisper.audio_manager import AudioManager

from codx.junior.engine.knowledge_engine import KnowledgeEngine
from codx.junior.engine.code_engine import CodeEngine
from codx.junior.engine.git_engine import GitEngine
from codx.junior.engine.file_engine import FileEngine
from codx.junior.engine.chat_engine_actions import ChatEngineActions
from codx.junior.engine.wiki_engine import WikiEngine

logger = logging.getLogger(__name__)

class CODXJuniorSession:
    """
    Main session class that orchestrates all sub-engine modules.

    Diagram:
    ```mermaid
    classDiagram
        CODXJuniorSession --> KnowledgeEngine
        CODXJuniorSession --> CodeEngine
        CODXJuniorSession --> GitEngine
        CODXJuniorSession --> FileEngine
        CODXJuniorSession --> ChatEngineActions
        CODXJuniorSession --> WikiEngine
    ```
    """

    def __init__(
        self,
        settings: CODXJuniorSettings = None,
        codx_path: str = None,
        channel: SessionChannel = None,
        user: CodxUser = None,
    ):
        self.settings = settings or CODXJuniorSettings.from_project_file(
            f"{codx_path}/project.json"
        )
        self.channel = channel
        self.user = user
        self.event_manager = EventManager(
            codx_path=codx_path,
            channel=channel,
        )
        self.audio_manager = AudioManager()

        # Initialize sub-engines
        self._knowledge_engine = KnowledgeEngine(session=self)
        self._code_engine = CodeEngine(session=self)
        self._git_engine = GitEngine(session=self)
        self._file_engine = FileEngine(session=self)
        self._chat_engine_actions = ChatEngineActions(session=self)
        self._wiki_engine = WikiEngine(session=self)

    # -------------------------------------------------------------------------
    # Core session methods
    # -------------------------------------------------------------------------

    def update_last_access_time(self) -> None:
        """Update the last access time to now."""
        self.settings.last_access_time = str(datetime.now())

    def switch_project(self, project_id: str) -> "CODXJuniorSession":
        """Switch to a different project by ID."""
        if not project_id or project_id == self.settings.project_id:
            return self
        settings = find_project_by_id(project_id=project_id)
        return (
            CODXJuniorSession(settings=settings, channel=self.channel)
            if settings
            else self
        )

    def log_info(self, msg: str, *args) -> None:
        """Log an info message prefixed with the project name."""
        logger.info("[%s] " + msg, self.settings.project_name, *args)

    def log_error(self, msg: str, *args) -> None:
        """Log an error message prefixed with the project name."""
        logger.error("[%s] " + msg, self.settings.project_name, *args)

    def log_exception(self, msg: str, *args) -> None:
        """Log an exception message prefixed with the project name."""
        logger.exception("[%s] " + msg, self.settings.project_name, *args)

    def coder_open_file(self, file_name: str) -> dict:
        """Open a file in the code server editor."""
        if not os.path.isfile(file_name) and not file_name.startswith(
            self.settings.abs_project_path
        ):
            file_name = f"{self.settings.abs_project_path}/{file_name}".replace("//", "/")

        cmd = f'code-server -r "{file_name}"'
        os.system(cmd)
        return {
            "cmd": cmd,
            "project_path": self.settings.abs_project_path,
            "file_name": file_name,
        }

    @contextmanager
    def chat_action(self, chat: Chat, event: str):
        """Context manager for wrapping chat actions with event notifications."""
        self.event_manager.chat_event(chat=chat, message=f"{event} starting")
        self.log_info(f"Start chat {chat.name}")
        try:
            yield
        except Exception as ex:
            self.event_manager.chat_event(
                chat=chat, message=f"{event} error: {ex}", event_type="error"
            )
            self.log_exception(f"Chat {chat.name} {event} error: {ex}")
        finally:
            self.event_manager.chat_event(chat=chat, message=f"{event} done")
            self.log_info(f"Chat done {chat.name}")

    def delete_project(self) -> None:
        """Delete the project directory."""
        shutil.rmtree(self.settings.codx_path)
        logger.error("PROJECT REMOVED %s", self.settings.codx_path)

    # -------------------------------------------------------------------------
    # Manager factories
    # -------------------------------------------------------------------------

    def get_mention_manager(self) -> MentionManager:
        """Return a MentionManager for this session."""
        return MentionManager(
            settings=self.settings, event_manager=self.event_manager
        )

    def get_chat_manager(self) -> ChatManager:
        """Return a ChatManager for this session."""
        return ChatManager(settings=self.settings, event_manager=self.event_manager)

    def get_profile_manager(self, settings: CODXJuniorSettings = None) -> ProfileManager:
        """Return a ProfileManager for this session."""
        return ProfileManager(settings=settings or self.settings)

    def get_ai(self, llm_model: str = None) -> AI:
        """Return an AI instance for this session."""
        return AI(settings=self.settings, llm_model=llm_model, user=self.user)

    def get_knowledge(self) -> Knowledge:
        """Return a Knowledge instance for this session."""
        return Knowledge(settings=self.settings)

    def get_wiki(self):
        """Return a WikiManager for this session."""
        from codx.junior.wiki.wiki_manager import WikiManager
        return WikiManager(settings=self.settings)

    def get_browser(self):
        """Return a Browser for this session."""
        from codx.junior.browser.browser import Browser
        return Browser(session=self)

    # -------------------------------------------------------------------------
    # Chat management
    # -------------------------------------------------------------------------

    @profile_function
    def load_chat(self, board: str, chat_name: str) -> Chat:
        """Load a chat by board and name."""
        return self.get_chat_manager().load_chat(board=board, chat_name=chat_name)

    def list_chats(self, from_date: str = None) -> list:
        """List all chats, optionally filtered by date."""
        return self.get_chat_manager().list_chats(from_date=from_date)

    async def save_chat(self, chat: Chat, chat_only: bool = False) -> Chat:
        """Persist a chat."""
        chat = self.get_chat_manager().save_chat(chat, chat_only)
        return chat

    def delete_chat(self, chat_id: str) -> None:
        """Delete a chat by ID."""
        self.get_chat_manager().delete_chat(chat_id=chat_id)

    # -------------------------------------------------------------------------
    # Profile management
    # -------------------------------------------------------------------------

    @profile_function
    def list_profiles(self) -> list:
        """List all available profiles."""
        return self.get_profile_manager().list_all_profiles()

    async def save_profile(self, profile: Profile) -> Profile:
        """Persist a profile."""
        return self.get_profile_manager().save_profile(profile=profile)

    def watch_project(self, watching: bool) -> None:
        """Enable or disable project watching."""
        self.settings.watching = watching
        self.settings.save_project()

    def read_profile(self, profile_name: str) -> Profile:
        """Read a profile by name."""
        return self.get_profile_manager().read_profile(profile_name)

    def delete_profile(self, profile_name: str) -> None:
        """Delete a profile by name."""
        return self.get_profile_manager().delete_profile(profile_name)

    def get_project_profile(self) -> Profile:
        """Return the project profile."""
        return self.get_profile_manager().read_profile("project")

    # -------------------------------------------------------------------------
    # Mention utilities
    # -------------------------------------------------------------------------

    def extract_query_mentions(self, query: str) -> list:
        """Extract @mentions from a query string."""
        chat_utils = ChatUtils(profile_manager=self.get_profile_manager())
        return chat_utils.extract_query_mentions(query=query)

    def find_projects_by_mentions(self, mentions: list) -> list:
        """Find projects referenced by @mention names."""
        chat_utils = ChatUtils(profile_manager=self.get_profile_manager())
        return chat_utils.find_projects_by_mentions(mentions=mentions)

    def find_profiles_by_mentions(self, mentions: list) -> list:
        """Find profiles referenced by @mention names."""
        chat_utils = ChatUtils(profile_manager=self.get_profile_manager())
        return chat_utils.find_profiles_by_mentions(mentions=mentions)

    def get_query_mentions(self, query: str) -> list:
        """Get all mentions from a query string."""
        chat_utils = ChatUtils(profile_manager=self.get_profile_manager())
        return chat_utils.get_query_mentions(query=query)

    # -------------------------------------------------------------------------
    # Project dependency helpers
    # -------------------------------------------------------------------------

    def get_project_dependencies(self) -> tuple:
        """Return child projects and dependency projects."""
        return self._knowledge_engine.get_project_dependencies()

    def get_all_search_projects(self) -> list:
        """Return all projects relevant for search."""
        return self._knowledge_engine.get_all_search_projects()

    # -------------------------------------------------------------------------
    # Knowledge operations (delegated)
    # -------------------------------------------------------------------------

    @profile_function
    async def knowledge_search(self, knowledge_search: KnowledgeSearch) -> dict:
        """Perform a knowledge search."""
        return await self._knowledge_engine.knowledge_search(knowledge_search)

    def delete_knowledge_source(self, sources: list) -> dict:
        """Delete knowledge documents by source paths."""
        return self._knowledge_engine.delete_knowledge_source(sources=sources)

    def index_knowledge_source(self, sources: list) -> dict:
        """Index knowledge documents by source paths."""
        return self._knowledge_engine.index_knowledge_source(sources=sources)

    def delete_knowledge(self) -> dict:
        """Reset all knowledge."""
        return self._knowledge_engine.delete_knowledge()

    def check_knowledge_status(self) -> dict:
        """Return current knowledge status."""
        return self._knowledge_engine.check_knowledge_status()

    def get_knowledge_files(self) -> List[str]:
        """Return current knowledge status."""
        return self._knowledge_engine.get_knowledge_files()

    @profile_function
    def find_project_documents(self, query: str) -> list:
        """Find project documents relevant to a query."""
        return self._knowledge_engine.find_project_documents(query=query)

    @profile_function
    def project_search(self, query: str) -> list:
        """Search knowledge for a query."""
        return self._knowledge_engine.project_search(query=query)

    @profile_function
    def select_afefcted_documents_from_knowledge(
        self,
        chat: Optional[Chat],
        ai: AI,
        query: str,
        ignore_documents: list = None,
        search_projects: list = None,
    ) -> tuple:
        """Select documents from knowledge relevant to a query."""
        return self._knowledge_engine.select_afefcted_documents_from_knowledge(
            chat=chat,
            ai=ai,
            query=query,
            ignore_documents=ignore_documents or [],
            search_projects=search_projects or [],
        )

    def extract_tags(self, doc) -> object:
        """Extract tags/keywords from a document."""
        return self._knowledge_engine.extract_tags(doc)

    def get_keywords(self, query: str) -> list:
        """Get keywords for a query."""
        return self._knowledge_engine.get_keywords(query=query)

    def create_knowledge_search_query(self, query: str) -> str:
        """Create a knowledge base search query from free text."""
        return self._knowledge_engine.create_knowledge_search_query(query=query)

    async def process_project_changes(self) -> None:
        """Process pending project file changes for knowledge indexing."""
        return await self._knowledge_engine.process_project_changes()

    async def process_project_mentions(self) -> None:
        """Process pending project file mention checks."""
        return await self._knowledge_engine.process_project_mentions()

    # -------------------------------------------------------------------------
    # Code operations (delegated)
    # -------------------------------------------------------------------------

    async def excute_bash_code(self, chat: Chat, code_block_info: dict) -> None:
        """Execute a bash code block."""
        return await self._code_engine.excute_bash_code(chat=chat, code_block_info=code_block_info)

    async def generate_code(self, chat: Chat, code_block_info: dict) -> None:
        """Generate or apply code from a code block."""
        return await self._code_engine.generate_code(chat=chat, code_block_info=code_block_info)

    async def improve_existing_code_patch(
        self, chat: Chat, code_generator: AICodeGenerator
    ) -> tuple:
        """Apply a patch-based code improvement."""
        return await self._code_engine.improve_existing_code_patch(
            chat=chat, code_generator=code_generator
        )

    async def generate_full_file_content(self, file_path: str, partial_content: str) -> str:
        """Apply a partial changes code improvement."""
        return await self._code_engine.generate_full_file_content(
            file_path=file_path, partial_content=partial_content
        )


    @profile_function
    async def improve_existing_code(
        self, chat: Chat, apply_changes: bool = None
    ) -> AICodeGenerator:
        """Improve existing code using AI."""
        return await self._code_engine.improve_existing_code(
            chat=chat, apply_changes=apply_changes
        )

    def get_ai_code_generator_changes(self, response: str) -> AICodeGenerator:
        """Parse AI response into a code generator object."""
        return self._code_engine.get_ai_code_generator_changes(response=response)

    @profile_function
    async def apply_improve_code_changes(
        self, code_generator: AICodeGenerator, chat: Chat = None
    ) -> None:
        """Apply AI-generated code changes to files."""
        return await self._code_engine.apply_improve_code_changes(
            code_generator=code_generator, chat=chat
        )

    async def change_file_with_instructions(
        self, instruction_list: list, file_path: str, content: str
    ) -> str:
        """Rewrite a file applying a list of instructions."""
        return await self._code_engine.change_file_with_instructions(
            instruction_list=instruction_list, file_path=file_path, content=content
        )

    def project_script_test(self) -> Optional[str]:
        """Run the project test script and return output."""
        return self._code_engine.project_script_test()

    def apply_patch(self, patch: str) -> None:
        """Apply a git-style patch to the project."""
        return self._code_engine.apply_patch(patch=patch)

    def extract_changes(self, content: str):
        """Extract change objects from AI response content."""
        return self._code_engine.extract_changes(content=content)

    async def change_file(
        self,
        context_documents: list,
        query: str,
        file_path: str,
        org_content: str,
        save_changes: bool = False,
    ) -> str:
        """Rewrite a file based on context documents and a query."""
        return await self._code_engine.change_file(
            context_documents=context_documents,
            query=query,
            file_path=file_path,
            org_content=org_content,
            save_changes=save_changes,
        )

    # -------------------------------------------------------------------------
    # Chat engine actions (delegated)
    # -------------------------------------------------------------------------

    def init_chat_from_url(self, chat: Chat) -> None:
        """Initialize a chat by downloading and parsing a URL."""
        return self._chat_engine_actions.init_chat_from_url(chat=chat)

    @profile_function
    async def chat_search(self, chat_id: str, query: str) -> tuple:
        """Search knowledge and respond within a chat context."""
        return await self._chat_engine_actions.chat_search(
            chat_id=chat_id, query=query
        )

    @profile_function
    async def api_chat_with_project(
        self, profile_name: str, messages: list
    ) -> Chat:
        """Chat with the project via the API."""
        return await self._chat_engine_actions.api_chat_with_project(
            profile_name=profile_name, messages=messages
        )

    def find_chat(self, chat_id: str, owner_project_id: str):
        _self = self
        if owner_project_id and owner_project_id != self.settings.project_id:
            _self =self.switch_project(project_id=owner_project_id)
        logger.info("Searching chat: %s at project: %s (%s)", chat_id, _self.settings.project_name, owner_project_id)
        return _self.get_chat_manager().find_by_id(chat_id=chat_id)

    @profile_function
    async def chat_with_project(
        self,
        chat_id: str = None,
        owner_project_id: str = None,
        chat: Chat = None,
        disable_knowledge: bool = False,
        callback=None,
        append_references: bool = True,
        chat_mode: str = None,
        iteration: int = 0,
    ) -> tuple:
        """Core method: chat with the project using AI and knowledge."""
        chat = chat if chat else self.find_chat(chat_id=chat_id, owner_project_id=owner_project_id)
        return await self._chat_engine_actions.chat_with_project(
            chat=chat,
            disable_knowledge=disable_knowledge,
            callback=callback,
            append_references=append_references,
            chat_mode=chat_mode,
            iteration=iteration,
        )

    @profile_function
    async def summarize_chat(
        self, chat: Chat, instructions: str = ""
    ) -> Message:
        """Summarize a chat conversation."""
        return await self._chat_engine_actions.summarize_chat(
            chat=chat, instructions=instructions
        )

    @profile_function
    async def generate_tasks(self, chat: Chat, instructions: str = "") -> None:
        """Generate sub-tasks from a chat."""
        return await self._chat_engine_actions.generate_tasks(
            chat=chat, instructions=instructions
        )

    def get_chat_analysis_parents(self, chat: Chat) -> str:
        """Collect parent chat messages for context analysis."""
        return self._chat_engine_actions.get_chat_analysis_parents(chat=chat)

    def convert_message(self, m: Message) -> object:
        """Convert a DB Message to a LangChain message object."""
        return self._chat_engine_actions.convert_message(m=m)

    # -------------------------------------------------------------------------
    # File operations (delegated)
    # -------------------------------------------------------------------------

    def parse_file_line(self, file: str, base_path: str) -> dict:
        """Parse a file entry into a structured dict."""
        return self._file_engine.parse_file_line(file=file, base_path=base_path)

    def read_directory(self, path: str) -> dict:
        """List the contents of a directory."""
        return self._file_engine.read_directory(path=path)

    def get_project_file_path(self, path: str) -> str:
        """Resolve a (possibly relative) path to an absolute project path."""
        return self._file_engine.get_project_file_path(path=path)

    def read_file(self, path: str) -> str:
        """Read a project file and return its content."""
        return self._file_engine.read_file(path=path)

    def diff_file(self, path: str, content: str, from_branch: str = None, to_branch: str = None) -> dict:
        """Diff a file against provided content, optionally comparing against specific branches."""
        return self._file_engine.diff_file(
            path=path,
            content=content,
            from_branch=from_branch,
            to_branch=to_branch
        )
    
    def diff_file_comments(
        self, path: str, content: str, comments: dict = None
    ) -> None:
        """Diff a file with inline comments (placeholder)."""
        return self._file_engine.diff_file_comments(
            path=path, content=content, comments=comments or {}
        )

    @profile_function
    async def process_project_file_before_saving(
        self, file_path: str, content: str
    ) -> str:
        """Apply file profiles to content before saving."""
        return await self._file_engine.process_project_file_before_saving(
            file_path=file_path, content=content
        )

    async def apply_file_profile(
        self, file_path: str, content: str, profile: Profile
    ) -> str:
        """Apply a single file profile to content."""
        return await self._file_engine.apply_file_profile(
            file_path=file_path, content=content, profile=profile
        )

    def get_valid_project_file_path(self, file_path: str) -> tuple:
        """Validate and resolve a file path within the user's projects."""
        return self._file_engine.get_valid_project_file_path(file_path=file_path)

    async def write_project_file(
        self, file_path: str, content: str, process: bool = True
    ) -> dict:
        """Write content to a project file, optionally running file profiles."""
        return await self._file_engine.write_project_file(
            file_path=file_path, content=content, process=process
        )

    def reset_project_file(
        self, file_path: str
    ) -> None:
        """Reset file's last change."""
        self._git_engine.reset_project_file(
            file_path=file_path
        )

    def search_files(self, search: str) -> list:
        """Search for files whose paths contain the search string."""
        return self._file_engine.search_files(search=search)

    def get_wiki_file(self, file_path: str) -> str:
        """Read a wiki file and return its content."""
        return self._file_engine.get_wiki_file(file_path=file_path)

    def get_readme(self) -> str:
        """Read the project README and return its content."""
        return self._file_engine.get_readme()

    def api_image_to_text(self, image_bytes: bytes) -> str:
        """Convert image bytes to text using OCR."""
        return self._file_engine.api_image_to_text(image_bytes=image_bytes)

    # -------------------------------------------------------------------------
    # Git operations (delegated)
    # -------------------------------------------------------------------------

    def get_git_engine(self):
        return self._git_engine

    def get_repo_branches(self) -> list:
        """Return all git branches for the project."""
        return self._git_engine.get_repo_branches()

    def get_project_branches(self) -> dict:
        """Return branches and repo tree."""
        return self._git_engine.get_project_branches()

    def get_project_branch_commits(self, branch: str) -> dict:
        """Return commits for a given branch."""
        return self._git_engine.get_project_branch_commits(branch=branch)

    def find_git_root_path(self) -> str:
        """Find the root path of the git repository."""
        return self._git_engine.find_git_root_path()

    def get_repo_changes(self, from_branch: str, to_branch: str) -> dict:
        """Return file changes between two branches."""
        return self._git_engine.get_repo_changes(
            from_branch=from_branch, to_branch=to_branch
        )

    def get_branch_commits(self, from_branch: str, repo_path: str) -> list:
        """Return commits for a branch."""
        return self._git_engine.get_branch_commits(
            from_branch=from_branch, repo_path=repo_path
        )

    def get_repo_tree(self) -> list:
        """Return the full repo tree with all branches and commits."""
        return self._git_engine.get_repo_tree()

    def get_branch_details(self, branch_name: str) -> dict:
        """Return detailed commit info for a branch."""
        return self._git_engine.get_branch_details(branch_name=branch_name)

    def get_project_current_branch(self) -> str:
        """Return the current git branch name."""
        return self._git_engine.get_project_current_branch()

    def get_project_parent_branch(self) -> str:
        """Return the parent branch of the current branch."""
        return self._git_engine.get_project_parent_branch()

    def get_project_changes(self, parent_branch: str = None) -> dict:
        """Return diff between current state and a parent branch."""
        return self._git_engine.get_project_changes(parent_branch=parent_branch)

    def build_code_changes_summary(self, force: bool = False) -> object:
        """Build a summary of code changes."""
        return self._git_engine.build_code_changes_summary(force=force)

    def get_pr_review_details(self, from_branch: str, to_branch: str) -> list:
        """Return PR review details between two branches."""
        return self._git_engine.get_pr_review_details(
            from_branch=from_branch, to_branch=to_branch
        )

    # -------------------------------------------------------------------------
    # Wiki operations (delegated)
    # -------------------------------------------------------------------------

    async def process_wiki_changes(self) -> None:
        """Process pending wiki changes."""
        return await self._wiki_engine.process_wiki_changes()

    async def update_wiki(self, file_path: str) -> None:
        """Update the wiki based on a changed file."""
        return await self._wiki_engine.update_wiki(file_path=file_path)

    def update_project_profile(self, file_path: str) -> None:
        """Deprecated: Update project profile from a file."""
        return self._wiki_engine.update_project_profile(file_path=file_path)

    # -------------------------------------------------------------------------
    # Misc
    # -------------------------------------------------------------------------

    def check_project(self) -> None:
        """Check and fix the project knowledge loader."""
        from codx.junior.knowledge.knowledge_loader import KnowledgeLoader
        try:
            self.log_info("check_project")
            loader = KnowledgeLoader(settings=self.settings)
            loader.fix_repo()
        except Exception as ex:
            logger.exception(str(ex))

    def run_app(self, app_name: str) -> None:
        """Run a named application."""
        from codx.junior.globals import APPS_COMMANDS
        from codx.junior.utils.utils import exec_command
        command = APPS_COMMANDS[app_name]
        exec_command(command)

    def get_project_apps(self) -> list:
        """Return available project applications."""
        from codx.junior.globals import APPS
        return APPS