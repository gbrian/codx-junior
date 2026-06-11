from typing import Optional, List
from pydantic import BaseModel, Field
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


class ProjectPermission(BaseModel):
    project_id: str
    permissions: str = Field(description="User permissions for the project", default=[])
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
    role: Optional[str] = Field(description="User role", default="user")
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

    # ── Token-limit policy (admin-managed, stored inline on the user) ──────────

    token_limit_rules: List[TokenLimitRule] = Field(
        default_factory=list,
        description="Daily token-limit rules for this user (admin-managed).",
    )
    token_limit_requests: List[TokenLimitRequest] = Field(
        default_factory=list,
        description="Pending / resolved limit-increase requests from this user.",
    )