"""
The always-present company assistant.

A company is a **manager-oriented** product shell: every screen has the
codx-junior assistant available, and the assistant — not a modal dialog — is the
place where settings and team management happen.

Why a company-native assistant
------------------------------
The project chat already exposes the ``company_management`` tool to the AI
profiles, but it needs an active project and a full chat turn. A manager working
in the company shell may not have a project open, needs an answer immediately
and must be able to provide structured data (a new user, a team roster, the
company settings) without leaving the company screen.

This module is the deterministic operating layer behind the assistant panel:

* it reads the **same company document** the screen renders,
* it performs the operations through :class:`~.manager.CompanyManager` (so
  validation, journaling and dispatch are identical to the API/tools),
* it enforces the company roles (admins add users, managers manage the work),
* it **returns form schemas** instead of opening dialogs; the UI renders those
  forms inside the assistant window and posts the values back to this endpoint.

The responses are LLM-shaped on purpose (markdown ``reply`` + ``suggestions`` +
optional ``form``) so a future profile-backed implementation can replace the
intent parser without changing the UI contract.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import os
import re
import secrets

from typing import Any, Dict, Iterable, List, Optional

from codx.junior.model.user import (
    COMPANY_ROLE_MEMBER,
    COMPANY_ROLES,
)
from .language import detect_language, language_name, resolve_language
from .profile_advisor import (
    ROLES,
    TEAM_PRESETS,
    profile_content,
    recommend as recommend_profiles,
)

logger = logging.getLogger(__name__)


#: Forms the assistant can render in its own window.
FORM_ADD_USER = "add_user"
FORM_EDIT_COMPANY = "edit_company"
FORM_CREATE_TEAM = "create_team"
FORM_ADD_TEAM_MEMBER = "add_team_member"

#: Suggestions shown as chips under the assistant input, per company view.
VIEW_SUGGESTIONS: Dict[str, List[str]] = {
    "overview": [
        "What needs my attention?",
        "How is our budget?",
        "I need a team",
        "Add a person",
        "Open company settings",
    ],
    "organization": [
        "Summarize the organization",
        "Show teams",
        "Add a person",
    ],
    "teams": [
        "Show teams",
        "I need a team",
        "I need a developer",
        "Who is in the teams?",
    ],
    "projects": [
        "Show projects",
        "Show missions",
        "What is running?",
    ],
    "missions": [
        "Show missions",
        "What is blocked?",
        "What is waiting for review?",
    ],
    "people": [
        "Who is in the company?",
        "Add a person",
        "Make someone a manager",
    ],
    "activity": [
        "What happened recently?",
        "Give me a company status",
    ],
    "": [
        "What needs my attention?",
        "How is our budget?",
        "Show teams",
        "Add a person",
        "Open company settings",
    ],
}


def _unique(items: Iterable[str]) -> List[str]:
    """Return non-empty strings, de-duplicated while keeping their order."""
    seen = set()
    result: List[str] = []
    for item in items or []:
        text = str(item or "").strip()
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _ic(text: str) -> str:
    """Case-insensitive comparison helper."""
    return (text or "").strip().lower()


def _bullets(lines: Iterable[str]) -> str:
    """Render a markdown bullet list."""
    items = [line for line in lines if line]
    return "\n".join(f"- {item}" for item in items)


class CompanyAssistant:
    """
    Deterministic, company-native implementation of the codx-junior assistant.

    Args:
        manager: Company manager used for every read/write. Injected by the API
            and by the tests.
        security: User security manager (company memberships / user creation).
    """

    def __init__(
        self,
        manager: Any,
        security: Any = None,
        profile_manager_factory: Any = None,
        ai_reasoner: Any = None,
    ):
        self.manager = manager
        # Injectable for tests: project_id -> ProfileManager (or None).
        self.profile_manager_factory = profile_manager_factory
        # Injectable for tests: (company, message, user, language, history, view)
        # -> answer dict. Production uses SmolAgent.
        self.ai_reasoner = ai_reasoner
        if security is None:
            # Imported lazily so this module (and its tests) never pulls the
            # whole auth stack when the caller already injected the security
            # manager.
            from codx.junior.security.user_management import UserSecurityManager

            security = UserSecurityManager()
        self.security = security

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def respond(
        self,
        company: Any,
        message: str = "",
        view: str = "",
        actor: str = "system",
        can_manage: bool = False,
        can_admin: bool = False,
        history: Optional[List[Dict[str, Any]]] = None,
        state: Optional[Dict[str, Any]] = None,
        form_id: str = "",
        values: Optional[Dict[str, Any]] = None,
        user: Any = None,
        language: str = "",
    ) -> Dict[str, Any]:
        """
        Answer one assistant turn.

        Args:
            company: Current company document.
            message: Free-form manager message.
            view: Company view the manager is looking at.
            actor: Username recorded in the journal.
            can_manage: Whether the actor may manage the company work.
            can_admin: Whether the actor may add/remove company users.
            history: Previous ``{role, content}`` turns (context only).
            state: Conversation state from the previous turn. When present the
                message is the ANSWER to the assistant's last question.
            form_id: Form submitted from the assistant window.
            values: Values submitted with ``form_id``.
            user: Authenticated ``CodxUser`` (personalisation + AI fallback).
            language: Browser/request language fallback (``es-ES``, …).

        Returns:
            ``reply``, ``suggestions``, ``options``, optional ``form``,
            ``state`` and ``changed``.
        """
        company = self.manager.get_company(company.id)
        user_language = getattr(user, "language", "") if user is not None else ""
        effective_language = resolve_language(user_language, str(message or ""), language)
        base = {
            "company_id": company.id,
            "view": view or "",
            "language": effective_language,
            "suggestions": list(VIEW_SUGGESTIONS.get(view or "", VIEW_SUGGESTIONS[""])),
            "options": [],
            "form": None,
            "state": None,
            "changed": False,
        }

        # A form submitted from inside the assistant window is an action, not a
        # chat message: execute it and answer with the result.
        if form_id:
            return {
                **base,
                **self._submit_form(
                    company=company,
                    form_id=form_id,
                    values=values or {},
                    actor=actor,
                    can_manage=can_manage,
                    can_admin=can_admin,
                    view=view,
                ),
            }

        text = str(message or "").strip()

        # A guided flow asks ONE question at a time and stores the draft in
        # `state`; the next message is the answer to that question. This is what
        # keeps the company usable without forms/screens.
        if state and state.get("intent"):
            try:
                result = self._continue_flow(
                    company=company,
                    state=state,
                    text=text,
                    actor=actor,
                    can_manage=can_manage,
                    can_admin=can_admin,
                    view=view,
                    user=user,
                    language=effective_language,
                )
            except Exception as ex:  # pragma: no cover - defensive
                logger.exception("Company assistant flow failed: %s", ex)
                result = {
                    "reply": (
                        "I could not finish that step: "
                        f"`{ex}`. Nothing was changed — shall we try again?"
                    ),
                    "state": state,
                    "changed": False,
                }
            return {**base, **result}

        if not text:
            return {
                **base,
                "reply": self._welcome(company, can_manage, can_admin),
            }

        try:
            result = self._dispatch_intent(
                company=company,
                text=text,
                view=view,
                actor=actor,
                can_manage=can_manage,
                can_admin=can_admin,
                history=history or [],
                user=user,
                language=effective_language,
            )
        except Exception as ex:  # pragma: no cover - defensive, but must answer
            logger.exception("Company assistant failed: %s", ex)
            result = {
                "reply": (
                    "I could not complete that action: "
                    f"`{ex}`. Nothing was changed."
                ),
                "changed": False,
            }

        # Keep the suggestion chips useful for the next turn.
        suggestions = result.pop("suggestions", None)
        options = result.pop("options", None)
        return {
            **base,
            **result,
            "suggestions": suggestions or base["suggestions"],
            "options": options or [],
        }

    # ------------------------------------------------------------------
    # Intent routing
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # AI reasoning fallback (SmolAgent)
    # ------------------------------------------------------------------

    def _display_name(self, user: Any) -> str:
        """Human-friendly name for personalisation."""
        if user is None:
            return ""
        username = str(getattr(user, "username", "") or "")
        full_name = str(getattr(user, "name", "") or "").strip()
        if full_name:
            return full_name
        if username:
            return username.replace(".", " ").split("@")[0].title()
        return ""

    def _company_context_for_ai(self, company: Any, user: Any, language: str, view: str) -> str:
        """Compact, factual company + user context for the LLM."""
        counts = company.counts()
        user_role = ""
        if user is not None:
            try:
                user_role = (user.company_role(company.id) if hasattr(user, "company_role") else "") or ""
            except Exception:
                user_role = ""
        lines = [
            f"Company: {company.name}",
            f"Company status: {company.status}",
            f"Mission: {company.mission or '(not set)'}",
            f"Vision: {company.vision or '(not set)'}",
            f"Counts: {counts}",
            f"Assistant language: {language_name(language)} ({language})",
            f"Current view: {view or 'home'}",
        ]
        if company.teams:
            lines.append("Teams:")
            for team in company.teams[:12]:
                lines.append(
                    f"- {team.name}: lead {team.lead_name or 'none'}, "
                    f"{team.human_count} people + {team.ai_count} AI, "
                    f"autonomy {team.autonomy}"
                )
        members = self.manager.company_members(company)
        if members:
            lines.append("People:")
            for member in members[:15]:
                lines.append(
                    f"- {member['username']} ({member.get('company_role', 'member')})"
                    + (f", {member.get('title')}" if member.get("title") else "")
                )
        if company.projects:
            lines.append("Projects:")
            try:
                children = self.manager.child_projects(company)
            except Exception:
                children = []
            for project in company.projects:
                lines.append(
                    f"- {project.name or project.project_id}: role "
                    f"{project.role or 'none'}, team {project.team_id or 'none'}"
                )
                for child in children:
                    if child.get("parent_project_id") == project.project_id:
                        lines.append(f"  - child: {child['project_name']}")
        open_missions = company.open_missions
        if open_missions:
            lines.append("Open missions:")
            for mission in open_missions[:12]:
                team = company.team(mission.team_id)
                lines.append(
                    f"- {mission.title}: {mission.status}, team "
                    f"{team.name if team else 'none'}, {mission.progress}%"
                )
        if user is not None:
            lines.append("Manager:")
            lines.append(
                f"- username: {getattr(user, 'username', '')}; "
                f"email: {getattr(user, 'email', '') or 'not set'}; "
                f"global role: {getattr(user, 'role', '') or 'user'}; "
                f"company role: {user_role or 'member'}; "
                f"preferred language: {getattr(user, 'language', 'auto') or 'auto'}"
            )
        return "\n".join(lines)

    def _ai_system_prompt(
        self,
        company: Any,
        user: Any,
        language: str,
        view: str,
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Build the system prompt for the fallback reasoner."""
        display_name = self._display_name(user) or "the manager"
        language_label = language_name(language)
        context = self._company_context_for_ai(company, user, language, view)
        history_lines = []
        for item in (history or [])[-8:]:
            role = item.get("role") or item.get("type") or "user"
            content = str(item.get("content") or item.get("text") or "").strip()
            if not content:
                continue
            history_lines.append(f"{role}: {content[:400]}")
        return f"""You are codx-junior, the always-present assistant of the company **{company.name}**.

You are talking to **{display_name}** ({getattr(user, 'username', '') if user else 'the manager'}),
who has no technical background. Use warm, plain language and be concise.

IMPORTANT:
- Answer in **{language_label}** ({language}). Do not switch language unless the manager does.
- Personalise naturally: you may address them as {display_name}; do not overuse the name.
- This turn was not understood by the rule-based assistant. Answer the manager's
  question with the company context below. If they asked for an action, explain
  what you can help with and ask one short clarifying question.
- Never claim that you performed an action in this turn. Actions are confirmed
  and executed by the company assistant; do not invent results.
- Never invent company data, people, projects, missions or numbers.
- If the request is unrelated to the company, answer helpfully in the same language.

Known company-assistant actions (for guidance only):
add/remove people, build teams and profiles, choose leads, create/link/unlink
projects, create and review missions, change company details, autopilot on/off.

Company and user context:
{context}

Recent conversation:
{chr(10).join(history_lines) if history_lines else '(none)'}
"""

    def _run_async_with_timeout(self, coro_factory, timeout: float) -> Any:
        """Run an async factory in a worker thread with a hard timeout."""
        def runner():
            return asyncio.run(coro_factory())

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(runner)
        try:
            return future.result(timeout=timeout)
        finally:
            executor.shutdown(wait=False)

    def _reason_with_smol(
        self,
        company: Any,
        text: str,
        user: Any,
        language: str,
        view: str,
        history: Optional[List[Dict[str, Any]]],
    ) -> Optional[str]:
        """Ask the project's LLM through SmolAgent for a reasoned answer."""
        if str(os.getenv("CODX_JUNIOR_COMPANY_AI_FALLBACK", "true")).lower() in (
            "0", "false", "no", "off", "disabled"
        ):
            return None
        settings = None
        for project in company.projects:
            settings = self.manager.project_settings(project.project_id)
            if settings is not None:
                break
        if settings is None:
            return None
        try:
            from codx.junior.ai.smol.smol_agent import SmolAgent
            from langchain.messages import HumanMessage

            agent = SmolAgent(
                settings=settings,
                user=user,
                system=self._ai_system_prompt(company, user, language, view, history),
            )

            async def run():
                return await agent.chat(
                    [HumanMessage(content=text)],
                    config={"tools": []},
                )

            timeout = float(os.getenv("CODX_JUNIOR_COMPANY_AI_TIMEOUT_SECONDS", "25"))
            result = self._run_async_with_timeout(run, max(5.0, timeout))
            content = str(getattr(result, "content", "") or "").strip()
            return content or None
        except Exception as ex:
            logger.exception("Company assistant AI fallback failed: %s", ex)
            return None

    def _ai_fallback(
        self,
        company: Any,
        text: str,
        actor: str = "system",
        user: Any = None,
        language: str = "",
        view: str = "",
        history: Optional[List[Dict[str, Any]]] = None,
        fallback_reply: str = "",
    ) -> Dict[str, Any]:
        """Answer an unrecognised message with AI reasoning, personalised."""
        effective_language = resolve_language(
            getattr(user, "language", "") if user is not None else "",
            text,
            language,
        )
        answer: Optional[str] = None
        if self.ai_reasoner is not None:
            try:
                result = self.ai_reasoner(
                    company=company,
                    text=text,
                    user=user,
                    language=effective_language,
                    view=view,
                    history=history or [],
                )
                if isinstance(result, dict):
                    answer = str(result.get("reply") or "").strip()
                elif result:
                    answer = str(result).strip()
            except Exception as ex:
                logger.exception("Company assistant injected AI reasoner failed: %s", ex)
        else:
            # The API normally passes the authenticated user. When it does not,
            # resolve it from the actor for personalisation.
            if user is None and actor and self.security is not None:
                try:
                    user = self.security.find_user(username=actor)
                except Exception:
                    user = None
            answer = self._reason_with_smol(
                company, text, user, effective_language, view, history
            )
        if not answer:
            return {
                "reply": fallback_reply or self._welcome(company, False, False, unknown=True),
                "state": None,
                "language": effective_language,
                "ai_fallback": False,
                "suggestions": list(VIEW_SUGGESTIONS.get(view or "", VIEW_SUGGESTIONS[""])),
            }
        return {
            "reply": answer,
            "state": None,
            "language": effective_language,
            "ai_fallback": True,
            "suggestions": list(VIEW_SUGGESTIONS.get(view or "", VIEW_SUGGESTIONS[""])),
        }

    def _dispatch_intent(
        self,
        company: Any,
        text: str,
        view: str,
        actor: str,
        can_manage: bool,
        can_admin: bool,
        history: List[Dict[str, Any]],
        user: Any = None,
        language: str = "",
    ) -> Dict[str, Any]:
        """Route one message to the right handler."""
        text = self._strip_chatter(text)
        lowered = _ic(text)

        if lowered in ("help", "?", "what can you do", "what can you do?"):
            return {"reply": self._help(company, can_manage, can_admin)}

        if "delete" in lowered and "company" in lowered:
            return self._delete_company(company, text, can_admin, actor)

        if re.search(r"\b(company )?settings\b", lowered) or "edit company" in lowered:
            return self._start_edit_company(company, can_manage)

        # "I need a developer" / "I need an IT team" is a profile/team design
        # request: inspect the project and suggest profiles + team.
        if self._is_build_need(lowered) and "link" not in lowered:
            return self._start_build_team(company, text, can_manage, can_admin)

        # Team commands are resolved FIRST when they name an existing team, so
        # "add user alice to Platform" is a team action and not the company
        # add-user form.
        target_team = self._team_target(company, text)
        if target_team is not None:
            if re.search(
                r"^(?:add|invite)\s+(?:user:|profile:)?"
                r"(?:user\s+|profile\s+|member\s+)?[\w.\-@]+\s+(?:to|into)\s+",
                text,
                re.I,
            ):
                return self._add_team_member(company, text, can_manage, actor, form=False)
            if re.search(
                r"^remove\s+(?:user:|profile:)?"
                r"(?:user\s+|profile\s+|member\s+)?[\w.\-@]+\s+from\s+",
                text,
                re.I,
            ):
                return self._remove_team_member(company, text, can_manage, actor)
            if re.search(
                r"^(?:make|set)\s+(?:user:|profile:)?"
                r"(?:user\s+|profile\s+|member\s+)?[\w.\-@]+\s+"
                r"(?:as\s+)?(?:the\s+)?lead\b",
                text,
                re.I,
            ):
                return self._set_team_lead(company, text, can_manage, actor)
            if "lead" in lowered:
                return self._start_set_lead(company, can_manage, team=target_team)

        if "project" in lowered and re.match(r"^(create|new|start)\b", lowered):
            return self._start_create_project(company, text, can_manage)

        if "project" in lowered and re.match(r"^(unlink|remove|detach)\b", lowered):
            return self._start_unlink_project(company, text, can_manage)

        if "project" not in lowered and re.match(r"^(unlink|remove|detach)\b", lowered):
            lowered_names = _ic(text)
            if any(
                (item.name or "").lower() in lowered_names
                or item.project_id.lower() in lowered_names
                for item in company.projects
            ):
                return self._start_unlink_project(company, text, can_manage)

        if re.match(r"^(link|connect)\b", lowered):
            return self._start_link_named_project(company, text, can_manage)

        if ("link" in lowered or "connect" in lowered) and "project" in lowered or \
                re.match(r"^(add)\s+(a\s+)?project\b", lowered):
            return self._start_link_project(company, can_manage)

        if re.match(r"^(add|invite|create|onboard)\b.*\b(user|person|member|employee|account)\b", lowered) or \
                re.match(r"^(add|invite|create|onboard) (a )?(new )?(user|person|member|employee)\b", lowered):
            return self._start_add_user(company, text, can_admin)

        if re.match(r"^(remove|take|drop)\b", lowered) and any(
            connector in lowered for connector in (" from ", " out of ", " off ")
        ):
            return self._remove_team_member(company, text, can_manage, actor)

        if "in charge" in lowered and "of" in lowered:
            return self._set_team_lead(company, text, can_manage, actor)

        if re.match(r"^(add|invite|hire)\b", lowered) and re.search(
            r"\b(?:as|to\s+be)\s+(?:an?\s+)?(admin|manager|member)\b", lowered
        ):
            return self._add_or_promote(company, text, can_admin)

        simple_add = re.match(r"^(?:add|invite|hire)\s+(?:user\s+)?(.+)$", text, re.I)
        if simple_add and not any(
            separator in lowered
            for separator in (" to ", " in ", " on ", " as ", " team", " mission", " project")
        ):
            return self._start_add_user_named(company, simple_add.group(1).strip(), can_admin)

        if re.match(r"^(add|put|include|assign)\b", lowered) and not any(
            word in lowered for word in ("user", "person", "member", "employee", "mission", "project", "company", "settings")
        ):
            return self._add_team_member(company, text, can_manage, actor, form=False)

        if "should" in lowered and any(
            phrase in lowered for phrase in ("join ", "be in ", "be on ", "be part of ")
        ):
            return self._add_team_member(company, text, can_manage, actor, form=False)

        if "lead" in lowered:
            return self._set_team_lead(company, text, can_manage, actor)

        if "remove" in lowered and ("user" in lowered or "person" in lowered or "member" in lowered):
            return self._remove_user(company, text, can_admin, actor)

        if re.search(r"^(?:make|set|change)\s+.*\b(admin|manager|member)\b", lowered):
            return self._change_company_role(company, text, can_admin)

        if ("add" in lowered and "team" not in lowered and "lead" not in lowered
                and not any(word in lowered for word in ("user", "person", "member", "employee"))
                and (" to " in lowered or " into " in lowered)):
            return self._add_team_member(company, text, can_manage, actor, form=False)

        if "remove" in lowered and " from " in lowered and "team" not in lowered:
            return self._remove_team_member(company, text, can_manage, actor)

        if "lead" in lowered and any(word in lowered for word in ("choose", "add", "pick", "who should", "set")):
            return self._start_set_lead(company, can_manage)

        if "lead" in lowered and ("make " in lowered or "set " in lowered):
            return self._set_team_lead(company, text, can_manage, actor)

        if "delete" in lowered and "team" in lowered:
            return self._delete_team(company, text, can_manage, actor, history)

        if ("team" in lowered
                and re.match(r"^(create|make|start|set\s+up|setup|add)\b", lowered)
                and " to " not in lowered and " from " not in lowered):
            return self._create_team(company, text, can_manage, actor)

        if ("create" in lowered or "new" in lowered or "add" in lowered) and "mission" in lowered:
            return self._start_create_mission(company, text, can_manage, actor)

        if "dispatch" in lowered and "mission" in lowered:
            return self._dispatch_mission(company, text, can_manage, actor)

        if re.match(r"^(approve|deny)\b", lowered) or "approval" in lowered:
            return self._approvals(company, text, can_manage, actor)

        if "review" in lowered and "mission" in lowered:
            return self._start_review_mission(company, text, can_manage)

        if ("accept" in lowered or "reject" in lowered) and "mission" in lowered:
            return self._review_mission(company, text, can_manage, actor)

        if "organization" in lowered or "org chart" in lowered or "department" in lowered:
            return self._organization(company)

        if "team" in lowered:
            return self._teams(company, text)

        if "people" in lowered or "user" in lowered or "member" in lowered or "who is" in lowered:
            return self._people(company)

        if "mission" in lowered or "review" in lowered or "blocked" in lowered or "running" in lowered:
            return self._missions(company, lowered)

        if "company chat" in lowered or "channel" in lowered or "chats" in lowered:
            return self._company_chats(company)

        if "project" in lowered:
            return self._projects(company)

        if "autopilot" in lowered or "autonomy" in lowered:
            return self._autopilot(company, text, can_manage, actor)

        if any(
            word in lowered
            for word in ("budget", "spend", "spent", "cost", "cxjcoins", "how much")
        ):
            return self._budget(company)

        if "attention" in lowered or "status" in lowered or "overview" in lowered or "summary" in lowered:
            return self._status(company)

        if "activity" in lowered or "recent" in lowered or "journal" in lowered:
            return self._activity(company)

        # A message that names a mission is about that mission.
        named_mission = next(
            (
                mission
                for mission in company.missions
                if mission.title and mission.title.lower() in lowered
            ),
            None,
        )
        if named_mission is not None:
            return self._mission_detail(company, named_mission)

        # Unknown message: AI reasoning fallback (personalised and in the
        # manager's language), with the capability summary as a safe fallback.
        return self._ai_fallback(
            company=company,
            text=text,
            actor=actor,
            user=user,
            language=language,
            view=view,
            history=history,
            fallback_reply=self._welcome(company, can_manage, can_admin, unknown=True),
        )

    # ------------------------------------------------------------------
    # Read-only answers
    # ------------------------------------------------------------------

    def _welcome(
        self,
        company: Any,
        can_manage: bool,
        can_admin: bool,
        unknown: bool = False,
    ) -> str:
        """Greeting / fallback answer."""
        counts = company.counts()
        people = len(self.manager.company_members(company))
        lines = [
            f"Hello — I'm **codx-junior**, the assistant of *{company.name}*.",
            "",
            f"I can see **{counts['teams']} team(s)**, **{people} company member(s)**, "
            f"**{counts['ai']} AI profile(s)** and **{counts['open_missions']} open mission(s)**.",
            "",
            "I can manage the work for you:",
            "- **Teams** — create a team, add or remove people, choose the lead.",
        ]
        if can_admin:
            lines.append("- **People** — add a company user or change a role.")
        lines.append("- **Settings** — update the company mission, vision and status.")
        lines.append("- **Missions** — review, dispatch and accept work.")
        if unknown:
            lines.insert(0, "I didn't catch that command, but here is what I can do:")
        if not can_manage:
            lines += [
                "",
                "Your role is **read-only** in this company: you can ask me anything "
                "about the organization, but changes require a manager or admin.",
            ]
        return "\n".join(lines)

    def _help(self, company: Any, can_manage: bool, can_admin: bool) -> str:
        """Capabilities, tailored to the caller's role."""
        return self._welcome(company, can_manage, can_admin)

    def _status(self, company: Any) -> Dict[str, Any]:
        """Company pulse: counts, running work and what needs attention."""
        counts = company.counts()
        people = len(self.manager.company_members(company))
        running = [mission for mission in company.missions if mission.status == "running"]
        review = [mission for mission in company.missions if mission.status == "review"]
        blocked = [mission for mission in company.missions if mission.status in ("blocked", "paused")]
        approvals = [
            mission for mission in company.missions
            if mission.approval_status in ("pending", "denied")
            and mission.status in ("ready", "blocked")
        ]
        lines = [
            f"### {company.name}",
            f"**{counts['open_missions']} open mission(s)** · "
            f"**{counts['running']} running** · **{counts['review']} in review** · "
            f"**{counts['done']} done**",
            "",
            f"- Teams: **{counts['teams']}** · People: **{people} human + {counts['ai']} AI**",
            f"- Projects: **{counts['projects']}** · Org units: **{counts['org_units']}** · "
            f"Chats: **{counts.get('chats', 0)}**",
            f"- Autopilot: **{'on' if company.autonomy.enabled else 'off'}** "
            f"({company.autonomy.level})",
        ]
        if running:
            lines += ["", "**Running now**"] + [
                f"- {mission.title} — {mission.progress}%"
                for mission in running[:8]
            ]
        if review:
            lines += ["", "**Waiting for a human**"] + [
                f"- {mission.title} (in review)"
                for mission in review[:8]
            ]
        if approvals:
            lines += ["", "**Waiting for approval**"] + [
                f"- {mission.title} ({mission.approval_status})"
                for mission in approvals[:8]
            ]
        if blocked:
            lines += ["", "**Needs attention**"] + [
                f"- {mission.title} ({mission.status})"
                for mission in blocked[:8]
            ]
        if not (running or review or blocked):
            lines += ["", "Nothing is running and nothing is waiting for review right now."]
        return {"reply": "\n".join(lines)}

    def _budget(self, company: Any) -> Dict[str, Any]:
        """
        Answer "how is our budget?" from the live company ledger.

        The numbers come from :meth:`CompanyManager.budget_state`, so the
        assistant and the UI always show the same daily/total spend, project
        limits and over-budget flags.
        """
        try:
            budget = self.manager.budget_state(company)
        except Exception:
            return {
                "reply": "I could not read the budget right now. Try again in a moment.",
                "suggestions": ["What needs my attention?", "Show projects"],
            }

        daily_limit = budget.get("daily_limit_cxjcoins") or 0
        spent_today = budget.get("spent_today_cxjcoins") or 0
        spent_total = budget.get("spent_total_cxjcoins") or 0
        lines = ["### Budget"]
        if daily_limit > 0:
            remaining = budget.get("remaining_today_cxjcoins")
            lines.append(
                f"Today: **{spent_today} / {daily_limit} cxjcoins**"
                + (f" · **{remaining}** left" if remaining is not None else "")
            )
            if budget.get("over_daily_budget"):
                lines.append(
                    "**The daily budget is exhausted.** The autopilot will not "
                    "start new missions until tomorrow or until you raise the limit."
                )
        else:
            lines.append(f"Spent today: **{spent_today} cxjcoins** (no daily limit set)")
        lines.append(f"Spent in total: **{spent_total} cxjcoins**")

        over_projects = [
            project for project in budget.get("projects", [])
            if project.get("over_budget")
        ]
        if over_projects:
            lines += ["", "**Projects over budget**"] + [
                f"- {project.get('name')} · "
                f"{project.get('spent_cxjcoins')} / {project.get('budget_cxjcoins')} cxjcoins"
                for project in over_projects
            ]

        over_teams = [
            team for team in budget.get("teams", [])
            if team.get("over_budget")
        ]
        if over_teams:
            lines += ["", "**Teams over budget**"] + [
                f"- {team.get('name')} · "
                f"{team.get('spent_cxjcoins')} / {team.get('budget_cxjcoins')} cxjcoins"
                for team in over_teams
            ]

        spent_missions = [
            mission for mission in company.missions
            if mission.spent_cxjcoins > 0
        ]
        if spent_missions:
            spent_missions.sort(key=lambda mission: mission.spent_cxjcoins, reverse=True)
            lines += ["", "**Where the spend went**"] + [
                f"- {mission.title} · {mission.spent_cxjcoins} cxjcoins"
                for mission in spent_missions[:5]
            ]

        if spent_total <= 0:
            lines += [
                "",
                "No AI spend has been recorded yet. When a mission runs, its "
                "orchestration run reports the cost here automatically.",
            ]

        return {
            "reply": "\n".join(lines),
            "suggestions": [
                "What needs my attention?",
                "Show projects",
                "Turn on autopilot" if not company.autonomy.enabled else "Turn off autopilot",
            ],
        }

    def _approvals(
        self,
        company: Any,
        text: str,
        can_manage: bool,
        actor: str,
    ) -> Dict[str, Any]:
        """List pending approvals, or approve/deny a named mission."""
        lowered = _ic(text)
        match = re.match(r"^(approve|deny)\s+(?:mission\s+)?(.+)$", text, re.I)
        if match and can_manage:
            action = match.group(1).lower()
            wanted = match.group(2).strip().strip("\"'").lower()
            mission = next(
                (
                    item for item in company.missions
                    if item.id.lower() == wanted
                    or (item.title and item.title.lower() == wanted)
                    or (item.title and wanted in item.title.lower())
                ),
                None,
            )
            if mission is None:
                return {
                    "reply": f"I could not find a mission called “{match.group(2).strip()}”.",
                    "suggestions": ["Show pending approvals", "Show missions"],
                }
            if action == "approve":
                self.manager.approve_mission(
                    company.id, mission.id, actor=actor
                )
                return {
                    "reply": (
                        f"**{mission.title}** is approved. You can dispatch it "
                        "whenever you are ready."
                    ),
                    "suggestions": ["Show missions", "What needs my attention?"],
                }
            self.manager.deny_mission(
                company.id, mission.id, note="Denied from the assistant", actor=actor
            )
            return {
                "reply": f"**{mission.title}** was denied and will not run.",
                "suggestions": ["Show pending approvals", "Show missions"],
            }

        pending = [
            mission for mission in company.missions
            if mission.approval_status in ("pending", "denied")
            and mission.status in ("ready", "blocked")
        ]
        if not pending:
            return {
                "reply": "Nothing is waiting for approval right now.",
                "suggestions": ["What needs my attention?", "Show missions"],
            }
        lines = ["### Approvals"]
        for mission in pending[:10]:
            lines.append(
                f"- **{mission.title}** · {mission.approval_status} · "
                f"{mission.priority} priority"
            )
        if can_manage:
            lines += [
                "",
                "Say **approve <mission>** or **deny <mission>** to decide.",
            ]
        else:
            lines += ["", "Your role is read-only in this company."]
        return {
            "reply": "\n".join(lines),
            "suggestions": ["Show missions", "What needs my attention?"],
        }

    def _teams(self, company: Any, text: str = "") -> Dict[str, Any]:
        """List the hybrid teams and their rosters (or one named team)."""
        wanted = _ic(text)
        named = next(
            (team for team in company.teams if team.name.lower() in wanted),
            None,
        ) if wanted else None
        if named is not None:
            roster = ", ".join(
                f"{member.name} ({'AI helper' if member.is_ai else 'person'}"
                + (f", {member.role}" if member.role else "")
                + ")"
                for member in named.members
            ) or "nobody yet"
            open_missions = [
                mission for mission in company.open_missions
                if mission.team_id == named.id
            ]
            lines = [
                f"### {named.name}",
                f"Lead: **{named.lead_name or 'no lead yet'}**",
                f"People: {roster}",
                f"Open missions: **{len(open_missions)}**",
            ]
            if named.description:
                lines.insert(1, named.description)
            return {"reply": "\n".join(lines)}
        if not company.teams:
            return {
                "reply": (
                    "There are no teams yet. Want me to set up the first one? "
                    "Just tell me what kind of team you need."
                ),
                "suggestions": ["I need a team", "I need an IT team"],
            }
        lines = ["### Teams"]
        for team in company.teams:
            lead = team.lead_name or "no lead"
            lines += [
                "",
                f"**{team.name}** · {team.human_count} human · {team.ai_count} AI · "
                f"{team.autonomy} · lead: {lead}",
            ]
            if team.description:
                lines.append(team.description)
            roster = ", ".join(
                f"{member.name} ({'AI' if member.is_ai else 'human'}"
                + (f", {member.role}" if member.role else "")
                + ")"
                for member in team.members
            )
            lines.append(f"Roster: {roster or '—'}")
        lines += ["", "You can ask me to add someone, remove someone or choose a "
                      "lead — no special wording needed. For example: “add Alice to "
                      "Platform” or “Alice should lead the Platform team”."]
        return {"reply": "\n".join(lines)}

    def _people(self, company: Any) -> Dict[str, Any]:
        """List the human roster and their company roles."""
        members = self.manager.company_members(company)
        if not members:
            return {
                "reply": (
                    "I don't see any human members yet. A company admin can add "
                    "people from here."
                )
            }
        lines = ["### People"]
        for member in members:
            title = f" · {member['title']}" if member.get("title") else ""
            owner = " · owner" if member.get("owner") else ""
            lines.append(
                f"- **{member['username']}** — {member.get('company_role', 'member')}"
                f"{title}{owner}"
            )
        return {"reply": "\n".join(lines)}

    def _project_path_for(self, name: str) -> str:
        """Build a project path from a plain name, path or repository URL."""
        value = (name or "").strip().strip('"').strip("'")
        lowered = value.lower()
        if lowered.startswith("http://") or lowered.startswith("https://") or value.startswith("/"):
            return value
        slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-") or "new-project"
        try:
            from codx.junior.project.project_discover import get_projects_root_path

            root = get_projects_root_path()
        except Exception:
            root = ""
        return f"{root.rstrip('/')}/{slug}" if root else slug

    def _start_create_project(self, company: Any, text: str, can_manage: bool) -> Dict[str, Any]:
        """Start creating a brand-new codx-junior project."""
        if not can_manage:
            return {"reply": _denied("create projects")}
        match = re.search(
            r"(?:create|new|start|add)\s+(?:a\s+)?(?:new\s+)?project\s+"
            r"(?:called\s+|named\s+)?(.+)$",
            text,
            re.I,
        )
        name = match.group(1).strip().strip('"').strip("'").rstrip("?.!,") if match else ""
        path_match = re.search(
            r"\b(?:at|in|from)\s+((?:https?://|/)[^\s]+)\s*$",
            text,
            re.I,
        )
        path = path_match.group(1) if path_match else ""
        if path:
            path = path.rstrip("/")
            name = re.split(r"[/\\]", path.split(":")[-1] if "://" in path else path)[-1]
            name = name[:-4] if name.endswith(".git") else name
        if not name:
            return self._question(
                "What should we call the new project?",
                {"intent": "create_project", "step": "name", "draft": {}},
            )
        if not path:
            name = re.sub(r"\s+(?:at|in|from)\s+.+$", "", name, flags=re.I)
            path = self._project_path_for(name)
        return self._confirm_action(
            {"type": "create_project", "name": name, "path": path},
            (
                f"I'll create the project **{name}** at `{path}` and link it to "
                "the company."
            ),
        )

    def _continue_create_project(
        self, company: Any, state: Dict[str, Any], text: str, can_manage: bool
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("create projects"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        name = text.strip().strip('"').strip("'").rstrip("?.!,")
        if not name:
            return self._question("What should we call the new project?", state)
        path = self._project_path_for(name)
        return self._confirm_action(
            {"type": "create_project", "name": name, "path": path},
            (
                f"I'll create the project **{name}** at `{path}` and link it to "
                "the company."
            ),
        )

    def _start_unlink_project(self, company: Any, text: str, can_manage: bool) -> Dict[str, Any]:
        """Start removing a project from the company mapping (not deleting it)."""
        if not can_manage:
            return {"reply": _denied("remove projects")}
        if not company.projects:
            return {"reply": "No projects are mapped to the company yet."}
        lowered = _ic(text)
        project = next(
            (
                item for item in company.projects
                if (item.name or "").lower() in lowered
                or item.project_id.lower() in lowered
            ),
            None,
        )
        if project is not None:
            return self._confirm_action(
                {
                    "type": "unlink_project",
                    "project_id": project.project_id,
                    "name": project.name or project.project_id,
                },
                (
                    f"I'll remove **{project.name or project.project_id}** from the "
                    "company. The project itself is not deleted. Open missions may "
                    "need to be reassigned first."
                ),
            )
        return self._question(
            "Which project should I remove from the company?",
            {"intent": "unlink_project", "step": "project", "draft": {}},
            options=[
                {"label": item.name or item.project_id, "value": item.project_id}
                for item in company.projects
            ],
        )

    def _continue_unlink_project(
        self, company: Any, state: Dict[str, Any], text: str, can_manage: bool
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("remove projects"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        project = next(
            (
                item for item in company.projects
                if item.project_id == text
                or (item.name or "").lower() == _ic(text)
            ),
            None,
        )
        if project is None:
            return self._question(
                "Which project should I remove from the company?",
                state,
                options=[
                    {"label": item.name or item.project_id, "value": item.project_id}
                    for item in company.projects
                ],
            )
        return self._confirm_action(
            {
                "type": "unlink_project",
                "project_id": project.project_id,
                "name": project.name or project.project_id,
            },
            (
                f"I'll remove **{project.name or project.project_id}** from the "
                "company. The project itself is not deleted."
            ),
        )

    def _start_link_named_project(self, company: Any, text: str, can_manage: bool) -> Dict[str, Any]:
        """Link a project explicitly named in the message ("link Web Console")."""
        if not can_manage:
            return {"reply": _denied("link projects")}
        try:
            discovered = self.manager.references().get("projects", [])
        except Exception:
            discovered = []
        lowered = _ic(text)
        linked = {project.project_id for project in company.projects}
        match = next(
            (
                project for project in discovered
                if project.get("project_id") not in linked
                and (
                    (project.get("project_name") or "").lower() in lowered
                    or (project.get("project_id") or "").lower() in lowered
                )
            ),
            None,
        )
        if match is None:
            return self._start_link_project(company, can_manage)
        return self._confirm_action(
            {
                "type": "link_project",
                "project_id": match["project_id"],
                "name": match.get("project_name") or match["project_id"],
            },
            f"I'll link **{match.get('project_name') or match['project_id']}** to the company.",
        )

    def _start_link_project(self, company: Any, can_manage: bool) -> Dict[str, Any]:
        """Start the link-project conversation."""
        if not can_manage:
            return {"reply": _denied("link projects")}
        try:
            discovered = self.manager.references().get("projects", [])
        except Exception:  # pragma: no cover - discovery is optional
            discovered = []
        linked = {project.project_id for project in company.projects}
        available = [
            project for project in discovered
            if project.get("project_id") and project["project_id"] not in linked
        ]
        if not available:
            return {
                "reply": (
                    "Every project I can find is already linked to the company. "
                    "If a project is missing, it may not be discovered yet."
                )
            }
        if len(available) == 1:
            project = available[0]
            return self._confirm_action(
                {
                    "type": "link_project",
                    "project_id": project["project_id"],
                    "name": project.get("project_name") or project["project_id"],
                },
                f"I found **{project.get('project_name') or project['project_id']}** and I'll link it to the company.",
            )
        return self._question(
            "Which project should I link?",
            {"intent": "link_project", "step": "project", "draft": {}},
            options=[
                {
                    "label": project.get("project_name") or project["project_id"],
                    "value": project["project_id"],
                }
                for project in available[:12]
            ],
        )

    def _continue_link_project(
        self, company: Any, state: Dict[str, Any], text: str, actor: str, can_manage: bool
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("link projects"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        draft = dict(state.get("draft") or {})
        step = state.get("step")
        if step == "confirm":
            if _ic(text) not in ("yes", "y", "ok", "okay", "link it", "sure"):
                return self._cancelled()
            project_id = draft.get("project_id", "")
        else:
            project_id = text.strip()
        try:
            discovered = self.manager.references().get("projects", [])
        except Exception:  # pragma: no cover
            discovered = []
        project = next(
            (
                item for item in discovered
                if item.get("project_id") == project_id
                or (item.get("project_name") or "").lower() == _ic(project_id)
            ),
            None,
        )
        if project is None:
            available = [
                item for item in discovered
                if not company.project(item.get("project_id", ""))
            ]
            return self._question(
                "Which project should I link?",
                {"intent": "link_project", "step": "project", "draft": {}},
                options=[
                    {
                        "label": item.get("project_name") or item["project_id"],
                        "value": item["project_id"],
                    }
                    for item in available[:12]
                ],
            )
        if company.project(project["project_id"]):
            return {
                "reply": "That project is already linked.",
                "state": None,
                "suggestions": ["Show projects", "Create a mission"],
            }
        return self._confirm_action(
            {
                "type": "link_project",
                "project_id": project["project_id"],
                "name": project.get("project_name") or project["project_id"],
            },
            f"I'll link **{project.get('project_name') or project['project_id']}** to the company.",
        )

    def _autopilot(self, company: Any, text: str, can_manage: bool, actor: str) -> Dict[str, Any]:
        """Explain or toggle the autopilot without a settings screen."""
        lowered = _ic(text)
        if can_manage and any(word in lowered for word in ("turn on", "enable", "start", "activate")):
            return self._confirm_action(
                {"type": "autopilot", "enabled": True},
                "I'll turn autopilot on in supervised mode (you still accept results).",
            )
        if can_manage and any(word in lowered for word in ("turn off", "disable", "stop", "pause")):
            return self._confirm_action(
                {"type": "autopilot", "enabled": False},
                "I'll turn autopilot off. Nothing will start without you.",
            )
        policy = company.autonomy
        return {
            "reply": (
                f"Autopilot is **{'on' if policy.enabled else 'off'}** "
                f"(level: **{policy.level}**, every {policy.interval_minutes} minutes). "
                "You can say **turn on autopilot** or **turn off autopilot**."
            ),
            "suggestions": [
                "Turn on autopilot" if not policy.enabled else "Turn off autopilot",
                "What needs my attention?",
            ],
        }

    def _company_chats(self, company: Any) -> Dict[str, Any]:
        """List the company channels and who owns them."""
        if not company.chats:
            return {
                "reply": (
                    "There are no company channels yet. Open **Chats** in the "
                    "company header to create one for a team."
                ),
                "suggestions": ["Show teams", "What needs my attention?"],
            }
        lines = ["### Company chats"]
        for ref in company.chats:
            team = company.team(ref.team_id)
            lines.append(
                f"- **#{ref.name or ref.chat_id}** · "
                f"{team.name if team else 'no team'} · "
                f"{ref.project_id}"
                + (" · pinned" if ref.pinned else "")
            )
        lines += [
            "",
            "Open **Chats** in the company header to read or write in a channel.",
        ]
        return {
            "reply": "\n".join(lines),
            "suggestions": ["Show teams", "What needs my attention?"],
        }

    def _projects(self, company: Any) -> Dict[str, Any]:
        """List linked projects, their children and open mission counts."""
        if not company.projects:
            return {
                "reply": (
                    "No projects are linked yet. I can link an existing one or "
                    "create a new project for you."
                ),
                "suggestions": ["Link a project", "Create a new project", "Create a mission"],
            }
        try:
            children = self.manager.child_projects(company)
        except Exception:
            children = []
        by_parent: Dict[str, List[Dict[str, Any]]] = {}
        for child in children:
            by_parent.setdefault(child["parent_project_id"], []).append(child)
        lines = ["### Projects"]
        for project in company.projects:
            open_missions = [
                mission for mission in company.open_missions
                if mission.project_id == project.project_id
            ]
            lines.append(
                f"- **{project.name or project.project_id}** · role: "
                f"{project.role or '—'} · team: {project.team_id or '—'} · "
                f"{len(open_missions)} open mission(s)"
            )
            for child in by_parent.get(project.project_id, []):
                lines.append(
                    f"  - **{child['project_name']}** · child project of "
                    f"{project.name or project.project_id}"
                )
        if children:
            lines += [
                "",
                f"They are **{len(children)} child project"
                + ("" if len(children) == 1 else "s")
                + "** under your mapped projects.",
            ]
        return {
            "reply": "\n".join(lines),
            "suggestions": ["Create a new project", "Link a project", "Create a mission"],
        }

    def _missions(self, company: Any, lowered: str) -> Dict[str, Any]:
        """List missions, optionally filtered by the question."""
        missions = list(company.missions)
        if "review" in lowered:
            missions = [mission for mission in missions if mission.status == "review"]
            title = "### Missions in review"
        elif "blocked" in lowered:
            missions = [mission for mission in missions if mission.status in ("blocked", "paused")]
            title = "### Blocked / paused missions"
        elif "running" in lowered:
            missions = [mission for mission in missions if mission.status == "running"]
            title = "### Running missions"
        elif "open" in lowered or "ready" in lowered:
            missions = list(company.open_missions)
            title = "### Open missions"
        else:
            title = "### Missions"
        if not missions:
            return {"reply": f"{title}\n\nNothing matches right now."}
        lines = [title]
        for mission in sorted(missions, key=lambda item: item.title.lower()):
            team = company.team(mission.team_id)
            lines.append(
                f"- **{mission.title}** · {mission.status} · {mission.priority} · "
                f"team: {team.name if team else '—'} · {mission.progress}%"
            )
        if any(mission.status == "review" for mission in missions):
            lines += ["", "If you want, I can accept the result or send it back to the team."]
        return {"reply": "\n".join(lines)}

    def _mission_detail(self, company: Any, mission: Any) -> Dict[str, Any]:
        """Explain one mission in plain language."""
        team = company.team(mission.team_id)
        project = company.project(mission.project_id)
        lines = [
            f"### {mission.title}",
            f"Status: **{mission.status}** · progress: **{mission.progress}%**",
            f"Team: **{team.name if team else 'no team yet'}** · "
            f"Project: **{(project.name if project else mission.project_id) or 'no project yet'}**",
        ]
        if mission.objective and mission.objective != mission.title:
            lines.append(f"Goal: {mission.objective}")
        if mission.result:
            lines.append(f"Result: {mission.result}")
        if mission.last_error:
            lines.append(f"Last problem: {mission.last_error}")
        if mission.status == "review":
            lines.append("It is waiting for you to accept or reject the result.")
        return {"reply": "\n".join(lines)}

    def _activity(self, company: Any) -> Dict[str, Any]:
        """Recent journal entries."""
        events = self.manager.journal(company.id, limit=12)
        if not events:
            return {"reply": "The company journal is empty."}
        lines = ["### Recent activity"]
        for event in reversed(events):
            lines.append(
                f"- `{event.get('at', '')[:16]}` **{event.get('type', '')}** — "
                f"{event.get('message', '')}"
            )
        return {"reply": "\n".join(lines)}

    # ------------------------------------------------------------------
    # Forms (rendered INSIDE the assistant window)
    # ------------------------------------------------------------------

    def _settings_form(self, company: Any, can_manage: bool) -> Dict[str, Any]:
        """Open the company settings form in the assistant window."""
        if not can_manage:
            return {"reply": _denied("change the company settings")}
        return {
            "reply": (
                "Let's update the company. Fill this in — I'll apply it right "
                "away, without opening a separate settings dialog."
            ),
            "form": {
                "id": FORM_EDIT_COMPANY,
                "title": "Company settings",
                "submit_label": "Save company",
                "description": "Mission, vision and identity of the company.",
                "values": {
                    "name": company.name,
                    "description": company.description,
                    "mission": company.mission,
                    "vision": company.vision,
                    "website": company.website,
                    "status": company.status,
                },
                "fields": [
                    {"name": "name", "label": "Name", "type": "text", "required": True},
                    {"name": "description", "label": "Description", "type": "textarea"},
                    {"name": "mission", "label": "Mission", "type": "textarea"},
                    {"name": "vision", "label": "Vision", "type": "textarea"},
                    {"name": "website", "label": "Website", "type": "text"},
                    {
                        "name": "status",
                        "label": "Status",
                        "type": "select",
                        "options": ["active", "paused", "archived"],
                    },
                ],
            },
        }

    def _add_user_form(self, company: Any) -> Dict[str, Any]:
        """Open the add-user form in the assistant window."""
        return {
            "reply": (
                "Who should join the company? I'll create the account (or enroll "
                "an existing user) and add them to the company."
            ),
            "form": {
                "id": FORM_ADD_USER,
                "title": "Add a person",
                "submit_label": "Add person",
                "description": (
                    "Leave the password empty to enroll an existing codx-junior "
                    "user. A new account needs a password."
                ),
                "values": {"role": COMPANY_ROLE_MEMBER, "user_role": "user"},
                "fields": [
                    {"name": "username", "label": "Username", "type": "text", "required": True},
                    {"name": "email", "label": "Email", "type": "email"},
                    {"name": "password", "label": "Initial password", "type": "password"},
                    {"name": "title", "label": "Title", "type": "text",
                     "placeholder": "Product manager, Engineer…"},
                    {
                        "name": "role",
                        "label": "Company role",
                        "type": "select",
                        "options": list(COMPANY_ROLES),
                        "required": True,
                    },
                    {
                        "name": "user_role",
                        "label": "codx-junior role",
                        "type": "select",
                        "options": ["user", "manager", "company_admin"],
                    },
                ],
            },
        }

    def _create_team_form(self, company: Any) -> Dict[str, Any]:
        """Open the create-team form in the assistant window."""
        profiles = self.manager.references().get("profiles", [])
        people = self.manager.company_members(company)
        return {
            "reply": (
                "Let's create a hybrid team. Give it a name, a lead and the first "
                "members (humans and AI profiles); I'll keep the lead in the roster."
            ),
            "form": {
                "id": FORM_CREATE_TEAM,
                "title": "Create a team",
                "submit_label": "Create team",
                "values": {"autonomy": "supervised", "members": []},
                "fields": [
                    {"name": "name", "label": "Team name", "type": "text", "required": True},
                    {"name": "description", "label": "What it does", "type": "textarea"},
                    {"name": "purpose", "label": "Outcome it owns", "type": "text"},
                    {
                        "name": "lead",
                        "label": "Lead",
                        "type": "select",
                        "options": [
                            f"user:{member['username']}" for member in people
                        ] + [
                            f"profile:{profile['name']}" for profile in profiles
                        ],
                    },
                    {
                        "name": "members",
                        "label": "Members",
                        "type": "multiselect",
                        "options": [
                            f"user:{member['username']}" for member in people
                        ] + [
                            f"profile:{profile['name']}" for profile in profiles
                        ],
                    },
                    {
                        "name": "project_id",
                        "label": "Project",
                        "type": "select",
                        "options": [
                            {"value": project.project_id, "label": project.name}
                            for project in company.projects
                        ],
                    },
                    {
                        "name": "autonomy",
                        "label": "Autonomy",
                        "type": "select",
                        "options": ["manual", "supervised", "autonomous"],
                    },
                ],
            },
        }

    def _add_team_member_form(self, company: Any) -> Dict[str, Any]:
        """Open the add-member form in the assistant window."""
        profiles = self.manager.references().get("profiles", [])
        people = self.manager.company_members(company)
        return {
            "reply": "Who should join which team?",
            "form": {
                "id": FORM_ADD_TEAM_MEMBER,
                "title": "Add a team member",
                "submit_label": "Add member",
                "fields": [
                    {
                        "name": "team_id",
                        "label": "Team",
                        "type": "select",
                        "required": True,
                        "options": [
                            {"value": team.id, "label": team.name}
                            for team in company.teams
                        ],
                    },
                    {
                        "name": "member",
                        "label": "Member",
                        "type": "select",
                        "required": True,
                        "options": [
                            f"user:{member['username']}" for member in people
                        ] + [
                            f"profile:{profile['name']}" for profile in profiles
                        ],
                    },
                    {"name": "role", "label": "Role in the team", "type": "text"},
                ],
            },
        }

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Guided conversations (one question at a time)
    # ------------------------------------------------------------------

    # ── Natural language helpers ───────────────────────────────────────

    #: Anything in this set (or a phrase starting with it) confirms an action.
    AFFIRMATIVE = (
        "ok", "okay", "k", "fine", "confirm", "confirmed", "yes", "y", "yeah",
        "yep", "yup", "sure", "go ahead", "go", "do it", "proceed", "please do",
        "sounds good", "of course", "absolutely", "definitely", "correct",
        "right", "that's right", "alright", "all right", "perfect", "great",
        "cool", "nice", "works", "works for me", "that works", "all good",
        "let's do it", "lets do it", "go for it", "make it so", "affirmative",
        "sounds good", "1", "👍",
    )
    NEGATIVE = (
        "no", "nope", "cancel", "stop", "don't", "do not", "not now", "later",
        "no thanks", "wait", "hold on", "forget it", "never mind", "abort",
        "nah", "skip", "leave it", "not really", "don't do it", "do not do it",
    )

    def _strip_chatter(self, text: str) -> str:
        """Remove greetings and polite prefixes from a manager message."""
        cleaned = str(text or "").strip()
        cleaned = re.sub(
            r"^(?:hi|hello|hey|good\s+(?:morning|afternoon|evening))[,\s!]+",
            "",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(
            r"^(?:please\s+)?(?:could|can|would)\s+you\s+"
            r"(?:mind\s+)?(?:please\s+)?",
            "",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(r"^please\s+", "", cleaned, flags=re.I)
        cleaned = re.sub(
            r"^(?:i\s+(?:want|need|would\s+like)\s+(?:you\s+)?to\s+"
            r"|i'd\s+like\s+(?:you\s+)?to\s+)",
            "",
            cleaned,
            flags=re.I,
        )
        gerunds = {
            "adding": "add", "removing": "remove", "creating": "create",
            "making": "make", "setting": "set", "deleting": "delete",
            "inviting": "invite", "putting": "put", "including": "include",
            "assigning": "assign", "linking": "link", "starting": "start",
        }
        first, _, rest = cleaned.partition(" ")
        replacement = gerunds.get(first.lower())
        if replacement:
            cleaned = f"{replacement} {rest}".strip()
        return cleaned.strip()

    def _is_affirmative(self, text: str) -> bool:
        """Accept ok / fine / confirm / yes / sure / go ahead … as consent."""
        answer = _ic(text)
        if answer.startswith("please "):
            answer = answer[7:]
        if not answer:
            return False
        if "confirm" in answer:
            return True
        return any(
            answer == word or answer.startswith(f"{word} ")
            or answer.startswith(f"{word},") or answer.startswith(f"{word}.")
            for word in self.AFFIRMATIVE
        )

    def _is_negative(self, text: str) -> bool:
        """Accept no / cancel / not now / later … as refusal."""
        answer = _ic(text)
        if answer.startswith("please "):
            answer = answer[7:]
        if not answer:
            return False
        return any(
            answer == word or answer.startswith(f"{word} ")
            or answer.startswith(f"{word},") or answer.startswith(f"{word}.")
            for word in self.NEGATIVE
        )

    def _find_team(self, company: Any, phrase: str) -> Any:
        """Find a team from a natural phrase ("the Platform team")."""
        text = (phrase or "").strip().strip('"').strip("'")
        text = text.rstrip("?.!,")
        text = re.sub(r"^the\s+", "", text, flags=re.I)
        text = re.sub(r"\s+team$", "", text, flags=re.I)
        if not text:
            return None
        team = company.team_by_name(text)
        if team is not None:
            return team
        # Last resort: a team whose name appears inside the phrase.
        wanted = _ic(text)
        return next(
            (item for item in company.teams if item.name.lower() in wanted),
            None,
        )

    def _confirm_action(
        self,
        action: Dict[str, Any],
        summary: str,
        options: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """Ask for consent before a write; any ok/fine/yes will execute it."""
        return {
            "reply": f"{summary}\n\nShall I go ahead?",
            "state": {
                "intent": "pending_action",
                "step": "confirm",
                "draft": {"action": action, "summary": summary},
            },
            "options": options or [
                {"label": "Yes, do it", "value": "yes"},
                {"label": "No, cancel", "value": "no"},
            ],
            "suggestions": [],
        }

    def _looks_like_new_order(self, text: str) -> bool:
        """Tell whether a reply is actually a different request."""
        lowered = _ic(self._strip_chatter(text))
        return bool(re.match(
            r"^(add|remove|delete|create|make|set|show|what|who|open|link|"
            r"dispatch|review|turn|start|build|i need|we need|suggest)\b",
            lowered,
        ))

    def _execute_action(
        self,
        company: Any,
        action: Dict[str, Any],
        actor: str,
        can_manage: bool,
        can_admin: bool,
    ) -> Dict[str, Any]:
        """Execute a confirmed action and answer in plain language."""
        kind = action.get("type", "")
        if kind == "create_team":
            if not can_manage:
                return {"reply": _denied("create teams"), "state": None}
            name = action.get("name", "")
            if company.team_by_name(name):
                return {"reply": f"There is already a team called **{name}**.", "state": None}
            try:
                company = self.manager.add_team(company.id, {"name": name}, actor=actor)
            except Exception as ex:
                return {"reply": f"I couldn't create the team: `{ex}`.", "state": None}
            team = company.team_by_name(name)
            return {
                "reply": (
                    f"Done — **{team.name if team else name}** is created. "
                    "You can add people, choose a lead, or create a mission for it "
                    "whenever you like."
                ),
                "state": None,
                "changed": True,
                "suggestions": ["Choose a lead", "Show teams", "Create a mission"],
            }
        if kind == "add_user":
            if not can_admin:
                return {"reply": _denied("add company users"), "state": None}
            username = action.get("username", "")
            display = action.get("display") or username
            role = action.get("role", "member")
            password = secrets.token_urlsafe(6)
            try:
                result = self.security.create_company_user(
                    company_id=company.id,
                    username=username,
                    password=password,
                    role=role,
                    title=display if display != username else "",
                    user_role="user",
                )
            except Exception as ex:
                return {"reply": f"I couldn't add {display}: `{ex}`.", "state": None}
            if result.get("created"):
                reply = (
                    f"Done — **{display}** is part of the company as **{role}**. "
                    f"Their username is `{result['username']}` and their temporary "
                    f"password is `{password}`. They can change it after signing in."
                )
            else:
                reply = (
                    f"Done — **{display}** was already a codx-junior user, so I added "
                    f"them to the company as **{role}**."
                )
            return {
                "reply": reply,
                "state": None,
                "changed": True,
                "suggestions": ["Show people", "I need a team", "What needs my attention?"],
            }
        if kind == "add_member":
            if not can_manage:
                return {"reply": _denied("manage teams"), "state": None}
            team = company.team(action.get("team_id", ""))
            if team is None:
                return {"reply": "I can't find that team anymore.", "state": None}
            try:
                company = self.manager.add_team_members(
                    company.id,
                    team.id,
                    [{"kind": action.get("kind", "profile"), "name": action.get("name", "")}],
                    actor=actor,
                )
            except Exception as ex:
                return {"reply": f"I couldn't add that person: `{ex}`.", "state": None}
            team = company.team(team.id)
            return {
                "reply": f"Done — **{action.get('name')}** is now part of **{team.name}**.",
                "state": None,
                "changed": True,
                "suggestions": ["Show teams", "Choose a lead", "Create a mission"],
            }
        if kind == "remove_member":
            if not can_manage:
                return {"reply": _denied("manage teams"), "state": None}
            team = company.team(action.get("team_id", ""))
            if team is None:
                return {"reply": "I can't find that team anymore.", "state": None}
            try:
                self.manager.remove_team_members(
                    company.id, team.id, [action.get("name", "")], actor=actor
                )
            except Exception as ex:
                return {"reply": f"I couldn't remove that person: `{ex}`.", "state": None}
            return {
                "reply": f"Done — **{action.get('name')}** was removed from **{team.name}**.",
                "state": None,
                "changed": True,
                "suggestions": ["Show teams", "Add a person"],
            }
        if kind == "set_lead":
            if not can_manage:
                return {"reply": _denied("manage teams"), "state": None}
            team = company.team(action.get("team_id", ""))
            if team is None:
                return {"reply": "I can't find that team anymore.", "state": None}
            try:
                self.manager.set_team_lead(
                    company.id,
                    team.id,
                    action.get("kind", "profile"),
                    action.get("name", ""),
                    actor=actor,
                )
            except Exception as ex:
                return {"reply": f"I couldn't set that lead: `{ex}`.", "state": None}
            return {
                "reply": f"Done — **{action.get('name')}** leads **{team.name}** now.",
                "state": None,
                "changed": True,
                "suggestions": ["Show teams", "Create a mission"],
            }
        if kind == "delete_team":
            if not can_manage:
                return {"reply": _denied("delete teams"), "state": None}
            team = company.team(action.get("team_id", ""))
            if team is None:
                return {"reply": "I can't find that team anymore.", "state": None}
            try:
                self.manager.delete_team(company.id, team.id, actor=actor)
            except Exception as ex:
                return {"reply": f"I couldn't delete the team: `{ex}`.", "state": None}
            return {
                "reply": f"Done — team **{team.name}** was deleted.",
                "state": None,
                "changed": True,
                "suggestions": ["Show teams", "What needs my attention?"],
            }
        if kind == "delete_company":
            if not can_admin:
                return {"reply": _denied("delete the company"), "state": None}
            name = company.name
            try:
                self.manager.delete_company(company.id, actor=actor)
            except Exception as ex:
                return {"reply": f"I couldn't delete the company: `{ex}`.", "state": None}
            return {
                "reply": f"Done — **{name}** was deleted.",
                "state": None,
                "changed": True,
                "deleted": True,
            }
        if kind == "edit_company":
            if not can_manage:
                return {"reply": _denied("change the company settings"), "state": None}
            field = action.get("field", "")
            label = action.get("label") or field
            try:
                self.manager.update_company(
                    company.id, {field: action.get("value", "")}, actor=actor
                )
            except Exception as ex:
                return {"reply": f"I couldn't save that: `{ex}`.", "state": None}
            return {
                "reply": f"Done — the {label} is updated.",
                "state": None,
                "changed": True,
                "suggestions": ["Open company settings", "What needs my attention?"],
            }
        if kind == "create_mission":
            if not can_manage:
                return {"reply": _denied("create missions"), "state": None}
            title = action.get("title", "")
            project_id = action.get("project_id", "")
            team_id = action.get("team_id", "")
            status = "ready" if project_id else "draft"
            try:
                company = self.manager.add_mission(
                    company.id,
                    {
                        "title": title,
                        "objective": title,
                        "team_id": team_id,
                        "project_id": project_id,
                        "status": status,
                        "created_by": actor,
                    },
                    actor=actor,
                )
            except Exception as ex:
                return {"reply": f"I couldn't create that mission: `{ex}`.", "state": None}
            if status == "ready":
                return {
                    "reply": f"Done — mission **{title}** is ready. Want me to start it now?",
                    "state": None,
                    "changed": True,
                    "suggestions": [f"Dispatch {title}", "Show missions"],
                }
            return {
                "reply": (
                    f"Done — mission **{title}** is saved as a draft. Link a project "
                    "when you are ready and I can start it."
                ),
                "state": None,
                "changed": True,
                "suggestions": ["Show projects", "Show missions"],
            }
        if kind == "link_project":
            if not can_manage:
                return {"reply": _denied("link projects"), "state": None}
            project_id = action.get("project_id", "")
            name = action.get("name") or project_id
            try:
                self.manager.link_project(company.id, project_id, actor=actor)
            except Exception as ex:
                return {"reply": f"I couldn't link that project: `{ex}`.", "state": None}
            return {
                "reply": f"Done — **{name}** is linked to the company.",
                "state": None,
                "changed": True,
                "suggestions": ["Show projects", "Create a mission"],
            }
        if kind == "create_project":
            if not can_manage:
                return {"reply": _denied("create projects"), "state": None}
            name = action.get("name", "")
            path = action.get("path", "")
            if not path:
                return {"reply": "I need a name or path for the new project.", "state": None}
            try:
                from codx.junior.project.project_manager import create_project
                from codx.junior.project.project_discover import update_project_snapshot

                user = None
                try:
                    user = self.security.find_user(username=actor)
                except Exception:
                    user = None
                project = create_project(project_path=path, user=user)
                if project is None:
                    raise RuntimeError("project creation returned no project")
                update_project_snapshot(project)
            except Exception as ex:
                return {"reply": f"I couldn't create the project: `{ex}`.", "state": None}
            linked = True
            try:
                self.manager.link_project(company.id, project.project_id, actor=actor)
            except Exception as ex:
                linked = False
                logger.warning("Company assistant: project created but not linked: %s", ex)
            return {
                "reply": (
                    f"Done — project **{project.project_name or name}** is created at "
                    f"`{getattr(project, 'abs_project_path', '') or getattr(project, 'project_path', '') or path}`"
                    + (" and linked to the company." if linked else
                       " but I couldn't link it to the company yet.")
                ),
                "state": None,
                "changed": True,
                "suggestions": ["Show projects", "Create a mission", "I need a team"],
            }
        if kind == "unlink_project":
            if not can_manage:
                return {"reply": _denied("remove projects"), "state": None}
            project_id = action.get("project_id", "")
            name = action.get("name") or project_id
            try:
                self.manager.unlink_project(company.id, project_id, actor=actor)
            except Exception as ex:
                return {
                    "reply": (
                        f"I couldn't remove **{name}** from the company: `{ex}`. "
                        "If it has open missions, reassign them first."
                    ),
                    "state": None,
                }
            return {
                "reply": (
                    f"Done — **{name}** is no longer mapped to the company. "
                    "The project itself is untouched."
                ),
                "state": None,
                "changed": True,
                "suggestions": ["Show projects", "Link a project", "Create a new project"],
            }
        if kind == "dispatch_mission":
            if not can_manage:
                return {"reply": _denied("dispatch missions"), "state": None}
            mission = company.get_mission(action.get("mission_id", ""))
            if mission is None:
                return {"reply": "I can't find that mission anymore.", "state": None}
            try:
                company = self.manager.dispatch_mission(company.id, mission.id, actor=actor)
            except Exception as ex:
                return {"reply": f"I couldn't start the mission: `{ex}`.", "state": None}
            mission = company.get_mission(mission.id)
            return {
                "reply": f"Done — **{mission.title}** is running.",
                "state": None,
                "changed": True,
                "suggestions": ["What needs my attention?", "Show missions"],
            }
        if kind in ("accept_mission", "reject_mission"):
            if not can_manage:
                return {"reply": _denied("review missions"), "state": None}
            mission = company.get_mission(action.get("mission_id", ""))
            if mission is None:
                return {"reply": "I can't find that mission anymore.", "state": None}
            try:
                if kind == "accept_mission":
                    self.manager.accept_mission(
                        company.id,
                        mission.id,
                        result=action.get("result") or "Accepted through the company assistant",
                        actor=actor,
                    )
                    return {
                        "reply": f"Done — **{mission.title}** is accepted and marked as done.",
                        "state": None,
                        "changed": True,
                        "suggestions": ["What needs my attention?", "Show missions"],
                    }
                self.manager.reject_mission(
                    company.id,
                    mission.id,
                    reason=action.get("reason") or "Please review the result and try again.",
                    actor=actor,
                )
                return {
                    "reply": (
                        f"Done — **{mission.title}** went back to the team with your feedback."
                    ),
                    "state": None,
                    "changed": True,
                    "suggestions": ["What needs my attention?", "Show missions"],
                }
            except Exception as ex:
                return {"reply": f"I couldn't review that mission: `{ex}`.", "state": None}
        if kind == "autopilot":
            if not can_manage:
                return {"reply": _denied("change autopilot"), "state": None}
            enabled = bool(action.get("enabled"))
            try:
                self.manager.update_autonomy(
                    company.id,
                    {"enabled": enabled, "level": "supervised" if enabled else "off"},
                    actor=actor,
                )
            except Exception as ex:
                return {"reply": f"I couldn't change autopilot: `{ex}`.", "state": None}
            return {
                "reply": (
                    "Autopilot is **on** in supervised mode."
                    if enabled else "Autopilot is **off**. Nothing will start without you."
                ),
                "state": None,
                "changed": True,
                "suggestions": ["What needs my attention?", "Show missions"],
            }
        if kind == "change_role":
            if not can_admin:
                return {"reply": _denied("change company roles"), "state": None}
            username = action.get("username", "")
            role = action.get("role", "member")
            members = self.manager.company_members(company)
            target = next((member for member in members if member["username"] == username), None)
            if target is None:
                return {"reply": f"**{username}** is not a company member yet.", "state": None}
            if target.get("owner") and role != "admin":
                return {"reply": "The company owner always stays an admin.", "state": None}
            if target.get("company_role") == "admin" and role != "admin":
                admins = [
                    member for member in members
                    if member.get("company_role") == "admin"
                ]
                if len(admins) <= 1:
                    return {
                        "reply": "The last company admin must stay an admin.",
                        "state": None,
                    }
            try:
                self.security.add_company_member(company.id, username, role)
            except Exception as ex:
                return {"reply": f"I couldn't change that role: `{ex}`.", "state": None}
            return {
                "reply": f"Done — **{username}** is now a company **{role}**.",
                "state": None,
                "changed": True,
                "suggestions": ["Show people", "What needs my attention?"],
            }
        if kind == "remove_user":
            if not can_admin:
                return {"reply": _denied("remove company users"), "state": None}
            username = action.get("username", "")
            if username == company.owner:
                return {"reply": "The company owner cannot be removed.", "state": None}
            members = self.manager.company_members(company)
            target = next(
                (member for member in members if member["username"] == username),
                None,
            )
            if target is None:
                return {"reply": f"**{username}** is not a company member.", "state": None}
            if target.get("company_role") == "admin":
                admins = [
                    member for member in members
                    if member.get("company_role") == "admin"
                ]
                if len(admins) <= 1:
                    return {
                        "reply": "The last company admin cannot be removed.",
                        "state": None,
                    }
            try:
                removed = self.security.remove_company_member(company.id, username)
            except Exception as ex:
                return {"reply": f"I couldn't remove that person: `{ex}`.", "state": None}
            if not removed:
                return {"reply": f"**{username}** is not a company member.", "state": None}
            return {
                "reply": f"Done — **{username}** was removed from the company.",
                "state": None,
                "changed": True,
                "suggestions": ["Show people", "Add a person"],
            }
        return {"reply": "I don't know how to do that yet.", "state": None}

    def _question(
        self,
        reply: str,
        state: Dict[str, Any],
        options: Optional[List[Any]] = None,
        suggestions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build the next step of a guided conversation."""
        return {
            "reply": reply,
            "state": state,
            "options": options or [],
            "suggestions": suggestions or [],
        }

    def _is_cancel(self, text: str) -> bool:
        """Tell whether the manager wants to stop the current flow."""
        return _ic(text) in (
            "cancel", "stop", "never mind", "nevermind", "later",
            "not now", "no thanks", "no",
        )

    def _cancelled(self) -> Dict[str, Any]:
        return {
            "reply": "No problem — I've stopped. What would you like to do?",
            "state": None,
            "suggestions": list(VIEW_SUGGESTIONS[""]),
        }

    def _role_options(self) -> List[Dict[str, str]]:
        return [
            {"label": "Help run the company", "value": "manager"},
            {"label": "Just follow the work", "value": "member"},
            {"label": "Manage people and settings", "value": "admin"},
        ]

    def _role_from_answer(self, text: str) -> Optional[str]:
        """Map a plain-language answer onto a company role."""
        answer = _ic(text)
        if answer in ("admin", "manager", "member"):
            return answer
        if any(word in answer for word in ("admin", "settings", "manage people", "manage users")):
            return "admin"
        if any(word in answer for word in ("manage", "manager", "help run", "lead", "owner")):
            return "manager"
        if any(word in answer for word in ("follow", "member", "view", "employee", "just", "worker")):
            return "member"
        return None

    def _username_from_display(self, display: str) -> str:
        """Turn a human name ("Carol Smith") into a login username."""
        value = (display or "").strip().lower()
        value = re.sub(r"\s+", ".", value)
        value = re.sub(r"[^a-z0-9._-]", "", value)
        return value.strip(".-")[:40]

    def _team_options(self, company: Any) -> List[Dict[str, str]]:
        return [{"label": team.name, "value": team.id} for team in company.teams]

    def _project_options(self, company: Any) -> List[Dict[str, str]]:
        return [
            {"label": project.name or project.project_id, "value": project.project_id}
            for project in company.projects
        ]

    def _people_options(self, company: Any) -> List[Dict[str, str]]:
        """People and AI helpers the manager can pick from, in plain language."""
        options = [
            {"label": member["username"], "value": f"user:{member['username']}"}
            for member in self.manager.company_members(company)
        ]
        try:
            profiles = self.manager.references().get("profiles", [])
        except Exception:  # pragma: no cover - profile catalog is optional
            profiles = []
        options += [
            {"label": f"{profile['name']} (AI helper)", "value": f"profile:{profile['name']}"}
            for profile in profiles[:12]
        ]
        return options[:24]

    # -- build a team / profile from a plain-language need -------------

    def _is_build_need(self, lowered: str) -> bool:
        """Detect “I need a developer”, “suggest an IT team”, …"""
        patterns = (
            r"^(i|we)\s+(need|want|would\s+like)\b",
            r"^(suggest|recommend|propose)\b.*\b(team|profiles?)\b",
            r"^(build|assemble|set\s+up|setup|design)\b.*\bteam\b",
            r"^create\s+(a\s+)?team\s+(for|to|that)\b",
            r"^(create|add|make)\s+(a\s+)?(new\s+)?profile\b",
            r"^(which|what)\s+(profiles?|team)\b.*\b(create|need|use)\b",
        )
        return any(re.search(pattern, lowered, re.I) for pattern in patterns)

    def _has_need_details(self, text: str) -> bool:
        """Tell whether the need names a role/team we can map."""
        lowered = _ic(text)
        for role in ROLES.values():
            if any(keyword in lowered for keyword in role["keywords"]):
                return True
        for preset in TEAM_PRESETS.values():
            if any(keyword in lowered for keyword in preset["keywords"]):
                return True
        return False

    def _profile_manager(self, project_id: str) -> Any:
        """Return the ProfileManager of a project (injectable for tests)."""
        if self.profile_manager_factory:
            try:
                return self.profile_manager_factory(project_id)
            except Exception as ex:
                logger.debug("Company assistant: profile manager factory failed: %s", ex)
                return None
        settings = self.manager.project_settings(project_id)
        if settings is None:
            return None
        from codx.junior.profiles.profile_manager import ProfileManager

        return ProfileManager(settings=settings)

    def _available_profiles(self, project_id: str) -> List[str]:
        manager = self._profile_manager(project_id)
        if manager is None:
            return []
        try:
            return [profile.name for profile in manager.list_all_profiles() if profile and profile.name]
        except Exception as ex:
            logger.debug("Company assistant: profile catalog failed: %s", ex)
            return []

    def _available_tool_names(self) -> List[str]:
        """Return the registered tool names, or [] when the runtime is absent."""
        try:
            from codx.junior.tools.profile_tools import _available_tool_names

            return _available_tool_names()
        except Exception as ex:  # pragma: no cover - tools are optional at import
            logger.debug("Company assistant: tool registry unavailable: %s", ex)
            return []

    def _start_build_team(self, company: Any, text: str, can_manage: bool, can_admin: bool = False) -> Dict[str, Any]:
        """Start “I need …” and ask for details when the need is generic."""
        if not can_manage:
            return {"reply": _denied("build teams")}
        lowered = _ic(text)
        if any(word in lowered for word in ("add a person", "add user", "invite", "onboard")):
            return self._start_add_user(company, text, can_admin)
        named_team = re.search(r"(?:called|named)\s+(.+)$", text, re.I)
        if named_team and "team" in lowered:
            name = named_team.group(1).strip().strip('"').strip("'").rstrip("?.!,")
            if name:
                return self._confirm_action(
                    {"type": "create_team", "name": name},
                    f"I'll create a team called **{name}**.",
                )
        if not self._has_need_details(text):
            return self._question(
                "Tell me what you need in plain language. For example: "
                "**I need a developer**, **I need an IT team** or **I need a QA**.",
                {"intent": "build_team", "step": "need", "draft": {}},
                suggestions=["I need a developer", "I need an IT team", "I need a QA"],
            )
        return self._recommend_profiles_for(company, text, can_manage)

    def _recommend_profiles_for(self, company: Any, need: str, can_manage: bool) -> Dict[str, Any]:
        """Inspect the linked project and ask for confirmation."""
        if not can_manage:
            return {"reply": _denied("build teams")}
        linked_ids = {project.project_id for project in company.projects}
        if not linked_ids:
            return {
                "reply": (
                    "I need a linked project to inspect before I can suggest the "
                    "right profiles. Let's link one first."
                ),
                "suggestions": ["Link a project"],
            }
        try:
            discovered = self.manager.references().get("projects", [])
        except Exception:
            discovered = []
        candidates = [
            project for project in discovered
            if project.get("project_id") in linked_ids
        ]
        if not candidates:
            return {
                "reply": (
                    "I couldn't inspect the linked project. Please check that it "
                    "is available, then ask me again."
                )
            }
        project = candidates[0]
        profiles = self._available_profiles(project["project_id"])
        suggestion = recommend_profiles(
            need,
            company_name=company.name,
            available_profiles=profiles,
            available_tools=self._available_tool_names(),
            projects=candidates,
        )
        if not suggestion.get("roles"):
            return {
                "reply": (
                    "I couldn't map that to a team yet. Tell me the kind of work "
                    "the team should do (for example: build software, test it, run "
                    "the infrastructure, support users)."
                ),
                "state": {"intent": "build_team", "step": "need", "draft": {}},
            }
        mode = suggestion.get("mode", "team")
        options = (
            [
                {"label": "Create the profile", "value": "create"},
                {"label": "Show me the details", "value": "details"},
                {"label": "Not now", "value": "cancel"},
            ]
            if mode == "profile"
            else [
                {"label": "Create the team and profiles", "value": "create"},
                {"label": "Show the profiles first", "value": "details"},
                {"label": "Use existing profiles only", "value": "existing"},
                {"label": "Not now", "value": "cancel"},
            ]
        )
        state = {
            "intent": "build_team",
            "step": "confirm",
            "draft": {"suggestion": suggestion},
        }
        project_note = (
            f"\n\nI'll set this up in **{suggestion.get('project_name') or project['project_id']}**."
            if suggestion.get("project_id") else ""
        )
        return self._question(
            suggestion["summary"] + project_note + "\n\nShould I create it?",
            state,
            options=options,
        )

    def _continue_build_team(
        self, company: Any, state: Dict[str, Any], text: str, actor: str, can_manage: bool
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("build teams"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        step = state.get("step")
        draft = dict(state.get("draft") or {})
        if step == "need":
            return self._recommend_profiles_for(company, text, can_manage)
        suggestion = draft.get("suggestion")
        if not isinstance(suggestion, dict):
            return {"reply": "Let's start again — what do you need?", "state": None}
        action = _ic(text)
        if "detail" in action or "show" in action or action in ("what", "profiles"):
            return {
                "reply": self._suggestion_details(suggestion),
                "state": state,
                "options": self._build_team_options(suggestion.get("mode", "team")),
            }
        if "existing" in action or "reuse" in action:
            return self._apply_suggestion(company, suggestion, actor, create_profiles=False)
        if self._is_negative(text):
            return self._cancelled()
        if self._is_affirmative(text) or "create" in action or "build" in action:
            return self._apply_suggestion(company, suggestion, actor, create_profiles=True)
        return self._question(
            "Should I create it?",
            state,
            options=self._build_team_options(suggestion.get("mode", "team")),
        )

    def _build_team_options(self, mode: str) -> List[Dict[str, str]]:
        if mode == "profile":
            return [
                {"label": "Create the profile", "value": "create"},
                {"label": "Show me the details", "value": "details"},
                {"label": "Not now", "value": "cancel"},
            ]
        return [
            {"label": "Create the team and profiles", "value": "create"},
            {"label": "Show the profiles first", "value": "details"},
            {"label": "Use existing profiles only", "value": "existing"},
            {"label": "Not now", "value": "cancel"},
        ]

    def _suggestion_details(self, suggestion: Dict[str, Any]) -> str:
        lines = [
            f"### Suggested {('team' if suggestion.get('mode') == 'team' else 'profile')}",
            f"Project: **{suggestion.get('project_name') or suggestion.get('project_id')}**",
            "",
        ]
        for role in suggestion.get("roles", []):
            action = "already exists" if role.get("existing") else (
                "will be created" if role.get("create") else "use existing"
            )
            bases = ", ".join(role.get("bases") or []) or "no base profile"
            tools = ", ".join(role.get("tools") or []) or "no extra tools"
            lines += [
                f"**{role.get('title')}** (`{role.get('profile_name')}`) — {action}",
                f"- Based on: {bases}",
                f"- Tools: {tools}",
                f"- Owns: {'; '.join(role.get('responsibilities') or [])}",
                "",
            ]
        return "\n".join(lines).strip()

    def _apply_suggestion(
        self,
        company: Any,
        suggestion: Dict[str, Any],
        actor: str,
        create_profiles: bool,
    ) -> Dict[str, Any]:
        """Create the missing project profiles and the suggested team."""
        project_id = str(suggestion.get("project_id") or "")
        if project_id not in {project.project_id for project in company.projects}:
            return {
                "reply": "That project is not linked to the company. Link it first and ask me again.",
                "state": None,
            }
        project_name = suggestion.get("project_name") or project_id
        profile_manager = self._profile_manager(project_id) if project_id else None
        if profile_manager is None:
            return {
                "reply": (
                    "I couldn't open the project profiles. Please make sure the "
                    "project is available and ask me again."
                ),
                "state": None,
            }
        created: List[str] = []
        reused: List[str] = []
        errors: List[str] = []
        available = set(self._available_profiles(project_id))
        available_tools = set(self._available_tool_names())

        # The suggestion is stored client-side between turns, so never trust it
        # blindly: names, bases and tools are validated here before a write.
        safe_roles: List[Dict[str, Any]] = []
        for role in suggestion.get("roles", []) or []:
            name = str(role.get("profile_name") or "").strip()
            if (
                not name
                or len(name) > 64
                or ".." in name
                or "/" in name
                or "\\" in name
                or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", name)
            ):
                errors.append(f"invalid profile name {name!r}")
                continue
            bases = [base for base in role.get("bases") or [] if base in available]
            tools = [
                tool for tool in role.get("tools") or []
                if not available_tools or tool in available_tools
            ]
            safe_roles.append({**role, "profile_name": name, "bases": bases, "tools": tools})

        if create_profiles:
            from codx.junior.model.profile import Profile

            for role in safe_roles:
                name = role.get("profile_name", "")
                if not role.get("create") or not name:
                    continue
                if name in available:
                    continue
                try:
                    profile = Profile(
                        name=name,
                        description=role.get("description", ""),
                        category=role.get("category", "agent"),
                        content=profile_content(
                            role,
                            company_name=company.name,
                            project_name=project_name,
                            stack=suggestion.get("stack") or {},
                        ),
                        profiles=list(role.get("bases") or []),
                        tools=list(role.get("tools") or []),
                        tags=["company", "team", "codx-junior"],
                        project_id=project_id,
                        use_knowledge=True,
                    )
                    profile_manager.save_profile(profile)
                    available.add(name)
                    created.append(name)
                except Exception as ex:
                    logger.warning("Company assistant: could not create profile %s: %s", name, ex)
                    errors.append(f"{name}: {ex}")

        # Resolve the profile actually used by each role.
        team_members: List[Dict[str, Any]] = []
        used_names: set = set()
        for role in safe_roles:
            candidate = role.get("profile_name", "")
            if candidate not in available:
                candidate = next(
                    (base for base in role.get("bases") or [] if base in available),
                    "",
                )
            if not candidate or candidate in used_names:
                continue
            used_names.add(candidate)
            if candidate in created:
                pass
            elif candidate not in reused:
                reused.append(candidate)
            team_members.append({
                "kind": "profile",
                "name": candidate,
                "role": role.get("title", ""),
                "responsibility": "; ".join(role.get("responsibilities") or []),
            })

        created_text = ", ".join(f"`{name}`" for name in created) or "none"
        reused_text = ", ".join(f"`{name}`" for name in reused) or "none"

        mode = "profile" if suggestion.get("mode") == "profile" else "team"
        if mode == "profile":
            lines = [
                f"Done — I set up the profile(s) in **{project_name}**.",
                f"- Created: {created_text}",
                f"- Reused: {reused_text}",
            ]
            if errors:
                lines.append(f"- Problems: {'; '.join(errors)}")
            lines.append("")
            lines.append("You can add this profile to a team whenever you like — just tell me.")
            return {
                "reply": "\n".join(lines),
                "state": None,
                "changed": bool(created),
                "suggestions": ["Show teams", "Create a team", "What needs my attention?"],
            }

        if not team_members:
            return {
                "reply": (
                    "I couldn't find or create a profile to put in the team. "
                    "The detail view shows what I found."
                ),
                "state": None,
                "suggestions": ["Show profiles"],
            }

        team_name = str(suggestion.get("team_name") or "Company Team").strip()[:120] or "Company Team"
        try:
            existing = company.team_by_name(team_name)
            if existing is not None:
                company = self.manager.add_team_members(
                    company.id,
                    existing.id,
                    team_members,
                    actor=actor,
                )
                team = company.team_by_name(team_name)
                if team is not None and not team.lead_name:
                    company = self.manager.set_team_lead(
                        company.id,
                        team.id,
                        "profile",
                        team_members[0]["name"],
                        actor=actor,
                    )
                    team = company.team_by_name(team_name)
                action = "updated"
            else:
                payload = {
                    "name": team_name,
                    "description": (
                        f"Suggested by codx-junior for: {suggestion.get('need', '')}"
                    ),
                    "purpose": suggestion.get("need", ""),
                    "members": team_members,
                    "lead_kind": "profile",
                    "lead_name": team_members[0]["name"],
                    "project_ids": [project_id] if project_id else [],
                    "autonomy": "supervised",
                }
                company = self.manager.add_team(company.id, payload, actor=actor)
                team = company.team_by_name(team_name)
                action = "created"
        except Exception as ex:
            return {
                "reply": (
                    f"I created the profiles but couldn't {('update' if 'team' in locals() else 'create')} "
                    f"the team: `{ex}`. You can ask me to try again."
                ),
                "state": None,
                "changed": bool(created),
            }

        lines = [
            f"Done — **{team_name}** is {action} in **{project_name}**.",
            f"- Profiles created: {created_text}",
            f"- Profiles reused: {reused_text}",
            f"- Team lead: **{team_members[0]['name']}**",
        ]
        if errors:
            lines.append(f"- Problems: {'; '.join(errors)}")
        lines.append("")
        lines.append(
            "You can ask me to add people, change the lead or create the first "
            "mission for this team whenever you like."
        )
        return {
            "reply": "\n".join(lines),
            "state": None,
            "changed": True,
            "suggestions": ["Show teams", "Create a mission", "What needs my attention?"],
        }

    # -- create team ---------------------------------------------------

    def _start_create_team(self, can_manage: bool) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("create teams")}
        return self._question(
            "Of course. What should we call the team? A short name is perfect — "
            "for example **Platform**, **Sales** or **Customer care**.",
            {"intent": "create_team", "step": "name", "draft": {}},
            suggestions=["Platform", "Product", "Customer care"],
        )

    def _continue_create_team(
        self, company: Any, state: Dict[str, Any], text: str, actor: str, can_manage: bool
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("create teams"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        name = text.strip().strip('"').strip("'")
        if not name:
            return self._question("What name should the team have?", state)
        if company.team_by_name(name):
            return self._question(
                f"There is already a team called **{name}**. What other name should we use?",
                state,
            )
        return self._confirm_action(
            {"type": "create_team", "name": name},
            f"I'll create a team called **{name}**.",
        )

    # -- add a person --------------------------------------------------

    def _start_add_user_named(self, company: Any, display: str, can_admin: bool) -> Dict[str, Any]:
        """Start adding a named person (no username syntax required)."""
        if not can_admin:
            return {"reply": _denied("add company users")}
        display = (display or "").strip().strip('"').strip("'").rstrip("?.!,")
        username = self._username_from_display(display)
        if not username:
            return self._start_add_user(company, "add a person", can_admin)
        return self._question(
            f"Got it — **{display}**. What will {display} do in the company?",
            {
                "intent": "add_user",
                "step": "role",
                "draft": {"display": display, "username": username},
            },
            options=self._role_options(),
        )

    def _start_add_user(self, company: Any, text: str, can_admin: bool) -> Dict[str, Any]:
        """Start the add-person conversation (one question at a time)."""
        if not can_admin:
            return {"reply": _denied("add company users")}
        parsed = self._parse_user_command(text)
        display = (parsed.get("username") or "").strip()
        if display:
            return self._question(
                f"Got it — **{display}**. What will {display} do in the company?",
                {"intent": "add_user", "step": "role", "draft": {"display": display}},
                options=self._role_options(),
            )
        return self._question(
            "Who would you like to add? You can give me their first name or username.",
            {"intent": "add_user", "step": "name", "draft": {}},
        )

    def _continue_add_user(
        self, company: Any, state: Dict[str, Any], text: str, can_admin: bool
    ) -> Dict[str, Any]:
        if not can_admin:
            return {"reply": _denied("add company users"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        draft = dict(state.get("draft") or {})
        step = state.get("step")

        if step == "name":
            display = text.strip().strip('"').strip("'").rstrip("?.!,")
            username = self._username_from_display(display)
            if not username:
                return self._question(
                    "I need a name to create the account. What is the person's name?",
                    state,
                )
            draft["display"] = display
            draft["username"] = username
            return self._question(
                f"Got it — **{display}**. What will {display} do in the company?",
                {"intent": "add_user", "step": "role", "draft": draft},
                options=self._role_options(),
            )

        if step == "role":
            role = self._role_from_answer(text)
            if role is None:
                return self._question(
                    "Should this person help run the company, just follow the work, "
                    "or manage people and settings?",
                    state,
                    options=self._role_options(),
                )
            display = draft.get("display") or draft.get("username") or "the new person"
            return self._confirm_action(
                {
                    "type": "add_user",
                    "username": draft.get("username", ""),
                    "display": display,
                    "role": role,
                },
                (
                    f"I'll add **{display}** to the company as **{role}** and create "
                    "a temporary password for them."
                ),
            )

        return {"reply": "Let's start again — who would you like to add?", "state": None}

    # -- add someone to a team ----------------------------------------

    def _start_add_team_member(self, company: Any, can_manage: bool) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("manage teams")}
        if not company.teams:
            return {
                "reply": (
                    "There are no teams yet. I can create one first if you like."
                ),
                "state": None,
                "suggestions": ["Create a team"],
            }
        if len(company.teams) == 1:
            team = company.teams[0]
            return self._question(
                f"Who should join **{team.name}**? You can use their name.",
                {"intent": "add_member", "step": "person", "draft": {"team_id": team.id}},
                options=self._people_options(company),
            )
        return self._question(
            "Which team should they join?",
            {"intent": "add_member", "step": "team", "draft": {}},
            options=self._team_options(company),
        )

    def _continue_add_member(
        self, company: Any, state: Dict[str, Any], text: str, actor: str, can_manage: bool
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("manage teams"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        draft = dict(state.get("draft") or {})
        step = state.get("step")

        if step == "team":
            team = next(
                (item for item in company.teams if item.id == text or item.name.lower() == _ic(text)),
                None,
            )
            if team is None:
                return self._question(
                    "Which team? Pick one below.",
                    state,
                    options=self._team_options(company),
                )
            draft["team_id"] = team.id
            return self._question(
                f"Who should join **{team.name}**?",
                {"intent": "add_member", "step": "person", "draft": draft},
                options=self._people_options(company),
            )

        if step == "person":
            team = company.team(draft.get("team_id", ""))
            if team is None:
                return {"reply": "I lost track of the team. Which team should they join?", "state": None}
            kind, name = self._resolve_member(company, text)
            return self._confirm_action(
                {"type": "add_member", "team_id": team.id, "kind": kind, "name": name},
                f"I'll add **{name}** to **{team.name}**.",
            )

        return {"reply": "Which team should they join?", "state": None}

    # -- change company details ---------------------------------------

    def _start_edit_company(self, company: Any, can_manage: bool) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("change the company settings")}
        return self._question(
            "Of course. What would you like to change?",
            {"intent": "edit_company", "step": "field", "draft": {}},
            options=[
                {"label": "Company name", "value": "name"},
                {"label": "Mission — why we exist", "value": "mission"},
                {"label": "Vision — where we are going", "value": "vision"},
                {"label": "Website", "value": "website"},
                {"label": "Status (active / paused / archived)", "value": "status"},
                {"label": "Show all settings", "value": "all"},
            ],
            suggestions=["Show all settings"],
        )

    def _continue_edit_company(
        self, company: Any, state: Dict[str, Any], text: str, can_manage: bool, actor: str
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("change the company settings"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        draft = dict(state.get("draft") or {})
        step = state.get("step")
        field_labels = {
            "name": "company name",
            "mission": "mission",
            "vision": "vision",
            "website": "website",
            "status": "status",
        }

        if step == "field":
            answer = _ic(text)
            if answer in ("all", "everything", "show all", "show all settings", "full"):
                return self._settings_form(company, can_manage)
            field = None
            if answer in field_labels:
                field = answer
            elif "name" in answer:
                field = "name"
            elif "mission" in answer or "why" in answer:
                field = "mission"
            elif "vision" in answer or "where" in answer:
                field = "vision"
            elif "website" in answer or "site" in answer or "url" in answer:
                field = "website"
            elif "status" in answer or "active" in answer or "pause" in answer:
                field = "status"
            if field is None:
                return self._question(
                    "Which detail would you like to change?",
                    state,
                    options=[
                        {"label": "Company name", "value": "name"},
                        {"label": "Mission", "value": "mission"},
                        {"label": "Vision", "value": "vision"},
                        {"label": "Website", "value": "website"},
                        {"label": "Status", "value": "status"},
                        {"label": "Show all settings", "value": "all"},
                    ],
                )
            draft["field"] = field
            if field == "status":
                return self._question(
                    "Should the company be active, paused or archived?",
                    {"intent": "edit_company", "step": "value", "draft": draft},
                    options=[
                        {"label": "Active", "value": "active"},
                        {"label": "Paused", "value": "paused"},
                        {"label": "Archived", "value": "archived"},
                    ],
                )
            return self._question(
                f"What should the new {field_labels.get(field, field)} be?",
                {"intent": "edit_company", "step": "value", "draft": draft},
            )

        if step == "value":
            field = draft.get("field", "")
            value = text.strip()
            if field == "status":
                lowered = _ic(text)
                if "pause" in lowered:
                    value = "paused"
                elif "archiv" in lowered:
                    value = "archived"
                elif "active" in lowered or "live" in lowered:
                    value = "active"
                else:
                    return self._question(
                        "Should the company be active, paused or archived?",
                        state,
                        options=[
                            {"label": "Active", "value": "active"},
                            {"label": "Paused", "value": "paused"},
                            {"label": "Archived", "value": "archived"},
                        ],
                    )
            if field not in field_labels:
                return {"reply": "I lost track of what to change. What would you like to change?", "state": None}
            label = field_labels.get(field, field)
            return self._confirm_action(
                {"type": "edit_company", "field": field, "value": value, "label": label},
                f"I'll change the {label} to **{value}**.",
            )

        return {"reply": "What would you like to change?", "state": None}

    # -- create a mission ---------------------------------------------

    def _start_create_mission(self, company: Any, text: str, can_manage: bool, actor: str) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("create missions")}
        remainder = re.sub(
            r"^(?:create|new|add)\s+(?:a\s+|the\s+)?mission"
            r"(?:\s+(?:called|named|to|for))?\s*",
            "",
            text,
            flags=re.I,
        ).strip()
        draft: Dict[str, Any] = {}
        if remainder and remainder.lower() not in ("please", "now"):
            draft["title"] = remainder
        return self._mission_ask_next(company, draft, actor)

    def _mission_ask_next(self, company: Any, draft: Dict[str, Any], actor: str) -> Dict[str, Any]:
        """Ask the next minimum question, or create the mission."""
        if not draft.get("title"):
            return self._question(
                "What should the mission achieve? Say it in one line, for example "
                "“Ship the new onboarding”.",
                {"intent": "create_mission", "step": "title", "draft": draft},
            )
        if company.teams and "team_id" not in draft:
            return self._question(
                "Which team should own this mission?",
                {"intent": "create_mission", "step": "team", "draft": draft},
                options=self._team_options(company) + [{"label": "No team yet", "value": "__none__"}],
            )
        if company.projects and "project_id" not in draft:
            return self._question(
                "Which project should it run in?",
                {"intent": "create_mission", "step": "project", "draft": draft},
                options=self._project_options(company) + [{"label": "No project yet", "value": "__none__"}],
            )
        return self._create_mission_from_draft(company, draft, actor)

    def _continue_create_mission(
        self, company: Any, state: Dict[str, Any], text: str, actor: str, can_manage: bool
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("create missions"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        draft = dict(state.get("draft") or {})
        step = state.get("step")

        if step == "title":
            title = text.strip().strip('"').strip("'")
            if not title:
                return self._question("What should the mission achieve?", state)
            draft["title"] = title
        elif step == "team":
            answer = text.strip()
            if _ic(answer) in ("__none__", "none", "no team", "no team yet", "skip"):
                draft["team_id"] = ""
            else:
                team = next(
                    (item for item in company.teams if item.id == answer or item.name.lower() == _ic(answer)),
                    None,
                )
                if team is None:
                    return self._question(
                        "Which team should own it?",
                        state,
                        options=self._team_options(company) + [{"label": "No team yet", "value": "__none__"}],
                    )
                draft["team_id"] = team.id
        elif step == "project":
            answer = text.strip()
            if _ic(answer) in ("__none__", "none", "no project", "no project yet", "skip"):
                draft["project_id"] = ""
            else:
                project = next(
                    (
                        item
                        for item in company.projects
                        if item.project_id == answer
                        or (item.name or "").lower() == _ic(answer)
                    ),
                    None,
                )
                if project is None:
                    return self._question(
                        "Which project should it run in?",
                        state,
                        options=self._project_options(company) + [{"label": "No project yet", "value": "__none__"}],
                    )
                draft["project_id"] = project.project_id
        return self._mission_ask_next(company, draft, actor)

    def _create_mission_from_draft(self, company: Any, draft: Dict[str, Any], actor: str) -> Dict[str, Any]:
        title = draft.get("title", "")
        project_id = draft.get("project_id", "")
        team_id = draft.get("team_id", "")
        status = "ready" if project_id else "draft"
        where = ""
        if team_id:
            team = company.team(team_id)
            if team is not None:
                where = f" for **{team.name}**"
        return self._confirm_action(
            {
                "type": "create_mission",
                "title": title,
                "team_id": team_id,
                "project_id": project_id,
            },
            (
                f"I'll create the mission **{title}**{where}. It will stay as a "
                "draft until a project is linked."
                if status == "draft"
                else f"I'll create the mission **{title}**{where} and make it ready to start."
            ),
        )

    # -- organization --------------------------------------------------

    def _organization(self, company: Any) -> Dict[str, Any]:
        units = company.org_units
        if not units:
            return {
                "reply": (
                    "You haven't defined departments yet. That's optional — most "
                    "small companies can work with teams only."
                )
            }
        lines = ["### Organization"]
        for unit in units:
            lead = unit.lead_name or "no lead"
            lines.append(f"- **{unit.name}** ({unit.kind}) · lead: {lead}")
        return {"reply": "\n".join(lines)}

    def _continue_delete_team(
        self, company: Any, state: Dict[str, Any], text: str, can_manage: bool
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("delete teams"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        team = self._find_team(company, text)
        if team is None:
            team = next((item for item in company.teams if item.id == text), None)
        if team is None:
            return self._question(
                "Which team should I delete?",
                state,
                options=self._team_options(company),
            )
        return self._confirm_action(
            {"type": "delete_team", "team_id": team.id, "name": team.name},
            f"I'll delete the team **{team.name}**.",
        )

    def _continue_pending_action(
        self,
        company: Any,
        state: Dict[str, Any],
        text: str,
        actor: str,
        can_manage: bool,
        can_admin: bool,
        view: str = "",
        user: Any = None,
        language: str = "",
    ) -> Dict[str, Any]:
        """Execute a confirmed action when the user says ok/fine/yes/confirm."""
        draft = state.get("draft") or {}
        action = draft.get("action") or {}
        summary = draft.get("summary") or "do that"
        if self._is_negative(text):
            return {
                "reply": "No problem — I won't do that.",
                "state": None,
                "suggestions": list(VIEW_SUGGESTIONS.get(view or "", VIEW_SUGGESTIONS[""])),
            }
        if self._is_affirmative(text):
            return self._execute_action(company, action, actor, can_manage, can_admin)
        # The user changed their mind and asked for something else: drop the
        # pending action and handle the new request naturally.
        if self._looks_like_new_order(text):
            return self._dispatch_intent(
                company=company,
                text=text,
                view=view,
                actor=actor,
                can_manage=can_manage,
                can_admin=can_admin,
                history=[],
                user=user,
                language=language,
            )
        return {
            "reply": f"Just to confirm: {summary} Is that okay?",
            "state": state,
            "options": [
                {"label": "Yes, do it", "value": "yes"},
                {"label": "No, cancel", "value": "no"},
            ],
        }

    def _continue_flow(
        self,
        company: Any,
        state: Dict[str, Any],
        text: str,
        actor: str,
        can_manage: bool,
        can_admin: bool,
        view: str = "",
        user: Any = None,
        language: str = "",
    ) -> Dict[str, Any]:
        """Route the answer to the question the assistant asked last turn."""
        if self._is_cancel(text):
            return self._cancelled()
        intent = state.get("intent")
        if intent == "pending_action":
            return self._continue_pending_action(
                company, state, text, actor, can_manage, can_admin, view, user, language
            )
        if intent == "create_team":
            return self._continue_create_team(company, state, text, actor, can_manage)
        if intent == "add_user":
            return self._continue_add_user(company, state, text, can_admin)
        if intent == "add_member":
            return self._continue_add_member(company, state, text, actor, can_manage)
        if intent == "edit_company":
            return self._continue_edit_company(company, state, text, can_manage, actor)
        if intent == "create_mission":
            return self._continue_create_mission(company, state, text, actor, can_manage)
        if intent == "review_mission":
            return self._continue_review_mission(company, state, text, actor, can_manage)
        if intent == "link_project":
            return self._continue_link_project(company, state, text, actor, can_manage)
        if intent == "create_project":
            return self._continue_create_project(company, state, text, can_manage)
        if intent == "unlink_project":
            return self._continue_unlink_project(company, state, text, can_manage)
        if intent == "set_lead":
            return self._continue_set_lead(company, state, text, actor, can_manage)
        if intent == "build_team":
            return self._continue_build_team(company, state, text, actor, can_manage)
        if intent == "delete_team":
            return self._continue_delete_team(company, state, text, can_manage)
        return self._ai_fallback(
            company=company,
            text=text,
            actor=actor,
            user=user,
            language=language,
            view=view,
            history=[],
            fallback_reply="Let's start again. What would you like to do?",
        )

    def _submit_form(
        self,
        company: Any,
        form_id: str,
        values: Dict[str, Any],
        actor: str,
        can_manage: bool,
        can_admin: bool,
    ) -> Dict[str, Any]:
        """Execute a form rendered by the assistant."""
        if form_id == FORM_EDIT_COMPANY:
            if not can_manage:
                return {"reply": _denied("change the company settings")}
            patch = {
                key: values.get(key)
                for key in ("name", "description", "mission", "vision", "website", "status")
                if values.get(key) is not None
            }
            company = self.manager.update_company(company.id, patch, actor=actor)
            return {
                "reply": f"Done — **{company.name}** is updated.",
                "changed": True,
            }

        if form_id == FORM_ADD_USER:
            if not can_admin:
                return {"reply": _denied("add company users")}
            result = self.security.create_company_user(
                company_id=company.id,
                username=values.get("username", ""),
                password=values.get("password", ""),
                email=values.get("email", ""),
                role=values.get("role", COMPANY_ROLE_MEMBER),
                title=values.get("title", ""),
                user_role=values.get("user_role", "user"),
            )
            company = self.manager.get_company(company.id)
            action = "created" if result.get("created") else "enrolled"
            return {
                "reply": (
                    f"Done — **{result['username']}** was {action} as "
                    f"**{result['membership']['role']}**. They can sign in with "
                    f"the company workspace."
                ),
                "changed": True,
            }

        if form_id == FORM_CREATE_TEAM:
            if not can_manage:
                return {"reply": _denied("create teams")}
            lead = str(values.get("lead") or "")
            members = values.get("members") or []
            if isinstance(members, str):
                members = [members]
            members = list(members)
            if lead:
                members = [lead] + members
            payload = {
                "name": values.get("name", ""),
                "description": values.get("description", ""),
                "purpose": values.get("purpose", ""),
                "autonomy": values.get("autonomy", "supervised"),
                "members": members,
                "project_ids": [values["project_id"]] if values.get("project_id") else [],
            }
            if lead:
                kind, _, name = lead.partition(":")
                payload["lead_kind"] = kind or "profile"
                payload["lead_name"] = name or lead
            company = self.manager.add_team(company.id, payload, actor=actor)
            team = company.team_by_name(values.get("name", ""))
            return {
                "reply": (
                    f"Done — team **{team.name if team else values.get('name')}** "
                    "is created. You can add more members from the Teams view "
                    "or by telling me."
                ),
                "changed": True,
            }

        if form_id == FORM_ADD_TEAM_MEMBER:
            if not can_manage:
                return {"reply": _denied("manage teams")}
            team_id = values.get("team_id", "")
            member = values.get("member", "")
            role = values.get("role", "")
            company = self.manager.add_team_members(
                company.id,
                team_id,
                [{"kind": member.split(":", 1)[0], "name": member.split(":", 1)[-1], "role": role}]
                if ":" in member else [member],
                actor=actor,
            )
            team = company.team(team_id)
            return {
                "reply": f"Done — **{member.split(':')[-1]}** is now in **{team.name if team else 'the team'}**.",
                "changed": True,
            }

        return {"reply": f"I don't know how to submit form `{form_id}`."}

    def _add_or_promote(self, company: Any, text: str, can_admin: bool) -> Dict[str, Any]:
        """Handle “add Alice as a manager”: promote if she exists, else add her."""
        if not can_admin:
            return {"reply": _denied("add or change company users")}
        match = re.search(
            r"^(?:add|invite|hire)\s+(?:user\s+)?(.+?)\s+"
            r"(?:as|to\s+be)\s+(?:an?\s+)?(admin|manager|member)\b",
            text,
            re.I,
        )
        if not match:
            return self._start_add_user(company, text, can_admin)
        display = match.group(1).strip().strip('"').strip("'")
        role = match.group(2).lower()
        username = self._username_from_display(display)
        members = self.manager.company_members(company)
        target = next(
            (
                member for member in members
                if member["username"].lower() in (username.lower(), display.lower())
            ),
            None,
        )
        if target is not None:
            return self._confirm_action(
                {"type": "change_role", "username": target["username"], "role": role},
                f"I'll change **{target['username']}**'s company role to **{role}**.",
            )
        return self._confirm_action(
            {
                "type": "add_user",
                "username": username,
                "display": display,
                "role": role,
            },
            f"I'll add **{display}** to the company as **{role}** and create a temporary password.",
        )

    def _change_company_role(self, company: Any, text: str, can_admin: bool) -> Dict[str, Any]:
        """Handle “make alice a manager” (company membership role)."""
        if not can_admin:
            return {"reply": _denied("change company roles")}
        match = re.search(
            r"(?:make|set|change)\s+(?:user:)?([\w.\-@]+)\s+"
            r"(?:a|an|the)?\s*(admin|manager|member)\b",
            text,
            re.I,
        )
        if not match:
            return {"reply": "Who should get the new role, and what should it be?"}
        username, role = match.group(1).strip(), match.group(2).lower()
        members = self.manager.company_members(company)
        target = next(
            (member for member in members if member["username"].lower() == username.lower()),
            None,
        )
        if target is None:
            return {"reply": f"**{username}** is not a company member yet."}
        username = target["username"]
        if target.get("owner"):
            return {"reply": "The company owner always stays an admin. Transfer ownership first."}
        if target.get("company_role") == "admin" and role != "admin":
            admins = [member for member in members if member.get("company_role") == "admin"]
            if len(admins) <= 1:
                return {"reply": "The last company admin must stay an admin. Promote another admin first."}
        return self._confirm_action(
            {"type": "change_role", "username": username, "role": role},
            f"I'll change **{username}**'s company role to **{role}**.",
        )

    def _remove_user(self, company: Any, text: str, can_admin: bool, actor: str) -> Dict[str, Any]:
        """Handle "remove user <name>" (company membership, not the team roster)."""
        if not can_admin:
            return {"reply": _denied("remove company users")}
        username = self._first_name_after(text, ("user", "person", "member"))
        if not username:
            return {"reply": "Who should I remove from the company?"}
        if username == company.owner:
            return {"reply": "The company owner cannot be removed. Transfer ownership first."}
        members = self.manager.company_members(company)
        target = next(
            (member for member in members if member["username"].lower() == username.lower()),
            None,
        )
        if target is None:
            return {"reply": f"**{username}** is not a company member."}
        username = target["username"]
        if target.get("company_role") == "admin":
            admins = [member for member in members if member.get("company_role") == "admin"]
            if len(admins) <= 1:
                return {
                    "reply": (
                        "The last company admin cannot be removed. Promote another "
                        "admin first."
                    )
                }
        return self._confirm_action(
            {"type": "remove_user", "username": username},
            f"I'll remove **{username}** from **{company.name}**.",
        )

    def _add_team_member(
        self,
        company: Any,
        text: str,
        can_manage: bool,
        actor: str,
        form: bool = False,
    ) -> Dict[str, Any]:
        """Handle "add alice to Platform" / open the add-member form."""
        if not can_manage:
            return {"reply": _denied("manage teams")}
        match = re.search(
            r"(?:add|put|include|assign)\s+(?:user:|profile:)?"
            r"(?:user\s+|profile\s+|member\s+)?"
            r"([\w.\-@]+)\s+(?:to|into|in|on)\s+(.+)$",
            text,
            re.I,
        )
        if not match:
            match = re.search(
                r"([\w.\-@]+)\s+should\s+(?:join|be\s+(?:in|on|part\s+of))\s+(.+)$",
                text,
                re.I,
            )
        if not match:
            return self._start_add_team_member(company, can_manage)
        name, team_name = match.group(1).strip(), match.group(2).strip()
        team = self._find_team(company, team_name)
        if team is None and _ic(team_name).strip(".") in ("the team", "a team", "team"):
            return self._start_add_team_member(company, can_manage)
        if team is None:
            return {
                "reply": (
                    f"I can't find a team called **{team_name}**. "
                    f"Teams: {', '.join(team.name for team in company.teams) or 'none'}."
                )
            }
        if name.lower() in ("someone", "somebody", "person", "member", "people", "anyone"):
            return self._question(
                f"Who should join **{team.name}**?",
                {"intent": "add_member", "step": "person", "draft": {"team_id": team.id}},
                options=self._people_options(company),
            )
        kind, name = self._resolve_member(company, name)
        return self._confirm_action(
            {
                "type": "add_member",
                "team_id": team.id,
                "kind": kind,
                "name": name,
            },
            f"I'll add **{name}** to **{team.name}**.",
        )

    def _remove_team_member(self, company: Any, text: str, can_manage: bool, actor: str) -> Dict[str, Any]:
        """Handle "remove alice from Platform"."""
        if not can_manage:
            return {"reply": _denied("manage teams")}
        match = re.search(
            r"(?:remove|take|drop)\s+(?:user:|profile:)?"
            r"(?:user\s+|profile\s+|member\s+)?"
            r"([\w.\-@]+)\s+(?:from|out\s+of|off)\s+(.+)$",
            text,
            re.I,
        )
        if not match:
            return {"reply": "Who should I remove, and from which team?"}
        name, team_name = match.group(1).strip(), match.group(2).strip()
        team = self._find_team(company, team_name)
        if team is None:
            return {"reply": f"I can't find a team called **{team_name}**."}
        _kind, name = self._resolve_member(company, name)
        return self._confirm_action(
            {"type": "remove_member", "team_id": team.id, "name": name},
            f"I'll remove **{name}** from **{team.name}**.",
        )

    def _start_set_lead(self, company: Any, can_manage: bool, team: Any = None) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("choose team leads")}
        if not company.teams:
            return {
                "reply": "There are no teams yet. I can create one first.",
                "suggestions": ["Create a team"],
            }
        if team is not None:
            return self._question(
                f"Who should lead **{team.name}**?",
                {"intent": "set_lead", "step": "person", "draft": {"team_id": team.id}},
                options=self._people_options(company),
            )
        if len(company.teams) == 1:
            team = company.teams[0]
            return self._question(
                f"Who should lead **{team.name}**?",
                {"intent": "set_lead", "step": "person", "draft": {"team_id": team.id}},
                options=self._people_options(company),
            )
        return self._question(
            "Which team needs a lead?",
            {"intent": "set_lead", "step": "team", "draft": {}},
            options=self._team_options(company),
        )

    def _continue_set_lead(
        self, company: Any, state: Dict[str, Any], text: str, actor: str, can_manage: bool
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("choose team leads"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        draft = dict(state.get("draft") or {})
        step = state.get("step")
        if step == "team":
            team = next(
                (item for item in company.teams if item.id == text or item.name.lower() == _ic(text)),
                None,
            )
            if team is None:
                return self._question("Which team needs a lead?", state, options=self._team_options(company))
            draft["team_id"] = team.id
            return self._question(
                f"Who should lead **{team.name}**?",
                {"intent": "set_lead", "step": "person", "draft": draft},
                options=self._people_options(company),
            )
        team = company.team(draft.get("team_id", ""))
        if team is None:
            return {"reply": "Which team needs a lead?", "state": None}
        kind, name = self._resolve_member(company, text)
        return self._confirm_action(
            {"type": "set_lead", "team_id": team.id, "kind": kind, "name": name},
            f"I'll make **{name}** the lead of **{team.name}**.",
        )

    def _set_team_lead(self, company: Any, text: str, can_manage: bool, actor: str) -> Dict[str, Any]:
        """Handle "make alice lead of Platform"."""
        if not can_manage:
            return {"reply": _denied("manage teams")}
        match = re.search(
            r"(?:make|set)\s+(?:user:|profile:)?(?:user\s+|profile\s+|member\s+)?"
            r"([\w.\-@]+)\s+(?:as\s+)?(?:the\s+)?lead\s+(?:of|for)\s+(.+)$",
            text,
            re.I,
        )
        if not match:
            match = re.search(
                r"([\w.\-@]+)\s+should\s+lead\s+(.+)$", text, re.I
            )
        if not match:
            match = re.search(
                r"(?:put|make|set)\s+([\w.\-@]+)\s+in\s+charge\s+of\s+(.+)$",
                text,
                re.I,
            )
        if not match:
            return self._start_set_lead(company, can_manage)
        name, team_name = match.group(1).strip(), match.group(2).strip()
        team = self._find_team(company, team_name)
        if team is None:
            return {"reply": f"I can't find a team called **{team_name}**."}
        kind, name = self._resolve_member(company, name)
        return self._confirm_action(
            {"type": "set_lead", "team_id": team.id, "kind": kind, "name": name},
            f"I'll make **{name}** the lead of **{team.name}**.",
        )

    def _create_team(self, company: Any, text: str, can_manage: bool, actor: str) -> Dict[str, Any]:
        """Handle "create team <name>" (form if the message is just the intent)."""
        if not can_manage:
            return {"reply": _denied("create teams")}
        match = re.search(
            r"(?:create|make|start|set\s+up|setup|add)\s+(?:a\s+)?team\s+"
            r"(?:called\s+|named\s+)?(.+)$",
            text,
            re.I,
        )
        name = (
            match.group(1).strip().strip('"').strip("'").rstrip("?.!,")
            if match else ""
        )
        if not name or name.lower() in ("a team", "the team"):
            return self._start_create_team(can_manage)
        return self._confirm_action(
            {"type": "create_team", "name": name},
            f"I'll create a team called **{name}**.",
        )

    def _delete_team(
        self,
        company: Any,
        text: str,
        can_manage: bool,
        actor: str,
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Delete a team only after an explicit confirmation."""
        if not can_manage:
            return {"reply": _denied("delete teams")}
        match = re.search(r"(?:delete|remove|drop)\s+(?:the\s+)?team\s+(.+)$", text, re.I)
        team_name = match.group(1).strip().strip('"').strip("'") if match else ""
        if not team_name:
            if not company.teams:
                return {"reply": "There are no teams to delete."}
            return self._question(
                "Which team should I delete?",
                {"intent": "delete_team", "step": "team", "draft": {}},
                options=self._team_options(company),
            )
        team = self._find_team(company, team_name)
        if team is None:
            return {"reply": f"I can't find a team called **{team_name}**."}
        return self._confirm_action(
            {"type": "delete_team", "team_id": team.id, "name": team.name},
            f"I'll delete the team **{team.name}**. Open missions must be reassigned first.",
        )

    def _delete_company(self, company: Any, text: str, can_admin: bool, actor: str) -> Dict[str, Any]:
        """Delete the company only after an explicit confirmation."""
        if not can_admin:
            return {"reply": _denied("delete the company")}
        return self._confirm_action(
            {"type": "delete_company"},
            (
                f"I'll permanently delete **{company.name}**, including its teams, "
                "missions and journal. The linked projects are untouched."
            ),
        )

    def _dispatch_mission(self, company: Any, text: str, can_manage: bool, actor: str) -> Dict[str, Any]:
        """Dispatch a mission by title."""
        if not can_manage:
            return {"reply": _denied("dispatch missions")}
        match = re.search(r"dispatch\s+(?:the\s+)?mission\s+(.+)$", text, re.I)
        title = match.group(1).strip().strip('"').strip("'") if match else ""
        mission = next(
            (
                item
                for item in company.missions
                if item.title.lower() == title.lower()
            ),
            None,
        )
        if mission is None:
            return {
                "reply": (
                    f"I can't find a mission called **{title}**. "
                    "Open the Missions view to see the exact titles."
                )
            }
        return self._confirm_action(
            {"type": "dispatch_mission", "mission_id": mission.id, "title": mission.title},
            f"I'll start the mission **{mission.title}** now.",
        )

    def _start_review_mission(self, company: Any, text: str, can_manage: bool) -> Dict[str, Any]:
        """Ask whether a mission in review is accepted or sent back."""
        if not can_manage:
            return {"reply": _denied("review missions")}
        mission = next(
            (
                item
                for item in company.missions
                if item.title and item.title.lower() in _ic(text)
            ),
            None,
        )
        if mission is None:
            pending = [item for item in company.missions if item.status == "review"]
            if not pending:
                return {"reply": "Nothing is waiting for review right now."}
            if len(pending) == 1:
                mission = pending[0]
            else:
                return self._question(
                    "Which mission would you like to review?",
                    {"intent": "review_mission", "step": "mission", "draft": {}},
                    options=[{"label": item.title, "value": item.id} for item in pending],
                )
        if mission.status != "review":
            return {
                "reply": (
                    f"**{mission.title}** is **{mission.status}**, not waiting for review."
                )
            }
        return self._question(
            f"The AI team finished **{mission.title}**. Do you accept the result, "
            "or should I send it back for changes?",
            {"intent": "review_mission", "step": "decision", "draft": {"mission_id": mission.id}},
            options=[
                {"label": "Accept the result", "value": "accept"},
                {"label": "Send it back for changes", "value": "reject"},
            ],
        )

    def _continue_review_mission(
        self, company: Any, state: Dict[str, Any], text: str, actor: str, can_manage: bool
    ) -> Dict[str, Any]:
        if not can_manage:
            return {"reply": _denied("review missions"), "state": None}
        if self._is_cancel(text):
            return self._cancelled()
        draft = dict(state.get("draft") or {})
        step = state.get("step")

        if step == "mission":
            mission = next(
                (item for item in company.missions if item.id == text),
                None,
            )
            if mission is None:
                pending = [item for item in company.missions if item.status == "review"]
                return self._question(
                    "Which mission would you like to review?",
                    state,
                    options=[{"label": item.title, "value": item.id} for item in pending],
                )
            draft["mission_id"] = mission.id
            return self._question(
                f"Do you accept the result of **{mission.title}**, or should I send it back?",
                {"intent": "review_mission", "step": "decision", "draft": draft},
                options=[
                    {"label": "Accept the result", "value": "accept"},
                    {"label": "Send it back for changes", "value": "reject"},
                ],
            )

        mission = company.get_mission(draft.get("mission_id", ""))
        if mission is None:
            return {"reply": "I lost track of that mission. Which one should I review?", "state": None}

        if step == "decision":
            answer = _ic(text)
            if "accept" in answer or answer in ("yes", "done", "ok", "okay"):
                return self._confirm_action(
                    {"type": "accept_mission", "mission_id": mission.id, "title": mission.title},
                    f"I'll accept the result of **{mission.title}** and mark it done.",
                )
            if "reject" in answer or "back" in answer or "change" in answer:
                return self._question(
                    f"What should the team change in **{mission.title}**?",
                    {"intent": "review_mission", "step": "reason", "draft": draft},
                )
            return self._question(
                "Should I accept the result or send it back for changes?",
                state,
                options=[
                    {"label": "Accept the result", "value": "accept"},
                    {"label": "Send it back for changes", "value": "reject"},
                ],
            )

        if step == "reason":
            reason = text.strip() or "Please review the result and try again."
            return self._confirm_action(
                {
                    "type": "reject_mission",
                    "mission_id": mission.id,
                    "title": mission.title,
                    "reason": reason,
                },
                f"I'll send **{mission.title}** back with: *{reason}*.",
            )

        return {"reply": "Should I accept the result or send it back?", "state": None}

    def _review_mission(self, company: Any, text: str, can_manage: bool, actor: str) -> Dict[str, Any]:
        """Accept or reject a mission that is waiting in review."""
        if not can_manage:
            return {"reply": _denied("review missions")}
        lowered = _ic(text)
        mission = next(
            (
                item
                for item in company.missions
                if item.title.lower() in lowered or item.id.lower() in lowered
            ),
            None,
        )
        if mission is None:
            return {
                "reply": (
                    "Which mission? Tell me its name and I'll take it from there."
                )
            }
        if mission.status != "review":
            return {
                "reply": (
                    f"**{mission.title}** is **{mission.status}**, not in review. "
                    "Only missions in review can be accepted or rejected."
                )
            }
        if re.match(r"^accept\b", lowered):
            return self._confirm_action(
                {
                    "type": "accept_mission",
                    "mission_id": mission.id,
                    "title": mission.title,
                },
                f"I'll accept the result of **{mission.title}** and mark it done.",
            )
        reason = ""
        if "because" in lowered:
            reason = text.split("because", 1)[-1].strip()
        return self._confirm_action(
            {
                "type": "reject_mission",
                "mission_id": mission.id,
                "title": mission.title,
                "reason": reason,
            },
            f"I'll send **{mission.title}** back to the team"
            + (f" with: *{reason}*." if reason else "."),
        )

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    def _team_target(self, company: Any, text: str) -> Any:
        """
        Return the team named after a ``to`` / ``from`` / ``of`` phrase.

        It lets the assistant tell a team command ("add user alice to
        Platform") apart from the company add-user form ("add a user"), even
        when both start with "add".
        """
        match = re.search(
            r"(?:to|into|from|of|for)\s+(.+)$",
            text or "",
            re.I,
        )
        if not match:
            return None
        return self._find_team(company, match.group(1))

    def _resolve_member(self, company: Any, raw: str) -> tuple:
        """Resolve a person/profile name case-insensitively to (kind, exact name)."""
        text = (raw or "").strip().strip('"').strip("'")
        if text.startswith("user:") or text.startswith("profile:"):
            kind, name = text.split(":", 1)
            text = name.strip()
            if kind == "user":
                for member in self.manager.company_members(company):
                    if member["username"].lower() == text.lower():
                        return "user", member["username"]
                return "user", text
        for member in self.manager.company_members(company):
            if member["username"].lower() == text.lower():
                return "user", member["username"]
        try:
            profiles = self.manager.references().get("profiles", [])
        except Exception:
            profiles = []
        for profile in profiles:
            if (profile.get("name") or "").lower() == text.lower():
                return "profile", profile["name"]
        return self._member_kind(company, text), text

    def _member_kind(self, company: Any, name: str) -> str:
        """Resolve a member reference kind from the company roster/profiles."""
        if name.startswith("user:"):
            return "user"
        if name.startswith("profile:"):
            return "profile"
        if any(member["username"] == name for member in self.manager.company_members(company)):
            return "user"
        return "profile"

    def _first_name_after(self, text: str, words: Iterable[str]) -> str:
        """Return the first real identifier after one of *words*."""
        stopwords = {
            "a", "an", "the", "user", "person", "member", "employee",
            "from", "to", "into", "of", "for", "team", "company",
        }
        for word in words:
            for match in re.finditer(rf"{word}\s+(?:user:)?([\w.\-@]+)", text, re.I):
                candidate = match.group(1).strip()
                if candidate.lower() not in stopwords:
                    return candidate
        return ""

    def _parse_user_command(self, text: str) -> Dict[str, str]:
        """Best-effort parse of a complete "add user" command."""
        result: Dict[str, str] = {}
        username = re.search(
            r"(?:user|person|member|employee)\s+(?:user:)?([\w.\-@]+)",
            text,
            re.I,
        )
        if username and username.group(1).strip().lower() not in (
            "a", "an", "the", "with", "as", "and", "to", "for"
        ):
            result["username"] = username.group(1).strip()
        email = re.search(r"[\w.\-+]+@[\w.\-]+\.[\w.\-]+", text)
        if email:
            result["email"] = email.group(0)
        password = re.search(r"password\s+(?:is\s+)?(\S+)", text, re.I)
        if password:
            result["password"] = password.group(1).strip()
        role = re.search(r"\bas\s+(?:an?\s+)?(admin|manager|member)\b", text, re.I)
        if role:
            result["role"] = role.group(1).lower()
        title = re.search(r"title\s+(.+)$", text, re.I)
        if title:
            result["title"] = title.group(1).strip()
        return result


def _denied(action: str) -> str:
    """Consistent refusal message for a role that cannot perform *action*."""
    return (
        f"I can't {action}: only a company admin or manager can do that. "
        "Ask an admin of this company to grant you the role."
    )


# Made with ❤️ by codx-junior
