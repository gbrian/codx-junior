"""
Code sub-engine for codx-junior.
Handles code generation, improvement, patch application and related operations.

Made with ❤️ by codx-junior
"""

import json
import logging
import os
import re
import subprocess
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from codx.junior.context import (
    AI_CODE_GENERATOR_PARSER,
    AI_CODE_VALIDATE_RESPONSE_PARSER,
    AICodeGenerator,
    generate_markdown_tree,
)
from codx.junior.db import Chat, Message
from codx.junior.profiles.profile_manager import ProfileManager
from codx.junior.utils.utils import (
    clean_string,
    exec_command,
    extract_json_blocks,
    write_file,
)

if TYPE_CHECKING:
    from codx.junior.engine.session import CODXJuniorSession

logger = logging.getLogger(__name__)


class CodeEngine:
    """
    Handles all code generation and improvement operations.

    ```mermaid
    flowchart TD
        CE[CodeEngine]
        CE --> excute_bash_code
        CE --> generate_code
        CE --> improve_existing_code
        CE --> apply_improve_code_changes
        CE --> change_file_with_instructions
        CE --> project_script_test
        CE --> apply_patch
    ```
    """

    def __init__(self, session: "CODXJuniorSession") -> None:
        """Initialize with a reference to the parent session."""
        self.session = session

    @property
    def settings(self):
        """Shortcut to session settings."""
        return self.session.settings

    @property
    def event_manager(self):
        """Shortcut to session event manager."""
        return self.session.event_manager

    async def excute_bash_code(self, chat: Chat, code_block_info: dict) -> None:
        """
        Execute a bash code block and record the result in the chat.

        Args:
            chat: The active chat.
            code_block_info: Dict with 'language' and 'code' keys.
        """
        # Switch project context if needed
        self.session = self.session.switch_project(chat.project_id)

        language = code_block_info["language"]
        code = code_block_info["code"]
        try:
            self.event_manager.chat_event(chat=chat, message="Executing bash script")
            stdout, stderr = exec_command(code, cwd=self.settings.abs_project_path)
            chat.messages.append(
                Message(
                    role="user",
                    content=f"""
            Executing bash script
            ```{language}
            {code}
            ```
            stdout: {stdout}
            stderr: {stderr}
            """,
                )
            )
            self.event_manager.chat_event(chat=chat, message="Applying patch done.")
            await self.session.save_chat(chat=chat)
        except Exception as ex:
            self.event_manager.chat_event(
                chat=chat, message=f"Error applying patch: {ex}", event_type="error"
            )
            raise ex

    async def generate_code(self, chat: Chat, code_block_info: dict) -> None:
        """
        Generate or apply code from a code block.
        Determines if the code is bash (executes) or file change (applies).

        Args:
            chat: The active chat.
            code_block_info: Dict with 'language' and 'code' keys.
        """
        self.session = self.session.switch_project(chat.project_id)

        language = code_block_info["language"]
        code = code_block_info["code"]
        ai = self.session.get_ai()
        messages = ai.chat(
            prompt=f"Answer only (YES or NO). Is this something I can execute in a terminal?:\nScript:\n{code}"
        )

        is_bash = "YES" in messages[-1].content
        if is_bash:
            return await self.excute_bash_code(chat=chat, code_block_info=code_block_info)

        try:
            chat.messages.append(
                Message(
                    role="user",
                    content=f"""
            Apply this code
            ```{language}
            {code}
            ```
            """,
                )
            )
            self.event_manager.chat_event(chat=chat, message="Applying patch")
            await self.improve_existing_code(chat=chat, apply_changes=True)
            self.event_manager.chat_event(chat=chat, message="Applying patch done.")
        except Exception as ex:
            self.event_manager.chat_event(
                chat=chat, message=f"Error applying patch: {ex}", event_type="error"
            )
            raise ex

    async def improve_existing_code_patch(
        self, chat: Chat, code_generator: AICodeGenerator
    ) -> tuple:
        """
        Apply a patch-based code improvement using git apply.

        Args:
            chat: The active chat.
            code_generator: The code generator with patch data.

        Returns:
            Tuple of (stdout, stderr).
        """
        self.session = self.session.switch_project(chat.project_id)

        patch = code_generator.code_patches[0]
        ts = datetime.now().strftime("%H%M%S")
        patch_file = f"{self.settings.abs_project_path}/{ts}.patch"

        with open(patch_file, "w", encoding="utf-8") as f:
            f.write(clean_string(patch.patch))

        git_patch = f"git apply {patch_file}"
        stdout, stderr = exec_command(git_patch, cwd=self.settings.abs_project_path)
        os.remove(patch_file)

        res = f"{stdout} {stderr}".lower()
        error = bool(len(stderr or "") != 0 or "error" in res)

        changes = code_generator.code_changes
        if error and changes:
            file_path = changes[0].file_path
            await self.apply_improve_code_changes(chat=chat, code_generator=code_generator)
            stdout = "Changes applied"
            stderr = ""
            if file_path not in chat.file_list:
                chat.file_list.append(file_path)
                self.session.coder_open_file(self.settings, file_name=file_path)

        await self.session.save_chat(chat)
        return stdout, stderr

    async def improve_existing_code(
        self, chat: Chat, apply_changes: bool = None
    ) -> AICodeGenerator:
        """
        Improve existing code using AI-generated find & replace instructions.

        Args:
            chat: The active chat containing conversation history.
            apply_changes: Whether to apply changes immediately. Defaults based on chat mode.

        Returns:
            AICodeGenerator with the changes.
        """
        self.session = self.session.switch_project(chat.project_id)
        self.event_manager.send_event(message="Code changes")

        valid_messages = [message for message in chat.messages if not message.hide]

        # If the last visible message is already an improvement, apply it directly
        if valid_messages[-1].improvement:
            code_generator = self.get_ai_code_generator_changes(
                response=valid_messages[-1].content
            )
            return await self.apply_improve_code_changes(
                chat=chat, code_generator=code_generator
            )

        from codx.junior.knowledge.knowledge_milvus import Knowledge

        knowledge = Knowledge(settings=self.settings)
        profile_manager = ProfileManager(settings=self.settings)

        if apply_changes is None:
            apply_changes = chat.mode == "task"

        sources = knowledge.get_all_sources()
        sources_tree = generate_markdown_tree(sources)

        request = f"""
        Assist the user on generating file changes for the project "{self.settings.project_name}" based on the comments below.
        Make sure that all proposed changes follow strictly the best practices.
        
        Best practices:
        ```markdown
        {profile_manager.read_profile("software_developer").content}
        ```
        Info about the project:
        - Root path: {self.settings.abs_project_path}
        - Files tree view: {sources_tree}
        Use this information for generating file paths and understanding the project's folder structure.

        Create a list of find&replace instructions for each change needed:
        INSTRUCTIONS:
          {AI_CODE_GENERATOR_PARSER.get_format_instructions()}
          
          * For new files create an absolute paths
          * Only update files that exists in the project's files
          * Keep content indentation; It is crucial to find the content to replace and to make new content work
        """

        request_msg = Message(role="user", content=request)
        chat.messages.append(request_msg)

        async def try_chat_code_changes(attempt: int, error: str = None) -> AICodeGenerator:
            """Recursive helper: attempt to get valid AI code changes."""
            if error:
                chat.messages.append(
                    Message(role="user", content=f"There was an error last time:\n {error}")
                )

            await self.session.chat_with_project(
                chat=chat, disable_knowledge=True, chat_mode="chat"
            )
            chat.messages[-1].improvement = True

            request_msg.improvement = True
            request_msg.hide = True

            if chat.mode == "task":
                chat.messages[-2].hide = False
                chat.messages[-1].hide = True

            response = chat.messages[-1].content.strip()
            try:
                return self.get_ai_code_generator_changes(response=response)
            except Exception as parse_ex:
                logger.error("Error parsing response: %s", response)
                attempt -= 1
                if attempt:
                    chat.messages.pop()
                    return await try_chat_code_changes(attempt, error=str(parse_ex))
                raise parse_ex

        code_generator = await try_chat_code_changes(attempt=1)

        if not apply_changes:
            return code_generator

        await self.apply_improve_code_changes(chat=chat, code_generator=code_generator)
        return code_generator

    def get_ai_code_generator_changes(self, response: str) -> AICodeGenerator:
        """
        Parse an AI response string into an AICodeGenerator object.
        Resolves relative file paths to absolute project paths.

        Args:
            response: Raw AI response string.

        Returns:
            Parsed AICodeGenerator.
        """
        code_generator = AI_CODE_GENERATOR_PARSER.invoke(response)
        for change in code_generator.code_changes:
            file_path = change.file_path
            if not file_path.startswith(self.settings.abs_project_path):
                change.file_path = os.path.join(self.settings.abs_project_path, file_path)
        return code_generator

    async def apply_improve_code_changes(
        self, code_generator: AICodeGenerator, chat: Chat = None
    ) -> None:
        """
        Apply AI-generated code changes to the filesystem.
        Groups changes by file path for efficiency.

        Args:
            code_generator: Generator containing the list of changes.
            chat: Optional chat to update with diff output.
        """
        self.session = self.session.switch_project(chat.project_id)

        changes = code_generator.code_changes
        self.session.log_info("improve_existing_code total changes: %d", len(changes))

        # Group changes by file path
        changes_by_file_path: dict = {}
        for change in changes:
            file_path = change.file_path
            if file_path not in changes_by_file_path:
                changes_by_file_path[file_path] = []
            changes_by_file_path[file_path].append(change)

        for file_path, file_changes in changes_by_file_path.items():
            change_type = file_changes[0].change_type
            self.session.log_info(
                "improve_existing_code change: %s - %s", change_type, file_path
            )
            self.event_manager.send_event(
                message=f"Code-gen: change {change_type} - {file_path}"
            )

            if change_type == "delete_file":
                os.remove(file_path)
                if chat and file_path in chat.file_list:
                    chat.file_list = [f for f in chat.file_list if f != file_path]
            else:
                content = ""
                if os.path.isfile(file_path):
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                instruction_list = [
                    json.dumps(change.__dict__) for change in file_changes
                ]
                self.session.log_info(
                    "Applying %d changes to %s", len(file_changes), file_path
                )
                new_content = await self.change_file_with_instructions(
                    instruction_list=instruction_list,
                    file_path=file_path,
                    content=content,
                )
                if new_content and new_content != content:
                    write_file(file_path=file_path, content=new_content)
                    if chat and file_path not in chat.file_list:
                        chat.file_list.append(file_path)
                else:
                    logger.error(
                        "Error applying changes to %s. New content: %s",
                        file_path,
                        new_content,
                    )

        if chat:
            file_paths = " ".join(changes_by_file_path.keys())
            git_diff, _ = exec_command(
                f"git diff {file_paths}", cwd=self.settings.abs_project_path
            )
            chat.messages.append(
                Message(role="assistant", content=f"```diff\n{git_diff}\n```")
            )

    async def change_file_with_instructions(
        self, instruction_list: list, file_path: str, content: str
    ) -> str:
        """
        Rewrite a file by having AI apply a list of instructions.

        Args:
            instruction_list: List of JSON-encoded instruction strings.
            file_path: Path of the file being changed.
            content: Current file content.

        Returns:
            New file content as a string.
        """
        profile_manager = ProfileManager(settings=self.settings)
        chat = Chat(name=f"changes_at_{file_path}", messages=[])

        content_instructions = f"EXISTING CONTENT:\n{content}" if content else ""
        chat.messages.append(
            Message(
                role="user",
                content=f"""
        {profile_manager.read_profile("software_developer").content}

        Rewrite full file content replacing codx instructions by required changes.
        Return only the file content without any further decoration or comments.
        Do not surround response with '```' marks, just content.
        Always respect current file content formatting.

        INSTRUCTIONS:
        { "- ".join(instruction_list) }

        { content_instructions }
        """,
            )
        )
        await self.session.chat_with_project(
            chat=chat, disable_knowledge=True, append_references=False
        )
        return chat.messages[-1].content

    def project_script_test(self) -> Optional[str]:
        """
        Run the configured project test script.

        Returns:
            Console output if tests fail (or match regex), empty string if they pass, None if no script.
        """
        self.session.log_info(
            "project_script_test, test: %s - %s",
            self.settings.script_test,
            self.settings.script_test_check_regex,
        )
        if not self.settings.script_test:
            return None

        command = self.settings.script_test.split(" ")
        result = subprocess.run(
            command,
            cwd=self.settings.abs_project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        console_out = result.stdout
        self.session.log_info("project_script_test: %s\nOUTPUT DONE", console_out)

        test_regex = self.settings.script_test_check_regex or "error"
        if re.search(test_regex, console_out):
            return console_out
        return ""

    def apply_patch(self, patch: str) -> None:
        """
        Apply a git-style diff patch to the project.

        Args:
            patch: Patch content string.
        """
        file_diff_lines = patch.split("\n")
        file_path = None

        for line in file_diff_lines:
            if line.startswith("+++ b/"):
                file_path = line[6:]  # Remove '+++ b/' prefix
                break

        if not file_path:
            logger.error("No file path found in patch.")
            return

        if not file_path.startswith(self.settings.abs_project_path):
            file_path = os.path.join(self.settings.abs_project_path, file_path)

        existing_content = ""
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                existing_content = f.read()

        new_content = existing_content + "\n"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(clean_string(new_content))

        logger.info("Patch applied and saved to %s", file_path)

    def extract_changes(self, content: str):
        """
        Extract change objects from AI response content (JSON blocks).

        Args:
            content: Raw AI response text.

        Yields:
            Individual change dicts.
        """
        for block in extract_json_blocks(content):
            try:
                for change in block:
                    yield change["change"]
            except (KeyError, TypeError):
                pass

    async def change_file(
        self,
        context_documents: list,
        query: str,
        file_path: str,
        org_content: str,
        save_changes: bool = False,
    ) -> str:
        """
        Rewrite a file based on context documents and a query using AI.

        Args:
            context_documents: List of context strings.
            query: The user's change request.
            file_path: Path of the file to change.
            org_content: Original file content.
            save_changes: Whether to persist the chat.

        Returns:
            New file content.
        """
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

        chat_name = "-".join(file_path.split("/")[-2:])
        chat_time = datetime.now().strftime("%H%M%S")
        chat = Chat(
            name=f"{chat_name}_{chat_time}",
            messages=[
                Message(
                    role="user",
                    content=profile_manager.read_profile("software_developer").content,
                ),
                Message(role="user", content=request),
            ],
        )
        try:
            chat = await self.session.chat_with_project(chat=chat, disable_knowledge=True)
            response = chat.messages[-1].content.strip()
            parsed_response = AI_CODE_VALIDATE_RESPONSE_PARSER.invoke(response)
            return parsed_response.new_content
        except Exception as ex:
            chat.messages.append(Message(role="error", content=str(ex)))
            raise ex
        finally:
            if save_changes:
                await self.session.save_chat(chat=chat)