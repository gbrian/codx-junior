"""
Commit message generation for codx-junior.

Extends :class:`codx.junior.engine.git_graph.GitGraphEngine` with the commit
message generation used by the git view's commit panel:

- :meth:`GitCommitMessageEngine.get_staged_changes`: staged files, diff stat
  and patch (the "changes summary" shown before committing).
- :meth:`GitCommitMessageEngine.generate_commit_message`: AI written commit
  message for the staged changes.
- :meth:`GitCommitMessageEngine.normalize_commit_message`: enforces the
  **50/72 rule** (subject <= 50 chars, body lines <= 72 chars).

The 50/72 rule is an industry standard for commit messages: 50 is the maximum
length of the subject line and 72 the maximum length of every body line, so the
message stays readable in ``git log``, in terminals and in the GitHub/GitLab
UIs.

Generated messages are only normalized, not translated: the subject keeps the
imperative mood asked to the model ("add", "fix", "refactor"...), so
``git log --oneline`` reads as a changelog.

```mermaid
sequenceDiagram
    participant UI as Commit panel
    participant API as git router
    participant Engine as GitCommitMessageEngine
    participant AI as LLM
    participant Git as git CLI

    UI->>API: GET /api/git/repo/staged
    API->>Engine: get_staged_changes()
    Engine->>Git: git diff --cached --name-status / --shortstat / diff
    Engine-->>API: { files, stat, diff, diff_truncated }
    API-->>UI: 200 changes summary

    UI->>API: POST /api/git/repo/commit/message { hint }
    API->>Engine: generate_commit_message(hint)
    Engine->>Git: git diff --cached
    Engine->>AI: prompt (50/72 rule + staged patch)
    AI-->>Engine: raw message
    Engine->>Engine: normalize_commit_message()
    Engine-->>API: { success, title, body, message }
    API-->>UI: 200 message | 400 { detail }
```

Made with ❤️ by codx-junior
"""

import logging
import os
import re
import textwrap

from typing import List, Optional

from codx.junior.engine.git_graph import GitGraphEngine

logger = logging.getLogger(__name__)

# Empty tree object: diff target used while the repository has no commits yet
EMPTY_TREE_HASH = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

# 50/72 rule: maximum subject length and maximum body line width
COMMIT_SUBJECT_LIMIT = 50
COMMIT_BODY_LIMIT = 72

# Maximum characters of the staged diff sent to the AI (keeps the prompt bounded)
COMMIT_MESSAGE_MAX_DIFF_CHARS = 12000

# ``git diff --name-status`` code -> semantic status name
NAME_STATUS = {
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "T": "typechange",
    "U": "conflict",
}

# List markers kept as a hanging indent when the body is wrapped
LIST_MARKER_PATTERN = re.compile(r"^([-*+]\s+|\d+[.)]\s+)")


