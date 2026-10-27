"""
Team models for codx-junior.

A **team** is a named group of profiles that work together on one capability:
a lead profile plus the profiles that cover the different responsibilities.

Teams are the *composition* layer on top of profiles: a team never stores the
instructions of its members, it only references their names. The instructions
are resolved by
:class:`~codx.junior.teams.team_manager.TeamManager` when the team is used, so
a team can never drift from the profile it composes.

Storage layout (one folder per team)::

    .codx/teams/<Name>/<Name>.team   # JSON definition (this model)
    .codx/teams/<Name>/<Name>.md     # Markdown charter (``content``)

The layout mirrors ``.codx/profiles`` on purpose: same two files, same
folder-name-equals-name invariant.

This module is the **single source of truth** for a team:

    - the stored shape (``members`` with ``role``/``responsibility``/``order``
      plus ``lead``),
    - the roster operations (add / update / remove / set lead / reorder),
    - the serialization used by the API and the tools (:meth:`Team.definition`),
    - the tool JSON schema (:meth:`Team.tool_properties`).

``TeamManager``, ``team_tools`` and ``api/teams`` only orchestrate: they never
reshape the data themselves, so the model, the tools and the API cannot drift
apart.

Made with ❤️ by codx-junior
"""

from datetime import datetime

from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel, Field, field_validator, model_validator

try:  # Python 3.10+: ``str | None`` produces a types.UnionType
    from types import UnionType

    UNION_ORIGINS = (Union, UnionType)
except ImportError:  # pragma: no cover - Python < 3.10
    UNION_ORIGINS = (Union,)


# Python type -> JSON-schema type used when exporting tool definitions.
JSON_TYPES = {
    str: "string",
    int: "integer",
    bool: "boolean",
    float: "number",
}

# Fields a caller (tool or API client) may send for a team, in a deliberate
# order: identity, roster, then the runtime configuration.
TEAM_TOOL_FIELDS = (
    "description",
    "goal",
    "lead",
    "members",
    "tools",
    "llm_model",
    "use_knowledge",
    "tags",
    "avatar",
    "content",
)

# Fields of a member a caller may send.
MEMBER_TOOL_FIELDS = ("profile", "role", "responsibility", "order")


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------


