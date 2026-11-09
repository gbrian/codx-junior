from typing import Optional, List
from pydantic import BaseModel, Field, computed_field, field_validator
from datetime import datetime
import uuid

from codx.junior.model.wallet import Wallet


# ---------------------------------------------------------------------------
# Token-limit extension
# ---------------------------------------------------------------------------


class TokenLimitExtension(BaseModel):
    """
    Temporary one-day override granted by an admin.

    date             – ISO date ``YYYY-MM-DD`` on which the override is valid.
                       Silently ignored on every other date → auto-expires.
    extra_tokens     – Absolute extra tokens added on top of ``limit_per_day``.
                       Mutually exclusive with ``extra_percent``.
    extra_percent    – Percentage increase over ``limit_per_day``
                       (e.g. 15 → +15 %).  Mutually exclusive with ``extra_tokens``.
                       ``None`` on both fields means *unlimited* for that day.
    """

    date: str                                # YYYY-MM-DD
    extra_tokens: Optional[int] = None       # absolute extra tokens
    extra_percent: Optional[float] = None    # e.g. 15.0 → +15 %
    # Both None → unlimited for that day


# ---------------------------------------------------------------------------
# Token-limit rule
# ---------------------------------------------------------------------------


class TokenLimitRule(BaseModel):
    """
    One daily token-limit rule attached to a ``CodxUser``.

    Scope
    -----
    Matches an incoming AI request when:
      • ``provider`` is ``None``  OR  equals the request provider
      • ``model``    is ``None``  OR  equals the request model

    Typical combinations::

        provider=None,     model=None       # global daily cap
        provider="openai", model=None       # per-provider daily cap
        provider="openai", model="gpt-4o"   # per-model daily cap

    Evaluation
    ----------
    Every matching rule is checked independently.  The request is **blocked**
    when *any* matched rule finds today's consumed tokens ≥ effective limit.

    Extension
    ---------
    The optional ``extension`` (admin-only) temporarily raises the cap for a
    single calendar day.  Stored inline → expires automatically, no cleanup
    job required.
    """

    limit_per_day: int
    provider: Optional[str] = None   # None → all providers
    model: Optional[str] = None      # None → all models
    extension: Optional[TokenLimitExtension] = None

    def effective_limit(self, today: str) -> Optional[int]:
        """
        Effective token cap for *today*.

        Priority:
        1. Active extension today:
           a. both ``extra_tokens`` and ``extra_percent`` are ``None`` → unlimited (return ``None``)
           b. ``extra_percent`` set → ``limit_per_day * (1 + extra_percent / 100)``
           c. ``extra_tokens`` set → ``limit_per_day + extra_tokens``
        2. No active extension → ``limit_per_day``
        """
        if self.extension and self.extension.date == today:
            ext = self.extension
            if ext.extra_tokens is None and ext.extra_percent is None:
                return None  # unlimited today
            if ext.extra_percent is not None:
                return int(self.limit_per_day * (1 + ext.extra_percent / 100))
            if ext.extra_tokens is not None:
                return self.limit_per_day + ext.extra_tokens
        return self.limit_per_day

    def matches(self, provider: str, model: str) -> bool:
        """``True`` when this rule covers the given provider/model pair."""
        return (
            (self.provider is None or self.provider == provider)
            and (self.model is None or self.model == model)
        )


# ---------------------------------------------------------------------------
# User-initiated limit-increase request
# ---------------------------------------------------------------------------


class TokenLimitRequestStatus(str):
    PENDING  = "pending"
    APPROVED = "approved"
    DENIED   = "denied"


