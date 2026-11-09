"""
Domain model of a codx-junior company.

A company is the **top-level** entity of the product:

```text
Company
├── Organization (departments / functions)   ← who is accountable for what
├── Teams (humans + AI profiles)             ← who does the work
├── Projects (linked codx-junior projects)   ← where the work happens
└── Missions (objectives)                    ← what the company is doing
```

Design notes
------------
* **References, never copies.** A team member is a ``(kind, name)`` reference:
  ``kind="user"`` points at a codx-junior user and ``kind="profile"`` points at
  an AI profile. Missions reference a team and a project by id, and the
  executable work is dispatched to the project's durable orchestration runtime.
  Nothing is duplicated, so a company can never silently drift from the project
  it runs.
* **One stored document + one journal.** ``store.py`` persists the company as a
  single JSON document and appends human-readable events to ``journal.jsonl``.
  The model below is the single source of truth for that document.
* **Derived fields are computed, never stored.** ``profile_names``,
  ``human_count``, ``ai_count``, ``open`` and friends are properties so they
  cannot disagree with the roster or the status.
* **Pydantic v2.** Validators normalise user input (``human`` → ``user``,
  ``ai``/``agent`` → ``profile``, trimming, de-duplication) so the API, the
  tools and the on-disk documents all share one shape.

Typical stored company (abridged):

```json
{
  "id": "6f1b2c3d-4e5f-6789-abcd-ef0123456789",
  "name": "codx-junior cloud",
  "slug": "codx-junior-cloud",
  "mission": "Offer codx-junior as a service",
  "org_units": [{"id": "org-eng", "name": "Engineering", "kind": "department"}],
  "teams": [{
    "id": "team-core",
    "name": "Core Platform",
    "org_unit_id": "org-eng",
    "lead": {"kind": "profile", "name": "orchestrator"},
    "members": [
      {"kind": "profile", "name": "software_developer", "role": "builder"},
      {"kind": "user", "name": "alice", "role": "product owner"}
    ],
    "project_ids": ["proj_123"]
  }],
  "projects": [{"project_id": "proj_123", "role": "platform"}],
  "missions": [{
    "id": "mission-1",
    "title": "Ship the hosted provisioning flow",
    "status": "ready",
    "team_id": "team-core",
    "project_id": "proj_123",
    "dispatch_mode": "auto"
  }],
  "autonomy": {"enabled": false, "level": "supervised", "interval_minutes": 60}
}
```

Made with ❤️ by codx-junior
"""

from __future__ import annotations

import re
import uuid

from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Canonical values
# ---------------------------------------------------------------------------

COMPANY_STATUSES = ("active", "paused", "archived")
ORG_UNIT_KINDS = ("department", "function", "division")
MEMBER_KINDS = ("user", "profile")

MISSION_STATUSES = (
    "draft",
    "ready",
    "running",
    "paused",
    "blocked",
    "review",
    "done",
    "cancelled",
)
MISSION_OPEN_STATUSES = ("ready", "running", "paused", "blocked", "review")
MISSION_PRIORITIES = ("low", "medium", "high", "critical")
MISSION_DISPATCH_MODES = ("manual", "auto")
MISSION_SOURCES = ("human", "autopilot", "template")

AUTONOMY_LEVELS = ("off", "supervised", "autonomous")
TEAM_AUTONOMY_LEVELS = ("manual", "supervised", "autonomous")

#: Longer names are unreadable in a card and cannot be referenced safely.
MAX_NAME_LENGTH = 120