class GitCommitMessageEngine(GitGraphEngine):
    """
    Engine for the commit panel: staged changes summary and AI commit messages.

    ```mermaid
    flowchart TD
        GCM[GitCommitMessageEngine]
        GCM --> get_staged_changes
        GCM --> generate_commit_message
        GCM --> normalize_commit_message
        GCM --> _commit_message_prompt
        GCM --> _fallback_commit_message
        GCM --> _git_staged
        GCM --> _clean_commit_message
        GCM --> _truncate_commit_line
        GCM --> _wrap_commit_body
    ```

    Being a :class:`GitGraphEngine`, it also serves every other endpoint of the
    git router (graph, branches, working tree, commits, merge, PR lifecycle).
    """

    # -------------------------------------------------------------------------
    # Staged changes summary
    # -------------------------------------------------------------------------

    def _git_staged(self, args: List[str], cwd: Optional[str] = None) -> dict:
        """
        Run a ``git diff --cached`` command, falling back to the empty tree.

        A repository without commits has no HEAD to diff the index against, so
        the command fails because of the unborn branch. The empty tree hash is
        used as the diff target in that case, which produces the same patch
        shape (every staged file shown as a new file).

        Args:
            args: Diff arguments, e.g. ``["diff", "--cached", "--name-status"]``.
            cwd: Working directory. Defaults to the repository root.

        Returns:
            Dict returned by ``_run_git``.
        """
        result = self._run_git(args, cwd=cwd)
        if result["ok"]:
            return result
        return self._run_git(list(args) + [EMPTY_TREE_HASH], cwd=cwd)

    def get_staged_changes(
        self,
        max_diff_chars: int = COMMIT_MESSAGE_MAX_DIFF_CHARS,
        include_diff: bool = True,
    ) -> dict:
        """
        Return a summary of the staged (index) changes.

        This is the payload both the commit panel and the commit message
        generator use: the staged files with their status, the diff stat and the
        staged patch. The patch is truncated to *max_diff_chars* so the AI
        prompt stays bounded on large commits.

        Args:
            max_diff_chars: Maximum number of diff characters returned
                (0 disables the truncation).
            include_diff: Include the staged patch in the result.

        Returns:
            Dict with 'success', 'repo_path', 'files' (each one with 'path',
            'code' and 'status'), 'file_count', 'stat', 'diff',
            'diff_truncated' and 'errors'.

        Example:
            >>> summary = engine.get_staged_changes()
            >>> summary["files"]
            [{'path': 'app.py', 'code': 'A', 'status': 'added'}]
        """
        repo_root = self._get_repo_root()
        names = self._git_staged(
            ["diff", "--cached", "--name-status"], cwd=repo_root
        )
        stat = self._git_staged(
            ["diff", "--cached", "--shortstat"], cwd=repo_root
        )
        if include_diff:
            diff_result = self._git_staged(
                ["diff", "--cached", "--no-color"], cwd=repo_root
            )
        else:
            diff_result = {"ok": True, "output": "", "error": ""}

        files: List[dict] = []
        for line in names["output"].split("\n"):
            if not line.strip() or "\t" not in line:
                continue
            parts = line.split("\t")
            code = (parts[0] or "").strip()[:1]
            # Rename/copy entries end with the destination path
            path = (parts[-1] or "").strip()
            if not path:
                continue
            files.append({
                "path": path,
                "code": code,
                "status": NAME_STATUS.get(code, "modified"),
            })

        diff = diff_result["output"]
        truncated = False
        if max_diff_chars and len(diff) > max_diff_chars:
            diff = diff[:max_diff_chars].rstrip() + "\n... (diff truncated)"
            truncated = True

        return {
            "success": bool(names["ok"] and stat["ok"] and diff_result["ok"]),
            "repo_path": repo_root,
            "files": files,
            "file_count": len(files),
            "stat": stat["output"],
            "diff": diff,
            "diff_truncated": truncated,
            "errors": [
                result["error"]
                for result in (names, stat, diff_result)
                if not result["ok"] and result["error"]
            ],
        }

    # -------------------------------------------------------------------------
    # Commit message normalization (50/72 rule)
    # -------------------------------------------------------------------------

    def _clean_commit_message(self, message: str) -> str:
        """
        Strip the decorations a model usually adds around a commit message.

        Code fences, surrounding quotes and leading/trailing blank lines are
        removed; the inner formatting (blank line between subject and body) is
        preserved.

        Args:
            message: Raw commit message (usually straight from the AI).

        Returns:
            Cleaned commit message, empty when nothing usable is left.

        Example:
            >>> engine._clean_commit_message('"fix: login timeout"')
            'fix: login timeout'
        """
        text = (message or "").replace("\r\n", "\n").strip()
        if not text:
            return ""

        lines = [
            line.rstrip()
            for line in text.split("\n")
            if not line.strip().startswith("```")
        ]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()

        cleaned = "\n".join(lines).strip()

        # Models often quote the whole message: "fix: ..." or 'fix: ...'
        if len(cleaned) >= 2 and cleaned[0] in "\"'`" and cleaned[-1] == cleaned[0]:
            cleaned = cleaned[1:-1].strip()

        return cleaned

    def _truncate_commit_line(self, text: str, limit: int) -> str:
        """
        Cut a commit message line at *limit* characters, never mid-word.

        Trailing punctuation is removed too: a subject must not end with a
        period, and a dangling comma/dash looks like a truncated line.

        Args:
            text: Line to truncate.
            limit: Maximum number of characters allowed.

        Returns:
            The line unchanged when it fits, a word-aligned cut otherwise.

        Example:
            >>> engine._truncate_commit_line("word " * 20, 50)
            'word word word word word word word word word word'
        """
        text = (text or "").strip()
        if len(text) <= limit:
            return text

        cut = text[:limit]
        space = cut.rfind(" ")
        if space > 0:
            cut = cut[:space]
        cut = cut.rstrip(" ,.;:-")
        return cut or text[:limit].strip()

    def _wrap_commit_body(
        self, body_lines: List[str], width: int = COMMIT_BODY_LIMIT
    ) -> List[str]:
        """
        Re-wrap the body of a commit message so every line fits *width* chars.

        Blank lines are kept as paragraph separators and list markers
        (``- ``, ``* ``, ``1. ``) are kept as a hanging indent, so wrapped items
        stay aligned.

        Args:
            body_lines: Body lines of the commit message.
            width: Maximum line width (72 by the 50/72 rule).

        Returns:
            Wrapped body lines, without trailing blank lines.

        Example:
            >>> lines = engine._wrap_commit_body(["- " + "word " * 40])
            >>> all(len(line) <= 72 for line in lines)
            True
        """
        wrapped: List[str] = []

        for line in body_lines:
            text = (line or "").strip()
            if not text:
                if wrapped and wrapped[-1] != "":
                    wrapped.append("")
                continue

            marker = LIST_MARKER_PATTERN.match(text)
            prefix = marker.group(1) if marker else ""
            content = text[len(prefix):] if prefix else text

            chunks = textwrap.wrap(
                content,
                width=max(10, width - len(prefix)),
                break_long_words=False,
                break_on_hyphens=False,
            ) or [""]

            wrapped.append(prefix + chunks[0])
            wrapped += [" " * len(prefix) + chunk for chunk in chunks[1:]]

        while wrapped and wrapped[-1] == "":
            wrapped.pop()

        return wrapped

    def normalize_commit_message(
        self,
        message: str,
        subject_limit: int = COMMIT_SUBJECT_LIMIT,
        body_limit: int = COMMIT_BODY_LIMIT,
    ) -> dict:
        """
        Normalize a commit message to the 50/72 rule.

        The first line becomes the subject (truncated to *subject_limit*
        characters at a word boundary) and the remaining lines become the body,
        re-wrapped to *body_limit* characters and separated by a blank line.

        Args:
            message: Raw commit message.
            subject_limit: Maximum subject length (50 by the 50/72 rule).
            body_limit: Maximum body line width (72 by the 50/72 rule).

        Returns:
            Dict with 'title', 'body' and 'message' (the full normalized
            message). Every value is empty when the input has no content.

        Example:
            >>> engine.normalize_commit_message("fix: login timeout")
            {'title': 'fix: login timeout', 'body': '',
             'message': 'fix: login timeout'}
        """
        cleaned = self._clean_commit_message(message)
        if not cleaned:
            return {"title": "", "body": "", "message": ""}

        lines = cleaned.split("\n")
        title = self._truncate_commit_line(lines[0], subject_limit)
        body = "\n".join(self._wrap_commit_body(lines[1:], width=body_limit))

        full_message = f"{title}\n\n{body}".strip() if body else title
        return {"title": title, "body": body, "message": full_message}

    # -------------------------------------------------------------------------
    # AI commit message generation
    # -------------------------------------------------------------------------

    def _commit_message_prompt(
        self, staged: dict, hint: str = "", include_body: bool = True
    ) -> str:
        """
        Build the AI prompt used to write the commit message.

        Args:
            staged: Result of :meth:`get_staged_changes`.
            hint: Optional user instructions (intent, issue reference...).
            include_body: Ask only for the subject line when False.

        Returns:
            Full prompt string, with the staged file list and patch.
        """
        files = "\n".join(
            f"{file['status']}: {file['path']}"
            for file in staged.get("files", [])
        )
        body_rule = (
            "- Add a blank line and a body explaining what changed and why;\n"
            "  never restate the diff line by line."
            if include_body
            else "- Return only the subject line, without body."
        )
        hint = (hint or "").strip()
        instructions = (
            f"\n<user_instructions>\n{hint}\n</user_instructions>\n"
            if hint
            else ""
        )

        return f"""You write git commit messages for a software repository.

Write the commit message for the staged changes below and follow the 50/72 rule:
- Subject: imperative mood ("add", "fix", "refactor"...), no trailing period,
  maximum {COMMIT_SUBJECT_LIMIT} characters.
{body_rule}
- Maximum {COMMIT_BODY_LIMIT} characters per body line.
{instructions}
<staged_changes>
{files}
</staged_changes>

<diff>
{staged.get("diff", "")}
</diff>

Return only the commit message: no fences, no quotes, no explanations.
"""

    def _fallback_commit_message(self, staged: dict) -> str:
        """
        Build a commit message without AI, from the staged file names.

        Used when the AI is unavailable or returns an unusable answer, so the
        commit panel always has something to show (the user can edit it).

        Args:
            staged: Result of :meth:`get_staged_changes`.

        Returns:
            Normalized commit message following the 50/72 rule, empty when
            nothing is staged.

        Example:
            >>> engine._fallback_commit_message({"files": [{"path": "app.py"}]})
            'chore: update app.py'
        """
        files = staged.get("files") or []
        count = len(files)
        if not count:
            return ""

        if count == 1:
            title = f"chore: update {os.path.basename(files[0]['path'])}"
        else:
            title = f"chore: update {count} files"

        return self.normalize_commit_message(title)["message"]

    async def generate_commit_message(
        self,
        hint: Optional[str] = None,
        include_body: bool = True,
        max_diff_chars: int = COMMIT_MESSAGE_MAX_DIFF_CHARS,
    ) -> dict:
        """
        Generate a commit message for the staged files using AI.

        The staged patch is summarized (truncated to *max_diff_chars*
        characters) and sent to the project LLM, which writes the message. The
        answer is normalized to the **50/72 rule**: at most 50 characters on the
        subject line and at most 72 characters per body line.

        When the AI fails or returns nothing usable, a plain message built from
        the staged file names is returned with 'fallback' set to True, so the
        user always gets an editable draft.

        Args:
            hint: Optional user instructions (intent, issue id...).
            include_body: Ask for a body or only for the subject line.
            max_diff_chars: Maximum characters of the staged diff in the prompt.

        Returns:
            Dict with 'success', 'title', 'body', 'message', 'fallback' (True
            when the AI answer could not be used), 'files', 'file_count',
            'stat', 'diff_truncated' and 'errors'. 'success' is False only when
            there is nothing staged.

        Example:
            >>> result = await engine.generate_commit_message()
            >>> result["title"]
            'add commit message endpoint'
            >>> result["fallback"]
            False
        """
        staged = self.get_staged_changes(max_diff_chars=max_diff_chars)
        result = {
            "success": False,
            "title": "",
            "body": "",
            "message": "",
            "fallback": False,
            "files": staged["files"],
            "file_count": staged["file_count"],
            "stat": staged["stat"],
            "diff_truncated": staged["diff_truncated"],
            "errors": list(staged["errors"]),
        }

        if not staged["files"]:
            result["errors"].append(
                "No staged changes: stage the files to commit before generating "
                "the message"
            )
            return result

        raw_message = ""
        ai_error = ""
        get_ai = getattr(self.session, "get_ai", None)

        if not callable(get_ai):
            ai_error = "AI is not available in this session"
        else:
            try:
                ai = get_ai()
                messages = await ai.a_chat(
                    prompt=self._commit_message_prompt(
                        staged, hint=hint or "", include_body=include_body
                    ),
                    headers={"tags": "commit-message"},
                )
                raw_message = str(getattr(messages[-1], "content", "") or "")
            except Exception as ex:
                logger.exception("Error generating the commit message: %s", ex)
                ai_error = str(ex)

        normalized = self.normalize_commit_message(raw_message)
        if not normalized["message"]:
            logger.warning(
                "AI commit message unavailable (%s): using the file list fallback",
                ai_error or "empty answer",
            )
            result["fallback"] = True
            result["errors"].append(
                ai_error or "The AI returned an empty commit message"
            )
            normalized = self.normalize_commit_message(
                self._fallback_commit_message(staged)
            )

        result.update(
            title=normalized["title"],
            body=normalized["body"],
            message=normalized["message"],
            success=bool(normalized["message"]),
        )
        return result

# Made with ❤️ by codx-junior