class TokenLimitRequest(BaseModel):
    """
    A request submitted by the user to temporarily raise their token limit.

    Stored in ``CodxUser.token_limit_requests`` so an admin can review and
    act on it via the admin endpoints.

    Fields
    ------
    id           – Unique request ID (timestamp-based, set by the server).
    created_at   – ISO datetime the request was created.
    date         – The calendar date the user is requesting extra tokens for.
    rule_index   – Which rule in ``token_limit_rules`` this request targets.
    reason       – Free-text explanation from the user.
    extra_tokens – Absolute extra tokens requested (mutually exclusive with
                   ``extra_percent``).
    extra_percent – Percentage increase requested (e.g. 50 → +50 %).
    status       – ``pending`` | ``approved`` | ``denied``
    admin_note   – Optional note added by the admin when resolving.
    resolved_at  – ISO datetime when the request was resolved.
    """

    id: str = ""
    created_at: str = ""
    date: str = ""                           # YYYY-MM-DD
    rule_index: int = 0
    reason: str = ""
    extra_tokens: Optional[int] = None
    extra_percent: Optional[float] = None
    status: str = "pending"
    admin_note: Optional[str] = None
    resolved_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Login / permissions helpers
# ---------------------------------------------------------------------------


class CodxUserLogin(BaseModel):
    username: Optional[str] = Field(default="")
    password: Optional[str] = Field(default="")
    email: Optional[str] = Field(default="")
    token: Optional[str] = Field(default="")


class CodxUserProjectProfile(BaseModel):
    name: Optional[str] = Field(default="")
    coder: Optional[bool] = Field(
        description="Can access to coder and change project files", default=False
    )
    admin: Optional[bool] = Field(
        description="Can access to project's admin", default=False
    )


# ---------------------------------------------------------------------------
# Project permission roles
# ---------------------------------------------------------------------------
# Values accepted by ``ProjectPermission.permissions``. They are plain strings
# (not an Enum) so every stored setting keeps working untouched.

# Full project administration.
PROJECT_PERMISSION_ADMIN = "admin"

# Custody of what the profiles learn in the project (rules written to the
# project's profile enrichment and knowledge files), without any other
# administrative capability: a knowledge admin cannot administrate the project.
PROJECT_PERMISSION_KNOWLEDGE_ADMIN = "knowledge_admin"


# ---------------------------------------------------------------------------
# Company roles / workspace mode
# ---------------------------------------------------------------------------
# codx-junior has two product shells:
#
#   * **company mode**  — the simplified, manager-oriented view of a company
#     (organization, teams, people, projects, missions and the always-present
#     codx-junior assistant).
#   * **working mode**  — today's project-oriented codx-junior workspace.
#
# The shell a user enters is derived from ``CodxUser.role`` and the companies
# the user belongs to. A per-user ``workspace_mode`` preference can force one
# of them (``auto`` keeps the role-based derivation).

# Global codx-junior roles.
USER_ROLE_ADMIN = "admin"
USER_ROLE_COMPANY_ADMIN = "company_admin"
USER_ROLE_MANAGER = "manager"
USER_ROLE_USER = "user"
USER_ROLES = (
    USER_ROLE_ADMIN,
    USER_ROLE_COMPANY_ADMIN,
    USER_ROLE_MANAGER,
    USER_ROLE_USER,
)

# Roles inside one company (stored in ``CodxUser.companies``).
COMPANY_ROLE_ADMIN = "admin"
COMPANY_ROLE_MANAGER = "manager"
COMPANY_ROLE_MEMBER = "member"
COMPANY_ROLES = (
    COMPANY_ROLE_ADMIN,
    COMPANY_ROLE_MANAGER,
    COMPANY_ROLE_MEMBER,
)

# Workspace mode preference.
WORKSPACE_MODE_AUTO = "auto"
WORKSPACE_MODE_COMPANY = "company"
WORKSPACE_MODE_WORK = "work"
WORKSPACE_MODES = (
    WORKSPACE_MODE_AUTO,
    WORKSPACE_MODE_COMPANY,
    WORKSPACE_MODE_WORK,
)

#: Roles that enter company mode by default. Global admins default to working
#: mode (today's product) but can switch; company admins and managers are the
#: manager-oriented personas the company shell was built for.
COMPANY_MODE_USER_ROLES = (
    USER_ROLE_COMPANY_ADMIN,
    USER_ROLE_MANAGER,
)


