import re
import json
import logging
from typing import Optional

# Add missing imports
from codx.junior.chat_manager import ChatManager
from codx.junior.profiles.profile_manager import ProfileManager

from codx.junior.profiling.profiler import profile_function

# Define the logger
logger = logging.getLogger(__name__)

# Initialize mention pattern strings
SINGLE_LINE_MENTION_START = "@" + "codx:"
MULTI_LINE_MENTION_START = "<" + "codx"
MULTI_LINE_MENTION_END = "</" + "codx>"

SINGLE_LINE_MENTION_START_PROGRESS = "@" + "codx-ok, please-wait...:"
MULTI_LINE_MENTION_START_PROGRESS = "<" + "codx-ok, please-wait..."
MULTI_LINE_MENTION_END_PROGRESS = "<" + "/codx-ok, please-wait...>"

class MentionFlags:
    knowledge: bool
    model: str
    chat_id: str
    code: bool
    image: bool

class Mention:
    mention: str
    start_line: int = 0
    end_line: int = 0
    flags: MentionFlags = MentionFlags()
    new_content: str

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
    def __init__(self, chat_manager: ChatManager, profile_manager: ProfileManager):
        self.chat_manager = chat_manager
        self.profile_manager = profile_manager

    def is_processing_mentions(self, content):
        if MULTI_LINE_MENTION_START_PROGRESS in content or SINGLE_LINE_MENTION_START_PROGRESS in content:
            return True
        return False

    def extract_mentions(self, content):
        if self.is_processing_mentions(content=content):
            return []

        content_lines = content.split("\n")
        mentions = []
        mention = None

        for ix, line in enumerate(content_lines):
            if SINGLE_LINE_MENTION_START in line:
                mention = Mention()
                mention.start_line = ix
                mention.add_line(line.split(SINGLE_LINE_MENTION_START)[1])
                mentions.append(mention)
                mention = None
            elif MULTI_LINE_MENTION_START in line:
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
                      .replace(MULTI_LINE_MMENTION_END, MULTI_LINE_MENTION_END_PROGRESS)

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

    async def check_file_for_mentions_inner(self, mentions, file_path: str, content: str = None, callback=None):
        chat_manager = self.chat_manager
        
        file_profiles = self.profile_manager.get_file_profiles(file_path=file_path)
        file_profiles = self.profile_manager.get_profiles_and_parents(file_profiles)
        profile_names = [p.name for p in file_profiles]

        self.send_notification(text=f"@codx {len(mentions)} mentions in {file_path.split('/')[-1]} profiles: {profile_names}")
        self.log_info(f"{len(mentions)} mentions found for {file_path} profiles: {profile_names}")

        use_knowledge = any(m.flags.knowledge for m in mentions)
        using_chat = any(m.flags.chat_id for m in mentions)

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
                                         "Changes:",
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

        # Process mentions
        await self.chat_with_project(chat=changes_chat, disable_knowledge=True, append_references=False, callback=callback)

        if save_mentions:
            chat_manager.save_chat(changes_chat)

        self.log_info(f"Mentions done file changes {file_path}")

        self.send_notification(text=f"@codx done for {file_path.split('/')[-1]}")

        return changes_chat.messages[-1].content

    @profile_function
    async def check_file_for_mentions(self, file_path: str, content: str = None, silent: bool = False, callback=None):
        mentions = None

        if not content:
            content = self.read_file()

        if self.is_processing_mentions(content=content):
            return "processing"

        mentions = self.extract_mentions(content)

        if not mentions:
            return ""

        new_content = self.notify_mentions_in_progress(content)
        if not silent:
            write_file(file_path=file_path, content=new_content)

        try:
            if not callback:
                async with await anyio.open_file(file_path, 'w') as file:
                    async def write_new_file_content(content):
                        if content:
                            await file.write(content)
                            await file.flush()
                    callback = write_new_file_content
            res = await self.check_file_for_mentions_inner(file_path=file_path,
                                                           content=content,
                                                           mentions=mentions,
                                                           callback=callback)
            self.log_info(f"[{self.settings.project_name}] Mentions manager done for {file_path}")
            return res
        except Exception as ex:
            self.log_exception(f"Error processing mentions at {file_path}: {ex}")