#: Prefix used to build readable ids (``org-...``, ``team-...``, ``msn-...``).
ID_PREFIXES = {
    "company": "cmp",
    "org": "org",
    "team": "team",
    "mission": "msn",
    "event": "evt",
    "spend": "spd",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def now_iso() -> str:
    """Return the current local time as an ISO-8601 string."""
    return datetime.now().isoformat()


def new_id(kind: str) -> str:
    """
    Return a readable, collision-safe id for *kind*.

    Args:
        kind: One of :data:`ID_PREFIXES` (``company``, ``org``, ``team``,
            ``mission``, ``event``).

    Returns:
        ``"<prefix>-<uuid4 hex>"``.
    """
    return f"{ID_PREFIXES.get(kind, 'id')}-{uuid.uuid4().hex}"


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 string, returning ``None`` when it is invalid/empty."""
    if not value:
        return None
    try:
        # ``Z`` is not accepted by every supported Python version.
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def slugify(value: str, fallback: str = "company") -> str:
    """
    Build a URL/file friendly slug from a free-form name.

    Args:
        value: Human readable name.
        fallback: Slug used when *value* has no usable characters.

    Returns:
        Lowercase slug with letters, digits and single dashes.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")
    return slug[:MAX_NAME_LENGTH] or fallback


def _clean(value: Any) -> str:
    """Trim a value into a string (``None`` becomes ``""``)."""
    return str(value).strip() if value is not None else ""


def _unique(items: Iterable[str]) -> List[str]:
    """Return the items in order, trimmed, without empty entries or duplicates."""
    seen = set()
    result: List[str] = []
    for item in items or []:
        text = _clean(item)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _normalize_member_kind(value: Any) -> str:
    """Map human-friendly member kinds onto the canonical ``user``/``profile``."""
    kind = _clean(value).lower()
    if kind in ("human", "user", "person", "employee"):
        return "user"
    if kind in ("ai", "agent", "profile", "assistant", "bot", "robot"):
        return "profile"
    return kind or "profile"


class CompanyMember(BaseModel):
    """
    A human user or an AI profile taking part in a company, org unit or team.

    The member is a **reference**: ``kind`` says which catalog owns the name
    (codx-junior users or project profiles). The company stores only what is
    specific to this organization: the role and the responsibility.

    Attributes:
        kind: ``user`` (human) or ``profile`` (AI). ``human``/``ai``/``agent``
            are accepted as aliases and normalized.
        name: Username for humans, profile name for AI members.
        role: Role inside the company/team (``ceo``, ``builder``, ``reviewer``).
        title: Human readable title shown in the UI.
        responsibility: One line describing what this member owns.
        order: Sort order inside the roster.
        active: Whether the member is currently available.
    """

    model_config = {"validate_assignment": True}

    kind: str = Field(
        default="profile",
        description="Reference kind: 'user' (human) or 'profile' (AI)",
    )
    name: str = Field(default="", description="Username or profile name")
    role: str = Field(default="", description="Role inside the company or team")
    title: str = Field(default="", description="Human readable title")
    responsibility: str = Field(
        default="", description="One line: what this member owns"
    )
    order: int = Field(default=0, description="Sort order inside the roster")
    active: bool = Field(default=True, description="Member is currently available")

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, value: Any) -> str:
        """Normalize the member kind aliases."""
        return _normalize_member_kind(value)

    @field_validator("name", "role", "title", "responsibility", mode="before")
    @classmethod
    def _strip(cls, value: Any) -> str:
        """Trim free-form strings so references match exactly."""
        return _clean(value)

    @field_validator("order", mode="before")
    @classmethod
    def _order(cls, value: Any) -> int:
        """Treat an unset order as 0 instead of failing validation."""
        return 0 if value is None else int(value)

    @field_validator("name")
    @classmethod
    def _name_required(cls, value: str) -> str:
        """A member without a name cannot be resolved; reject it early."""
        if not value:
            raise ValueError("member name is required")
        return value

    @field_validator("kind")
    @classmethod
    def _kind_required(cls, value: str) -> str:
        """Only users and profiles are valid reference kinds."""
        if value not in MEMBER_KINDS:
            raise ValueError(
                f"invalid member kind '{value}' (expected one of "
                f"{', '.join(MEMBER_KINDS)})"
            )
        return value

    @property
    def key(self) -> str:
        """Stable ``kind:name`` key used for de-duplication and removals."""
        return f"{self.kind}:{self.name}"

    @property
    def is_ai(self) -> bool:
        """``True`` when the member is an AI profile."""
        return self.kind == "profile"

    @property
    def is_human(self) -> bool:
        """``True`` when the member is a human user."""
        return self.kind == "user"

    @classmethod
    def from_any(cls, value: Any) -> "CompanyMember":
        """
        Build a member from a name, a mapping or an existing member.

        Plain strings are treated as AI profiles because that is the most common
        reference in a company command tool; humans must say ``"user:alice"``
        or send an object with ``{"kind": "user", "name": "alice"}``.

        Args:
            value: ``"analyst"``, ``"user:alice"``, a dict or a member.

        Returns:
            The validated member.

        Raises:
            ValueError: If the value cannot be interpreted.
        """
        if isinstance(value, CompanyMember):
            return value.model_copy()
        if isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError("empty member reference")
            if ":" in text.split("/", 1)[0]:
                kind, name = text.split(":", 1)
                return cls(kind=kind, name=name)
            return cls(kind="profile", name=text)
        if isinstance(value, dict):
            return cls(
                kind=value.get("kind") or value.get("type") or "profile",
                name=value.get("name") or value.get("username") or value.get("profile") or "",
                role=value.get("role") or "",
                title=value.get("title") or "",
                responsibility=value.get("responsibility") or value.get("description") or "",
                order=value.get("order", 0),
                active=value.get("active", True),
            )
        raise ValueError(
            f"invalid member {value!r}: expected a name, an object or a member"
        )

    @classmethod
    def parse_list(cls, values: Optional[Iterable[Any]]) -> List["CompanyMember"]:
        """
        Normalize a list of member references, de-duplicating by ``kind:name``.

        Args:
            values: Iterable of names, mappings or members.

        Returns:
            Members in the given order.

        Raises:
            ValueError: If any entry is invalid.
        """
        members: List[CompanyMember] = []
        seen = set()
        for index, value in enumerate(values or []):
            member = cls.from_any(value)
            if not member.order:
                member.order = index
            if member.key in seen:
                continue
            seen.add(member.key)
            members.append(member)
        return members