class CompanyMembership(BaseModel):
    """
    Membership of one human user in one company.

    The company is the top-level entity; this is the user-side index of the
    companies a person belongs to. The role decides what the user may do inside
    that company:

        admin    add/remove users, manage every company setting
        manager  manage teams, projects, missions through the assistant
        member   follow the work (read-only company views)

    Attributes:
        company_id: Company id (the folder/document id, never the name).
        role: ``admin`` | ``manager`` | ``member``.
        title: Human readable title inside the company (``Head of Product``).
        joined_at: ISO timestamp of the first membership write.
    """

    model_config = {"validate_assignment": True}

    company_id: str = Field(default="", description="Company id")
    role: str = Field(
        default=COMPANY_ROLE_MEMBER,
        description="Company role: admin | manager | member",
    )
    title: str = Field(default="", description="Title inside the company")
    joined_at: str = Field(default="", description="ISO timestamp")

    @field_validator("company_id", "title", "joined_at", mode="before")
    @classmethod
    def _strip(cls, value):
        """Trim free-form strings (``None`` becomes ``""``)."""
        return str(value).strip() if value is not None else ""

    @field_validator("role", mode="before")
    @classmethod
    def _role(cls, value):
        """Normalize and validate the company role."""
        role = str(value or "").strip().lower() or COMPANY_ROLE_MEMBER
        if role not in COMPANY_ROLES:
            raise ValueError(
                f"invalid company role '{role}' (expected one of "
                f"{', '.join(COMPANY_ROLES)})"
            )
        return role

    @field_validator("company_id")
    @classmethod
    def _company_required(cls, value):
        """A membership without a company cannot be resolved."""
        if not value:
            raise ValueError("company_id is required")
        return value

    @property
    def is_admin(self) -> bool:
        """``True`` when the user can administer the company."""
        return self.role == COMPANY_ROLE_ADMIN

    @property
    def is_manager(self) -> bool:
        """``True`` when the user can manage the company work."""
        return self.role in (COMPANY_ROLE_ADMIN, COMPANY_ROLE_MANAGER)


class ProjectPermission(BaseModel):
    project_id: str
    permissions: str = Field(
        description=(
            "User permission for the project: "
            f"'{PROJECT_PERMISSION_ADMIN}' (full project administration) or "
            f"'{PROJECT_PERMISSION_KNOWLEDGE_ADMIN}' (can change what the "
            "profiles learn: rules and knowledge files)."
        ),
        default=[],
    )
    children: Optional[bool] = Field(
        description="Same access to children projects", default=True
    )
    apps: Optional[List[str]] = Field(default=[])


# ---------------------------------------------------------------------------
# Main CodxUser model
# ---------------------------------------------------------------------------


