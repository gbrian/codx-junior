"""
Profiles API router — visualize and edit what a profile has learned.

This router follows the project convention: every router lives in
``codx/junior/api/`` and exports a ``router`` attribute. It is discovered
automatically by :func:`codx.junior.api.discover_routers` (called from
``codx.junior.app.load_routers``) and mounted under ``/api``, so **no change is
needed in ``app.py``**.

Resources
---------
The profile is part of the path and the project comes from the request session
(the ``codx_path`` query parameter / ``x-codx-path`` header handled by the
session middleware) — it is never sent in a body:

GET    /api/profiles/{profile_name}/knowledge          rules + files + limits + can_write
GET    /api/profiles/{profile_name}/knowledge/files    read one knowledge file
PUT    /api/profiles/{profile_name}/knowledge/files    create/update a knowledge file
DELETE /api/profiles/{profile_name}/knowledge/files    delete a project-owned file
PUT    /api/profiles/{profile_name}/knowledge/rules    create/replace a rule (upsert by title)
DELETE /api/profiles/{profile_name}/knowledge/rules    forget a rule
POST   /api/profiles/{profile_name}/knowledge/promote  move rule <-> knowledge file

Conventions
-----------
* ``PUT`` creates **and** updates (upsert semantics);
* ``DELETE`` takes the resource name as a query parameter, because a DELETE body
  is not reliably forwarded by proxies and HTTP clients;
* request bodies only describe the resource (file name, content, title).

Storage (owned by :class:`~codx.junior.profiles.profile_manager.ProfileManager`)
-------------------------------------------------------------------------------
* **Rules** — short, always-relevant instructions stored as ``## <title>``
  blocks in ``<project .codx>/profiles/<Name>/enrich.md``. They are composed into
  the profile content, so they reach every chat prompt and cost tokens: they are
  addressed by title, so writing an existing title replaces it instead of adding
  a duplicate.
* **Knowledge files** — reference material under
  ``<project .codx>/profiles/<Name>/knowledge/**``, indexed and retrieved on
  demand. Base (``codx/junior/profiles/<Name>/knowledge``) and parent-project
  files are read-only from here.

Permissions
-----------
Reading is open to any project user; writing requires
:meth:`UserSecurityManager.can_manage_profile_knowledge` (codx-junior admin,
project admin or project ``knowledge_admin``) — the same rule the
``profile_learning`` tool applies, so the UI and the tool never disagree. The
overview reports ``can_write`` so a read-only client knows it up front.

Diagram
-------
```mermaid
flowchart LR
    Client -->|GET .../knowledge| Overview
    Client -->|GET .../knowledge/files| ReadFile
    Client -->|PUT .../knowledge/files| WriteFile
    Client -->|DELETE .../knowledge/files| DeleteFile
    Client -->|PUT .../knowledge/rules| UpsertRule
    Client -->|DELETE .../knowledge/rules| ForgetRule
    Client -->|POST .../knowledge/promote| Promote

    Overview --> ProfileManager
    ReadFile --> ProfileManager
    WriteFile --> ProfileManager
    DeleteFile --> ProfileManager
    UpsertRule --> ProfileManager
    ForgetRule --> ProfileManager
    Promote --> ProfileManager

    ProfileManager --> Disk[.codx/profiles/NAME/enrich.md + knowledge/**]
    ProfileManager --> Chain[base profile + parent projects - read-only]
```

Made with ❤️ by codx-junior
"""

