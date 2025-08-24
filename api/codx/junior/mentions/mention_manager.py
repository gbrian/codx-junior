import re
import json
import logging
import anyio
from slugify import slugify

from datetime import datetime

from typing import Optional

from codx.junior.chat.chat_engine import ChatEngine
# Add missing imports
from codx.junior.chat_manager import ChatManager
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.events.event_manager import EventManager

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
    knowledge: bool = False
    model: str = ''
    chat_id: str = ''
    code: bool = False
    image: bool = False

class Mention(BaseModel):
    mention: str = ''
    start_line: int = 0
    end_line: int = 0
    flags: MentionFlags = MentionFlags()
    new_content: str = ''

    def __str__(self):
        data = {
          **self.__dict__,
          "flags": self.flags.__dict__
        }
        return json.dumps(data, indent=2)

    def add_line(self, line):
        line = self.extract_flags(line.strip())
        if not self.mention:
            self.mention = line
        else:
            self.mention = f"{self.mention}\n{line}"

    def extract_flags(self, line):
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

class MentionManager:

    # Constructor for MentionManager
    def __init__(self,
                settings,
                event_manager: EventManager):
        self.settings = settings
        self.chat_manager = ChatManager(settings=settings)
        self.profile_manager = ProfileManager(settings=settings)
        self.event_manager = event_manager
        self.chat_utils = ChatUtils(profile_manager=self.profile_manager)
        self.chat_engine = ChatEngine(settings=settings, event_manager=event_manager)

    def is_processing_mentions(self, content):
        if MULTI_LINE_MENTION_START_PROGRESS in content or SINGLE_LINE_MENTION_START_PROGRESS in content:
            return True
        return False

    def check_if_file_has_mentions(self, file_path: str) -> bool:
        with open(file_path, 'r') as file:
            content = file.read()
            if self.extract_mentions(content=content):
                return True
        return False

    def extract_mentions(self, content: str) -> list[Mention]:
        if self.is_processing_mentions(content=content):
            return []

        content_lines = content.split("\n")
        mentions: list[Mention] = []
        mention: Optional[Mention] = None

        for ix, line in enumerate(content_lines):
            if SINGLE_LINE_MENTION_START in line:
                mention = Mention()
                mention.start_line = ix
                mention.add_line(line.split(SINGLE_LINE_MENTION_START)[1])
                mentions.append(mention)
                mention = None
            elif MULTI_LINE_MENTION_START in line:
                _, *rest = line.split(MULTI_LINE_MENTION_START, 1)
                if rest:  # If there is content after the codx tag, capture it
                    mention = Mention()
                    mention.start_line = ix
                    mention.add_line(rest[0].strip())  # adding initial line content after codx
                    mentions.append(mention)
                else:  # Only the start of a multi-line mention, no content on the same line
                    mention = Mention()
                    mention.start_line = ix
                    mentions.append(mention)
            elif mention and MULTI_LINE_MENTION_END in line:
                mention.end_line = ix
                mention = None
            elif mention:
                mention.add_line(line)

        return mentions

    def notify_mentions_in_progress(self, content):
        return content.replace(SINGLE_LINE_MENTION_START, SINGLE_LINE_MENTION_START_PROGRESS) \
                      .replace(MULTI_LINE_MENTION_START, MULTI_LINE_MENTION_START_PROGRESS) \
                      .replace(MULTI_LINE_MENTION_END, MULTI_LINE_MENTION_END_PROGRESS)

    def notify_mentions_error(self, content, error):
        return content.replace("codx-ok, please-wait...", f"codx-error: {error}")

    def strip_mentions(self, content, mentions):
        content_lines = content.split("\n")
        new_content = []
        last_index = 0
        for mention in mentions:
            new_content = new_content + content_lines[last_index:mention.start_line]
            last_index = (mention.end_line if mention.end_line else mention.start_line) + 1
        if last_index < len(content) - 1:
            new_content = new_content + content_lines[last_index:]
        return "\n".join(new_content).strip()

    def replace_mentions(self, content, mentions):
        content_lines = content.split("\n")
        new_content = []
        last_index = 0
        for mention in mentions:
            new_content = new_content + content_lines[last_index:mention.start_line]
            if mention.new_content:
                new_content = new_content + mention.new_content.split("\n")
            last_index = (mention.end_line if mention.end_line else mention.start_line) + 1
        if last_index < len(content) - 1:
            new_content = new_content + content_lines[last_index:]
        return "\n".join(new_content)

    def read_file(self, file_path):
        def prepare_ipynb_for_llm():
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                notebook_data = json.loads(file.read())

                # Remove outputs from each cell
                for cell in notebook_data.get('cells', []):
                    if 'outputs' in cell:
                        del cell['outputs']
                return json.dumps(notebook_data)

        if file_path.endswith(".ipynb"):
            return prepare_ipynb_for_llm()

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    @profile_function
    async def check_file_for_mentions_inner(self, mentions, file_path: str, content: str = None, callback=None):
        logger.info(f"Inside check_file_for_mentions_inner for {file_path}")
        
        file_profiles = self.profile_manager.get_file_profiles(file_path=file_path)
        file_profiles = self.profile_manager.get_profiles_and_parents(file_profiles)
        profile_names = [p.name for p in file_profiles]

        self.event_manager.send_notification(text=f"codx {len(mentions)} mentions in {file_path.split('/')[-1]} profiles: {profile_names}")
        logger.info(f"{len(mentions)} mentions found for {file_path} profiles: {profile_names}")

        use_knowledge = any(m.flags.knowledge for m in mentions)
        using_chat = any(m.flags.chat_id for m in mentions)

        save_mentions = self.settings.save_mentions

        if using_chat:
            use_knowledge = False
            logger.info(f"Skip KNOWLEDGE search for processing, using_chat={using_chat}")

        def mention_info(mention):
            chat = self.chat_manager.find_by_id(mention.flags.chat_id) if mention.flags.chat_id else None
            if chat:
                logger.info(f"using CHAT for processing mention: {mention.mention}")
                return f"""Based on this conversation:
                ```markdown
                {self.chat_manager.serialize_chat(chat)}
                ```
                User commented in line {mention.start_line}: {mention.mention}
                """
            return f"User commented in line {mention.start_line}: {mention.mention}"

        query = "\n  *".join([mention_info(mention) for mention in mentions])
        query_mentions = self.chat_utils.get_query_mentions(query=query)

        file_chat_name = "-".join(file_path.split("/")[-2:])

        logger.info(f"Create mention chat {file_chat_name}")
        analysis_chat = None
        if use_knowledge:
            analysis_chat = Chat(name=slugify(f"analysis_at_{file_chat_name}-{datetime.datetime.now()}"),
                                 board="mentions",
                                 column="analysis",
                                 mode="chat",
                                 tags=["use_knowledge" if use_knowledge else "skip_knowledge"],
                                 messages=
                                 [
                                     Message(role="user", content="\n".join([
                                         f"Find at @{self.settings.project_name} all information needed to apply all changes to file: {file_path}",
                                         "",
                                         "Changes:",
                                         query,
                                         "",
                                         "File content:",
                                         content
                                     ]))
                                 ])
            logger.info(f"Chat with project analysis {analysis_chat.name}")
            await self.chat_engine.chat_with_project(chat=analysis_chat)
            if save_mentions:
                analysis_chat = self.chat_manager.save_chat(analysis_chat)

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

            file_profile_content = f"""Best practices for this file:
            {file_profile_content}
            """

        changes_chat.messages.append(Message(role="user", content="""
        Apply codx comments and rewrite full content.
        Return only the content without any further decoration or comments.
        Do not surround response with '```' marks, just content.
        Remove codx comments from the final version.
        Do not return the <document> tags but respect tags present of the original content.
        """))

        changes_chat.messages.append(
            Message(
                role="user",
                profiles=[profile.name for profile in file_profiles],
                files=[file_path],
                content=f"""
                    Given this document:
                    <document>

                    {content}

                    </document>

                    User has added these comments:
                    <comments>
                    @{self.settings.project_name} {query}
                    </comments>

                    {file_profile_content}
                    """)
        )

        logger.info(f"Mentions generate changes {file_path}")

        # Process mentions
        await self.chat_engine.chat_with_project(chat=changes_chat, disable_knowledge=True, append_references=False, callback=callback)

        if save_mentions:
            self.chat_manager.save_chat(changes_chat)

        logger.info(f"Mentions done file changes {file_path}")

        self.event_manager.send_notification(text=f"codx mentions done for {file_path.split('/')[-1]}")
        response = changes_chat.messages[-1].content.strip()
        if response.startswith("<document>") and response.endsswith("</document>"):
            response = response[9:-10]
        return response

    async def check_file_for_mentions(self, file_path: str, content: str = None, silent: bool = False, callback=None):
        mentions = None

        if not content:
            content = self.read_file(file_path=file_path)

        if self.is_processing_mentions(content=content):
            logger.info(f"File already in processing state. {file_path}")
            return "processing"

        mentions = self.extract_mentions(content)

        if not mentions:
            return ""

        logger.info(f"Processing mentions for file:. {file_path}")    
        new_content = self.notify_mentions_in_progress(content)
        if not silent:
            logger.debug(f"Writing progress notification to file: {file_path}")
            write_file(file_path=file_path, content=new_content)

        def open_file_to_write():
            return open(file_path, 'w')
        stream_file = {}
        try:
            if not callback:
                logger.debug(f"Open file to write: {file_path}")
                def write_new_file_content(content):
                    if content:
                        if not stream_file.get("file"):
                            stream_file["file"] = open_file_to_write()
                        stream_file["file"].write(content)
                        stream_file["file"].flush()
                callback = write_new_file_content
            res = await self.check_file_for_mentions_inner(file_path=file_path,
                                                           content=new_content,
                                                           mentions=mentions,
                                                           callback=callback)
            logger.info(f"[{self.settings.project_name}] Mentions manager done for {file_path}")
            return res
        except Exception as ex:
            logger.exception(f"Error processing mentions at {file_path}: {ex}")
        finally:
            if stream_file.get("file"):
                stream_file["file"].close()