class CodxUser(BaseModel):
    username: Optional[str] = Field(default="")
    email: Optional[str] = Field(default="")
    avatar: Optional[str] = Field(default="")
    theme: Optional[str] = Field(default="dim")
    projects: Optional[List[ProjectPermission]] = Field(default=[])
    role: Optional[str] = Field(description="User role", default=USER_ROLE_USER)
    # ── Company shell ────────────────────────────────────────────────────────
    # A user can belong to many companies. The membership role is what the
    # company assistant and the company API authorize against; changing it
    # requires company admin (or global admin) rights.
    companies: Optional[List[CompanyMembership]] = Field(
        default=[],
        description=(
            "Companies the user belongs to, with the role inside each one: "
            "'admin' (add users / every setting), 'manager' (manage the work "
            "through the assistant) or 'member' (follow the work)."
        ),
    )
    workspace_mode: Optional[str] = Field(
        default=WORKSPACE_MODE_AUTO,
        description=(
            "Preferred product shell: 'auto' (derived from the role and the "
            "company memberships), 'company' (simplified manager view) or "
            "'work' (today's project workspace)."
        ),
    )
    token: Optional[str] = Field(default="")
    disabled: Optional[bool] = Field(default=False)
    github: Optional[str] = Field(default="")
    apps: Optional[List[str]] = Field(default=[])
    api_key: Optional[str] = Field(default="")
    env: Optional[dict] = Field(default={})
    wallet: Wallet = Field(
        default=Wallet(),
        description="User's wallets"
    )

    # ── GitHub OAuth admin status ─────────────────────────────────────────────

    github_admin: Optional[bool] = Field(
        default=False,
        description="True if user was granted admin role via GitHub account (from GITHUB_ADMINS env var).",
    )

    # ── GitHub-only login mode ────────────────────────────────────────────────

    github_only: Optional[bool] = Field(
        default=False,
        description="If True, only GitHub OAuth login is allowed. Manual password login is disabled.",
    )

    # ── Token-limit policy (admin-managed, stored inline on the user) ──────────

    token_limit_rules: List[TokenLimitRule] = Field(
        default_factory=list,
        description="Daily token-limit rules for this user (admin-managed).",
    )
    token_limit_requests: List[TokenLimitRequest] = Field(
        default_factory=list,
        description="Pending / resolved limit-increase requests from this user.",
    )

    # ── Company helpers ──────────────────────────────────────────────────────

    @field_validator("role", mode="before")
    @classmethod
    def _user_role(cls, value):
        """Normalize the global role, keeping legacy values working."""
        role = str(value or "").strip().lower() or USER_ROLE_USER
        return role if role in USER_ROLES else USER_ROLE_USER

    @field_validator("workspace_mode", mode="before")
    @classmethod
    def _workspace_mode(cls, value):
        """Validate the product shell preference."""
        mode = str(value or "").strip().lower() or WORKSPACE_MODE_AUTO
        if mode not in WORKSPACE_MODES:
            raise ValueError(
                f"invalid workspace_mode '{mode}' (expected one of "
                f"{', '.join(WORKSPACE_MODES)})"
            )
        return mode

    @field_validator("companies", mode="before")
    @classmethod
    def _companies(cls, value):
        """Normalize stored memberships (accept id strings and dicts)."""
        if value is None:
            return []
        result: List[CompanyMembership] = []
        seen = set()
        for item in value:
            if isinstance(item, CompanyMembership):
                membership = item
            elif isinstance(item, str):
                if not item.strip():
                    continue
                membership = CompanyMembership(company_id=item)
            elif isinstance(item, dict):
                if not str(item.get("company_id") or "").strip():
                    continue
                membership = CompanyMembership(**item)
            else:
                continue
            if not membership.company_id or membership.company_id in seen:
                continue
            seen.add(membership.company_id)
            result.append(membership)
        return result

    def company_membership(self, company_id: str) -> Optional[CompanyMembership]:
        """Return the membership for *company_id*, or ``None``."""
        company_id = str(company_id or "")
        return next(
            (
                membership
                for membership in (self.companies or [])
                if membership.company_id == company_id
            ),
            None,
        )

    def company_role(self, company_id: str) -> str:
        """Return the role inside *company_id* (``""`` when not a member)."""
        membership = self.company_membership(company_id)
        return membership.role if membership else ""

    def is_company_admin(self, company_id: str) -> bool:
        """``True`` when the user may administer *company_id*."""
        return (
            self.role == USER_ROLE_ADMIN
            or self.company_role(company_id) == COMPANY_ROLE_ADMIN
        )

    def is_company_manager(self, company_id: str) -> bool:
        """``True`` when the user may manage the work of *company_id*."""
        return (
            self.role == USER_ROLE_ADMIN
            or self.company_role(company_id) in (
                COMPANY_ROLE_ADMIN,
                COMPANY_ROLE_MANAGER,
            )
        )

    def resolved_workspace_mode(self) -> str:
        """
        Return the shell this user should enter.

        ``workspace_mode`` wins when it is explicit; otherwise the role and the
        company memberships decide. Global admins keep today's working mode by
        default, so a normal installation is unchanged for them.
        """
        if self.workspace_mode in (
            WORKSPACE_MODE_COMPANY,
            WORKSPACE_MODE_WORK,
        ):
            return self.workspace_mode
        if self.role in COMPANY_MODE_USER_ROLES:
            return WORKSPACE_MODE_COMPANY
        if self.companies:
            return WORKSPACE_MODE_COMPANY
        return WORKSPACE_MODE_WORK

    @computed_field  # type: ignore[misc]
    @property
    def is_company_mode(self) -> bool:
        """Convenience flag used by API payloads and the UI."""
        return self.resolved_workspace_mode() == WORKSPACE_MODE_COMPANY

    @computed_field  # type: ignore[misc]
    @property
    def company_ids(self) -> List[str]:
        """Ids of the companies the user belongs to."""
        return [membership.company_id for membership in (self.companies or [])]