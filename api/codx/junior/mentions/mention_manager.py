import re
import json
import logging
import anyio
from slugify import slugify

from datetime import datetime

from typing import Optional, List

from codx.junior.chat.chat_engine import ChatEngine
# Add missing imports
from codx.junior.chat_manager import ChatManager
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.events.event_manager import EventManager

from codx.junior.model.model import CodxUser

from codx.junior.db import (
  Chat,
  Message
)

from pydantic import BaseModel

from codx.junior.profiling.profiler import profile_function

from codx.junior.utils.utils import (
    write_file
)
from codx.junior.utils.chat_utils import ChatUtils


# Define the logger
logger = logging.getLogger(__name__)

# Initialize mention pattern strings
SINGLE_LINE_MENTION_START = "@" + "codx:"
MULTI_LINE_MENTION_START = "<" + "codx"
MULTI_LINE_MENTION_END = "</" + "codx>"

SINGLE_LINE_MENTION_START_PROGRESS = "@" + "codx-ok, please-wait...:"
MULTI_LINE_MENTION_START_PROGRESS = "<" + "codx-ok, please-wait..."
MULTI_LINE_MENTION_END_PROGRESS = "<" + "/codx-ok, please-wait...>"


class MentionFlags(BaseModel):
    """Flags parsed from a mention annotation in a document."""

    knowledge: bool = False
    model: str = ''
    chat_id: str = ''
    code: bool = False
    image: bool = False


class Mention(BaseModel):
    """Represents a single mention found in a document."""

    mention: str = ''
    start_line: int = 0
    end_line: int = 0
    flags: MentionFlags = MentionFlags()
    new_content: str = ''

    def __str__(self) -> str:
        data = {
          **self.__dict__,
          "flags": self.flags.__dict__
        }
        return json.dumps(data, indent=2)

    def add_line(self, line: str) -> None:
        """Append a line of text to the mention content."""
        line = self.extract_flags(line.strip())
        if not self.mention:
            self.mention = line
        else:
            self.mention = f"{self.mention}\n{line}"

    def extract_flags(self, line: str) -> str:
        """Extract flags from a line and update self.flags, returning the cleaned line."""
        flag_patterns = {}
        for flag_name, flag_value in vars(MentionFlags).items():
            if isinstance(flag_value, bool):
                flag_patterns[flag_name] = r'--' + flag_name.replace('_', '-')
            else:
                flag_patterns[flag_name] = r'--' + flag_name.replace('_', '-') + r'=([^ ]+)'

        for flag, pattern in flag_patterns.items():
            match = re.search(pattern, line)
            if match:
                if isinstance(getattr(self.flags, flag), bool):
                    setattr(self.flags, flag, True)
                    line = re.sub(pattern, '', line).strip()
                else:
                    setattr(self.flags, flag, match.group(1))
                    line = re.sub(match.group(0), '', line).strip()

        return line


def resolve_mention_model(mentions: List[Mention]) -> Optional[str]:
    """
    Resolve the LLM model to use from the list of mentions.

    Returns the first non-empty model flag found among the mentions,
    or None if no mention specifies a model.

    Args:
        mentions: List of Mention objects parsed from the document.

    Returns:
        The model name string if any mention specifies one, otherwise None.
    """
    for mention in mentions:
        if mention.flags.model:
            logger.debug("Using model '%s' from mention flags", mention.flags.model)
            return mention.flags.model
    return None


