"""
Business operations for companies.

The manager is the only place that mutates a :class:`~.models.Company`: the API,
the profile tools and the autopilot all call the same methods, so validation,
journaling and dispatch behave identically no matter who acts.

What it owns
------------
* **Validation** — names, references (users/profiles/projects), org tree cycles,
  team rosters, mission destinations and status transitions.
* **Mission lifecycle** — create, dispatch to the project orchestration runtime,
  sync the run back, accept/reject.
* **Autonomy** — the guard-railed cycle that dispatches at most N ``auto``
  missions per interval, never more than the concurrency limit.
* **Dashboard** — :meth:`snapshot` returns the exact payload the UI renders.
* **Journal** — every mutation appends a human-readable event.

Dependency injection
--------------------
The AI runtime is heavy and optional. The manager therefore accepts providers:

* ``projects_provider`` / ``users_provider`` / ``profiles_provider`` for the
  reference catalog (tests use fakes),
* ``project_settings_provider`` for the real ``CODXJuniorSettings`` used by
  dispatch,
* ``dispatcher`` to start the work (default: durable orchestration),
* ``run_status_provider`` to read a run back,
* ``clock`` for deterministic cycles.

Nothing in this module imports the AI stack at import time.

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import logging
import re

from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .models import (
    MISSION_PRIORITIES,
    MISSION_TRANSITIONS,
    AutonomyPolicy,
    Company,
    CompanyEvent,
    CompanyMember,
    CompanyProject,
    CompanyTeam,
    Mission,
    OrgUnit,
    can_transition,
    new_id,
    now_iso,
    parse_iso,
    slugify,
)
from .store import CompanyNotFound, CompanyStore, CompanyStoreError
from .templates import apply_template

logger = logging.getLogger(__name__)

#: Fields a generic company update may touch. Org/teams/projects/missions and
#: autonomy have dedicated methods so a broad PUT cannot delete work.
COMPANY_EDITABLE_FIELDS = (
    "name",
    "slug",
    "description",
    "mission",
    "vision",
    "values",
    "website",
    "logo",
    "color",
    "status",
    "owner",
    "tags",
)

TEAM_EDITABLE_FIELDS = (
    "name",
    "description",
    "purpose",
    "org_unit_id",
    "lead_kind",
    "lead_name",
    "members",
    "project_ids",
    "autonomy",
    "tools",
    "tags",
    "color",
    "icon",
)

MISSION_EDITABLE_FIELDS = (
    "title",
    "objective",
    "acceptance",
    "priority",
    "team_id",
    "project_id",
    "owner_kind",
    "owner_name",
    "dispatch_mode",
    "budget_cxjcoins",
    "due_date",
    "tags",
)

AUTONOMY_EDITABLE_FIELDS = (
    "enabled",
    "level",
    "interval_minutes",
    "max_concurrent_missions",
    "max_missions_per_cycle",
    "daily_budget_cxjcoins",
    "require_human_acceptance",
)

#: Order used when picking the next mission to dispatch.
_PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}

#: Run statuses that mean "still working" (sync keeps the mission running).
_ACTIVE_RUN_STATUSES = ("queued", "running")
_TERMINAL_RUN_STATUSES = (
    "completed",
    "failed",
    "stopped",
    "budget_exhausted",
    "stalled",
)


class CompanyValidationError(ValueError):
    """The requested operation would produce an invalid company."""


class CompanyConflict(CompanyValidationError):
    """The requested operation conflicts with the current state."""


class CompanyDispatchError(RuntimeError):
    """A mission could not be dispatched to its project."""


# ---------------------------------------------------------------------------
# Default providers (lazy: no AI stack at import time)
# ---------------------------------------------------------------------------


def _default_projects() -> List[Dict[str, Any]]:
    """Return the discovered codx-junior projects as plain dictionaries."""
    try:
        from codx.junior.project.project_discover import find_all_projects

        projects = find_all_projects() or {}
    except Exception as ex:  # pragma: no cover - discovery is best effort
        logger.warning("Company: project discovery failed: %s", ex)
        return []
    result: List[Dict[str, Any]] = []
    for project_id, settings in projects.items():
        if settings is None:
            continue
        result.append(
            {
                "project_id": getattr(settings, "project_id", project_id) or project_id,
                "project_name": getattr(settings, "project_name", "") or project_id,
                "project_path": getattr(settings, "abs_project_path", "")
                or getattr(settings, "project_path", ""),
                "codx_path": getattr(settings, "codx_path", ""),
            }
        )
    return sorted(result, key=lambda project: project["project_name"].lower())


def _default_users() -> List[Dict[str, Any]]:
    """Return the codx-junior users as plain dictionaries."""
    try:
        from codx.junior.security.user_management import UserSecurityManager

        users = UserSecurityManager().list_user() or []
        return [
            {
                "username": user.get("username", ""),
                "avatar": user.get("avatar", ""),
            }
            for user in users
            if user.get("username")
        ]
    except Exception as ex:  # pragma: no cover - auth may be disabled
        logger.debug("Company: user catalog unavailable: %s", ex)
        return []


def _default_project_settings(project_id: str) -> Any:
    """Return the real ``CODXJuniorSettings`` of a project, or ``None``."""
    try:
        from codx.junior.project.project_discover import find_all_projects

        projects = find_all_projects() or {}
        return projects.get(project_id) or next(
            (
                settings
                for settings in projects.values()
                if settings and getattr(settings, "project_id", None) == project_id
            ),
            None,
        )
    except Exception as ex:  # pragma: no cover - defensive
        logger.warning("Company: could not resolve project settings: %s", ex)
        return None


def _default_profiles(project_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Return the profiles visible from the linked projects (union by name)."""
    try:
        from codx.junior.profiles.profile_manager import ProfileManager
        from codx.junior.project.project_discover import find_all_projects

        projects = find_all_projects() or {}
        settings_list = []
        for project_id, settings in projects.items():
            if settings is None:
                continue
            if project_ids and project_id not in project_ids:
                continue
            settings_list.append(settings)
        catalog: Dict[str, Dict[str, Any]] = {}
        for settings in settings_list:
            try:
                manager = ProfileManager(settings=settings)
                for profile in manager.list_all_profiles():
                    if not profile or not profile.name:
                        continue
                    entry = catalog.setdefault(
                        profile.name,
                        {
                            "name": profile.name,
                            "category": getattr(profile, "category", "") or "",
                            "description": getattr(profile, "description", "") or "",
                            "projects": [],
                        },
                    )
                    project_name = getattr(settings, "project_name", "") or ""
                    if project_name and project_name not in entry["projects"]:
                        entry["projects"].append(project_name)
            except Exception as ex:  # pragma: no cover - one bad project is not fatal
                logger.debug("Company: profiles of one project failed: %s", ex)
        return sorted(catalog.values(), key=lambda profile: profile["name"].lower())
    except Exception as ex:  # pragma: no cover - defensive
        logger.debug("Company: profile catalog unavailable: %s", ex)
        return []