def json_type(annotation: Any) -> Dict[str, Any]:
    """
    Translate a pydantic field annotation into a JSON-schema type fragment.

    LLM tool definitions cannot use ``$ref``/``$defs``, so the annotation is
    flattened here instead of relying on ``model_json_schema()``.

    Args:
        annotation: Field annotation (``str``, ``Optional[str]``, ``List[str]``).

    Returns:
        JSON-schema fragment, e.g. ``{"type": "array", "items": {"type": "string"}}``.
    """
    origin = get_origin(annotation)
    args = [arg for arg in get_args(annotation) if arg is not type(None)]

    if origin in UNION_ORIGINS:
        return json_type(args[0]) if args else {"type": "string"}
    if origin in (list, List):
        item = json_type(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": item}
    return {"type": JSON_TYPES.get(annotation, "string")}


def field_schema(model: Type[BaseModel], name: str) -> Dict[str, Any]:
    """
    Build the JSON-schema fragment of one model field.

    The ``description`` declared on the model is reused as-is, so the tool
    documentation and the model documentation are the same text.

    Args:
        model: Model that declares the field.
        name: Field name.

    Returns:
        JSON-schema fragment with ``type`` and, when available, ``description``.

    Raises:
        KeyError: If the model has no such field.
    """
    field = model.model_fields[name]
    schema = json_type(field.annotation)
    if field.description:
        schema["description"] = field.description
    return schema


class TeamMember(BaseModel):
    """
    One profile taking part in a team.

    The member is identified by ``profile`` (the profile **name**), and adds
    the part that only makes sense inside the team: the role, the
    responsibility this profile owns and the composition order.

    Attributes:
        profile: Profile name (as used by ``@mentions``).
        role: Short role inside the team (``lead``, ``backend``, ``reviewer``...).
        responsibility: One line describing what this member owns.
        order: Sort order when composing the team instructions.
    """

    model_config = {"validate_assignment": True}

    profile: str = Field(
        default="",
        description="Name of the profile this member plays (the @mention name)",
    )
    role: str = Field(
        default="",
        description="Role inside the team, e.g. 'lead', 'backend', 'reviewer'",
    )
    responsibility: str = Field(
        default="",
        description="One line: what this member owns inside the team",
    )
    order: int = Field(
        default=0,
        description="Order in the roster (the lead is always composed first)",
    )

    @field_validator("profile", "role", "responsibility", mode="before")
    @classmethod
    def _strip_strings(cls, value: Any) -> Any:
        """Strip surrounding whitespace so ' analyst ' and 'analyst' match."""
        return value.strip() if isinstance(value, str) else value

    @field_validator("order", mode="before")
    @classmethod
    def _default_order(cls, value: Any) -> Any:
        """Treat ``None`` as 0: an unset order must not break the sorting."""
        return 0 if value is None else value

    @classmethod
    def tool_properties(cls) -> Dict[str, Any]:
        """
        Return the JSON-schema properties of a member object.

        Used by the tool definition so the member shape is declared once, in
        the model.

        Returns:
            Mapping of field name to its JSON-schema fragment.
        """
        return {name: field_schema(cls, name) for name in MEMBER_TOOL_FIELDS}


class Team(BaseModel):
    """
    A group of profiles working together under a lead.

    Attributes:
        name: Team identity. Also the folder name and the ``@mention``, so it
            must be mention-safe (letters, digits, ``_``, ``-``, ``.``).
        description: When to use the team, in 1-3 sentences.
        goal: The outcome the team is responsible for.
        avatar: Avatar URL shown in the UI.
        lead: Profile name of the team lead. Always composed first.
        members: Profiles taking part in the team, with their role.
        tools: Extra tools granted to the whole team (on top of each member's).
        llm_model: Model override for the team (empty inherits the default).
        use_knowledge: Whether project knowledge is injected for the team.
        tags: Free-form discovery tags.
        content: Markdown charter, persisted in ``<Name>.md`` (never in the JSON).
        path: Absolute path of the ``.team`` file.
        project_id: Owning project id.
        created_at: Creation timestamp (ISO).
        updated_at: Last update timestamp (ISO).
    """

    name: str = Field(
        default="",
        description="Team name: also the folder name and the @mention",
    )
    description: str = Field(
        default="",
        description="When to use the team, in 1-3 sentences",
    )
    goal: str = Field(
        default="",
        description="Outcome the team is responsible for",
    )
    avatar: str = Field(default="", description="Avatar URL shown in the UI")
    lead: str = Field(
        default="",
        description="Profile name of the team lead (always composed first)",
    )
    members: List[TeamMember] = Field(
        default_factory=list,
        description=(
            "Profiles taking part in the team, with their role and "
            "responsibility. Also accepts plain profile names"
        ),
    )
    tools: List[str] = Field(
        default_factory=list,
        description="Extra tools granted to the whole team",
    )
    llm_model: str = Field(
        default="",
        description="Model override (empty inherits the project/default model)",
    )
    use_knowledge: bool = Field(
        default=True,
        description="Whether project knowledge (RAG) context is injected",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Free-form discovery tags (lowercase, kebab-case)",
    )
    content: Optional[str] = Field(
        default=None,
        description="Markdown charter, stored in the team's .md file",
    )
    path: str = Field(default="", description="Absolute path of the .team file")
    project_id: Optional[str] = Field(default=None, description="Owning project id")
    created_at: Optional[str] = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Creation timestamp (ISO)",
    )
    updated_at: Optional[str] = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Last update timestamp (ISO)",
    )

    # -------------------------------------------------------------------------
    # Construction
    # -------------------------------------------------------------------------

    @model_validator(mode="before")
    @classmethod
    def _normalize_members(cls, data: Any) -> Any:
        """
        Normalize the ``members`` input before validation.

        A caller may send a roster as plain profile names (``["analyst"]``), as
        objects (``[{"profile": "analyst", "role": "research"}]``) or as
        already-built :class:`TeamMember` instances. Normalizing here means the
        tool, the API and the stored JSON all share one structure instead of
        each one parsing its own variant.

        Args:
            data: Raw model input.

        Returns:
            The input with ``members`` normalized to ``TeamMember`` objects.
        """
        if isinstance(data, dict) and "members" in data:
            data = {**data, "members": cls.parse_members(data.get("members"))}
        return data

    @classmethod
    def parse_members(cls, raw: Optional[List[Any]]) -> List[TeamMember]:
        """
        Normalize a roster into ``TeamMember`` objects.

        Args:
            raw: List of profile names, member dicts or ``TeamMember`` objects.

        Returns:
            Deduplicated members, in the given order.

        Raises:
            ValueError: If an entry is malformed or has no profile name.
        """
        members: List[TeamMember] = []
        seen = set()

        for index, item in enumerate(raw or []):
            if isinstance(item, TeamMember):
                member = item.model_copy()
            elif isinstance(item, str):
                member = TeamMember(profile=item, order=index)
            elif isinstance(item, dict):
                member = TeamMember(
                    profile=item.get("profile") or item.get("name") or "",
                    role=item.get("role") or "",
                    responsibility=(
                        item.get("responsibility") or item.get("description") or ""
                    ),
                    order=item.get("order", index),
                )
            else:
                raise ValueError(
                    f"Invalid member at position {index}: expected a profile name "
                    f"or an object, got {type(item).__name__}"
                )

            if not member.profile:
                raise ValueError(f"Member at position {index} has no profile name")
            if member.profile in seen:
                continue
            seen.add(member.profile)
            members.append(member)

        return members

    # -------------------------------------------------------------------------
    # Roster reads
    # -------------------------------------------------------------------------

    def ordered_members(self) -> List[TeamMember]:
        """
        Return the members in composition order: the lead first.

        The lead is always composed first so its instructions prime the rest of
        the team. A lead that is missing from the roster is returned as a
        virtual member (nothing is written): a team whose file went stale must
        still compose without losing its coordinating profile.

        Returns:
            Ordered members, lead first, then the rest by ``order`` and name.
        """
        members = [
            member for member in (self.members or []) if member and member.profile
        ]
        lead = (self.lead or "").strip()

        if not lead:
            return sorted(members, key=lambda member: (member.order, member.profile))

        lead_member = next(
            (member for member in members if member.profile == lead), None
        )
        if lead_member is None:
            lead_member = TeamMember(profile=lead, role="lead", order=-1)

        rest = [member for member in members if member.profile != lead]
        return [lead_member] + sorted(
            rest, key=lambda member: (member.order, member.profile)
        )

    @property
    def profile_names(self) -> List[str]:
        """
        Return the profile names of the roster, in composition order.

        This is the derived "list of profiles" of the team: it is never stored,
        so it can never disagree with ``members``/``lead``.
        """
        return [member.profile for member in self.ordered_members()]

    def member(self, profile: str) -> Optional[TeamMember]:
        """
        Find a roster member by exact profile name.

        Args:
            profile: Profile name.

        Returns:
            The member, or ``None`` when the profile is not in the roster.
        """
        profile = (profile or "").strip()
        return next(
            (
                member
                for member in (self.members or [])
                if member.profile == profile
            ),
            None,
        )

    def has_member(self, profile: str) -> bool:
        """
        Tell whether a profile is part of the roster.

        Args:
            profile: Profile name.

        Returns:
            ``True`` when the profile is a member.
        """
        return self.member(profile) is not None

    def roster_names(self) -> str:
        """
        Render the roster for error messages.

        Returns:
            Comma separated profile names, or ``none``.
        """
        return ", ".join(self.profile_names) or "none"

    # -------------------------------------------------------------------------
    # Roster writes
    # -------------------------------------------------------------------------

    def ensure_lead_in_roster(self) -> bool:
        """
        Add the lead to the roster when it is missing.

        A lead outside the roster would coordinate a team it does not own, so
        write paths call this before saving.

        Returns:
            ``True`` when the lead had to be added.
        """
        lead = (self.lead or "").strip()
        if not lead or self.has_member(lead):
            return False
        self.members = [
            TeamMember(profile=lead, role="lead", order=-1)
        ] + list(self.members or [])
        return True

    def upsert_member(
        self,
        profile: str,
        role: Optional[str] = None,
        responsibility: Optional[str] = None,
        order: Optional[int] = None,
        promote_if_no_lead: bool = True,
    ) -> str:
        """
        Add a profile to the roster, or update it when already present.

        Args:
            profile: Profile name to add or update.
            role: Role inside the team.
            responsibility: What the member owns.
            order: Sort order (defaults to the end of the roster).
            promote_if_no_lead: Make it the lead when the team has none (a team
                without a lead has nobody to consolidate the answer).

        Returns:
            ``"added"`` or ``"updated"``.

        Raises:
            ValueError: If the profile name is empty.
        """
        profile = (profile or "").strip()
        if not profile:
            raise ValueError("profile is required")

        member = self.member(profile)
        if member is not None:
            if role is not None:
                member.role = role
            if responsibility is not None:
                member.responsibility = responsibility
            if order is not None:
                member.order = order
            return "updated"

        members = list(self.members or [])
        members.append(
            TeamMember(
                profile=profile,
                role=role or "",
                responsibility=responsibility or "",
                order=len(members) if order is None else order,
            )
        )
        self.members = members

        if promote_if_no_lead and not (self.lead or "").strip():
            self.lead = profile
        return "added"

    def update_member(
        self,
        profile: str,
        role: Optional[str] = None,
        responsibility: Optional[str] = None,
        order: Optional[int] = None,
    ) -> List[str]:
        """
        Update an existing member, never creating one.

        A profile that is not in the roster raises instead of silently growing
        the team, so a typo surfaces.

        Args:
            profile: Profile name of the member to update.
            role: New role.
            responsibility: New one-line responsibility.
            order: New sort order.

        Returns:
            Names of the fields that changed.

        Raises:
            ValueError: If the profile is not a member or no field is provided.
        """
        member = self.member(profile)
        if member is None:
            raise ValueError(
                f"Profile '{profile}' is not a member of team '{self.name}'. "
                f"Members: {self.roster_names()}. Use add_member to add it."
            )
        if role is None and responsibility is None and order is None:
            raise ValueError(
                "Nothing to update: provide at least one of role, "
                "responsibility or order"
            )

        changed: List[str] = []
        if role is not None:
            member.role = role
            changed.append("role")
        if responsibility is not None:
            member.responsibility = responsibility
            changed.append("responsibility")
        if order is not None:
            member.order = order
            changed.append("order")
        return changed

    def remove_member(self, profile: str) -> bool:
        """
        Remove a profile from the roster.

        Removing the lead clears ``lead``: leaving a lead pointing at a profile
        that is no longer in the team would compose a roster the team does not
        own.

        Args:
            profile: Profile name to remove.

        Returns:
            ``True`` when the removed profile was the team lead.

        Raises:
            ValueError: If the profile is not a member.
        """
        profile = (profile or "").strip()
        if not self.has_member(profile):
            raise ValueError(
                f"Profile '{profile}' is not a member of team '{self.name}'. "
                f"Members: {self.roster_names()}"
            )

        self.members = [
            member for member in (self.members or []) if member.profile != profile
        ]
        lead_cleared = (self.lead or "").strip() == profile
        if lead_cleared:
            self.lead = ""
        return lead_cleared

    def set_lead(self, profile: str) -> Dict[str, Any]:
        """
        Change the team lead.

        The new lead is added to the roster when missing, and the previous
        lead's generic ``lead`` role is cleared so the roster never shows two
        leads.

        Args:
            profile: Profile name of the new lead.

        Returns:
            Dict with ``previous``, ``lead``, ``changed``, ``added_to_roster``
            and ``cleared_role``.

        Raises:
            ValueError: If the profile name is empty.
        """
        profile = (profile or "").strip()
        if not profile:
            raise ValueError("lead profile is required")

        previous = (self.lead or "").strip()
        result: Dict[str, Any] = {
            "previous": previous,
            "lead": profile,
            "changed": previous != profile,
            "added_to_roster": False,
            "cleared_role": False,
        }

        if not self.has_member(profile):
            self.members = list(self.members or []) + [
                TeamMember(profile=profile, role="lead", order=-1)
            ]
            result["added_to_roster"] = True

        if previous and previous != profile:
            previous_member = self.member(previous)
            if previous_member and (previous_member.role or "").strip().lower() == "lead":
                previous_member.role = ""
                result["cleared_role"] = True

        self.lead = profile
        return result

    def reorder_members(self, order: List[str]) -> List[str]:
        """
        Set the roster order.

        The order drives the sequence of the composed instructions (after the
        lead). Members missing from ``order`` keep their relative order and are
        appended at the end, so a partial list never drops anyone.

        Args:
            order: Member profile names in the desired order.

        Returns:
            Names of the members appended at the end (not listed in ``order``).

        Raises:
            ValueError: If the list is empty, has duplicates or names a profile
                that is not a member.
        """
        names = [entry.strip() for entry in (order or []) if (entry or "").strip()]
        if not names:
            raise ValueError(
                "order is required: pass the member profile names in the desired "
                "sequence"
            )

        seen = set()
        duplicated = [name for name in names if name in seen or seen.add(name)]
        if duplicated:
            raise ValueError(f"Duplicated member(s): {duplicated}")

        unknown = [name for name in names if not self.has_member(name)]
        if unknown:
            raise ValueError(
                f"Not member(s) of team '{self.name}': {unknown}. "
                f"Members: {self.roster_names()}"
            )

        listed = set(names)
        appended = [
            member.profile
            for member in sorted(
                [
                    member
                    for member in (self.members or [])
                    if member.profile and member.profile not in listed
                ],
                key=lambda member: (member.order, member.profile),
            )
        ]

        for index, profile in enumerate(names + appended):
            member = self.member(profile)
            if member:
                member.order = index
        return appended

    # -------------------------------------------------------------------------
    # Serialization
    # -------------------------------------------------------------------------

    def definition(self, include_content: bool = False) -> Dict[str, Any]:
        """
        Build the portable definition of the team.

        ``profile_names`` is added next to ``members`` so consumers that only
        need the names do not have to map the roster themselves; it is derived,
        never stored.

        Args:
            include_content: Include the Markdown charter.

        Returns:
            Dict ready to be JSON-serialised.
        """
        data = self.model_dump()
        data["profile_names"] = self.profile_names
        if not include_content:
            data["content"] = None
        return data

    @classmethod
    def tool_properties(cls, fields: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        """
        Return the JSON-schema properties of a team payload.

        The tool definition is generated from here, so adding a field to the
        model is enough to expose it to the tools.

        Args:
            fields: Field names to export (defaults to :data:`TEAM_TOOL_FIELDS`).

        Returns:
            Mapping of field name to its JSON-schema fragment.
        """
        names = tuple(fields) if fields else TEAM_TOOL_FIELDS
        properties: Dict[str, Any] = {}

        for name in names:
            if name != "members":
                properties[name] = field_schema(cls, name)
                continue
            properties["members"] = {
                "type": "array",
                "description": cls.model_fields["members"].description,
                "items": {
                    "anyOf": [
                        {"type": "string"},
                        {
                            "type": "object",
                            "properties": TeamMember.tool_properties(),
                            "required": ["profile"],
                        },
                    ]
                },
            }

        return properties

# Made with ❤️ by codx-junior