import logging
import os

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from codx.junior.engine import CODXJuniorSession
from codx.junior.model.model import CodxUser
from codx.junior.profiles.profile_manager import MAX_RULE_CHARS, ProfileManager
from codx.junior.security.user_management import (
    UserSecurityManager,
    get_authenticated_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profiles", tags=["profiles"])

# Argument limits: the same bounds the ``profile_learning`` tool enforces, so a
# REST client cannot bypass them (an unbounded body would be written to disk and
# later injected into the model context).
MAX_FILE_NAME_CHARS = 500
MAX_FILE_CONTENT_CHARS = 200000
MAX_RULE_TITLE_CHARS = 200
MAX_QUERY_TEXT_CHARS = 200

# "rule_to_file": the rule is too long for the prompt -> indexed file.
# "file_to_rule": the file is really a short durable instruction.
PromoteDirection = Literal["rule_to_file", "file_to_rule"]


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class ApiModel(BaseModel):
    """
    Base for request bodies: trims strings before validating them.

    Trimming at validation time means ``min_length`` also rejects
    whitespace-only values, so " " can never be stored as a file name or a rule.
    """

    model_config = ConfigDict(str_strip_whitespace=True)


class KnowledgeFileWrite(ApiModel):
    """
    Body of ``PUT /api/profiles/{profile_name}/knowledge/files``.

    The profile is in the path and the project comes from the request session,
    so the body only describes the file.
    """

    file_name: str = Field(
        min_length=1,
        max_length=MAX_FILE_NAME_CHARS,
        description=(
            "Path relative to the profile knowledge folder (e.g. "
            "'guidelines/state.md'). '.md' is added when no extension is given."
        ),
    )
    content: str = Field(
        min_length=1,
        max_length=MAX_FILE_CONTENT_CHARS,
        description="Full file content (Markdown text)",
    )
    overwrite: bool = Field(
        default=False,
        description=(
            "Replace the file when it already exists. Read it first and only "
            "pass true when you know what you are replacing."
        ),
    )


class RuleWrite(ApiModel):
    """
    Body of ``PUT /api/profiles/{profile_name}/knowledge/rules``.

    Writing an existing title REPLACES that rule, so instructions are never
    duplicated and the prompt budget is not silently consumed. ``title`` is the
    identifier used later to update, forget or promote the rule.
    """

    title: str = Field(
        min_length=1,
        max_length=MAX_RULE_TITLE_CHARS,
        description="Rule title (identifier), e.g. 'Angular conventions'",
    )
    content: str = Field(
        min_length=1,
        max_length=MAX_RULE_CHARS,
        description=(
            "Instruction markdown. Keep it short and imperative: a rule is "
            f"injected into every chat and holds at most {MAX_RULE_CHARS} "
            "characters."
        ),
    )


class PromoteRequest(ApiModel):
    """Body of ``POST /api/profiles/{profile_name}/knowledge/promote``."""

    direction: PromoteDirection = Field(
        description=(
            "'rule_to_file' (rule too long for the prompt -> indexed file) or "
            "'file_to_rule' (file is really a short durable instruction)."
        )
    )
    title: Optional[str] = Field(
        default=None,
        max_length=MAX_RULE_TITLE_CHARS,
        description="Rule title (source of rule_to_file, target of file_to_rule)",
    )
    file_name: Optional[str] = Field(
        default=None,
        max_length=MAX_FILE_NAME_CHARS,
        description=(
            "Knowledge file path relative to its folder (target of "
            "rule_to_file, source of file_to_rule)"
        ),
    )
    keep_source: bool = Field(
        default=False,
        description="Keep the source after promoting (default: move it)",
    )


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProfileKnowledgeContext:
    """Validated (profile, permissions) pair, ready to hit :class:`ProfileManager`."""

    profile_name: str
    manager: ProfileManager
    can_write: bool


def get_project_session(request: Request) -> CODXJuniorSession:
    """
    Return the project session attached to the request by the middleware.

    The session middleware (``app.add_codx_junior_settings``) creates it from the
    ``codx_path`` query parameter or the ``x-codx-path`` header, so every route of
    this router is automatically project-scoped without asking the client for a
    project id.

    Args:
        request: The incoming HTTP request.

    Returns:
        The active :class:`CODXJuniorSession`.

    Raises:
        HTTPException: 400 when the request carries no project session.
    """
    session = getattr(request.state, "codx_junior_session", None)
    if session is None:
        raise HTTPException(
            status_code=400,
            detail="No project session for this request (codx_path is required)",
        )
    return session


def profile_knowledge_context(
    request: Request,
    profile_name: str = Path(
        min_length=1,
        description="Profile name (e.g. software_developer)",
    ),
    session: CODXJuniorSession = Depends(get_project_session),
    user: Optional[CodxUser] = Depends(get_authenticated_user),
) -> ProfileKnowledgeContext:
    """
    Resolve the profile of the request and the caller's write permission.

    Used as a FastAPI dependency, so this validation runs for every endpoint of
    the router exactly once per request (FastAPI caches ``Depends`` results).

    Args:
        request: The incoming HTTP request.
        profile_name: Profile name (path parameter).
        session: The active project session.
        user: The authenticated user (may be ``None``).

    Returns:
        ProfileKnowledgeContext with the ProfileManager and ``can_write``.

    Raises:
        HTTPException: 404 when the profile is unknown for this project.

    Example:
        GET /api/profiles/software_developer/knowledge?codx_path=/path/to/project
    """
    manager = ProfileManager(settings=session.settings)
    name = (profile_name or "").strip()

    if not name or not manager.profile_exists(name):
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown profile '{name}': it does not exist in this project, "
                "in a parent project or in the base profiles."
            ),
        )

    try:
        can_write = UserSecurityManager().can_manage_profile_knowledge(
            user=user, settings=session.settings
        )
    except Exception as ex:
        logger.warning(
            "Could not resolve profile knowledge permission for project '%s': %s",
            getattr(session.settings, "project_name", ""),
            ex,
        )
        can_write = False

    return ProfileKnowledgeContext(
        profile_name=name,
        manager=manager,
        can_write=can_write,
    )