class CompanyManager:
    """
    CRUD + operating system for companies.

    Args:
        root_path: Companies root (default: ``CODX_JUNIOR_COMPANIES_PATH``).
        store: Optional pre-built :class:`CompanyStore` (tests).
        projects_provider: Callable returning the project catalog.
        users_provider: Callable returning the user catalog.
        profiles_provider: Callable(project_ids) returning the profile catalog.
        project_settings_provider: Callable(project_id) returning settings.
        dispatcher: Callable(company, mission, brief) starting the mission.
        run_status_provider: Callable(project_id, run_id) returning run status.
        clock: Callable returning ``datetime.now``.
    """

    def __init__(
        self,
        root_path: Optional[str] = None,
        store: Optional[CompanyStore] = None,
        projects_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        users_provider: Optional[Callable[[], List[Dict[str, Any]]]] = None,
        profiles_provider: Optional[
            Callable[[Optional[List[str]]], List[Dict[str, Any]]]
        ] = None,
        project_settings_provider: Optional[Callable[[str], Any]] = None,
        dispatcher: Optional[Callable[[Company, Mission, str], Dict[str, Any]]] = None,
        run_status_provider: Optional[
            Callable[[str, str], Dict[str, Any]]
        ] = None,
        clock: Optional[Callable[[], datetime]] = None,
    ):
        self.store = store or CompanyStore(root_path=root_path)
        self._projects_provider = projects_provider or _default_projects
        self._users_provider = users_provider or _default_users
        self._profiles_provider = profiles_provider or _default_profiles
        self._project_settings_provider = (
            project_settings_provider or _default_project_settings
        )
        self._dispatcher = dispatcher or self._default_dispatcher
        self._run_status_provider = run_status_provider or self._default_run_status
        self._clock = clock or datetime.now

    # ------------------------------------------------------------------
    # Small utilities
    # ------------------------------------------------------------------

    def _now(self) -> datetime:
        """Return the manager clock."""
        return self._clock()

    def _event(
        self,
        company: Company,
        event_type: str,
        message: str = "",
        actor: str = "system",
        mission_id: str = "",
        **data: Any,
    ) -> CompanyEvent:
        """Append a journal event for *company*."""
        event = CompanyEvent(
            type=event_type,
            actor=actor or "system",
            message=message,
            mission_id=mission_id,
            data=data,
        )
        return self.store.append_event(company.id, event)

    @staticmethod
    def _clean(value: Any) -> str:
        """Trim a value into a string."""
        return str(value).strip() if value is not None else ""

    @staticmethod
    def _apply(instance: Any, patch: Dict[str, Any], fields: Iterable[str]) -> List[str]:
        """
        Apply a validated patch to a pydantic model.

        Args:
            instance: Model to mutate.
            patch: Raw patch values.
            fields: Allowed field names.

        Returns:
            Names of the fields that actually changed.
        """
        changed: List[str] = []
        for field in fields:
            if field not in patch or patch[field] is None:
                continue
            value = patch[field]
            if getattr(instance, field, None) != value:
                setattr(instance, field, value)
                changed.append(field)
        return changed

    def _project_catalog(self) -> List[Dict[str, Any]]:
        """Return the (normalized) project catalog."""
        try:
            projects = self._projects_provider() or []
        except Exception as ex:  # pragma: no cover - defensive
            logger.warning("Company: project catalog failed: %s", ex)
            return []
        normalized = []
        for project in projects:
            if not project:
                continue
            project_id = self._clean(
                project.get("project_id") or project.get("id") or ""
            )
            if not project_id:
                continue
            normalized.append(
                {
                    "project_id": project_id,
                    "project_name": self._clean(
                        project.get("project_name")
                        or project.get("name")
                        or project_id
                    ),
                    "project_path": self._clean(
                        project.get("project_path") or project.get("path") or ""
                    ),
                    "codx_path": self._clean(project.get("codx_path") or ""),
                }
            )
        return normalized

    def _profile_catalog(self, project_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Return the (normalized) profile catalog."""
        try:
            profiles = self._profiles_provider(project_ids) or []
        except Exception as ex:  # pragma: no cover - defensive
            logger.warning("Company: profile catalog failed: %s", ex)
            return []
        normalized = []
        for profile in profiles:
            name = self._clean(profile.get("name") if isinstance(profile, dict) else profile)
            if not name:
                continue
            normalized.append(
                profile
                if isinstance(profile, dict)
                else {"name": name, "category": "", "description": "", "projects": []}
            )
        return normalized

    def _validate_member(
        self,
        member: CompanyMember,
        *,
        projects: Optional[List[Dict[str, Any]]] = None,
        users: Optional[List[Dict[str, Any]]] = None,
        profiles: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Validate a member reference against the catalogs.

        Catalogs are only enforced when they are available: a fresh install with
        no discovered project must still be able to define a company, and tests
        can inject their own catalog.
        """
        if member.is_ai:
            catalog = profiles if profiles is not None else self._profile_catalog()
            if not catalog:
                return
            names = {self._clean(profile.get("name")) for profile in catalog}
            if member.name not in names:
                sample = ", ".join(sorted(names)[:12])
                raise CompanyValidationError(
                    f"AI profile '{member.name}' does not exist in the linked "
                    f"projects. Available profiles: {sample or 'none'}"
                )
            return

        catalog = users if users is not None else self._users()
        if not catalog:
            return
        names = {self._clean(user.get("username")) for user in catalog}
        if member.name not in names:
            sample = ", ".join(sorted(names)[:12])
            raise CompanyValidationError(
                f"User '{member.name}' does not exist. Available users: "
                f"{sample or 'none'}"
            )

    def _users(self) -> List[Dict[str, Any]]:
        """Return the user catalog (safe when auth is disabled)."""
        try:
            return self._users_provider() or []
        except Exception as ex:  # pragma: no cover - defensive
            logger.debug("Company: user catalog failed: %s", ex)
            return []

    def _validate_project(self, project_id: str, projects: Optional[List[Dict[str, Any]]] = None) -> None:
        """Validate a project reference against the discovery catalog."""
        project_id = self._clean(project_id)
        if not project_id:
            raise CompanyValidationError("project_id is required")
        catalog = projects if projects is not None else self._project_catalog()
        if not catalog:
            return
        if not any(project["project_id"] == project_id for project in catalog):
            available = ", ".join(
                f"{project['project_name']} ({project['project_id']})"
                for project in catalog[:10]
            )
            raise CompanyValidationError(
                f"Project '{project_id}' is not a discovered codx-junior project. "
                f"Available: {available or 'none'}"
            )

    def _validate_team_members(
        self,
        team: CompanyTeam,
        projects: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Validate every member of a team (and the lead identity)."""
        profile_catalog = (
            self._profile_catalog([project["project_id"] for project in projects])
            if projects
            else self._profile_catalog()
        )
        user_catalog = self._users()
        for member in team.members:
            self._validate_member(
                member,
                projects=projects,
                users=user_catalog,
                profiles=profile_catalog,
            )
        if team.lead_name:
            self._validate_member(
                CompanyMember(kind=team.lead_kind, name=team.lead_name),
                projects=projects,
                users=user_catalog,
                profiles=profile_catalog,
            )

    def _validate_org_parent(
        self,
        company: Company,
        unit_id: str,
        parent_id: str,
    ) -> None:
        """Reject a missing parent or a parent cycle."""
        parent_id = self._clean(parent_id)
        if not parent_id:
            return
        if parent_id == unit_id:
            raise CompanyValidationError("an org unit cannot be its own parent")
        if not company.org_unit(parent_id):
            raise CompanyValidationError(
                f"Parent org unit '{parent_id}' does not exist"
            )
        seen = {unit_id}
        current = company.org_unit(parent_id)
        while current is not None and current.parent_id:
            if current.id in seen:
                raise CompanyValidationError(
                    "The org unit hierarchy would contain a cycle"
                )
            seen.add(current.id)
            current = company.org_unit(current.parent_id)
        if current is not None and current.id in seen:
            raise CompanyValidationError(
                "The org unit hierarchy would contain a cycle"
            )

    def _slug_in_use(self, slug: str, exclude_id: str = "") -> bool:
        """Tell whether *slug* is already used by another company."""
        wanted = (slug or "").lower()
        for company in self.list_companies(include_archived=True):
            if company["id"] == exclude_id:
                continue
            if (company.get("slug") or "").lower() == wanted:
                return True
        return False

    # ------------------------------------------------------------------
    # Company CRUD
    # ------------------------------------------------------------------

    def list_companies(self, include_archived: bool = True) -> List[Dict[str, Any]]:
        """
        List every stored company.

        Args:
            include_archived: When false, archived companies are hidden.

        Returns:
            Company summaries sorted by name.
        """
        result: List[Dict[str, Any]] = []
        for company_id in self.store.list_ids():
            try:
                company = self.store.load(company_id)
            except Exception as ex:
                logger.warning("Company '%s' skipped: %s", company_id, ex)
                continue
            if not include_archived and company.status == "archived":
                continue
            result.append(company.summary())
        return sorted(result, key=lambda item: item["name"].lower())

    def get_company(self, company_id: str) -> Company:
        """
        Load a company by id **or** slug.

        Args:
            company_id: Company id or slug.

        Returns:
            The company.

        Raises:
            CompanyNotFound: If no company matches.
        """
        company_id = self._clean(company_id)
        if not company_id:
            raise CompanyNotFound("company_id is required")
        if self.store.exists(company_id):
            return self.store.load(company_id)
        # Slug fallback: the UI may address a company by its readable slug.
        for stored_id in self.store.list_ids():
            try:
                company = self.store.load(stored_id)
            except Exception:
                continue
            if company.slug.lower() == company_id.lower():
                return company
        raise CompanyNotFound(f"Company '{company_id}' not found")

    def create_company(
        self,
        company: Any,
        actor: str = "system",
        template: str = "",
        project_ids: Optional[List[str]] = None,
    ) -> Company:
        """
        Create a company.

        Args:
            company: A :class:`Company`, mapping or JSON payload.
            actor: Username recorded in the audit trail.
            template: Optional starter (``saas``, ``blank``).
            project_ids: Projects to link before applying the template.

        Returns:
            The persisted company.

        Raises:
            CompanyValidationError: On invalid input.
            CompanyConflict: When the slug is already used.
        """
        if isinstance(company, Company):
            company = company.model_copy(deep=True)
        else:
            try:
                company = Company(**dict(company or {}))
            except Exception as ex:
                raise CompanyValidationError(str(ex)) from ex

        company.id = new_id("company")
        company.created_at = now_iso()
        company.updated_at = company.created_at
        company.name = self._clean(company.name)
        if not company.name:
            raise CompanyValidationError("company name is required")
        company.slug = slugify(company.slug or company.name)
        if self._slug_in_use(company.slug):
            raise CompanyConflict(
                f"A company with slug '{company.slug}' already exists"
            )
        if not company.owner:
            company.owner = actor

        # Link requested projects first so the template can point teams at them.
        projects = self._project_catalog()
        for project_id in project_ids or []:
            project_id = self._clean(
                project_id.get("project_id") if isinstance(project_id, dict) else project_id
            )
            if not project_id or company.project(project_id):
                continue
            self._validate_project(project_id, projects=projects)
            match = next(
                (item for item in projects if item["project_id"] == project_id),
                None,
            )
            company.projects.append(
                CompanyProject(
                    project_id=project_id,
                    name=(match or {}).get("project_name", project_id),
                    role="",
                )
            )

        company = apply_template(company, template, project_ids=project_ids)

        # Assign ids to anything the caller left blank.
        for unit in company.org_units:
            unit.id = unit.id or new_id("org")
            unit.updated_at = now_iso()
        for team in company.teams:
            team.id = team.id or new_id("team")
            team.ensure_lead()
            team.updated_at = now_iso()
        for mission in company.missions:
            mission.id = mission.id or new_id("mission")
            mission.updated_at = now_iso()

        self._ensure_unique_children(company)
        for team in company.teams:
            self._validate_team_members(team, projects=projects)

        saved = self.store.save(company)
        self._event(
            saved,
            "company.created",
            f"Company '{saved.name}' created",
            actor=actor,
            template=template or None,
        )
        logger.info("Company created: %s (%s)", saved.name, saved.id)
        return saved

    def update_company(
        self,
        company_id: str,
        patch: Any,
        actor: str = "system",
    ) -> Company:
        """
        Update the company-level fields (never the org/teams/projects/missions).

        Args:
            company_id: Company id.
            patch: Mapping (or :class:`Company`) with the fields to change.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.

        Raises:
            CompanyConflict: When the new slug is already used.
        """
        values = self._patch_dict(patch)
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            if "slug" in values and values["slug"]:
                slug = slugify(values["slug"])
                if self._slug_in_use(slug, exclude_id=company.id):
                    raise CompanyConflict(
                        f"A company with slug '{slug}' already exists"
                    )
                values["slug"] = slug
            if "name" in values:
                name = self._clean(values["name"])
                if not name:
                    raise CompanyValidationError("company name is required")
                values["name"] = name
            changed = self._apply(company, values, COMPANY_EDITABLE_FIELDS)
            saved = self.store.save(company)
            if changed:
                self._event(
                    saved,
                    "company.updated",
                    f"Company updated: {', '.join(changed)}",
                    actor=actor,
                    changed=changed,
                )
            return saved

    def delete_company(self, company_id: str, actor: str = "system") -> Dict[str, Any]:
        """
        Delete a company (folder + journal).

        Args:
            company_id: Company id.
            actor: Username recorded in the audit trail.

        Returns:
            ``{"deleted": id, "name": name}``.
        """
        company = self.get_company(company_id)
        with self.store.lock(company.id):
            self.store.delete(company.id)
        logger.info("Company deleted: %s by %s", company.id, actor)
        return {"deleted": company.id, "name": company.name}

    # ------------------------------------------------------------------
    # Organization
    # ------------------------------------------------------------------

    def add_org_unit(
        self, company_id: str, unit: Any, actor: str = "system"
    ) -> Company:
        """
        Add a department/function to the company organization.

        Args:
            company_id: Company id.
            unit: :class:`OrgUnit` or mapping.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        payload = self._patch_dict(unit)
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            payload["id"] = new_id("org")
            try:
                org_unit = OrgUnit(**payload)
            except Exception as ex:
                raise CompanyValidationError(str(ex)) from ex
            self._validate_org_parent(company, org_unit.id, org_unit.parent_id)
            self._ensure_unique_org_name(company, org_unit.name)
            company.org_units.append(org_unit)
            saved = self.store.save(company)
            self._event(
                saved,
                "org_unit.created",
                f"Org unit '{org_unit.name}' created",
                actor=actor,
                org_unit_id=org_unit.id,
            )
            return saved

    def update_org_unit(
        self,
        company_id: str,
        unit_id: str,
        patch: Any,
        actor: str = "system",
    ) -> Company:
        """
        Update an org unit.

        Args:
            company_id: Company id.
            unit_id: Org unit id.
            patch: Mapping with the fields to change.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        values = self._patch_dict(patch)
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            org_unit = company.org_unit(unit_id)
            if org_unit is None:
                raise CompanyNotFound(f"Org unit '{unit_id}' not found")
            if "parent_id" in values:
                self._validate_org_parent(company, unit_id, values["parent_id"])
            if "name" in values:
                name = self._clean(values["name"])
                if not name:
                    raise CompanyValidationError("org unit name is required")
                self._ensure_unique_org_name(company, name, exclude_id=unit_id)
                values["name"] = name
            changed = self._apply(
                org_unit,
                values,
                (
                    "name",
                    "kind",
                    "description",
                    "parent_id",
                    "lead_kind",
                    "lead_name",
                    "responsibilities",
                    "color",
                    "icon",
                    "order",
                ),
            )
            org_unit.updated_at = now_iso()
            saved = self.store.save(company)
            if changed:
                self._event(
                    saved,
                    "org_unit.updated",
                    f"Org unit '{org_unit.name}' updated: {', '.join(changed)}",
                    actor=actor,
                    org_unit_id=unit_id,
                )
            return saved

    def delete_org_unit(
        self, company_id: str, unit_id: str, actor: str = "system"
    ) -> Company:
        """
        Delete an org unit, detaching its children and teams.

        Args:
            company_id: Company id.
            unit_id: Org unit id.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            org_unit = company.org_unit(unit_id)
            if org_unit is None:
                raise CompanyNotFound(f"Org unit '{unit_id}' not found")
            company.org_units = [
                unit for unit in company.org_units if unit.id != unit_id
            ]
            for child in company.org_units:
                if child.parent_id == unit_id:
                    child.parent_id = ""
            for team in company.teams:
                if team.org_unit_id == unit_id:
                    team.org_unit_id = ""
            saved = self.store.save(company)
            self._event(
                saved,
                "org_unit.deleted",
                f"Org unit '{org_unit.name}' deleted",
                actor=actor,
                org_unit_id=unit_id,
            )
            return saved

    # ------------------------------------------------------------------
    # Teams
    # ------------------------------------------------------------------

    def add_team(self, company_id: str, team: Any, actor: str = "system") -> Company:
        """
        Add a hybrid team to the company.

        Args:
            company_id: Company id.
            team: :class:`CompanyTeam` or mapping.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        payload = self._patch_dict(team)
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            payload["id"] = new_id("team")
            try:
                company_team = CompanyTeam(**payload)
            except Exception as ex:
                raise CompanyValidationError(str(ex)) from ex
            if not company_team.lead_name and company_team.members:
                company_team.lead_kind = company_team.members[0].kind
                company_team.lead_name = company_team.members[0].name
            self._ensure_unique_team_name(company, company_team.name)
            if company_team.org_unit_id and not company.org_unit(
                company_team.org_unit_id
            ):
                raise CompanyValidationError(
                    f"Org unit '{company_team.org_unit_id}' does not exist"
                )
            projects = self._project_catalog()
            for project_id in company_team.project_ids:
                self._validate_project(project_id, projects=projects)
            self._validate_team_members(company_team, projects=projects)
            company.teams.append(company_team)
            saved = self.store.save(company)
            self._event(
                saved,
                "team.created",
                f"Team '{company_team.name}' created",
                actor=actor,
                team_id=company_team.id,
                members=[member.key for member in company_team.members],
            )
            return saved

    def update_team(
        self,
        company_id: str,
        team_id: str,
        patch: Any,
        actor: str = "system",
    ) -> Company:
        """
        Update a team (including a full roster replacement when ``members`` is sent).

        Args:
            company_id: Company id.
            team_id: Team id.
            patch: Mapping with fields to change.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        values = self._patch_dict(patch)
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            team = company.team(team_id)
            if team is None:
                raise CompanyNotFound(f"Team '{team_id}' not found")
            if "name" in values:
                name = self._clean(values["name"])
                if not name:
                    raise CompanyValidationError("team name is required")
                self._ensure_unique_team_name(company, name, exclude_id=team_id)
                values["name"] = name
            if "org_unit_id" in values and values["org_unit_id"]:
                if not company.org_unit(values["org_unit_id"]):
                    raise CompanyValidationError(
                        f"Org unit '{values['org_unit_id']}' does not exist"
                    )
            if "members" in values:
                try:
                    values["members"] = CompanyMember.parse_list(values["members"])
                except Exception as ex:
                    raise CompanyValidationError(str(ex)) from ex
            if "project_ids" in values:
                projects = self._project_catalog()
                for project_id in values["project_ids"]:
                    self._validate_project(project_id, projects=projects)
            changed = self._apply(team, values, TEAM_EDITABLE_FIELDS)
            if "lead_name" in changed or "lead_kind" in changed or "members" in changed:
                team.ensure_lead()
            if not team.lead_name and team.members:
                team.lead_kind = team.members[0].kind
                team.lead_name = team.members[0].name
            team.updated_at = now_iso()
            self._validate_team_members(team)
            saved = self.store.save(company)
            if changed:
                self._event(
                    saved,
                    "team.updated",
                    f"Team '{team.name}' updated: {', '.join(changed)}",
                    actor=actor,
                    team_id=team_id,
                )
            return saved

    def delete_team(
        self,
        company_id: str,
        team_id: str,
        actor: str = "system",
        force: bool = False,
    ) -> Company:
        """
        Delete a team.

        Args:
            company_id: Company id.
            team_id: Team id.
            actor: Username recorded in the audit trail.
            force: Detach open missions instead of refusing.

        Returns:
            The updated company.

        Raises:
            CompanyConflict: When open missions reference the team and not forced.
        """
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            team = company.team(team_id)
            if team is None:
                raise CompanyNotFound(f"Team '{team_id}' not found")
            open_missions = [
                mission
                for mission in company.open_missions
                if mission.team_id == team_id
            ]
            if open_missions and not force:
                raise CompanyConflict(
                    f"Team '{team.name}' owns {len(open_missions)} open mission(s). "
                    "Reassign or close them first, or force the delete."
                )
            for mission in open_missions:
                mission.team_id = ""
                mission.updated_at = now_iso()
            company.teams = [item for item in company.teams if item.id != team_id]
            for project in company.projects:
                if project.team_id == team_id:
                    project.team_id = ""
            saved = self.store.save(company)
            self._event(
                saved,
                "team.deleted",
                f"Team '{team.name}' deleted",
                actor=actor,
                team_id=team_id,
                detached_missions=[mission.id for mission in open_missions],
            )
            return saved

    def add_team_members(
        self,
        company_id: str,
        team_id: str,
        members: Iterable[Any],
        actor: str = "system",
    ) -> Company:
        """
        Add (or update) humans and AI profiles in a team.

        Args:
            company_id: Company id.
            team_id: Team id.
            members: Names, ``kind:name`` strings or member mappings.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        try:
            parsed = CompanyMember.parse_list(list(members or []))
        except Exception as ex:
            raise CompanyValidationError(str(ex)) from ex
        if not parsed:
            raise CompanyValidationError("members are required")
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            team = company.team(team_id)
            if team is None:
                raise CompanyNotFound(f"Team '{team_id}' not found")
            self._validate_team_members(
                CompanyTeam(
                    id=team.id,
                    name=team.name,
                    members=parsed,
                    lead_kind=team.lead_kind,
                    lead_name=team.lead_name,
                )
            )
            results = [team.upsert_member(member) for member in parsed]
            if not team.lead_name:
                team.lead_kind = team.members[0].kind
                team.lead_name = team.members[0].name
            team.updated_at = now_iso()
            saved = self.store.save(company)
            self._event(
                saved,
                "team.members.added",
                f"{len(parsed)} member(s) upserted in '{team.name}'",
                actor=actor,
                team_id=team_id,
                members=[member.key for member in parsed],
                results=results,
            )
            return saved

    def remove_team_members(
        self,
        company_id: str,
        team_id: str,
        members: Iterable[str],
        actor: str = "system",
    ) -> Company:
        """
        Remove members from a team by ``kind:name`` or plain name.

        Args:
            company_id: Company id.
            team_id: Team id.
            members: References to remove.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        refs = [self._clean(member) for member in (members or []) if self._clean(member)]
        if not refs:
            raise CompanyValidationError("members are required")
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            team = company.team(team_id)
            if team is None:
                raise CompanyNotFound(f"Team '{team_id}' not found")
            removed = []
            for ref in refs:
                if ":" in ref:
                    kind, name = ref.split(":", 1)
                    if team.member(kind, name) is not None:
                        team.remove_member(kind, name)
                        removed.append(ref)
                    continue
                matching = [
                    member
                    for member in team.members
                    if member.name == ref
                ]
                for member in matching:
                    team.remove_member(member.kind, member.name)
                    removed.append(member.key)
            if not removed:
                raise CompanyValidationError(
                    f"None of {refs} is a member of '{team.name}'"
                )
            if not team.lead_name and team.members:
                team.lead_kind = team.members[0].kind
                team.lead_name = team.members[0].name
            team.updated_at = now_iso()
            saved = self.store.save(company)
            self._event(
                saved,
                "team.members.removed",
                f"{len(removed)} member(s) removed from '{team.name}'",
                actor=actor,
                team_id=team_id,
                members=removed,
            )
            return saved

    def set_team_lead(
        self,
        company_id: str,
        team_id: str,
        kind: str,
        name: str,
        actor: str = "system",
    ) -> Company:
        """
        Change a team lead (adding it to the roster when needed).

        Args:
            company_id: Company id.
            team_id: Team id.
            kind: ``user`` or ``profile``.
            name: Username or profile name.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        name = self._clean(name)
        if not name:
            raise CompanyValidationError("lead name is required")
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            team = company.team(team_id)
            if team is None:
                raise CompanyNotFound(f"Team '{team_id}' not found")
            member = CompanyMember(kind=kind or "profile", name=name, role="lead")
            self._validate_member(member)
            team.lead_kind = member.kind
            team.lead_name = member.name
            team.ensure_lead()
            team.updated_at = now_iso()
            saved = self.store.save(company)
            self._event(
                saved,
                "team.lead.changed",
                f"Team '{team.name}' lead is now {member.key}",
                actor=actor,
                team_id=team_id,
                lead=member.key,
            )
            return saved

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def link_project(
        self,
        company_id: str,
        project_id: str,
        actor: str = "system",
        **options: Any,
    ) -> Company:
        """
        Link a discovered codx-junior project to the company.

        Args:
            company_id: Company id.
            project_id: codx-junior project id.
            actor: Username recorded in the audit trail.
            **options: ``name``, ``role``, ``description``, ``team_id``,
                ``priority``, ``budget_cxjcoins``.

        Returns:
            The updated company.
        """
        project_id = self._clean(project_id)
        projects = self._project_catalog()
        self._validate_project(project_id, projects=projects)
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            existing = company.project(project_id)
            match = next(
                (item for item in projects if item["project_id"] == project_id),
                None,
            )
            payload = {
                "name": options.get("name")
                or (existing.name if existing else "")
                or (match or {}).get("project_name", project_id),
                "role": options.get("role", existing.role if existing else ""),
                "description": options.get(
                    "description", existing.description if existing else ""
                ),
                "team_id": options.get("team_id", existing.team_id if existing else ""),
                "priority": options.get(
                    "priority", existing.priority if existing else "medium"
                ),
                "budget_cxjcoins": options.get(
                    "budget_cxjcoins", existing.budget_cxjcoins if existing else 0.0
                ),
                "status": options.get(
                    "status", existing.status if existing else "active"
                ),
            }
            if payload["team_id"] and not company.team(payload["team_id"]):
                raise CompanyValidationError(
                    f"Team '{payload['team_id']}' does not exist"
                )
            if existing is None:
                company.projects.append(
                    CompanyProject(project_id=project_id, **payload)
                )
                event_type = "project.linked"
                message = f"Project '{payload['name']}' linked"
            else:
                for field, value in payload.items():
                    setattr(existing, field, value)
                existing.updated_at = now_iso()
                event_type = "project.updated"
                message = f"Project '{existing.name}' updated"
            saved = self.store.save(company)
            self._event(
                saved,
                event_type,
                message,
                actor=actor,
                project_id=project_id,
            )
            return saved

    def unlink_project(
        self,
        company_id: str,
        project_id: str,
        actor: str = "system",
        force: bool = False,
    ) -> Company:
        """
        Unlink a project from the company.

        Args:
            company_id: Company id.
            project_id: Project id.
            actor: Username recorded in the audit trail.
            force: Detach open missions instead of refusing.

        Returns:
            The updated company.

        Raises:
            CompanyConflict: When open missions run in the project and not forced.
        """
        project_id = self._clean(project_id)
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            project = company.project(project_id)
            if project is None:
                raise CompanyNotFound(f"Project '{project_id}' is not linked")
            open_missions = [
                mission
                for mission in company.open_missions
                if mission.project_id == project_id
            ]
            if open_missions and not force:
                raise CompanyConflict(
                    f"Project '{project.name or project_id}' has "
                    f"{len(open_missions)} open mission(s). Close or reassign them "
                    "first, or force the unlink."
                )
            for mission in open_missions:
                mission.project_id = ""
                mission.updated_at = now_iso()
            company.projects = [
                item for item in company.projects if item.project_id != project_id
            ]
            for team in company.teams:
                team.project_ids = [
                    item for item in team.project_ids if item != project_id
                ]
            saved = self.store.save(company)
            self._event(
                saved,
                "project.unlinked",
                f"Project '{project.name or project_id}' unlinked",
                actor=actor,
                project_id=project_id,
            )
            return saved

    # ------------------------------------------------------------------
    # Missions
    # ------------------------------------------------------------------

    def add_mission(
        self, company_id: str, mission: Any, actor: str = "system"
    ) -> Company:
        """
        Add a mission to the company.

        Args:
            company_id: Company id.
            mission: :class:`Mission` or mapping.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        payload = self._patch_dict(mission)
        payload["id"] = new_id("mission")
        payload.setdefault("created_by", actor)
        try:
            company_mission = Mission(**payload)
        except Exception as ex:
            raise CompanyValidationError(str(ex)) from ex
        if company_mission.status in ("running", "paused", "review", "done"):
            raise CompanyValidationError(
                f"A new mission cannot start in '{company_mission.status}'. "
                "Create it as draft/ready and dispatch it."
            )
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            self._validate_mission_destination(company, company_mission)
            company.missions.append(company_mission)
            saved = self.store.save(company)
            self._event(
                saved,
                "mission.created",
                f"Mission '{company_mission.title}' created",
                actor=actor,
                mission_id=company_mission.id,
                team_id=company_mission.team_id,
                project_id=company_mission.project_id,
            )
            return saved

    def update_mission(
        self,
        company_id: str,
        mission_id: str,
        patch: Any,
        actor: str = "system",
    ) -> Company:
        """
        Update a mission. Status changes go through :meth:`transition_mission`.

        Args:
            company_id: Company id.
            mission_id: Mission id.
            patch: Mapping with fields to change.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        values = self._patch_dict(patch)
        status = values.pop("status", None)
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            mission = company.get_mission(mission_id)
            if mission is None:
                raise CompanyNotFound(f"Mission '{mission_id}' not found")
            self._apply(mission, values, MISSION_EDITABLE_FIELDS)
            if status and status != mission.status:
                if not can_transition(mission.status, status):
                    raise CompanyValidationError(
                        f"Mission cannot move from '{mission.status}' to '{status}'. "
                        f"Allowed: {', '.join(MISSION_TRANSITIONS.get(mission.status, [])) or 'none'}"
                    )
                if status == "running" and not mission.run_id:
                    raise CompanyConflict(
                        "Use dispatch_mission to move a mission to running: a "
                        "running mission needs an orchestration run."
                    )
                mission.status = status
                if status == "done":
                    mission.completed_at = now_iso()
            self._validate_mission_destination(company, mission)
            mission.updated_at = now_iso()
            saved = self.store.save(company)
            self._event(
                saved,
                "mission.updated",
                f"Mission '{mission.title}' updated",
                actor=actor,
                mission_id=mission_id,
                status=mission.status,
            )
            return saved

    def delete_mission(
        self,
        company_id: str,
        mission_id: str,
        actor: str = "system",
        force: bool = False,
    ) -> Company:
        """
        Delete a mission.

        A running mission must be stopped (or forced) first, so deleting a card
        never leaves an orphan run spending money in a project.

        Args:
            company_id: Company id.
            mission_id: Mission id.
            actor: Username recorded in the audit trail.
            force: Allow deleting a running mission (the run is not cancelled).

        Returns:
            The updated company.
        """
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            mission = company.get_mission(mission_id)
            if mission is None:
                raise CompanyNotFound(f"Mission '{mission_id}' not found")
            if mission.status == "running" and not force:
                raise CompanyConflict(
                    f"Mission '{mission.title}' is running. Pause/stop it first "
                    "or force the delete."
                )
            company.missions = [
                item for item in company.missions if item.id != mission_id
            ]
            saved = self.store.save(company)
            self._event(
                saved,
                "mission.deleted",
                f"Mission '{mission.title}' deleted",
                actor=actor,
                mission_id=mission_id,
                run_id=mission.run_id,
            )
            return saved

    def dispatch_mission(
        self,
        company_id: str,
        mission_id: str,
        actor: str = "system",
        force: bool = False,
    ) -> Company:
        """
        Dispatch a mission to its project's durable orchestration runtime.

        Args:
            company_id: Company id.
            mission_id: Mission id.
            actor: Username recorded in the audit trail.
            force: Re-dispatch a mission that is already running.

        Returns:
            The updated company (mission now ``running`` with a ``run_id``).

        Raises:
            CompanyDispatchError: When the run cannot be created; the mission is
                kept in its previous state with ``last_error`` set.
        """
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            mission = company.get_mission(mission_id)
            if mission is None:
                raise CompanyNotFound(f"Mission '{mission_id}' not found")
            if mission.status == "running" and mission.run_id and not force:
                raise CompanyConflict(
                    f"Mission '{mission.title}' is already running "
                    f"(run {mission.run_id})"
                )
            if mission.status not in ("ready", "blocked", "running"):
                raise CompanyConflict(
                    f"Mission '{mission.title}' is '{mission.status}'; only ready "
                    "or blocked missions can be dispatched (move a paused mission "
                    "back to ready first)"
                )
            self._validate_mission_destination(company, mission)
            brief = self.build_mission_brief(company, mission)
            try:
                result = self._dispatcher(company, mission, brief) or {}
            except Exception as ex:
                message = str(ex) or ex.__class__.__name__
                mission.last_error = message
                mission.updated_at = now_iso()
                saved = self.store.save(company)
                self._event(
                    saved,
                    "mission.dispatch_failed",
                    f"Mission '{mission.title}' could not be dispatched: {message}",
                    actor=actor,
                    mission_id=mission_id,
                    error=message,
                )
                logger.warning("Company dispatch failed: %s", message)
                raise CompanyDispatchError(message) from ex

            mission.run_id = self._clean(result.get("run_id"))
            mission.run_status = self._clean(result.get("status") or "running")
            mission.status = "running"
            mission.dispatched_at = now_iso()
            mission.updated_at = mission.dispatched_at
            mission.last_error = ""
            mission.progress = 0
            saved = self.store.save(company)
            self._event(
                saved,
                "mission.dispatched",
                f"Mission '{mission.title}' dispatched to project "
                f"'{mission.project_id}' (run {mission.run_id or 'unknown'})",
                actor=actor,
                mission_id=mission_id,
                run_id=mission.run_id,
                project_id=mission.project_id,
                team_id=mission.team_id,
            )
            logger.info(
                "Company mission dispatched: %s (%s) run=%s",
                mission.title,
                mission.id,
                mission.run_id,
            )
            return saved

    def transition_mission(
        self,
        company_id: str,
        mission_id: str,
        status: str,
        actor: str = "system",
        force: bool = False,
    ) -> Company:
        """
        Move a mission through the explicit status machine.

        Args:
            company_id: Company id.
            mission_id: Mission id.
            status: Target status.
            actor: Username recorded in the audit trail.
            force: Skip the transition table (used by admins to repair state).

        Returns:
            The updated company.
        """
        status = self._clean(status).lower()
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            mission = company.get_mission(mission_id)
            if mission is None:
                raise CompanyNotFound(f"Mission '{mission_id}' not found")
            if not force and not can_transition(mission.status, status):
                raise CompanyValidationError(
                    f"Mission cannot move from '{mission.status}' to '{status}'. "
                    f"Allowed: {', '.join(MISSION_TRANSITIONS.get(mission.status, [])) or 'none'}"
                )
            if status == "running" and not mission.run_id:
                raise CompanyConflict(
                    "Use dispatch_mission to move a mission to running: a running "
                    "mission needs an orchestration run."
                )
            previous = mission.status
            mission.status = status
            mission.updated_at = now_iso()
            if status == "done":
                mission.completed_at = now_iso()
                mission.progress = 100
            if status == "cancelled" and mission.run_id and previous == "running":
                mission.last_error = (
                    "Mission cancelled; the orchestration run was not stopped."
                )
            saved = self.store.save(company)
            self._event(
                saved,
                "mission.transitioned",
                f"Mission '{mission.title}': {previous} → {status}",
                actor=actor,
                mission_id=mission_id,
                previous=previous,
                status=status,
            )
            return saved

    def accept_mission(
        self,
        company_id: str,
        mission_id: str,
        result: str = "",
        actor: str = "system",
    ) -> Company:
        """
        Accept a mission in review, marking it done.

        Args:
            company_id: Company id.
            mission_id: Mission id.
            result: Human summary of the outcome.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            mission = company.get_mission(mission_id)
            if mission is None:
                raise CompanyNotFound(f"Mission '{mission_id}' not found")
            if mission.status not in ("review", "running"):
                raise CompanyConflict(
                    f"Mission '{mission.title}' is '{mission.status}', not in review"
                )
            mission.status = "done"
            mission.progress = 100
            mission.completed_at = now_iso()
            mission.result = self._clean(result) or mission.result or "Accepted"
            mission.updated_at = mission.completed_at
            saved = self.store.save(company)
            self._event(
                saved,
                "mission.accepted",
                f"Mission '{mission.title}' accepted",
                actor=actor,
                mission_id=mission_id,
                run_id=mission.run_id,
                result=mission.result[:500],
            )
            return saved

    def reject_mission(
        self,
        company_id: str,
        mission_id: str,
        reason: str = "",
        actor: str = "system",
    ) -> Company:
        """
        Reject a mission in review, returning it to ``ready``.

        Args:
            company_id: Company id.
            mission_id: Mission id.
            reason: Why the outcome is not acceptable (kept for the next run).
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            mission = company.get_mission(mission_id)
            if mission is None:
                raise CompanyNotFound(f"Mission '{mission_id}' not found")
            if mission.status not in ("review", "running", "blocked"):
                raise CompanyConflict(
                    f"Mission '{mission.title}' is '{mission.status}', not in review"
                )
            previous_run = mission.run_id
            mission.status = "ready"
            mission.progress = 0
            mission.run_id = ""
            mission.run_status = ""
            mission.last_error = self._clean(reason)
            mission.updated_at = now_iso()
            saved = self.store.save(company)
            self._event(
                saved,
                "mission.rejected",
                f"Mission '{mission.title}' returned to ready",
                actor=actor,
                mission_id=mission_id,
                previous_run_id=previous_run,
                reason=mission.last_error[:500],
            )
            return saved

    # ------------------------------------------------------------------
    # Autonomy
    # ------------------------------------------------------------------

    def update_autonomy(
        self,
        company_id: str,
        patch: Any,
        actor: str = "system",
    ) -> Company:
        """
        Configure the autopilot policy.

        Args:
            company_id: Company id.
            patch: Mapping with the policy fields to change.
            actor: Username recorded in the audit trail.

        Returns:
            The updated company.
        """
        values = self._patch_dict(patch)
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            changed = self._apply(company.autonomy, values, AUTONOMY_EDITABLE_FIELDS)
            if company.autonomy.level == "off":
                company.autonomy.enabled = False
            if company.autonomy.enabled and company.autonomy.level == "off":
                company.autonomy.level = "supervised"
            if company.autonomy.last_cycle_at:
                last = parse_iso(company.autonomy.last_cycle_at) or self._now()
                company.autonomy.next_cycle_at = (
                    last + timedelta(minutes=company.autonomy.interval_minutes)
                ).isoformat()
            company.updated_at = now_iso()
            saved = self.store.save(company)
            if changed:
                self._event(
                    saved,
                    "autonomy.updated",
                    f"Autopilot updated: {', '.join(changed)}",
                    actor=actor,
                    enabled=saved.autonomy.enabled,
                    level=saved.autonomy.level,
                )
            return saved

    def sync_missions(self, company_id: str, actor: str = "system") -> Dict[str, Any]:
        """
        Mirror the orchestration runs back onto the company missions.

        Args:
            company_id: Company id.
            actor: Username recorded for status events.

        Returns:
            ``{"company_id", "checked", "changed", "missions": [...]}``.
        """
        with self.store.lock(self._company_id(company_id)):
            company = self.get_company(company_id)
            changed: List[Dict[str, Any]] = []
            checked = 0
            for mission in company.missions:
                if not mission.run_id or mission.status in ("done", "cancelled"):
                    continue
                checked += 1
                try:
                    run = self._run_status_provider(mission.project_id, mission.run_id)
                except Exception as ex:
                    logger.debug(
                        "Company: run %s not readable: %s", mission.run_id, ex
                    )
                    continue
                if not run:
                    continue
                status = self._clean(run.get("status"))
                progress = run.get("progress")
                if progress is not None:
                    mission.progress = max(0, min(100, int(progress)))
                mission.run_status = status or mission.run_status
                target = self._mission_status_for_run(company, run)
                if target and target != mission.status:
                    previous = mission.status
                    mission.status = target
                    mission.updated_at = now_iso()
                    if target == "done":
                        mission.completed_at = now_iso()
                        mission.progress = 100
                    if target == "blocked":
                        mission.last_error = (
                            self._clean(run.get("error"))
                            or f"Run finished as '{status}'"
                        )
                    changed.append(
                        {
                            "id": mission.id,
                            "title": mission.title,
                            "previous": previous,
                            "status": target,
                            "run_status": status,
                        }
                    )
                    self._event(
                        company,
                        "mission.run_synced",
                        f"Mission '{mission.title}': {previous} → {target} "
                        f"(run {status or 'unknown'})",
                        actor=actor,
                        mission_id=mission.id,
                        run_id=mission.run_id,
                        run_status=status,
                    )
            if changed:
                self.store.save(company)
            return {
                "company_id": company.id,
                "checked": checked,
                "changed": len(changed),
                "missions": changed,
            }

    def cycle(
        self,
        company_id: str,
        actor: str = "autopilot",
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Run one autonomy cycle.

        The cycle first syncs the running missions, then dispatches up to
        ``max_missions_per_cycle`` ``auto`` missions while respecting
        ``max_concurrent_missions``. A disabled autopilot does nothing unless
        *force* is set (a human asking "run one cycle now").

        Args:
            company_id: Company id.
            actor: Username recorded in the journal.
            force: Run even when the policy says it is not due/enabled.

        Returns:
            A cycle report: ``status``, ``dispatched``, ``failed``, ``synced``
            and the resulting ``autonomy`` block.
        """
        now = self._now()
        company = self.get_company(company_id)
        if not force:
            if not company.autonomy.enabled or company.autonomy.level == "off":
                return {
                    "status": "disabled",
                    "company_id": company.id,
                    "message": "Autopilot is disabled. Enable it first.",
                    "autonomy": company.autonomy.model_dump(),
                }
            if not company.autonomy.is_due(now):
                return {
                    "status": "not_due",
                    "company_id": company.id,
                    "message": (
                        "Next cycle is due at "
                        f"{company.autonomy.next_cycle_at or 'unknown'}"
                    ),
                    "autonomy": company.autonomy.model_dump(),
                }

        synced = self.sync_missions(company.id, actor=actor)
        company = self.get_company(company.id)

        candidates = self._dispatchable_missions(company)
        running = len(company.active_missions)
        slots = max(
            0,
            company.autonomy.max_concurrent_missions - running,
        )
        limit = min(slots, company.autonomy.max_missions_per_cycle)
        dispatched: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []
        for mission in candidates[:limit]:
            try:
                self.dispatch_mission(company.id, mission.id, actor=actor)
                current = self.get_company(company.id)
                updated = current.get_mission(mission.id)
                dispatched.append(
                    {
                        "id": mission.id,
                        "title": mission.title,
                        "run_id": updated.run_id if updated else "",
                    }
                )
            except Exception as ex:
                failed.append({"id": mission.id, "title": mission.title, "error": str(ex)})
                logger.warning(
                    "Company cycle could not dispatch mission '%s': %s",
                    mission.title,
                    ex,
                )

        company = self.get_company(company.id)
        summary = (
            f"{len(dispatched)} dispatched, {len(failed)} failed, "
            f"{synced.get('changed', 0)} synced"
        )
        company.autonomy.mark_cycle(summary, now=now)
        company.updated_at = now_iso()
        self.store.save(company)
        self._event(
            company,
            "autopilot.cycle",
            f"Autopilot cycle: {summary}",
            actor=actor,
            dispatched=dispatched,
            failed=failed,
            synced=synced.get("missions", []),
            forced=force,
        )
        return {
            "status": "ran",
            "company_id": company.id,
            "dispatched": dispatched,
            "failed": failed,
            "synced": synced,
            "autonomy": company.autonomy.model_dump(),
            "summary": summary,
        }

    def run_due_cycles(self, actor: str = "autopilot") -> List[Dict[str, Any]]:
        """
        Run a cycle for every company whose autopilot is due.

        Args:
            actor: Username recorded in the journals.

        Returns:
            One report per company that was due (failures included).
        """
        reports: List[Dict[str, Any]] = []
        for summary in self.list_companies():
            company_id = summary["id"]
            try:
                company = self.get_company(company_id)
            except Exception as ex:
                logger.warning("Company '%s' unreadable: %s", company_id, ex)
                continue
            if not company.autonomy.is_due(self._now()):
                continue
            try:
                reports.append(self.cycle(company_id, actor=actor))
            except Exception as ex:
                logger.exception(
                    "Company autopilot cycle failed for '%s': %s", company_id, ex
                )
                reports.append(
                    {
                        "status": "error",
                        "company_id": company_id,
                        "error": str(ex),
                    }
                )
        return reports

    # ------------------------------------------------------------------
    # Reads for the UI / tools
    # ------------------------------------------------------------------

    def snapshot(self, company_id: str, journal_limit: int = 30) -> Dict[str, Any]:
        """
        Build the full payload the company dashboard renders.

        Args:
            company_id: Company id.
            journal_limit: Number of journal entries included.

        Returns:
            ``company``, ``counts``, ``teams``, ``projects``, ``missions``,
            ``attention``, ``journal`` and ``autonomy``.
        """
        company = self.get_company(company_id)
        catalog = {project["project_id"]: project for project in self._project_catalog()}
        teams = []
        for team in company.teams:
            open_missions = [
                mission
                for mission in company.open_missions
                if mission.team_id == team.id
            ]
            teams.append(
                {
                    **team.model_dump(),
                    "human_count": team.human_count,
                    "ai_count": team.ai_count,
                    "open_missions": len(open_missions),
                    "running_missions": len(
                        [mission for mission in open_missions if mission.status == "running"]
                    ),
                }
            )
        projects = []
        for project in company.projects:
            discovered = catalog.get(project.project_id)
            projects.append(
                {
                    **project.model_dump(),
                    "available": discovered is not None,
                    "discovered_name": (discovered or {}).get("project_name", ""),
                    "discovered_path": (discovered or {}).get("project_path", ""),
                    "open_missions": len(
                        [
                            mission
                            for mission in company.open_missions
                            if mission.project_id == project.project_id
                        ]
                    ),
                }
            )
        missions = [
            mission.model_dump()
            for mission in sorted(company.missions, key=self._mission_sort_key)
        ]
        attention = self._attention(company, catalog)
        journal = [
            event.model_dump()
            for event in self.store.read_events(company.id, limit=journal_limit)
        ]
        return {
            "company": company.model_dump(),
            "counts": company.counts(),
            "teams": teams,
            "projects": projects,
            "missions": missions,
            "attention": attention,
            "journal": journal,
            "autonomy": company.autonomy.model_dump(),
            "due": company.autonomy.is_due(self._now()),
        }

    def references(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Return the catalogs a company picker needs.

        Args:
            project_id: Optional project scope for the profile catalog.

        Returns:
            ``projects``, ``users``, ``profiles`` and ``templates``.
        """
        projects = self._project_catalog()
        profiles = self._profile_catalog([project_id] if project_id else None)
        return {
            "projects": projects,
            "users": self._users(),
            "profiles": profiles,
            "templates": ["blank", "saas"],
        }

    def resolve_team(self, company_id: str, team_id: str) -> Dict[str, Any]:
        """
        Resolve a team into its roster, with availability per reference.

        Args:
            company_id: Company id.
            team_id: Team id.

        Returns:
            The team, its members with ``available`` flags and mission counts.
        """
        company = self.get_company(company_id)
        team = company.team(team_id)
        if team is None:
            raise CompanyNotFound(f"Team '{team_id}' not found")
        profiles = {
            profile["name"]: profile for profile in self._profile_catalog(team.project_ids)
        }
        users = {user["username"]: user for user in self._users()}
        members = []
        for member in team.members:
            entry = member.model_dump()
            if member.is_ai:
                entry["available"] = not profiles or member.name in profiles
                entry["projects"] = (profiles.get(member.name) or {}).get("projects", [])
            else:
                entry["available"] = not users or member.name in users
                entry["projects"] = []
            members.append(entry)
        return {
            **team.model_dump(),
            "members": members,
            "human_count": team.human_count,
            "ai_count": team.ai_count,
            "missions": [
                mission.model_dump()
                for mission in company.missions
                if mission.team_id == team.id
            ],
        }

    def journal(self, company_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Return the most recent journal events (newest last)."""
        company = self.get_company(company_id)
        return [
            event.model_dump()
            for event in self.store.read_events(company.id, limit=limit)
        ]

    def build_mission_brief(self, company: Company, mission: Mission) -> str:
        """
        Build the objective handed to the project orchestration run.

        The brief is what makes the AI team work *as the company*: it carries the
        company direction, the org context, the team roster with responsibilities
        and the acceptance criteria, not just the mission title.

        Args:
            company: Owning company.
            mission: Mission to dispatch.

        Returns:
            A markdown brief.
        """
        team = company.team(mission.team_id)
        project = company.project(mission.project_id)
        org_unit = company.org_unit(team.org_unit_id) if team else None
        lines = [
            f"# Mission: {mission.title}",
            "",
            "## Company",
            f"- **Company:** {company.name}",
        ]
        if company.mission:
            lines.append(f"- **Mission:** {company.mission}")
        if company.vision:
            lines.append(f"- **Vision:** {company.vision}")
        if company.values:
            lines.append(f"- **Values:** {', '.join(company.values)}")
        lines += ["", "## Mission objective", mission.objective or mission.title]
        if mission.acceptance:
            lines += ["", "## Acceptance criteria", mission.acceptance]
        if project:
            lines += [
                "",
                "## Project",
                f"- **Project:** {project.name or project.project_id}",
                f"- **Role in the company:** {project.role or 'not specified'}",
            ]
            if project.description:
                lines.append(f"- **Why it exists:** {project.description}")
        if team:
            lines += [
                "",
                "## Team",
                f"- **Team:** {team.name}",
            ]
            if team.purpose:
                lines.append(f"- **Purpose:** {team.purpose}")
            if org_unit:
                lines.append(f"- **Org unit:** {org_unit.name} ({org_unit.kind})")
            lines.append("- **Roster:**")
            for member in team.members:
                role = member.role or "member"
                responsibility = f" — {member.responsibility}" if member.responsibility else ""
                lines.append(
                    f"  - `{member.name}` ({member.kind}, {role}){responsibility}"
                )
            lines += [
                "",
                "Work as this team. Use the team profiles for their areas of "
                "ownership, keep the work visible on the project board, and "
                "verify the result against the acceptance criteria before "
                "reporting completion.",
            ]
        if mission.due_date:
            lines += ["", f"Due date: {mission.due_date}"]
        if mission.last_error and mission.status in ("ready", "blocked"):
            lines += [
                "",
                "## Previous attempt feedback",
                mission.last_error,
                "Address this feedback explicitly in the new run.",
            ]
        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _patch_dict(value: Any) -> Dict[str, Any]:
        """Convert a model/patch into a plain dict, dropping private keys."""
        if value is None:
            return {}
        if hasattr(value, "model_dump"):
            data = value.model_dump(exclude_unset=True)
        elif isinstance(value, dict):
            data = dict(value)
        else:
            raise CompanyValidationError(
                f"Expected an object, got {type(value).__name__}"
            )
        return {key: item for key, item in data.items() if not key.startswith("_")}

    def _company_id(self, company_id: str) -> str:
        """Resolve a company id/slug to the stored id (used for locks)."""
        return self.get_company(company_id).id

    def _ensure_unique_children(self, company: Company) -> None:
        """Validate child names/ids and referential integrity of a new company."""
        names = set()
        for unit in company.org_units:
            key = unit.name.lower()
            if key in names:
                raise CompanyConflict(f"Duplicated org unit name: {unit.name}")
            names.add(key)
        team_names = set()
        for team in company.teams:
            key = team.name.lower()
            if key in team_names:
                raise CompanyConflict(f"Duplicated team name: {team.name}")
            team_names.add(key)
            if team.org_unit_id and not company.org_unit(team.org_unit_id):
                raise CompanyValidationError(
                    f"Team '{team.name}' points at unknown org unit "
                    f"'{team.org_unit_id}'"
                )
        for project in company.projects:
            if not project.project_id:
                raise CompanyValidationError("company project needs a project_id")
        mission_ids = set()
        for mission in company.missions:
            if mission.id in mission_ids:
                raise CompanyConflict(f"Duplicated mission id: {mission.id}")
            mission_ids.add(mission.id)

    def _ensure_unique_org_name(
        self, company: Company, name: str, exclude_id: str = ""
    ) -> None:
        """Reject a duplicated org unit name (case-insensitive)."""
        wanted = (name or "").strip().lower()
        for unit in company.org_units:
            if unit.id != exclude_id and unit.name.lower() == wanted:
                raise CompanyConflict(f"An org unit named '{name}' already exists")

    def _ensure_unique_team_name(
        self, company: Company, name: str, exclude_id: str = ""
    ) -> None:
        """Reject a duplicated team name (case-insensitive)."""
        wanted = (name or "").strip().lower()
        for team in company.teams:
            if team.id != exclude_id and team.name.lower() == wanted:
                raise CompanyConflict(f"A team named '{name}' already exists")

    def _validate_mission_destination(self, company: Company, mission: Mission) -> None:
        """Validate the team/project of a mission (project optional while draft)."""
        if mission.team_id and not company.team(mission.team_id):
            raise CompanyValidationError(
                f"Team '{mission.team_id}' does not exist in this company"
            )
        if mission.project_id:
            if not company.project(mission.project_id):
                raise CompanyValidationError(
                    f"Project '{mission.project_id}' is not linked to this company"
                )
        elif mission.status in ("ready", "running"):
            raise CompanyValidationError(
                "A ready/running mission needs a linked project_id"
            )

    def _dispatchable_missions(self, company: Company) -> List[Mission]:
        """
        Return the auto missions that are ready to be dispatched.

        A mission is dispatchable by the autopilot only when it is ``ready``,
        marked ``auto``, has a team and a project, **and** its team is not
        ``manual``: a manual team explicitly only accepts human dispatches.
        """
        candidates = []
        for mission in company.missions:
            if (
                mission.status != "ready"
                or mission.dispatch_mode != "auto"
                or not mission.team_id
                or not mission.project_id
            ):
                continue
            team = company.team(mission.team_id)
            if team is not None and team.autonomy == "manual":
                continue
            candidates.append(mission)
        return sorted(candidates, key=self._mission_sort_key)

    @staticmethod
    def _mission_sort_key(mission: Mission) -> Tuple[int, str, str]:
        """Sort missions by priority, then due date, then creation."""
        return (
            _PRIORITY_RANK.get(mission.priority, 9),
            mission.due_date or "9999-12-31",
            mission.created_at or "",
        )

    def _mission_status_for_run(self, company: Company, run: Dict[str, Any]) -> Optional[str]:
        """Map an orchestration run status onto a mission status."""
        status = (run.get("status") or "").strip().lower()
        if status in _ACTIVE_RUN_STATUSES:
            return "running"
        if status == "paused":
            return "paused"
        if status == "completed":
            if (
                company.autonomy.level == "autonomous"
                and not company.autonomy.require_human_acceptance
            ):
                return "done"
            return "review"
        if status in ("failed", "stopped", "budget_exhausted", "stalled"):
            return "blocked"
        return None

    def _attention(
        self, company: Company, catalog: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build the "needs a human" list shown on the dashboard."""
        today = date.today()
        items: List[Dict[str, Any]] = []
        for mission in company.missions:
            reason = ""
            if mission.status == "blocked":
                reason = "blocked"
            elif mission.last_error:
                reason = "error"
            elif mission.due_date:
                try:
                    due = date.fromisoformat(mission.due_date[:10])
                    if due < today and mission.is_open:
                        reason = "overdue"
                except ValueError:
                    pass
            elif not mission.team_id and mission.is_open:
                reason = "unassigned_team"
            elif not mission.project_id and mission.status in ("ready", "running"):
                reason = "unassigned_project"
            if not reason:
                continue
            items.append(
                {
                    "mission_id": mission.id,
                    "title": mission.title,
                    "status": mission.status,
                    "priority": mission.priority,
                    "reason": reason,
                    "last_error": mission.last_error,
                    "due_date": mission.due_date,
                    "project_id": mission.project_id,
                }
            )
        for project in company.projects:
            if project.project_id not in catalog:
                items.append(
                    {
                        "mission_id": "",
                        "title": project.name or project.project_id,
                        "status": project.status,
                        "priority": project.priority,
                        "reason": "project_missing",
                        "project_id": project.project_id,
                    }
                )
        return items

    # ------------------------------------------------------------------
    # Default dispatch / run status (durable orchestration)
    # ------------------------------------------------------------------

    @staticmethod
    def _board_title(value: str, fallback: str) -> str:
        """
        Turn a company/mission name into a safe board title.

        Board titles become folders under ``.codx/tasks``. Path separators and
        control characters are stripped so a company name like ``a/b`` can never
        escape the project's tasks folder, and the title is kept short enough to
        stay readable on a card.
        """
        title = re.sub(r"[\\/:*?\"<>|\x00-\x1f]+", " ", str(value or ""))
        title = " ".join(title.split()).strip()
        return (title[:60] or fallback).strip()

    def _default_dispatcher(
        self, company: Company, mission: Mission, brief: str
    ) -> Dict[str, Any]:
        """
        Start a durable orchestration run for a mission.

        The AI stack is imported lazily: creating a company or editing its org
        never pays for it.
        """
        settings = self._project_settings_provider(mission.project_id)
        if settings is None:
            raise CompanyDispatchError(
                f"Project '{mission.project_id}' is not available (not discovered). "
                "Make sure the project is registered in codx-junior."
            )
        try:
            from codx.junior.chat_manager import ChatManager
            from codx.junior.orchestration.models import RunConfig
            from codx.junior.orchestration.service import OrchestrationService
        except Exception as ex:  # pragma: no cover - AI stack unavailable
            raise CompanyDispatchError(
                f"The orchestration runtime is not available: {ex}"
            ) from ex

        team = company.team(mission.team_id)
        profiles = self._project_profiles(settings, team)
        config = RunConfig(
            budget_cxjcoins=float(mission.budget_cxjcoins or 0.0),
            supervisor_profiles=profiles,
            board=self._board_title(company.name, "Company"),
            sprint=f"Mission: {self._board_title(mission.title, mission.id[-6:])}",
            verification="supervisor",
            created_by="company",
        )
        service = OrchestrationService(
            settings=settings,
            chat_manager=ChatManager(settings=settings),
        )
        run = service.create_run(
            name=mission.title,
            objective=brief,
            config=config,
            created_by="company",
            start=True,
            persist_main=True,
        )
        return {
            "run_id": run.run_id,
            "status": run.status,
            "main_chat_id": run.main_chat_id,
        }

    def _project_profiles(self, settings: Any, team: Optional[CompanyTeam]) -> List[str]:
        """
        Pick the supervisor profiles that exist in the target project.

        The team lead is preferred; ``orchestrator``/``software_developer`` are
        safe fallbacks because they ship with codx-junior.
        """
        try:
            from codx.junior.profiles.profile_manager import ProfileManager

            available = {
                profile.name
                for profile in ProfileManager(settings=settings).list_all_profiles()
                if profile and profile.name
            }
        except Exception:
            available = set()
        wanted: List[str] = []
        if team and team.lead_kind == "profile" and team.lead_name:
            wanted.append(team.lead_name)
        if team:
            wanted.extend(
                member.name
                for member in team.members
                if member.is_ai and member.name not in wanted
            )
        for fallback in ("orchestrator", "project", "software_developer"):
            if fallback not in wanted:
                wanted.append(fallback)
        selected = [name for name in wanted if not available or name in available]
        if not selected:
            selected = ["orchestrator"] if "orchestrator" in available else list(available)[:1]
        # The first selected profile is the supervisor; keep the list small so
        # the main task is not composed with the whole roster.
        return selected[:1] if selected else ["orchestrator"]

    def _default_run_status(self, project_id: str, run_id: str) -> Dict[str, Any]:
        """Read an orchestration run from the project store (light import)."""
        settings = self._project_settings_provider(project_id)
        if settings is None:
            raise CompanyDispatchError(
                f"Project '{project_id}' is not available (not discovered)"
            )
        from codx.junior.orchestration.store import RunStore

        run = RunStore(getattr(settings, "codx_path", "")).load(run_id)
        return {
            "run_id": run.run_id,
            "status": run.status,
            "progress": run.progress(),
            "error": getattr(run, "last_error", "") or "",
            "name": run.name,
        }


# Made with ❤️ by codx-junior
