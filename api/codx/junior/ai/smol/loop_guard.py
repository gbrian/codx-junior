"""
Loop protection for SmolAgent tool calling.

Provides :class:`LoopGuard`, a small stateful helper that enforces:
    1. A maximum number of tool rounds (depth guard).
    2. Fingerprint-based detection of identical repeated tool-call rounds.
"""
import hashlib
import json
import logging
from typing import Any, Dict, List, Tuple

from codx.junior.ai.smol.constants import (
    MAX_TOOL_ROUNDS,
    MAX_IDENTICAL_ROUNDS,
    TOOL_ROUNDS_ERROR_MSG,
    TOOL_LOOP_ERROR_MSG,
)

logger = logging.getLogger(__name__)


class ToolLoopError(RuntimeError):
    """Raised when the model is stuck requesting tools without progress."""


def fingerprint_tool_calls(tool_calls: Dict[str, Dict[str, Any]]) -> str:
    """
    Produce a stable, order-independent hash of a set of tool calls.

    Args:
        tool_calls: Mapping of tool_call_id → {id, function, arguments}.

    Returns:
        A hex digest uniquely representing the tool-call set.
    """
    entries: List[Tuple[str, str]] = []
    for tool_call in tool_calls.values():
        raw_args = tool_call.get("arguments", "")
        try:
            normalised: str = json.dumps(
                json.loads(raw_args) if isinstance(raw_args, str) else raw_args,
                sort_keys=True,
            )
        except (json.JSONDecodeError, TypeError):
            normalised = str(raw_args)
        entries.append((tool_call.get("function", ""), normalised))
    entries.sort()
    return hashlib.sha256(json.dumps(entries).encode()).hexdigest()


class LoopGuard:
    """
    Stateful guard used once per conversation to prevent infinite tool loops.

    Usage::

        guard = LoopGuard()
        while ...:
            guard.check(tool_calls)  # raises ToolLoopError when stuck
    """

    def __init__(
        self,
        max_rounds: int = MAX_TOOL_ROUNDS,
        max_identical_rounds: int = MAX_IDENTICAL_ROUNDS,
    ) -> None:
        """
        Args:
            max_rounds:           Maximum sequential tool rounds allowed.
            max_identical_rounds: Identical consecutive rounds that trigger
                                  loop detection.
        """
        self.max_rounds: int = max_rounds
        self.max_identical_rounds: int = max_identical_rounds
        self.rounds: int = 0
        self.fingerprints: List[str] = []

    def check(self, tool_calls: Dict[str, Dict[str, Any]]) -> None:
        """
        Register a new tool round and verify both guards.

        Args:
            tool_calls: The current round's accumulated tool calls.

        Raises:
            ToolLoopError: When max rounds are exceeded or a stuck loop
                           (identical consecutive rounds) is detected.
        """
        self.rounds += 1
        if self.rounds > self.max_rounds:
            logger.error("LoopGuard: max tool rounds (%d) exceeded", self.max_rounds)
            raise ToolLoopError(TOOL_ROUNDS_ERROR_MSG.format(rounds=self.max_rounds))

        fingerprint = fingerprint_tool_calls(tool_calls)
        recent = self.fingerprints[-self.max_identical_rounds:]
        if len(recent) >= self.max_identical_rounds and all(fp == fingerprint for fp in recent):
            logger.error(
                "LoopGuard: identical tool round repeated %d times (fingerprint=%s)",
                self.max_identical_rounds,
                fingerprint[:12],
            )
            raise ToolLoopError(TOOL_LOOP_ERROR_MSG.format(count=self.max_identical_rounds))

        self.fingerprints.append(fingerprint)
        logger.debug(
            "LoopGuard: round=%d fingerprint=%s", self.rounds, fingerprint[:12]
        )

# Made with ❤️ by codx-junior