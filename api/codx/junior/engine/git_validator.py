"""
AI validation of project changes.

Extends :class:`codx.junior.engine.git_commit_message.GitCommitMessageEngine`
with the pieces behind the git view's **Validator** section:

- :meth:`GitValidatorEngine.get_validation_context`: the changed files and the
  profiles associated with them. The default selection is derived with
  :meth:`ProfileManager.get_file_profiles_by_file_path`, so a Vue change starts
  with the Vue profile, a Python change with the Python one, and so on.
- :meth:`GitValidatorEngine.validate_changes`: sends the change set and the
  selected profile content to the project LLM and returns its Markdown review.

The section can validate the uncommitted working tree (the default) or two
refs. It never writes to the repository: validation is a read-only review.

```mermaid
sequenceDiagram
    participant UI as Validator section
    participant API as git router
    participant Engine as GitValidatorEngine
    participant PM as ProfileManager
    participant AI as LLM

    UI->>API: GET /api/git/repo/validate/context?source=local
    API->>Engine: get_validation_context()
    Engine->>Engine: get_local_changes()
    Engine->>PM: list_all_profiles()
    Engine->>PM: get_file_profiles_by_file_path(file)
    Engine-->>API: files + profiles + defaults
    UI->>API: POST /api/git/repo/validate { profiles }
    API->>Engine: validate_changes(profiles)
    Engine->>AI: profile context + diff + report template
    AI-->>Engine: Markdown review
    Engine-->>API: review + files + profiles
```

Made with ❤️ by codx-junior
"""

import logging
import os

from typing import Dict, List, Optional, Tuple

from codx.junior.engine.git_commit_message import GitCommitMessageEngine

logger = logging.getLogger(__name__)

# Maximum characters of the patch sent to the model. The diff of a large local
# change set can be huge; the review must stay inside the prompt budget.
VALIDATOR_MAX_DIFF_CHARS = 40000

# Maximum changed files listed in the prompt. The complete list is still
# returned to the UI; only the prompt is bounded (a generated folder can hold
# thousands of untracked files).
VALIDATOR_MAX_PROMPT_FILES = 200

# Profiles used when no changed file matches a `file_match` profile.
VALIDATOR_FALLBACK_PROFILES = ("reviewer", "pr_review", "agent_work_reviewer")

# Status name used by the validation payloads.
STATUS_BY_CODE = {
    "?": "untracked",
    "A": "added",
    "M": "modified",
    "D": "deleted",
    "R": "renamed",
    "C": "copied",
    "T": "typechange",
    "U": "conflict",
}

CODE_BY_STATUS = {
    "untracked": "?",
    "new": "A",
    "added": "A",
    "deleted": "D",
    "renamed": "R",
    "copied": "C",
    "typechange": "T",
    "conflict": "U",
    "modified": "M",
}