class MentionManager:
    """
    Manages detection and processing of codx mentions embedded in documents.

    Mentions are special annotations that trigger LLM-powered transformations
    of the surrounding document content.

    Diagram::

        .. mermaid::

           flowchart TD
               A[File Read] --> B{Has Mentions?}
               B -- No --> C[Return Empty]
               B -- Yes --> D[Mark In-Progress]
               D --> E[check_file_for_mentions_inner]
               E --> F{use_knowledge?}
               F -- Yes --> G[Analysis Chat]
               G --> H[Changes Chat]
               F -- No --> H
               H --> I[Write New Content]
               I --> J[Done]
    """

    def __init__(
        self,
        settings,
        event_manager: EventManager,
    ) -> None:
        """
        Initialise MentionManager with project settings and an event manager.

        Args:
            settings: Project settings object.
            event_manager: EventManager used to broadcast notifications.
        """
        self.settings = settings
        self.chat_manager = ChatManager(settings=settings)
        self.profile_manager = ProfileManager(settings=settings)
        self.event_manager = event_manager
        self.chat_utils = ChatUtils(profile_manager=self.profile_manager)
        self.chat_engine = ChatEngine(
            settings=settings,
            event_manager=event_manager,
            user=CodxUser(username="mention_manager"),
        )

    def is_processing_mentions(self, content: str) -> bool:
        """Return True if the content already contains in-progress mention markers."""
        return (
            MULTI_LINE_MENTION_START_PROGRESS in content
            or SINGLE_LINE_MENTION_START_PROGRESS in content
        )

    def check_if_file_has_mentions(self, file_path: str) -> bool:
        """Return True if the file at file_path contains any codx mentions."""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return bool(self.extract_mentions(content=content))

    def extract_mentions(self, content: str) -> List[Mention]:
        """
        Parse all codx mentions from the given content string.

        Args:
            content: Full text content of a document.

        Returns:
            List of Mention objects found in the content.
        """
        if self.is_processing_mentions(content=content):
            return []

        content_lines = content.split("\n")
        mentions: List[Mention] = []
        current_mention: Optional[Mention] = None

        for ix, line in enumerate(content_lines):
            if SINGLE_LINE_MENTION_START in line:
                single = Mention()
                single.start_line = ix
                single.add_line(line.split(SINGLE_LINE_MENTION_START)[1])
                mentions.append(single)
            elif MULTI_LINE_MENTION_START in line:
                _, *rest = line.split(MULTI_LINE_MENTION_START, 1)
                current_mention = Mention()
                current_mention.start_line = ix
                if rest:
                    current_mention.add_line(rest[0].strip())
                mentions.append(current_mention)
            elif current_mention and MULTI_LINE_MENTION_END in line:
                current_mention.end_line = ix
                current_mention = None
            elif current_mention:
                current_mention.add_line(line)

        return mentions

    def notify_mentions_in_progress(self, content: str) -> str:
        """Replace mention markers with in-progress markers in the content."""
        return (
            content
            .replace(SINGLE_LINE_MENTION_START, SINGLE_LINE_MENTION_START_PROGRESS)
            .replace(MULTI_LINE_MENTION_START, MULTI_LINE_MENTION_START_PROGRESS)
            .replace(MULTI_LINE_MENTION_END, MULTI_LINE_MENTION_END_PROGRESS)
        )

    def notify_mentions_error(self, content: str, error: str) -> str:
        """Replace in-progress markers with an error marker in the content."""
        return content.replace("codx-ok, please-wait...", f"codx-error: {error}")

    def strip_mentions(self, content: str, mentions: List[Mention]) -> str:
        """
        Remove mention blocks from the content, returning clean text.

        Args:
            content: Original document content.
            mentions: List of Mention objects to remove.

        Returns:
            Document content with mention blocks removed.
        """
        content_lines = content.split("\n")
        new_content: List[str] = []
        last_index = 0
        for mention in mentions:
            new_content.extend(content_lines[last_index:mention.start_line])
            last_index = (mention.end_line if mention.end_line else mention.start_line) + 1
        if last_index < len(content) - 1:
            new_content.extend(content_lines[last_index:])
        return "\n".join(new_content).strip()

    def replace_mentions(self, content: str, mentions: List[Mention]) -> str:
        """
        Replace mention blocks in the content with their generated new_content.

        Args:
            content: Original document content.
            mentions: List of Mention objects with populated new_content.

        Returns:
            Document content with mention blocks replaced by new_content.
        """
        content_lines = content.split("\n")
        new_content: List[str] = []
        last_index = 0
        for mention in mentions:
            new_content.extend(content_lines[last_index:mention.start_line])
            if mention.new_content:
                new_content.extend(mention.new_content.split("\n"))
            last_index = (mention.end_line if mention.end_line else mention.start_line) + 1
        if last_index < len(content) - 1:
            new_content.extend(content_lines[last_index:])
        return "\n".join(new_content)

    def read_file(self, file_path: str) -> str:
        """
        Read the content of a file, with special handling for Jupyter notebooks.

        Args:
            file_path: Absolute path to the file.

        Returns:
            File content as a string.
        """
        if file_path.endswith(".ipynb"):
            return self._read_ipynb(file_path)
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def _read_ipynb(self, file_path: str) -> str:
        """
        Read a Jupyter notebook file, stripping cell outputs for LLM consumption.

        Args:
            file_path: Absolute path to the .ipynb file.

        Returns:
            JSON string of the notebook without cell outputs.
        """
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            notebook_data = json.loads(file.read())
        for cell in notebook_data.get('cells', []):
            cell.pop('outputs', None)
        return json.dumps(notebook_data)

    @profile_function
    async def check_file_for_mentions_inner(
        self,
        mentions: List[Mention],
        file_path: str,
        content: str = None,
        callback=None,
    ) -> str:
        """
        Core processing logic: build LLM chats and generate the new document content.

        Uses the model flag from the first mention that specifies one (if any) to
        override the default LLM model for both the analysis and changes chats.

        Args:
            mentions: List of Mention objects extracted from the document.
            file_path: Absolute path to the file being processed.
            content: Current (in-progress-marked) document content.
            callback: Optional async callback for streaming responses.

        Returns:
            New document content produced by the LLM.
        """
        logger.info("Inside check_file_for_mentions_inner for %s", file_path)

        file_profiles = self.profile_manager.get_file_profiles_by_file_path(file_path=file_path)
        profile_names = [p.name for p in file_profiles]
        file_label = file_path.split('/')[-1]

        self.event_manager.send_notification(
            text=(
                f"codx {len(mentions)} mentions in {file_label} "
                f"profiles: {profile_names}"
            )
        )
        logger.info(
            "%d mentions found for %s profiles: %s",
            len(mentions), file_path, profile_names,
        )

        use_knowledge = any(m.flags.knowledge for m in mentions)
        using_chat = any(m.flags.chat_id for m in mentions)

        # Resolve model override from mention flags (first non-empty wins)
        mention_model = resolve_mention_model(mentions)
        if mention_model:
            logger.info("Mention model override: '%s'", mention_model)

        save_mentions = self.settings.save_mentions

        if using_chat:
            use_knowledge = False
            logger.info(
                "Skip KNOWLEDGE search for processing, using_chat=%s", using_chat
            )

        def mention_info(mention: Mention) -> str:
            """Build a descriptive string for a single mention."""
            chat = (
                self.chat_manager.find_by_id(mention.flags.chat_id)
                if mention.flags.chat_id
                else None
            )
            if chat:
                logger.info("Using CHAT for processing mention: %s", mention.mention)
                serialized = self.chat_manager.serialize_chat(chat)
                return (
                    f"Based on this conversation:\n"
                    f"```markdown\n{serialized}\n```\n"
                    f"User commented in line {mention.start_line}: {mention.mention}"
                )
            return f"User commented in line {mention.start_line}: {mention.mention}"

        query = "\n  *".join([mention_info(m) for m in mentions])
        query_mentions = self.chat_utils.get_query_mentions(query=query)

        file_chat_name = "-".join(file_path.split("/")[-2:])
        logger.info("Create mention chat %s", file_chat_name)

        analysis_chat: Optional[Chat] = None
        if use_knowledge:
            analysis_chat = Chat(
                name=slugify(f"analysis_at_{file_chat_name}-{datetime.now()}"),
                board="mentions",
                column="analysis",
                mode="chat",
                llm_model=mention_model,  # Apply model override from mention flags
                tags=["use_knowledge" if use_knowledge else "skip_knowledge"],
                messages=[
                    Message(
                        role="user",
                        content="\n".join([
                            f"Find at @{self.settings.project_name} all information "
                            f"needed to apply all changes to file: {file_path}",
                            "",
                            "Changes:",
                            query,
                            "",
                            "File content:",
                            content,
                        ]),
                    )
                ],
            )
            logger.info("Chat with project analysis %s", analysis_chat.name)
            await self.chat_engine.chat_with_project(chat=analysis_chat)
            if save_mentions:
                analysis_chat = self.chat_manager.save_chat(analysis_chat)

        changes_chat = Chat(
            name=slugify(f"changes_at_{file_chat_name}-{datetime.now()}"),
            board="mentions",
            column="changes",
            parent_chat=analysis_chat.id if analysis_chat else None,
            llm_model=mention_model,  # Apply model override from mention flags
            tags=["use_knowledge" if use_knowledge else "skip_knowledge"],
            profiles=[p.name for p in query_mentions.profiles],
            messages=[],
        )

        if analysis_chat:
            changes_chat.messages.append(analysis_chat.messages[-1])

        changes_chat.messages.append(
            Message(
                role="user",
                profiles=profile_names,
                files=[file_path],
                content=(
                    f"<document>\n{content}\n</document>\n\n"
                    f"<user_instructions>\n{query}\n</user_instructions>\n\n"
                    "Given the elements \"document\" and \"user_instructions\" do this:\n"
                    " - Apply user_instructions to document content\n"
                    " - Pay attention to do not loose any detail or part of the document.\n"
                    " - IMPORTANT: Return only the new document content without <document> tags"
                ),
            )
        )

        logger.info("Mentions generate changes %s", file_path)

        # Process mentions with the LLM
        await self.chat_engine.chat_with_project(
            chat=changes_chat,
            disable_knowledge=True,
            append_references=False,
            callback=callback,
        )

        if save_mentions:
            self.chat_manager.save_chat(changes_chat)

        logger.info("Mentions done file changes %s", file_path)

        response_message = changes_chat.messages[-1]
        if response_message.error:
            raise RuntimeError(response_message.error)

        response = response_message.content.strip()

        INVALID_HEADERS = ["<document>", "```"]

        def starts_with_invalid_header(text: str) -> Optional[str]:
            """Return the matched invalid header prefix, or None."""
            return next((h for h in INVALID_HEADERS if text.startswith(h)), None)

        org_starts_with_invalid = starts_with_invalid_header(content)
        response_starts_with_invalid = starts_with_invalid_header(response)

        # Strip the wrapper header/footer added by the LLM if the original did not have them
        if not org_starts_with_invalid and response_starts_with_invalid:
            response = "\n".join(response.split("\n")[1:-1])

        return response

    async def check_file_for_mentions(
        self,
        file_path: str,
        content: str = None,
        silent: bool = False,
        callback=None,
    ) -> str:
        """
        Entry point: check a file for codx mentions and process them.

        Args:
            file_path: Absolute path to the file to inspect.
            content: Optional pre-read content; if None the file is read from disk.
            silent: If True, skip writing the in-progress marker to disk.
            callback: Optional async callback for streaming LLM responses.

        Returns:
            "processing" if already in-progress, empty string if no mentions found,
            otherwise the path is updated in-place and an empty string is returned.
        """
        if not content:
            content = self.read_file(file_path=file_path)

        if self.is_processing_mentions(content=content):
            logger.info("File already in processing state. %s", file_path)
            return "processing"

        mentions = self.extract_mentions(content)

        if not mentions:
            return ""

        logger.info("Processing mentions for file: %s", file_path)
        new_content = self.notify_mentions_in_progress(content)
        if not silent:
            logger.debug("Writing progress notification to file: %s", file_path)
            write_file(file_path=file_path, content=new_content)

        try:
            res = await self.check_file_for_mentions_inner(
                file_path=file_path,
                content=new_content,
                mentions=mentions,
                callback=callback,
            )
            logger.info(
                "[%s] Mentions manager done for %s",
                self.settings.project_name, file_path,
            )
            write_file(file_path=file_path, content=res)
            self.event_manager.send_notification(
                text=f"codx mentions done for {file_path.split('/')[-1]}"
            )
            logger.info("Mentions done, write file: %s", file_path)
        except (RuntimeError, ValueError, OSError) as ex:
            logger.exception("Error processing mentions at %s: %s", file_path, ex)
            self.event_manager.send_notification(
                text=f"codx mentions ERROR for file {file_path.split('/')[-1]}: {ex}"
            )

        return ""

# Made with ❤️ by codx-junior