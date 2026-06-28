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
        CE --> generate_full_file_content
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

    async def generate_full_file_content(
        self, file_path: str, partial_content: str, original_content: str = None
    ) -> str:
        """
        Generate a complete file content from partial LLM output.
        
        Uses AI to create the full file by passing the original content,
        the partial changes, and file-specific profiles to ensure proper
        formatting and structure.

        Args:
            file_path: Path of the file being generated.
            partial_content: Partial or complete content from LLM generation.
            original_content: Original file content (if file exists). If None, reads from disk.

        Returns:
            Complete file content as a string.

        Raises:
            RuntimeError: If AI generation fails.
        """
        # Read original content if not provided
        if original_content is None:
            original_content = ""
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        original_content = f.read()
                except Exception as read_ex:
                    logger.warning(
                        "Could not read original file %s: %s", file_path, read_ex
                    )

        profile_manager = ProfileManager(settings=self.settings)
        
        # Get file-specific profiles for better context
        file_profiles = profile_manager.get_file_profiles_by_file_path(file_path)
        profile_instructions = ""
        
        if file_profiles:
            profile_content_list = [
                profile_manager.get_profile_With_content(profile).parsed_content
                for profile in file_profiles
            ]
            profile_instructions = "\n\n".join(profile_content_list)
        else:
            # Fallback to software_developer profile
            default_profile = profile_manager.read_profile("software_developer")
            if default_profile:
                profile_instructions = profile_manager.get_profile_With_content(
                    default_profile
                ).parsed_content

        # Get relative path for better readability in prompts
        try:
            rel_file_path = os.path.relpath(file_path, self.settings.abs_project_path)
        except ValueError:
            rel_file_path = file_path

        # Create the request prompt with JSON response format
        request_prompt = f"""You are a code generation assistant. Your task is to generate the COMPLETE and FINAL version of a file.

FILE PATH: {rel_file_path}
PROJECT PATH: {self.settings.abs_project_path}

PROFILE GUIDELINES:
```
{profile_instructions}
```

ORIGINAL FILE CONTENT (if empty, this is a new file):
```
{original_content if original_content else "(New file - no original content)"}
```

PARTIAL/GENERATED CONTENT TO COMPLETE:
```
{partial_content}
```

INSTRUCTIONS:
1. Generate the COMPLETE file content, not partial changes
2. Preserve all formatting, indentation, and structure from the original file
3. Integrate the generated content seamlessly
4. Do NOT include code block markers (```) in your response
5. Do NOT include any explanations, comments, or decoration
6. Return ONLY the valid file content in JSON format as follows:

{{
  "file_path": "{rel_file_path}",
  "content": "<<FULL FILE CONTENT HERE>>"
}}

Ensure the JSON is valid and the content is properly escaped if needed."""

        try:
            ai = self.session.get_ai()
            self.session.log_info(
                "Generating full file content for %s using AI", file_path
            )
            
            messages = await ai.a_chat(prompt=request_prompt)
            response_content = messages[-1].content.strip()
            
            # Extract JSON from response
            parsed_response = self._extract_json_response(response_content)
            
            if not parsed_response or "content" not in parsed_response:
                logger.error(
                    "Invalid AI response format for file %s: %s",
                    file_path,
                    response_content,
                )
                raise RuntimeError(
                    f"AI did not return valid JSON with 'content' field for {file_path}"
                )
            
            full_content = parsed_response["content"]
            
            if not full_content:
                logger.error("AI returned empty content for file %s", file_path)
                raise RuntimeError(f"AI returned empty content for {file_path}")
            
            self.session.log_info(
                "Successfully generated full content for %s (%d chars)",
                file_path,
                len(full_content),
            )
            
            return full_content
            
        except Exception as ex:
            logger.exception(
                "Failed to generate full file content for %s: %s", file_path, ex
            )
            raise RuntimeError(
                f"Failed to generate full file content for {file_path}: {ex}"
            ) from ex

    def _extract_json_response(self, response: str) -> Optional[dict]:
        """
        Extract JSON object from AI response, handling various formats.

        Args:
            response: Raw response text from AI.

        Returns:
            Parsed JSON dict, or None if extraction fails.
        """
        response = response.strip()
        
        # Try to find JSON object in the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        
        # Try to parse entire response as JSON
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.debug("Could not parse response as JSON: %s", response[:100])
            return None

    def apply_patch(self, patch: str) -> str:
        """
        Apply a git-style diff patch and return the complete file content.
        
        Reads the original file, applies the patch through AI to ensure
        completeness, and returns the final content without saving.

        Args:
            patch: Patch content string (git diff format).

        Returns:
            Complete file content after applying the patch.

        Raises:
            RuntimeError: If the patch cannot be applied.
        """
        file_path = None
        
        # Extract file path from patch header
        file_diff_lines = patch.split("\n")
        for line in file_diff_lines:
            if line.startswith("+++ b/"):
                file_path = line[6:]  # Remove '+++ b/' prefix
                break

        if not file_path:
            raise RuntimeError("No file path found in patch header")

        # Resolve to absolute path if needed
        if not file_path.startswith(self.settings.abs_project_path):
            file_path = os.path.join(self.settings.abs_project_path, file_path)

        # Read original content
        original_content = ""
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    original_content = f.read()
            except Exception as read_ex:
                logger.warning(
                    "Could not read original file %s: %s", file_path, read_ex
                )

        # Prepare the patch request for AI
        profile_manager = ProfileManager(settings=self.settings)
        
        # Get file-specific profiles
        file_profiles = profile_manager.get_file_profiles_by_file_path(file_path)
        profile_instructions = ""
        
        if file_profiles:
            profile_content_list = [
                profile_manager.get_profile_With_content(profile).parsed_content
                for profile in file_profiles
            ]
            profile_instructions = "\n\n".join(profile_content_list)
        else:
            default_profile = profile_manager.read_profile("software_developer")
            if default_profile:
                profile_instructions = profile_manager.get_profile_With_content(
                    default_profile
                ).parsed_content

        try:
            rel_file_path = os.path.relpath(file_path, self.settings.abs_project_path)
        except ValueError:
            rel_file_path = file_path

        # Create patch application request
        request_prompt = f"""You are a code generation assistant. Your task is to apply a git patch to a file and return the COMPLETE final version.

FILE PATH: {rel_file_path}
PROJECT PATH: {self.settings.abs_project_path}

PROFILE GUIDELINES:
```
{profile_instructions}
```

ORIGINAL FILE CONTENT:
```
{original_content if original_content else "(New file)"}
```

GIT PATCH TO APPLY:
```patch
{patch}
```

INSTRUCTIONS:
1. Apply the patch to the original file content
2. Generate the COMPLETE file content, not partial changes
3. Preserve all formatting, indentation, and structure
4. Do NOT include code block markers (```) in your response
5. Do NOT include any explanations, comments, or decoration
6. Return ONLY the valid file content in JSON format as follows:

{{
  "file_path": "{rel_file_path}",
  "content": "<<COMPLETE FILE CONTENT HERE AFTER APPLYING PATCH>>"
}}

Ensure the JSON is valid and the content is properly escaped if needed."""

        try:
            ai = self.session.get_ai()
            self.session.log_info("Applying patch to %s using AI", file_path)
            
            messages = ai.chat(prompt=request_prompt)
            response_content = messages[-1].content.strip()
            
            # Extract JSON from response
            parsed_response = self._extract_json_response(response_content)
            
            if not parsed_response or "content" not in parsed_response:
                logger.error(
                    "Invalid AI response format for patch on %s: %s",
                    file_path,
                    response_content,
                )
                raise RuntimeError(
                    f"AI did not return valid JSON with 'content' field for {file_path}"
                )
            
            final_content = parsed_response["content"]
            
            if not final_content:
                raise RuntimeError(f"AI returned empty content after applying patch to {file_path}")
            
            self.session.log_info(
                "Successfully applied patch to %s (%d chars)",
                file_path,
                len(final_content),
            )
            
            return final_content
            
        except Exception as ex:
            logger.exception(
                "Failed to apply patch to %s: %s", file_path, ex
            )
            raise RuntimeError(f"Failed to apply patch to {file_path}: {ex}") from ex

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
