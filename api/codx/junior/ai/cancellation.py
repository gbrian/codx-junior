import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CancelledError(Exception):
    """Raised when an AI request is cancelled via a CancellationToken."""
    pass


class CancellationToken:
    """
    A token that can be used to cancel an in-flight AI request.

    Each token carries a unique ``token_id`` (UUID4) that is sent to clients
    via the response message metadata so they can cancel the request either by
    ``chat_id`` or by ``token_id``.

    flowchart TD
        A[Create token] --> B[Assign token_id UUID]
        B --> C{cancel() called?}
        C -->|Yes| D[Set cancelled_at timestamp]
        D --> E[Raise CancelledError on next check]
        C -->|No| F[Request completes normally]
    """

    def __init__(self, chat_id: str) -> None:
        self.chat_id: str = chat_id
        self.token_id: str = str(uuid.uuid4())
        self.cancelled_at: Optional[datetime] = None
        self._event = asyncio.Event()

    @property
    def is_cancelled(self) -> bool:
        return self.cancelled_at is not None

    def cancel(self) -> None:
        """Mark this token as cancelled."""
        if not self.is_cancelled:
            self.cancelled_at = datetime.now(tz=timezone.utc)
            self._event.set()
            logger.info(
                "CancellationToken cancelled for chat_id='%s' token_id='%s' at %s",
                self.chat_id,
                self.token_id,
                self.cancelled_at,
            )

    def check(self) -> None:
        """
        Raise CancelledError if this token has been cancelled.
        Call this at yield points inside synchronous code.
        """
        if self.is_cancelled:
            raise CancelledError(
                f"Request for chat '{self.chat_id}' (token '{self.token_id}') "
                f"was cancelled at {self.cancelled_at}"
            )

    async def wait_for_cancellation(self) -> datetime:
        """Async wait until the token is cancelled. Returns the cancellation time."""
        await self._event.wait()
        return self.cancelled_at


class CancellationRegistry:
    """
    Global registry that maps chat_id -> CancellationToken and
    token_id -> CancellationToken for dual-key lookup.

    Tokens are registered when a chat starts and removed when it finishes
    (or is cancelled).

    flowchart TD
        A[chat_with_project starts] --> B[register token]
        B --> C{AI running}
        C -->|cancel by chat_id| D[token.cancel via chat_id]
        C -->|cancel by token_id| E[token.cancel via token_id]
        C -->|request finishes| F[unregister token]
        D --> F
        E --> F
    """

    def __init__(self) -> None:
        self._by_chat_id: Dict[str, CancellationToken] = {}
        self._by_token_id: Dict[str, CancellationToken] = {}

    def register(self, chat_id: str) -> CancellationToken:
        """
        Create and register a new CancellationToken for *chat_id*.

        If a token already exists for this chat it is replaced (the previous
        in-flight request — if any — is not cancelled automatically).

        :param chat_id: The chat ``doc_id`` to associate with this token.
        :return: The newly created CancellationToken.
        """
        token = CancellationToken(chat_id=chat_id)
        self._by_chat_id[chat_id] = token
        self._by_token_id[token.token_id] = token
        logger.debug(
            "CancellationToken registered for chat_id='%s' token_id='%s'",
            chat_id,
            token.token_id,
        )
        return token

    def unregister(self, chat_id: str) -> None:
        """
        Remove the token for *chat_id* from both lookup indices.

        :param chat_id: The chat ``doc_id`` whose token should be removed.
        """
        token = self._by_chat_id.pop(chat_id, None)
        if token:
            self._by_token_id.pop(token.token_id, None)
        logger.debug("CancellationToken unregistered for chat_id='%s'", chat_id)

    def cancel(self, chat_id: str) -> bool:
        """
        Cancel the in-flight request for *chat_id*.

        :param chat_id: The chat ``doc_id`` to cancel.
        :returns: True if a token was found and cancelled, False otherwise.
        """
        token = self._by_chat_id.get(chat_id)
        if token:
            token.cancel()
            return True
        logger.warning(
            "cancel() called for chat_id='%s' but no token found", chat_id
        )
        return False

    def cancel_by_token_id(self, token_id: str) -> bool:
        """
        Cancel the in-flight request identified by *token_id*.

        :param token_id: The UUID string of the CancellationToken to cancel.
        :returns: True if a token was found and cancelled, False otherwise.
        """
        token = self._by_token_id.get(token_id)
        if token:
            token.cancel()
            return True
        logger.warning(
            "cancel_by_token_id() called for token_id='%s' but no token found",
            token_id,
        )
        return False

    def get(self, chat_id: str) -> Optional[CancellationToken]:
        """Return the token for *chat_id*, or None."""
        return self._by_chat_id.get(chat_id)

    def get_by_token_id(self, token_id: str) -> Optional[CancellationToken]:
        """Return the token for *token_id*, or None."""
        return self._by_token_id.get(token_id)


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere you need the registry.
# ---------------------------------------------------------------------------
CANCELLATION_REGISTRY = CancellationRegistry()