class OrgUnit(BaseModel):
    """
    A department, function or division of the company organization.

    Org units form a tree through ``parent_id`` (empty means top level). Teams
    point at the org unit that owns them, so moving a team or renaming a
    department never touches the team itself.

    Attributes:
        id: Unique org unit id.
        name: Name shown in the org chart (``Engineering``, ``Customer Success``).
        kind: ``department``, ``function`` or ``division``.
        description: What the unit is responsible for.
        parent_id: Parent unit id (empty for a top-level unit).
        lead_kind / lead_name: Member reference of the unit lead.
        responsibilities: Concrete responsibilities (used in mission briefs).
        color: UI accent colour.
        icon: UI FontAwesome class.
        order: Sort order among siblings.
    """

    model_config = {"validate_assignment": True}

    id: str = Field(default="", description="Unique org unit id")
    name: str = Field(default="", description="Department/function name")
    kind: str = Field(
        default="department", description="department | function | division"
    )
    description: str = Field(default="", description="What this unit owns")
    parent_id: str = Field(default="", description="Parent org unit id")
    lead_kind: str = Field(
        default="user", description="Lead reference kind: user | profile"
    )
    lead_name: str = Field(default="", description="Lead username or profile name")
    responsibilities: List[str] = Field(
        default_factory=list, description="Concrete responsibilities of the unit"
    )
    color: str = Field(default="#6366f1", description="UI accent colour")
    icon: str = Field(default="", description="UI FontAwesome class")
    order: int = Field(default=0, description="Sort order among siblings")
    created_at: str = Field(default_factory=now_iso, description="Creation timestamp")
    updated_at: str = Field(default_factory=now_iso, description="Last update timestamp")

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, value: Any) -> str:
        """Validate the org unit kind."""
        kind = _clean(value).lower() or "department"
        if kind not in ORG_UNIT_KINDS:
            raise ValueError(
                f"invalid org unit kind '{kind}' (expected one of "
                f"{', '.join(ORG_UNIT_KINDS)})"
            )
        return kind

    @field_validator("lead_kind", mode="before")
    @classmethod
    def _lead_kind(cls, value: Any) -> str:
        """Normalize the lead reference kind."""
        kind = _normalize_member_kind(value)
        return kind if kind in MEMBER_KINDS else "user"

    @field_validator("name", "description", "parent_id", "lead_name", "color", "icon", mode="before")
    @classmethod
    def _strip(cls, value: Any) -> str:
        """Trim free-form strings."""
        return _clean(value)

    @field_validator("responsibilities", mode="before")
    @classmethod
    def _responsibilities(cls, value: Any) -> List[str]:
        """Normalize responsibilities into a de-duplicated list of strings."""
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return _unique(value)

    @model_validator(mode="after")
    def _validate(self) -> "OrgUnit":
        """Require a name and forbid a unit from being its own parent."""
        if not self.name:
            raise ValueError("org unit name is required")
        if self.parent_id and self.parent_id == self.id:
            raise ValueError("an org unit cannot be its own parent")
        return self

    @property
    def lead(self) -> Optional[CompanyMember]:
        """Return the lead as a member reference, or ``None`` when unset."""
        if not self.lead_name:
            return None
        return CompanyMember(kind=self.lead_kind, name=self.lead_name, role="lead")


