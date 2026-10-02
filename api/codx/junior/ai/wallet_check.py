import logging
from codx.junior.model.model import CodxUser

logger = logging.getLogger(__name__)


def _get_today_spent(username: str) -> float:
    """
    Query today's total CXJ coins spent by the user from analytics storage.

    Returns:
        Total CXJ coins spent today (float), or 0.0 if no data.
    """
    try:
        from datetime import date
        from codx.junior.analytics.analytics import Analytics

        today = date.today().isoformat()
        analytics = Analytics()
        totals = analytics.get_total_usage(
            start_date=today,
            end_date=today,
            username=username,
        )
        return totals.get("total_cxjcoins", 0.0)
    except Exception as exc:
        logger.warning(
            "_get_today_spent: failed to query analytics for user '%s': %s",
            username,
            exc,
        )
        return 0.0


def check_user_wallet(user: CodxUser) -> None:
    """
    Check if the user is allowed to make an AI request.

    Rules:
    - No user          → allow (anonymous / internal call)
    - No wallet        → allow (no billing configured)
    - Wallet disabled  → raise InsufficientFundsError
    - No spending limits → allow (unlimited wallet)
    - Has spending limits → check each one against today's analytics spend;
                            raise if any limit is exhausted

    Raises:
        InsufficientFundsError: when the user has no budget left for today.
    """
    if not user:
        return

    wallet = getattr(user, "wallet", None)
    if not wallet:
        logger.debug("check_user_wallet: user '%s' has no wallet — allowing.", user.username)
        return

    if not wallet.enabled:
        raise Exception(
            f"User '{user.username}' wallet is disabled."
        )

    # No spending limits configured → unlimited, just allow
    if not wallet.spending_limits:
        logger.debug(
            "check_user_wallet: user '%s' has no spending limits — allowing.",
            user.username,
        )
        return

    # Fetch today's actual spend from analytics (single query for all limits)
    today_spent = _get_today_spent(user.username)

    # Check each spending limit against analytics-sourced spend
    for limit in wallet.spending_limits:
        remaining = limit.limit_cxjcoins - today_spent
        logger.debug(
            "check_user_wallet: user '%s' [%s] today_spent=%.4f limit=%.4f remaining=%.4f",
            user.username,
            limit.period.value,
            today_spent,
            limit.limit_cxjcoins,
            remaining,
        )
        if remaining <= 0:
            raise Exception(
                f"User '{user.username}' has no budget left for the "
                f"{limit.period.value} period "
                f"(limit: {limit.limit_cxjcoins:.4f}, "
                f"spent today: {today_spent:.4f})."
            )