def profile_knowledge_admin(
    context: ProfileKnowledgeContext = Depends(profile_knowledge_context),
) -> ProfileKnowledgeContext:
    """
    Dependency for write endpoints: they require knowledge administration rights.

    Args:
        context: Validated profile + permission pair (cached for this request).

    Returns:
        The same context, so handlers keep a single parameter.

    Raises:
        HTTPException: 403 when the user has no knowledge administration rights.
    """
    if context.can_write:
        return context
    raise HTTPException(
        status_code=403,
        detail=(
            "Only a project admin, a project knowledge admin or a codx-junior "
            "admin can change what a profile learns."
        ),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _relative(context: ProfileKnowledgeContext, path: Optional[str]) -> Optional[str]:
    """
    Render a server path relative to the project root.

    Args:
        context: Validated profile context (provides the project path).
        path: Absolute path.

    Returns:
        The relative path when it lives inside the project, else the original.
    """
    project_path = getattr(context.manager.settings, "abs_project_path", None)
    if not path or not project_path or not path.startswith(project_path):
        return path
    return os.path.relpath(path, project_path)


def _bad_request(ex: Exception) -> HTTPException:
    """
    Map a storage :class:`ValueError` to a 400 the client can display.

    ``ProfileManager`` raises ``ValueError`` for every invalid write (unknown
    profile, name escaping the folder, unsupported extension, existing file
    without ``overwrite``, rule too long, rule budget full...). The message is
    already actionable, so it is forwarded verbatim.

    Args:
        ex: The caught ValueError.

    Returns:
        The HTTPException to raise.
    """
    return HTTPException(status_code=400, detail=str(ex))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/{profile_name}/knowledge",
    summary="What a profile has learned for the project",
)
def get_profile_knowledge(
    context: ProfileKnowledgeContext = Depends(profile_knowledge_context),
) -> Dict[str, Any]:
    """
    Return the knowledge overview of a profile: rules, files and limits.

    Every path in the payload is relative to the project root and ``can_write``
    tells the client whether the write actions must be disabled.

    Args:
        context: Validated profile + permission pair.

    Returns:
        Overview produced by ``ProfileManager.profile_knowledge_overview`` plus
        relative paths and ``can_write``.

    Example:
        GET /api/profiles/software_developer/knowledge?codx_path=/my/project
    """
    overview = context.manager.profile_knowledge_overview(
        profile_name=context.profile_name
    )

    logger.info(
        "get_profile_knowledge: profile='%s' project='%s' rules=%d files=%d can_write=%s",
        context.profile_name,
        getattr(context.manager.settings, "project_name", ""),
        len(overview.get("rules", [])),
        len(overview.get("knowledge_files", [])),
        context.can_write,
    )

    return {
        **overview,
        "rules": [
            {**rule, "path": _relative(context, rule.get("path"))}
            for rule in overview.get("rules", [])
        ],
        "knowledge_files": [
            {**entry, "path": _relative(context, entry.get("path"))}
            for entry in overview.get("knowledge_files", [])
        ],
        "rules_file": _relative(context, overview.get("rules_file")),
        "knowledge_folder": _relative(context, overview.get("knowledge_folder")),
        "can_write": context.can_write,
    }