class GitValidatorEngine(GitCommitMessageEngine):
    """
    Engine for the Validator section: change context, profile defaults and the
    AI review itself.
    """

    # -------------------------------------------------------------------------
    # Change set and profile context
    # -------------------------------------------------------------------------

    def _changes_for_source(
        self,
        source: str = "local",
        from_branch: Optional[str] = None,
        to_branch: Optional[str] = None,
        paths: Optional[List[str]] = None,
    ) -> dict:
        """
        Return the change payload for the selected source.

        Args:
            source: ``local`` (uncommitted changes) or ``branch`` (two refs).
            from_branch: Base branch for local changes, or the source branch.
            to_branch: Target branch when comparing refs.
            paths: Optional list of local files to restrict the review to.

        Returns:
            Payload shaped like :meth:`GitWorkspaceEngine.get_local_changes` /
            :meth:`GitEngine.get_repo_changes`.

        Raises:
            ValueError: When a branch comparison misses one of the refs.
        """
        source = (source or "local").strip().lower()

        if source == "branch":
            if not (from_branch or "").strip() or not (to_branch or "").strip():
                raise ValueError(
                    "from_branch and to_branch are required to validate a branch comparison"
                )
            return self.get_repo_changes(
                from_branch=from_branch, to_branch=to_branch
            )

        # Local changes: compare the working tree against the current branch (or
        # the explicitly requested base branch).
        base_branch = (from_branch or "").strip()
        if not base_branch or base_branch.lower() == "local":
            base_branch = (
                self._sanitize_branch_name(self.get_project_current_branch())
                or "HEAD"
            )
        return self.get_local_changes(base_ref=base_branch, paths=paths)

    def _file_entries(self, changes: dict) -> List[dict]:
        """
        Normalize the changed files of a review payload.

        Args:
            changes: Payload returned by ``get_local_changes`` / ``get_repo_changes``.

        Returns:
            List of ``{path, code, status, additions, deletions, staged,
            unstaged}`` entries.
        """
        pr_status = {
            entry.get("file_name"): entry.get("status")
            for entry in (changes.get("pr_details") or [])
            if entry.get("file_name")
        }

        files: List[dict] = []
        for path, entry in (changes.get("branch_file_and_commits") or {}).items():
            entry = entry or {}
            diff = entry.get("diff") or ""
            counts = self._count_diff_lines(diff)
            code = str(entry.get("code") or "").strip()
            status = str(entry.get("status") or "").strip()
            if not status:
                status = pr_status.get(path, "") or STATUS_BY_CODE.get(code, "modified")
            if not code:
                code = CODE_BY_STATUS.get(status, "M")
            files.append({
                "path": path,
                "code": code,
                "status": status,
                "additions": counts["additions"],
                "deletions": counts["deletions"],
                "staged": bool(entry.get("staged")),
                "unstaged": bool(entry.get("unstaged")),
            })
        return files

    @staticmethod
    def _profile_summary(profile) -> dict:
        """Return the lightweight profile entry shown by the Validator UI."""
        return {
            "name": getattr(profile, "name", "") or "",
            "description": getattr(profile, "description", "") or "",
            "category": getattr(profile, "category", "") or "",
            "avatar": getattr(profile, "avatar", "") or "",
            "file_match": getattr(profile, "file_match", "") or "",
            "use_knowledge": bool(getattr(profile, "use_knowledge", False)),
        }

    def _default_profiles_for_files(
        self, file_paths: List[str], profiles: List
    ) -> Tuple[List[str], str]:
        """
        Resolve the default profiles from the changed files.

        The association is the profile manager's: every changed file is matched
        against each profile ``file_match`` regex. When no profile matches, the
        validator profiles (``agent-validator``) and the well-known reviewer
        profiles are used as a fallback.

        Args:
            file_paths: Changed file paths (repo-relative or absolute).
            profiles: Pre-loaded profile list (avoids one chain scan per file).

        Returns:
            Tuple ``(default_profile_names, source)`` where source is ``files``,
            ``validator`` or an empty string.
        """
        if not file_paths or not profiles:
            return [], ""

        manager = self.session.get_profile_manager()
        project_path = getattr(self.settings, "abs_project_path", "") or ""
        matched: Dict[str, object] = {}

        for path in dict.fromkeys(file_paths):
            absolute = path if os.path.isabs(path) else os.path.join(project_path, path)
            for profile in manager.get_file_profiles_by_file_path(
                file_path=absolute, profiles=profiles
            ):
                if profile and getattr(profile, "name", ""):
                    matched[profile.name] = profile

        if matched:
            return sorted(matched), "files"

        validators = [
            profile for profile in profiles
            if str(getattr(profile, "category", "") or "").lower()
            in ("agent-validator", "validator")
        ]
        if not validators:
            by_name = {getattr(p, "name", ""): p for p in profiles}
            validators = [
                by_name[name] for name in VALIDATOR_FALLBACK_PROFILES if name in by_name
            ]

        if validators:
            return [validators[0].name], "validator"
        return [], ""

    def _build_context(
        self,
        source: str = "local",
        from_branch: Optional[str] = None,
        to_branch: Optional[str] = None,
        paths: Optional[List[str]] = None,
    ) -> Tuple[dict, dict, List]:
        """
        Build the validation context and return it with the raw change payload.

        Returns:
            Tuple ``(context, changes, all_profiles)``. The context is safe to
            send to the client (it carries no patch), while ``changes`` keeps the
            diff used to build the prompt.
        """
        changes = self._changes_for_source(
            source=source,
            from_branch=from_branch,
            to_branch=to_branch,
            paths=paths,
        )
        files = self._file_entries(changes)

        manager = self.session.get_profile_manager()
        all_profiles = manager.list_all_profiles()
        default_profiles, defaults_source = self._default_profiles_for_files(
            [entry["path"] for entry in files], all_profiles
        )

        summaries = sorted(
            (self._profile_summary(profile) for profile in all_profiles if profile),
            key=lambda profile: (
                (profile.get("category") or "").lower(),
                (profile.get("name") or "").lower(),
            ),
        )

        context = {
            "success": True,
            "source": (source or "local").strip().lower(),
            "base_branch": changes.get("base_branch") or "",
            "from_branch": changes.get("from_branch") or from_branch or "",
            "to_branch": changes.get("to_branch") or to_branch or "",
            "compare_type": changes.get("compare_type") or "local",
            "repo_path": changes.get("repo_path") or "",
            "stat": changes.get("stat") or "",
            "files": files,
            "file_count": len(files),
            "profiles": summaries,
            "profile_count": len(summaries),
            "default_profiles": default_profiles,
            "default_profiles_source": defaults_source,
            "errors": [],
        }
        return context, changes, all_profiles

    def get_validation_context(
        self,
        source: str = "local",
        from_branch: Optional[str] = None,
        to_branch: Optional[str] = None,
        paths: Optional[List[str]] = None,
    ) -> dict:
        """
        Return the Validator context: changed files plus the profile selection.

        Args:
            source: ``local`` (uncommitted changes) or ``branch``.
            from_branch: Base branch for local changes, or the source branch.
            to_branch: Target branch for a branch comparison.
            paths: Optional local file paths to restrict the review to.

        Returns:
            Dict with 'success', 'source', branch labels, 'stat', 'files',
            'profiles' (lightweight entries), 'default_profiles' and
            'default_profiles_source'.

        Example:
            >>> context = engine.get_validation_context()
            >>> context["default_profiles_source"]
            'files'
        """
        context, _changes, _profiles = self._build_context(
            source=source,
            from_branch=from_branch,
            to_branch=to_branch,
            paths=paths,
        )
        return context

    # -------------------------------------------------------------------------
    # Prompt and AI review
    # -------------------------------------------------------------------------

    def _validation_prompt(
        self,
        changes: dict,
        files: List[dict],
        profiles: List,
        source: str,
        base_branch: str,
        instructions: str = "",
        max_diff_chars: int = VALIDATOR_MAX_DIFF_CHARS,
    ) -> Tuple[str, bool]:
        """
        Build the review prompt and report whether the patch was truncated.

        Args:
            changes: Change payload (carries the diff).
            files: Normalized file entries.
            profiles: Profiles selected by the user.
            source: ``local`` or ``branch``.
            base_branch: Branch the changes are compared against.
            instructions: Optional reviewer instructions from the user.
            max_diff_chars: Patch budget (0 disables the truncation).

        Returns:
            Tuple ``(prompt, diff_truncated)``.
        """
        diff = changes.get("diff") or ""
        truncated = False
        if max_diff_chars and len(diff) > max_diff_chars:
            diff = diff[:max_diff_chars].rstrip() + "\n... (diff truncated)"
            truncated = True

        prompt_files = files[:VALIDATOR_MAX_PROMPT_FILES]
        file_lines = "\n".join(
            f"- [{entry['status']}] {entry['path']} "
            f"(+{entry['additions']}/-{entry['deletions']})"
            for entry in prompt_files
        ) or "- (no files)"
        if len(files) > len(prompt_files):
            file_lines += (
                f"\n- ... and {len(files) - len(prompt_files)} more file(s) "
                "(the patch below is truncated too)"
            )

        profile_sections = []
        for profile in profiles:
            name = getattr(profile, "name", "") or "profile"
            content = (
                getattr(profile, "content", None)
                or getattr(profile, "parsed_content", None)
                or ""
            )
            if str(content).strip():
                profile_sections.append(
                    f"### Reviewer profile: {name}\n{str(content).strip()}"
                )
        profile_text = "\n\n".join(profile_sections)
        profile_block = f"\n## Review profiles\n{profile_text}\n" if profile_text else ""

        if source == "local":
            source_text = (
                "uncommitted local changes compared against "
                f"`{base_branch or 'HEAD'}`"
            )
        else:
            from_label = changes.get("from_branch") or "HEAD"
            to_label = changes.get("to_branch") or base_branch or "HEAD"
            source_text = f"changes between `{from_label}` and `{to_label}`"

        instructions_text = (
            f"\n## Extra instructions from the user\n{instructions.strip()}\n"
            if (instructions or "").strip()
            else ""
        )

        prompt = f"""You are a meticulous software reviewer. Validate the project changes described below and explain your findings to the user.

## Review focus
Review **{source_text}**. Use the reviewer profiles as the review rules/persona. Only report problems you can support with the patch: never invent files, lines or behaviour that the diff does not show. Focus on correctness, regressions, security, performance, tests and maintainability. Be concise but specific.
{profile_block}
## Changed files
{file_lines}

## Change statistics
{changes.get('stat') or 'n/a'}
{instructions_text}
## Patch
```diff
{diff}
```

## Required report format
Return clean Markdown, with no preamble or closing chatter, using these sections:

## Summary
A short paragraph describing what changed and the overall risk.

## Findings
A table or list with: severity (blocker / major / minor / nit), file and line, the problem, and a concrete recommendation. Say explicitly when there are no findings.

## Per-file review
One subsection per changed file. Mention what changed and whether the change is safe.

## Risks
Potential regressions, missing tests, compatibility or security concerns.

## Verdict
One of **APPROVED**, **APPROVED WITH COMMENTS** or **CHANGES REQUESTED**, followed by the next steps.
"""
        return prompt, truncated

    async def validate_changes(
        self,
        profiles: Optional[List[str]] = None,
        source: str = "local",
        from_branch: Optional[str] = None,
        to_branch: Optional[str] = None,
        paths: Optional[List[str]] = None,
        instructions: str = "",
        max_diff_chars: int = VALIDATOR_MAX_DIFF_CHARS,
    ) -> dict:
        """
        Run the AI review of the selected changes.

        Args:
            profiles: Profile names selected by the user. Empty means "use the
                profiles associated with the changed files".
            source: ``local`` or ``branch``.
            from_branch: Base branch (local) or source branch.
            to_branch: Target branch for a branch comparison.
            paths: Optional local file paths to restrict the review to.
            instructions: Extra reviewer instructions.
            max_diff_chars: Prompt budget for the patch (0 disables it).

        Returns:
            Dict with 'success', 'review' (Markdown), 'files', 'profiles'
            (used names), 'profile_details', 'source', 'base_branch',
            'diff_truncated', 'errors' and 'fallback' (True when the AI could
            not answer; 'review' is then empty).

        Example:
            >>> result = await engine.validate_changes(profiles=["reviewer"])
            >>> result["success"]
            True
        """
        context, changes, all_profiles = self._build_context(
            source=source,
            from_branch=from_branch,
            to_branch=to_branch,
            paths=paths,
        )

        result = {
            "success": False,
            "review": "",
            "fallback": False,
            "source": context["source"],
            "base_branch": context["base_branch"],
            "from_branch": context["from_branch"],
            "to_branch": context["to_branch"],
            "files": context["files"],
            "file_count": context["file_count"],
            "stat": context["stat"],
            "profiles": [],
            "profile_details": [],
            "default_profiles": context["default_profiles"],
            "diff_truncated": False,
            "errors": [],
        }

        if not context["files"]:
            result["errors"].append("No changes to validate")
            return result

        requested = [name.strip() for name in (profiles or []) if (name or "").strip()]
        if not requested:
            requested = list(context["default_profiles"])

        by_name = {
            getattr(profile, "name", ""): profile for profile in all_profiles
        }
        selected = [by_name[name] for name in requested if name in by_name]
        missing = [name for name in requested if name not in by_name]
        if missing:
            result["errors"].append(
                f"Unknown profile(s): {', '.join(missing)}"
            )

        result["profiles"] = [profile.name for profile in selected]
        result["profile_details"] = [
            self._profile_summary(profile) for profile in selected
        ]

        prompt, truncated = self._validation_prompt(
            changes=changes,
            files=context["files"],
            profiles=selected,
            source=context["source"],
            base_branch=context["base_branch"],
            instructions=instructions or "",
            max_diff_chars=max_diff_chars,
        )
        result["diff_truncated"] = truncated

        get_ai = getattr(self.session, "get_ai", None)
        if not callable(get_ai):
            result["fallback"] = True
            result["errors"].append("AI is not available in this session")
            return result

        try:
            ai = get_ai()
            messages = await ai.a_chat(
                prompt=prompt, headers={"tags": "git-validator"}
            )
            review = str(getattr(messages[-1], "content", "") or "").strip()
        except Exception as ex:
            logger.exception("Error validating the git changes: %s", ex)
            result["fallback"] = True
            result["errors"].append(str(ex) or "AI validation failed")
            return result

        if not review:
            result["fallback"] = True
            result["errors"].append("The AI returned an empty review")
            return result

        result["review"] = review
        result["success"] = True
        return result


# Made with ❤️ by codx-junior