class CompanyTeam(BaseModel):
    """
    A hybrid team of humans and AI profiles inside the company.

    The team is the **composition layer** of the company: it references users
    and profiles (never copies them), can be attached to one or more projects,
    and is the unit missions are assigned to. The lead is always kept in the
    roster so a team can never point at a coordinator it does not own.

    Attributes:
        id: Unique team id.
        name: Team name (unique inside the company).
        description: What the team does, in 1-3 sentences.
        purpose: The outcome the team is responsible for.
        org_unit_id: Org unit that owns the team (empty = unassigned).
        lead_kind / lead_name: Member reference of the team lead.
        members: Hybrid roster (humans + AI profiles).
        project_ids: Projects this team works on (empty = any company project).
        autonomy: How much the team can do without a human (manual |
            supervised | autonomous).
        tools: Extra tool names granted to the team.
        tags: Discovery tags.
        color / icon: UI presentation.
    """

    model_config = {"validate_assignment": True}

    id: str = Field(default="", description="Unique team id")
    name: str = Field(default="", description="Team name")
    description: str = Field(default="", description="What the team does")
    purpose: str = Field(default="", description="Outcome the team owns")
    org_unit_id: str = Field(default="", description="Owning org unit id")
    lead_kind: str = Field(default="profile", description="Lead reference kind")
    lead_name: str = Field(default="", description="Lead username or profile name")
    members: List[CompanyMember] = Field(
        default_factory=list, description="Hybrid roster (humans + AI profiles)"
    )
    project_ids: List[str] = Field(
        default_factory=list, description="Projects this team works on"
    )
    autonomy: str = Field(
        default="supervised", description="manual | supervised | autonomous"
    )
    tools: List[str] = Field(default_factory=list, description="Extra tool names")
    tags: List[str] = Field(default_factory=list, description="Discovery tags")
    budget_cxjcoins: float = Field(
        default=0.0,
        description="Optional AI budget for this team (0 = no limit)",
    )
    color: str = Field(default="#6366f1", description="UI accent colour")
    icon: str = Field(default="fa-solid fa-people-group", description="UI icon")
    created_at: str = Field(default_factory=now_iso, description="Creation timestamp")
    updated_at: str = Field(default_factory=now_iso, description="Last update timestamp")

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data: Any) -> Any:
        """Normalize member aliases before validation."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if "members" in data:
            data["members"] = CompanyMember.parse_list(data.get("members"))
        if "lead" in data and not data.get("lead_name"):
            lead = data.get("lead")
            if isinstance(lead, dict):
                data["lead_kind"] = lead.get("kind") or data.get("lead_kind") or "profile"
                data["lead_name"] = lead.get("name") or ""
            elif isinstance(lead, str) and lead:
                data["lead_name"] = lead
        return data

    @field_validator("lead_kind", mode="before")
    @classmethod
    def _lead_kind(cls, value: Any) -> str:
        """Normalize the lead reference kind."""
        kind = _normalize_member_kind(value)
        return kind if kind in MEMBER_KINDS else "profile"

    @field_validator("autonomy", mode="before")
    @classmethod
    def _autonomy(cls, value: Any) -> str:
        """Validate the team autonomy level."""
        level = _clean(value).lower() or "supervised"
        if level not in TEAM_AUTONOMY_LEVELS:
            raise ValueError(
                f"invalid team autonomy '{level}' (expected one of "
                f"{', '.join(TEAM_AUTONOMY_LEVELS)})"
            )
        return level

    @field_validator("name", "description", "purpose", "lead_name", "color", "icon", mode="before")
    @classmethod
    def _strip(cls, value: Any) -> str:
        """Trim free-form strings."""
        return _clean(value)

    @field_validator("project_ids", "tools", "tags", mode="before")
    @classmethod
    def _string_lists(cls, value: Any) -> List[str]:
        """Normalize string lists (accept a single string)."""
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return _unique(value)

    @field_validator("budget_cxjcoins", mode="before")
    @classmethod
    def _budget(cls, value: Any) -> float:
        """Clamp the team budget to a non-negative number."""
        try:
            return max(0.0, float(value or 0.0))
        except (TypeError, ValueError):
            return 0.0

    @model_validator(mode="after")
    def _validate(self) -> "CompanyTeam":
        """Require a name and keep the lead in the roster."""
        if not self.name:
            raise ValueError("team name is required")
        if len(self.name) > MAX_NAME_LENGTH:
            raise ValueError(f"team name is longer than {MAX_NAME_LENGTH} characters")
        self.ensure_lead()
        return self

    def ensure_lead(self) -> bool:
        """
        Add the lead to the roster when it is missing.

        A lead outside the roster would coordinate a team it does not own, so
        every write path calls this. The lead is placed first.

        Returns:
            ``True`` when the lead had to be added.
        """
        if not self.lead_name:
            return False
        exact = next(
            (
                member
                for member in self.members
                if member.kind == self.lead_kind and member.name == self.lead_name
            ),
            None,
        )
        if exact is not None:
            return False
        # A write can set lead_kind and lead_name in two assignment steps; the
        # first step would otherwise add a second copy of the SAME person under
        # the new kind. Align the existing reference instead.
        same_name = next(
            (member for member in self.members if member.name == self.lead_name),
            None,
        )
        if same_name is not None:
            # The same person is already in the roster under another kind
            # reference. Do not duplicate it and do not rewrite the existing
            # reference: a later assignment completes the lead change.
            return False
        self.members = [
            CompanyMember(
                kind=self.lead_kind,
                name=self.lead_name,
                role="lead",
                order=-1,
            )
        ] + list(self.members)
        return True

    @property
    def lead_member(self) -> Optional[CompanyMember]:
        """Return the lead member from the roster (or a virtual reference)."""
        if not self.lead_name:
            return None
        for member in self.members:
            if member.kind == self.lead_kind and member.name == self.lead_name:
                return member
        return CompanyMember(kind=self.lead_kind, name=self.lead_name, role="lead")

    @property
    def human_count(self) -> int:
        """Number of human members."""
        return sum(1 for member in self.members if member.is_human)

    @property
    def ai_count(self) -> int:
        """Number of AI profile members."""
        return sum(1 for member in self.members if member.is_ai)

    @property
    def profile_names(self) -> List[str]:
        """Profile names in the roster (the AI part of the team)."""
        return [member.name for member in self.members if member.is_ai]

    @property
    def user_names(self) -> List[str]:
        """Usernames in the roster (the human part of the team)."""
        return [member.name for member in self.members if member.is_human]

    def member(self, kind: str, name: str) -> Optional[CompanyMember]:
        """Find a roster member by reference."""
        kind = _normalize_member_kind(kind)
        return next(
            (
                member
                for member in self.members
                if member.kind == kind and member.name == name
            ),
            None,
        )

    def upsert_member(self, member: CompanyMember) -> str:
        """
        Add or update a member.

        Args:
            member: Member to add/update.

        Returns:
            ``"added"`` or ``"updated"``.
        """
        existing = self.member(member.kind, member.name)
        if existing is not None:
            existing.role = member.role or existing.role
            existing.title = member.title or existing.title
            existing.responsibility = member.responsibility or existing.responsibility
            existing.active = member.active
            return "updated"
        member.order = len(self.members) if not member.order else member.order
        self.members.append(member)
        if not self.lead_name:
            self.lead_kind = member.kind
            self.lead_name = member.name
        return "added"

    def remove_member(self, kind: str, name: str) -> bool:
        """
        Remove a member, clearing the lead when it is the one removed.

        Args:
            kind: Reference kind.
            name: Username or profile name.

        Returns:
            ``True`` when the removed member was the lead.
        """
        kind = _normalize_member_kind(kind)
        self.members = [
            member
            for member in self.members
            if not (member.kind == kind and member.name == name)
        ]
        if self.lead_kind == kind and self.lead_name == name:
            self.lead_kind = "profile"
            self.lead_name = ""
            return True
        return False


class CompanyProject(BaseModel):
    """
    A codx-junior project linked to the company.

    The company never copies project settings: it stores the reference
    (``project_id``), the role the project plays in the company and which team
    owns it. Names/paths are cached only for display; discovery remains the
    source of truth.

    Attributes:
        project_id: codx-junior project id.
        name: Cached project name for display.
        role: Role in the company (``platform``, ``marketing-site``...).
        description: Why the project exists in the company.
        team_id: Team that owns the project (empty = unassigned).
        priority: Company priority (low/medium/high/critical).
        status: ``active``, ``paused`` or ``archived``.
        budget_cxjcoins: Optional AI budget assigned to the project.
    """

    model_config = {"validate_assignment": True}

    project_id: str = Field(default="", description="codx-junior project id")
    name: str = Field(default="", description="Cached project name")
    role: str = Field(default="", description="Role inside the company")
    description: str = Field(default="", description="Why the project exists")
    team_id: str = Field(default="", description="Owning team id")
    priority: str = Field(default="medium", description="low | medium | high | critical")
    status: str = Field(default="active", description="active | paused | archived")
    budget_cxjcoins: float = Field(default=0.0, description="Optional AI budget")
    created_at: str = Field(default_factory=now_iso, description="Creation timestamp")
    updated_at: str = Field(default_factory=now_iso, description="Last update timestamp")

    @field_validator("project_id")
    @classmethod
    def _project_id(cls, value: str) -> str:
        """A project reference must have an id."""
        value = _clean(value)
        if not value:
            raise ValueError("project_id is required")
        return value

    @field_validator("priority", mode="before")
    @classmethod
    def _priority(cls, value: Any) -> str:
        """Validate the project priority."""
        priority = _clean(value).lower() or "medium"
        if priority not in MISSION_PRIORITIES:
            raise ValueError(
                f"invalid priority '{priority}' (expected one of "
                f"{', '.join(MISSION_PRIORITIES)})"
            )
        return priority

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: Any) -> str:
        """Validate the project status."""
        status = _clean(value).lower() or "active"
        if status not in COMPANY_STATUSES:
            raise ValueError(
                f"invalid project status '{status}' (expected one of "
                f"{', '.join(COMPANY_STATUSES)})"
            )
        return status

    @field_validator("budget_cxjcoins", mode="before")
    @classmethod
    def _budget(cls, value: Any) -> float:
        """Clamp the budget to a non-negative number."""
        try:
            return max(0.0, float(value or 0.0))
        except (TypeError, ValueError):
            return 0.0


class AutonomyPolicy(BaseModel):
    """
    How much the company can run on its own.

    The policy is **off by default** and only dispatches missions whose
    ``dispatch_mode`` is ``auto``. Even when enabled, a company never exceeds
    ``max_concurrent_missions`` and ``max_missions_per_cycle``, so enabling the
    autopilot cannot start an unbounded amount of work.

    Attributes:
        enabled: Whether the background autopilot may run cycles.
        level: ``off``, ``supervised`` or ``autonomous``.
        interval_minutes: Minimum time between two automatic cycles.
        max_concurrent_missions: Open (running) missions allowed at once.
        max_missions_per_cycle: Missions dispatched by a single cycle.
        daily_budget_cxjcoins: Soft daily AI budget (0 = no limit).
        require_human_acceptance: Completed runs stop at ``review`` until a
            human accepts them.
        last_cycle_at / next_cycle_at: Cycle bookkeeping (ISO-8601).
        cycle_count: Number of cycles executed so far.
        last_cycle_summary: One-line result of the last cycle.
    """

    model_config = {"validate_assignment": True}

    enabled: bool = Field(default=False, description="Autopilot enabled")
    level: str = Field(default="supervised", description="off | supervised | autonomous")
    interval_minutes: int = Field(default=60, description="Minutes between cycles")
    max_concurrent_missions: int = Field(
        default=2, description="Maximum missions running at the same time"
    )
    max_missions_per_cycle: int = Field(
        default=1, description="Missions dispatched by one cycle"
    )
    daily_budget_cxjcoins: float = Field(
        default=0.0, description="Soft daily AI budget (0 = no limit)"
    )
    require_human_acceptance: bool = Field(
        default=True,
        description="Completed runs stop at 'review' until a human accepts them",
    )
    last_cycle_at: str = Field(default="", description="Last cycle timestamp")
    next_cycle_at: str = Field(default="", description="Next due cycle timestamp")
    cycle_count: int = Field(default=0, description="Executed cycles")
    last_cycle_summary: str = Field(default="", description="Result of the last cycle")

    @field_validator("level", mode="before")
    @classmethod
    def _level(cls, value: Any) -> str:
        """Validate the autonomy level."""
        level = _clean(value).lower() or "supervised"
        if level not in AUTONOMY_LEVELS:
            raise ValueError(
                f"invalid autonomy level '{level}' (expected one of "
                f"{', '.join(AUTONOMY_LEVELS)})"
            )
        return level

    @field_validator("interval_minutes", mode="before")
    @classmethod
    def _interval(cls, value: Any) -> int:
        """Clamp the interval into [5, 1440] minutes."""
        try:
            return max(5, min(1440, int(value or 60)))
        except (TypeError, ValueError):
            return 60

    @field_validator("max_concurrent_missions", mode="before")
    @classmethod
    def _concurrent(cls, value: Any) -> int:
        """Clamp concurrency into [1, 20]."""
        try:
            return max(1, min(20, int(value or 2)))
        except (TypeError, ValueError):
            return 2

    @field_validator("max_missions_per_cycle", mode="before")
    @classmethod
    def _per_cycle(cls, value: Any) -> int:
        """Clamp the per-cycle dispatch count into [1, 10]."""
        try:
            return max(1, min(10, int(value or 1)))
        except (TypeError, ValueError):
            return 1

    @field_validator("daily_budget_cxjcoins", mode="before")
    @classmethod
    def _budget(cls, value: Any) -> float:
        """Clamp the budget to a non-negative number."""
        try:
            return max(0.0, float(value or 0.0))
        except (TypeError, ValueError):
            return 0.0

    def is_due(self, now: Optional[datetime] = None) -> bool:
        """
        Tell whether an automatic cycle is due.

        Args:
            now: Instant to compare against (defaults to now).

        Returns:
            ``True`` when enabled and the interval since the last cycle elapsed.
        """
        if not self.enabled or self.level == "off":
            return False
        current = now or datetime.now()
        last = parse_iso(self.last_cycle_at)
        if last is None:
            return True
        # ``next_cycle_at`` is a cache; recompute from the interval when absent.
        due = parse_iso(self.next_cycle_at) or (
            last + timedelta(minutes=self.interval_minutes)
        )
        return current >= due

    def mark_cycle(self, summary: str = "", now: Optional[datetime] = None) -> None:
        """Record a finished cycle and schedule the next one."""
        current = now or datetime.now()
        self.last_cycle_at = current.isoformat()
        self.next_cycle_at = (
            current + timedelta(minutes=self.interval_minutes)
        ).isoformat()
        self.cycle_count += 1
        if summary:
            self.last_cycle_summary = summary


class Mission(BaseModel):
    """
    A company objective, dispatched to a project's orchestration runtime.

    A mission is what turns a company from a diagram into an operating
    organization: it names an outcome, assigns it to a hybrid team and a
    project, and (when dispatched) starts a durable orchestration run that the
    project's worker executes step by step.

    Attributes:
        id: Unique mission id.
        title: Short outcome name.
        objective: What must be achieved, in the company's voice.
        acceptance: How the outcome will be judged.
        status: See :data:`MISSION_STATUSES`.
        priority: low | medium | high | critical.
        team_id: Team responsible for the mission.
        project_id: Project where the mission runs.
        dispatch_mode: ``manual`` (only a human dispatches) or ``auto`` (the
            autopilot may dispatch it).
        source: ``human``, ``autopilot`` or ``template``.
        budget_cxjcoins: AI budget for the run (0 = no hard budget).
        due_date: Optional ISO date the mission is due.
        run_id: Durable orchestration run created by dispatch.
        run_status: Last known orchestration status.
        progress: 0-100 cache mirrored from the run.
        result: Outcome written on acceptance.
        last_error: Last dispatch/sync error (kept for humans).
        tags: Free-form discovery tags.
    """

    model_config = {"validate_assignment": True}

    id: str = Field(default="", description="Unique mission id")
    title: str = Field(default="", description="Short outcome name")
    objective: str = Field(default="", description="What must be achieved")
    acceptance: str = Field(default="", description="How the outcome is judged")
    status: str = Field(default="draft", description="Mission status")
    priority: str = Field(default="medium", description="low | medium | high | critical")
    team_id: str = Field(default="", description="Responsible team id")
    project_id: str = Field(default="", description="Project where the mission runs")
    owner_kind: str = Field(default="user", description="Owner reference kind")
    owner_name: str = Field(default="", description="Owner username or profile name")
    dispatch_mode: str = Field(
        default="manual", description="manual (human) | auto (autopilot may dispatch)"
    )
    source: str = Field(default="human", description="human | autopilot | template")
    budget_cxjcoins: float = Field(default=0.0, description="Run budget (0 = none)")
    spent_cxjcoins: float = Field(
        default=0.0,
        description="AI spend reported by the orchestration run (cxjcoins)",
    )
    due_date: str = Field(default="", description="Optional ISO due date")
    run_id: str = Field(default="", description="Orchestration run id")
    run_status: str = Field(default="", description="Last orchestration status")
    progress: int = Field(default=0, description="Progress 0-100")
    result: str = Field(default="", description="Outcome written on acceptance")
    last_error: str = Field(default="", description="Last dispatch/sync error")
    tags: List[str] = Field(default_factory=list, description="Discovery tags")
    created_by: str = Field(default="", description="Username that created it")
    created_at: str = Field(default_factory=now_iso, description="Creation timestamp")
    updated_at: str = Field(default_factory=now_iso, description="Last update timestamp")
    dispatched_at: str = Field(default="", description="Dispatch timestamp")
    completed_at: str = Field(default="", description="Completion timestamp")

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: Any) -> str:
        """Validate the mission status."""
        status = _clean(value).lower() or "draft"
        if status not in MISSION_STATUSES:
            raise ValueError(
                f"invalid mission status '{status}' (expected one of "
                f"{', '.join(MISSION_STATUSES)})"
            )
        return status

    @field_validator("priority", mode="before")
    @classmethod
    def _priority(cls, value: Any) -> str:
        """Validate the mission priority."""
        priority = _clean(value).lower() or "medium"
        if priority not in MISSION_PRIORITIES:
            raise ValueError(
                f"invalid mission priority '{priority}' (expected one of "
                f"{', '.join(MISSION_PRIORITIES)})"
            )
        return priority

    @field_validator("dispatch_mode", mode="before")
    @classmethod
    def _dispatch_mode(cls, value: Any) -> str:
        """Validate the dispatch mode."""
        mode = _clean(value).lower() or "manual"
        if mode not in MISSION_DISPATCH_MODES:
            raise ValueError(
                f"invalid dispatch_mode '{mode}' (expected one of "
                f"{', '.join(MISSION_DISPATCH_MODES)})"
            )
        return mode

    @field_validator("source", mode="before")
    @classmethod
    def _source(cls, value: Any) -> str:
        """Validate the mission source."""
        source = _clean(value).lower() or "human"
        return source if source in MISSION_SOURCES else "human"

    @field_validator("owner_kind", mode="before")
    @classmethod
    def _owner_kind(cls, value: Any) -> str:
        """Normalize the owner reference kind."""
        kind = _normalize_member_kind(value)
        return kind if kind in MEMBER_KINDS else "user"

    @field_validator(
        "title",
        "objective",
        "acceptance",
        "team_id",
        "project_id",
        "owner_name",
        "due_date",
        "run_id",
        "run_status",
        "result",
        "last_error",
        "created_by",
        mode="before",
    )
    @classmethod
    def _strip(cls, value: Any) -> str:
        """Trim free-form strings."""
        return _clean(value)

    @field_validator("budget_cxjcoins", "spent_cxjcoins", mode="before")
    @classmethod
    def _budget(cls, value: Any) -> float:
        """Clamp the budget/spend to a non-negative number."""
        try:
            return max(0.0, float(value or 0.0))
        except (TypeError, ValueError):
            return 0.0

    @field_validator("progress", mode="before")
    @classmethod
    def _progress(cls, value: Any) -> int:
        """Clamp progress into [0, 100]."""
        try:
            return max(0, min(100, int(value or 0)))
        except (TypeError, ValueError):
            return 0

    @field_validator("tags", mode="before")
    @classmethod
    def _tags(cls, value: Any) -> List[str]:
        """Normalize the tag list."""
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return _unique(value)

    @model_validator(mode="after")
    def _validate(self) -> "Mission":
        """Require the fields that make a mission executable."""
        if not self.title:
            raise ValueError("mission title is required")
        if not self.objective:
            self.objective = self.title
        return self

    @property
    def is_open(self) -> bool:
        """``True`` while the mission still needs attention."""
        return self.status in MISSION_OPEN_STATUSES

    @property
    def is_terminal(self) -> bool:
        """``True`` when the mission will not change by itself anymore."""
        return self.status in ("done", "cancelled")

    @property
    def owner(self) -> Optional[CompanyMember]:
        """Return the owner reference, or ``None`` when unset."""
        if not self.owner_name:
            return None
        return CompanyMember(kind=self.owner_kind, name=self.owner_name)


class CompanyEvent(BaseModel):
    """
    One entry of the company journal.

    Events are append-only and human-readable: they are what lets a human audit
    what the AI organization did, when and why (``company.created``,
    ``mission.dispatched``, ``autopilot.cycle``...).
    """

    id: str = Field(default_factory=lambda: new_id("event"))
    at: str = Field(default_factory=now_iso, description="Event timestamp")
    type: str = Field(default="", description="Event type (e.g. mission.dispatched)")
    actor: str = Field(default="system", description="Who triggered the event")
    message: str = Field(default="", description="Human readable summary")
    mission_id: str = Field(default="", description="Related mission id")
    data: Dict[str, Any] = Field(default_factory=dict, description="Extra event data")


class SpendEntry(BaseModel):
    """
    One delta of AI spend attributed to a mission.

    The company keeps a small append-only ledger so it can answer "how much did
    we spend today?" without scanning every run in every project. The mission
    itself stores the cumulative ``spent_cxjcoins``; this ledger stores the
    positive deltas reported by each run sync.

    Attributes:
        id: Unique entry id.
        at: Timestamp of the sync that observed the spend.
        mission_id: Mission the cost belongs to.
        project_id: Project where the run executed.
        run_id: Orchestration run that reported the cost.
        amount: Positive delta in cxjcoins.
        note: Optional human-readable detail.
    """

    id: str = Field(default_factory=lambda: new_id("spend"))
    at: str = Field(default_factory=now_iso, description="Observation timestamp")
    mission_id: str = Field(default="", description="Mission id")
    project_id: str = Field(default="", description="Project id")
    run_id: str = Field(default="", description="Orchestration run id")
    amount: float = Field(default=0.0, description="Positive spend delta (cxjcoins)")
    note: str = Field(default="", description="Optional detail")

    @field_validator("amount", mode="before")
    @classmethod
    def _amount(cls, value: Any) -> float:
        """Clamp the amount to a non-negative number."""
        try:
            return max(0.0, float(value or 0.0))
        except (TypeError, ValueError):
            return 0.0


class Company(BaseModel):
    """
    The top-level company entity.

    Attributes:
        id: Unique company id.
        name: Display name.
        slug: URL friendly name (unique among companies).
        description: What the company does.
        mission / vision / values: Company direction, injected into every
            mission brief so AI teams work with the same context.
        website: Public website.
        logo / color: UI presentation.
        status: ``active``, ``paused`` or ``archived``.
        owner: Username of the human owner (empty = unowned).
        org_units: Departments/functions tree.
        teams: Hybrid teams.
        projects: Linked codx-junior projects.
        missions: Objectives and their execution state.
        autonomy: Autopilot policy.
        tags: Discovery tags.
    """

    model_config = {"validate_assignment": True}

    id: str = Field(default="", description="Unique company id")
    name: str = Field(default="", description="Company name")
    slug: str = Field(default="", description="URL friendly unique name")
    description: str = Field(default="", description="What the company does")
    mission: str = Field(default="", description="Why the company exists")
    vision: str = Field(default="", description="Where the company is going")
    values: List[str] = Field(default_factory=list, description="Operating values")
    website: str = Field(default="", description="Public website")
    logo: str = Field(default="", description="Logo URL")
    color: str = Field(default="#6366f1", description="UI accent colour")
    status: str = Field(default="active", description="active | paused | archived")
    owner: str = Field(default="", description="Owner username")
    org_units: List[OrgUnit] = Field(default_factory=list)
    teams: List[CompanyTeam] = Field(default_factory=list)
    projects: List[CompanyProject] = Field(default_factory=list)
    missions: List[Mission] = Field(default_factory=list)
    spend: List[SpendEntry] = Field(
        default_factory=list,
        description="Append-only AI spend ledger (bounded to the most recent entries)",
    )
    spent_cxjcoins: float = Field(
        default=0.0,
        description="Cumulative AI spend observed by the company (cxjcoins)",
    )
    autonomy: AutonomyPolicy = Field(default_factory=AutonomyPolicy)
    tags: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso, description="Creation timestamp")
    updated_at: str = Field(default_factory=now_iso, description="Last update timestamp")
    version: int = Field(default=1, description="Document version")

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: Any) -> str:
        """Validate the company status."""
        status = _clean(value).lower() or "active"
        if status not in COMPANY_STATUSES:
            raise ValueError(
                f"invalid company status '{status}' (expected one of "
                f"{', '.join(COMPANY_STATUSES)})"
            )
        return status

    @field_validator("name", "slug", "description", "mission", "vision", "website", "logo", "color", "owner", mode="before")
    @classmethod
    def _strip(cls, value: Any) -> str:
        """Trim free-form strings."""
        return _clean(value)

    @field_validator("spent_cxjcoins", mode="before")
    @classmethod
    def _spent(cls, value: Any) -> float:
        """Clamp the cumulative spend to a non-negative number."""
        try:
            return max(0.0, float(value or 0.0))
        except (TypeError, ValueError):
            return 0.0

    @field_validator("values", "tags", mode="before")
    @classmethod
    def _string_lists(cls, value: Any) -> List[str]:
        """Normalize string lists."""
        if value is None:
            return []
        if isinstance(value, str):
            value = [value]
        return _unique(value)

    @model_validator(mode="after")
    def _validate(self) -> "Company":
        """Require a name and keep derived identifiers coherent."""
        if not self.name:
            raise ValueError("company name is required")
        if len(self.name) > MAX_NAME_LENGTH:
            raise ValueError(f"company name is longer than {MAX_NAME_LENGTH} characters")
        if not self.slug:
            self.slug = slugify(self.name)
        for team in self.teams:
            team.ensure_lead()
        return self

    # -- lookups -----------------------------------------------------------

    def org_unit(self, unit_id: str) -> Optional[OrgUnit]:
        """Find an org unit by id."""
        return next((unit for unit in self.org_units if unit.id == unit_id), None)

    def team(self, team_id: str) -> Optional[CompanyTeam]:
        """Find a team by id."""
        return next((team for team in self.teams if team.id == team_id), None)

    def team_by_name(self, name: str) -> Optional[CompanyTeam]:
        """Find a team by case-insensitive name."""
        wanted = (name or "").strip().lower()
        return next(
            (team for team in self.teams if team.name.lower() == wanted), None
        )

    def project(self, project_id: str) -> Optional[CompanyProject]:
        """Find a linked project by project id."""
        return next(
            (
                project
                for project in self.projects
                if project.project_id == project_id
            ),
            None,
        )

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        """
        Find a mission by id.

        Named ``get_mission`` (not ``mission``) because ``mission`` is the
        company's mission statement field: a method with the same name would be
        shadowed by the field.
        """
        return next(
            (mission for mission in self.missions if mission.id == mission_id),
            None,
        )

    # -- derived state -----------------------------------------------------

    @property
    def human_count(self) -> int:
        """Distinct human users participating in the company."""
        return len(
            {
                member.name
                for team in self.teams
                for member in team.members
                if member.is_human
            }
        )

    @property
    def ai_count(self) -> int:
        """Distinct AI profiles participating in the company."""
        return len(
            {
                member.name
                for team in self.teams
                for member in team.members
                if member.is_ai
            }
        )

    @property
    def open_missions(self) -> List[Mission]:
        """Missions that still need attention."""
        return [mission for mission in self.missions if mission.is_open]

    @property
    def active_missions(self) -> List[Mission]:
        """Missions currently running."""
        return [mission for mission in self.missions if mission.status == "running"]

    def counts(self) -> Dict[str, int]:
        """
        Return the counters shown in the company header.

        Returns:
            Mapping with projects, teams, org_units, humans, ai, missions and
            one entry per mission status.
        """
        counts: Dict[str, int] = {
            "projects": len(self.projects),
            "teams": len(self.teams),
            "org_units": len(self.org_units),
            "humans": self.human_count,
            "ai": self.ai_count,
            "missions": len(self.missions),
            "open_missions": len(self.open_missions),
            "spent_cxjcoins": round(
                max(
                    self.spent_cxjcoins,
                    sum(mission.spent_cxjcoins for mission in self.missions),
                ),
                4,
            ),
        }
        for status in MISSION_STATUSES:
            counts[status] = sum(
                1 for mission in self.missions if mission.status == status
            )
        return counts

    def summary(self) -> Dict[str, Any]:
        """
        Return the compact company representation used by list endpoints.

        Returns:
            Identity, status, counts and autonomy bookkeeping.
        """
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "status": self.status,
            "owner": self.owner,
            "color": self.color,
            "logo": self.logo,
            "counts": self.counts(),
            "autonomy": self.autonomy.model_dump(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Mission status transitions accepted by the manager. A transition not listed
# here is rejected, so a tool cannot move a mission into an impossible state.
MISSION_TRANSITIONS: Dict[str, List[str]] = {
    "draft": ["ready", "cancelled"],
    "ready": ["running", "cancelled"],
    "running": ["paused", "blocked", "review", "done", "cancelled"],
    "paused": ["running", "ready", "blocked", "cancelled"],
    "blocked": ["ready", "cancelled"],
    "review": ["done", "ready", "blocked", "cancelled"],
    "done": [],
    "cancelled": [],
}


def can_transition(current: str, target: str) -> bool:
    """
    Tell whether a mission status transition is allowed.

    Args:
        current: Current mission status.
        target: Requested status.

    Returns:
        ``True`` when :data:`MISSION_TRANSITIONS` allows the change.
    """
    if current == target:
        return True
    return target in MISSION_TRANSITIONS.get(current, [])


# Made with ❤️ by codx-junior