@router.get(
    "/{profile_name}/knowledge/files",
    summary="Read a profile knowledge file",
)
def read_knowledge_file(
    file_name: str = Query(
        min_length=1,
        max_length=MAX_FILE_NAME_CHARS,
        description="Path relative to the knowledge folder",
    ),
    context: ProfileKnowledgeContext = Depends(profile_knowledge_context),
) -> Dict[str, Any]:
    """
    Return the content of one knowledge file (base or any project level).

    Args:
        file_name: Path relative to the knowledge folder.
        context: Validated profile + permission pair.

    Returns:
        ``{file, source, path, content}``.

    Raises:
        HTTPException: 404 when the file does not exist in the profile chain.
    """
    entry = context.manager._resolve_knowledge_file(
        profile_name=context.profile_name, file_name=file_name
    )
    if not entry:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Knowledge file '{file_name}' not found for profile "
                f"'{context.profile_name}'."
            ),
        )

    return {
        "file": entry["file"],
        "source": entry["source"],
        "path": _relative(context, entry["path"]),
        "content": context.manager.read_profile_knowledge(
            profile_name=context.profile_name, file_name=entry["file"]
        ),
    }


@router.put(
    "/{profile_name}/knowledge/files",
    summary="Create or update a profile knowledge file",
)
def write_knowledge_file(
    payload: KnowledgeFileWrite,
    context: ProfileKnowledgeContext = Depends(profile_knowledge_admin),
) -> Dict[str, Any]:
    """
    Create or update a knowledge file in the project of the request.

    The file always lands in the CURRENT project; base and parent projects keep
    their own files (and stay read-only from here).

    Args:
        payload: File name, content and overwrite flag.
        context: Validated profile context with write permission.

    Returns:
        ``{file, path}`` with the path relative to the project root.

    Raises:
        HTTPException: 400 on an invalid write (e.g. the file exists and
            ``overwrite`` is false), 403 without knowledge administration rights.
    """
    try:
        path = context.manager.save_profile_knowledge(
            profile_name=context.profile_name,
            file_name=payload.file_name,
            content=payload.content,
            overwrite=payload.overwrite,
        )
    except ValueError as ex:
        raise _bad_request(ex)

    knowledge_path = context.manager.profile_knowledge_path(context.profile_name)
    logger.info(
        "write_knowledge_file: profile='%s' file='%s' overwrite=%s",
        context.profile_name,
        payload.file_name,
        payload.overwrite,
    )
    return {
        "file": os.path.relpath(path, knowledge_path),
        "path": _relative(context, path),
    }


@router.delete(
    "/{profile_name}/knowledge/files",
    summary="Delete a project-owned profile knowledge file",
)
def delete_knowledge_file(
    file_name: str = Query(
        min_length=1,
        max_length=MAX_FILE_NAME_CHARS,
        description="Path relative to the knowledge folder",
    ),
    context: ProfileKnowledgeContext = Depends(profile_knowledge_admin),
) -> Dict[str, Any]:
    """
    Delete a knowledge file owned by the project of the request.

    Base and parent project files are read-only, so only files stored in this
    project can be deleted (``ProfileManager`` enforces it).

    Args:
        file_name: Path relative to the knowledge folder.
        context: Validated profile context with write permission.

    Returns:
        ``{file, path}``.

    Raises:
        HTTPException: 400 when the file does not belong to this project,
            403 without knowledge administration rights.
    """
    try:
        path = context.manager.delete_profile_knowledge(
            profile_name=context.profile_name, file_name=file_name
        )
    except ValueError as ex:
        raise _bad_request(ex)

    logger.info(
        "delete_knowledge_file: profile='%s' file='%s'",
        context.profile_name,
        file_name,
    )
    return {
        "file": file_name,
        "path": _relative(context, path),
    }


@router.put(
    "/{profile_name}/knowledge/rules",
    summary="Learn (create or replace) a profile rule",
)
def write_rule(
    payload: RuleWrite,
    context: ProfileKnowledgeContext = Depends(profile_knowledge_admin),
) -> Dict[str, Any]:
    """
    Upsert a rule in the project's profile enrichment (``enrich.md``).

    Rules are injected into every chat prompt, so they are short and addressed by
    title: writing an existing title replaces it instead of adding a duplicate.

    Args:
        payload: Rule title and content.
        context: Validated profile context with write permission.

    Returns:
        ``{title, created, rules, path}``.

    Raises:
        HTTPException: 400 on invalid input (too long, rule budget full),
            403 without knowledge administration rights.
    """
    try:
        result = context.manager.upsert_profile_rule(
            profile_name=context.profile_name,
            title=payload.title,
            text=payload.content,
        )
    except ValueError as ex:
        raise _bad_request(ex)

    logger.info(
        "write_rule: profile='%s' title='%s' created=%s",
        context.profile_name,
        result["title"],
        result["created"],
    )
    return {
        "title": result["title"],
        "created": result["created"],
        "rules": result["rules"],
        "path": _relative(context, result["path"]),
    }


@router.delete(
    "/{profile_name}/knowledge/rules",
    summary="Forget a profile rule",
)
def delete_rule(
    title: str = Query(
        min_length=1,
        max_length=MAX_QUERY_TEXT_CHARS,
        description="Rule title",
    ),
    context: ProfileKnowledgeContext = Depends(profile_knowledge_admin),
) -> Dict[str, Any]:
    """
    Remove a rule learned by the project of the request.

    Inherited rules (parent projects, base profile) are read-only: they can only
    be removed from the level that learned them.

    Args:
        title: Rule title.
        context: Validated profile context with write permission.

    Returns:
        ``{title, path}``.

    Raises:
        HTTPException: 400 when the rule was not learned here, 403 without
            knowledge administration rights.
    """
    try:
        path = context.manager.delete_profile_rule(
            profile_name=context.profile_name, title=title
        )
    except ValueError as ex:
        raise _bad_request(ex)

    logger.info(
        "delete_rule: profile='%s' title='%s'", context.profile_name, title
    )
    return {
        "title": title,
        "path": _relative(context, path),
    }


@router.post(
    "/{profile_name}/knowledge/promote",
    summary="Move content between rules and knowledge files",
)
def promote_knowledge(
    payload: PromoteRequest,
    context: ProfileKnowledgeContext = Depends(profile_knowledge_admin),
) -> Dict[str, Any]:
    """
    Promote a rule to a knowledge file (or the other way around).

    ``rule_to_file`` is the "this rule is too long for the prompt" action;
    ``file_to_rule`` promotes a short file into an always-injected instruction.

    Args:
        payload: Direction and source/target of the promotion.
        context: Validated profile context with write permission.

    Returns:
        ``{direction, profile, title, file, path, rule_deleted|file_deleted}``.

    Raises:
        HTTPException: 400 on invalid input, 403 without knowledge
            administration rights.
    """
    try:
        if payload.direction == "rule_to_file":
            if not payload.title:
                raise ValueError("title is required for rule_to_file")
            result = context.manager.promote_profile_rule_to_knowledge(
                profile_name=context.profile_name,
                title=payload.title,
                file_name=payload.file_name,
                delete_rule=not payload.keep_source,
            )
            logger.info(
                "promote_knowledge: profile='%s' rule '%s' -> file '%s'",
                context.profile_name,
                result["title"],
                result["file"],
            )
            return {
                "direction": payload.direction,
                "profile": context.profile_name,
                "title": result["title"],
                "file": result["file"],
                "path": _relative(context, result["path"]),
                "rule_deleted": result["rule_deleted"],
            }

        if not payload.file_name:
            raise ValueError("file_name is required for file_to_rule")
        result = context.manager.promote_profile_knowledge_to_rule(
            profile_name=context.profile_name,
            file_name=payload.file_name,
            title=payload.title,
            delete_file=not payload.keep_source,
        )
        logger.info(
            "promote_knowledge: profile='%s' file '%s' -> rule '%s'",
            context.profile_name,
            payload.file_name,
            result["title"],
        )
        return {
            "direction": payload.direction,
            "profile": context.profile_name,
            "title": result["title"],
            "file": payload.file_name,
            "path": _relative(context, result["path"]),
            "file_deleted": result["file_deleted"],
        }
    except ValueError as ex:
        raise _bad_request(ex)

# Made with ❤️ by codx-junior