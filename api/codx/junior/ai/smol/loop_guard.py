"""
Loop protection for SmolAgent tool calling.

Provides :class:`LoopGuard`, a small stateful helper that enforces:
    1. A maximum number of tool rounds (depth guard).
    2. A maximum number of tool calls per round (breadth guard).
    3. Fingerprint-based detection of identical repeated tool-call rounds.

The guard resolves limits with the following priority:
    1. Explicitly passed parameters (model/provider configured)
    2. Fallback defaults (safe defaults for unconfined execution)

Made with ❤️ by codx-junior
"""
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from codx.junior.ai.smol.constants import (
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_TOOL_CALLS,
    MAX_IDENTICAL_ROUNDS,
    TOOL_ROUNDS_ERROR_MSG,
    TOOL_LOOP_ERROR_MSG,
    TOOL_CALLS_EXCEEDED_ERROR_MSG,
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

    Enforces three protection mechanisms:
    1. **Depth guard**: Maximum number of iterative tool rounds.
    2. **Breadth guard**: Maximum number of tool calls per single round.
    3. **Stuck loop detection**: Fingerprint-based detection of identical
       consecutive rounds (indicates model is not making progress).

    Limits are resolved with priority: Explicit parameter > Fallback default.
    This allows model/provider settings to override defaults while ensuring
    safe bounds even when no configuration is present.

    Usage::

        guard = LoopGuard(
            max_iterations=model_settings.max_iterations,
            max_tool_calls=model_settings.max_tool_calls
        )
        while ...:
            guard.check(tool_calls)  # raises ToolLoopError when stuck
    """

    def __init__(
        self,
        max_iterations: Optional[int] = None,
        max_tool_calls: Optional[int] = None,
        max_identical_rounds: int = MAX_IDENTICAL_ROUNDS,
    ) -> None:
        """
        Args:
            max_iterations:       Maximum sequential tool rounds allowed.
                                 Falls back to DEFAULT_MAX_ITERATIONS if None.
            max_tool_calls:       Maximum tool calls allowed per single round.
                                 Falls back to DEFAULT_MAX_TOOL_CALLS if None.
            max_identical_rounds: Identical consecutive rounds that trigger
                                 loop detection (typically 3).
        """
        self.max_iterations: int = max_iterations or DEFAULT_MAX_ITERATIONS
        self.max_tool_calls: int = max_tool_calls or DEFAULT_MAX_TOOL_CALLS
        self.max_identical_rounds: int = max_identical_rounds
        self.rounds: int = 0
        self.fingerprints: List[str] = []

        logger.debug(
            "LoopGuard initialized: max_iterations=%d, max_tool_calls=%d, "
            "max_identical_rounds=%d",
            self.max_iterations,
            self.max_tool_calls,
            self.max_identical_rounds,
        )

    def check(self, tool_calls: Dict[str, Dict[str, Any]]) -> None:
        """
        Register a new tool round and verify all guards (depth, breadth, stuck loop).

        Checks (in order):
        1. **Depth guard**: Increment round counter and check against max_iterations.
        2. **Breadth guard**: Verify tool_calls count doesn't exceed max_tool_calls.
        3. **Stuck loop guard**: Check for identical consecutive rounds.

        Args:
            tool_calls: The current round's accumulated tool calls dict
                       (mapping tool_call_id → tool_call dict).

        Raises:
            ToolLoopError: When max iterations are exceeded, tool call limit
                          is violated, or a stuck loop is detected.
        """
        # 1. Depth guard: check iteration count
        self.rounds += 1
        if self.rounds > self.max_iterations:
            logger.error(
                "LoopGuard: max iterations (%d) exceeded at round %d",
                self.max_iterations,
                self.rounds,
            )
            raise ToolLoopError(
                TOOL_ROUNDS_ERROR_MSG.format(rounds=self.max_iterations)
            )

        # 2. Breadth guard: check tool calls per round
        num_tool_calls = len(tool_calls)
        if num_tool_calls > self.max_tool_calls:
            logger.error(
                "LoopGuard: tool call limit exceeded at round %d: "
                "max=%d, actual=%d",
                self.rounds,
                self.max_tool_calls,
                num_tool_calls,
            )
            raise ToolLoopError(
                TOOL_CALLS_EXCEEDED_ERROR_MSG.format(
                    max_calls=self.max_tool_calls,
                    actual_calls=num_tool_calls,
                )
            )

        # 3. Stuck loop guard: check for identical consecutive rounds
        fingerprint = fingerprint_tool_calls(tool_calls)
        recent = self.fingerprints[-self.max_identical_rounds:]
        if (
            len(recent) >= self.max_identical_rounds
            and all(fp == fingerprint for fp in recent)
        ):
            logger.error(
                "LoopGuard: identical tool round repeated %d times at round %d "
                "(fingerprint=%s)",
                self.max_identical_rounds,
                self.rounds,
                fingerprint[:12],
            )
            raise ToolLoopError(
                TOOL_LOOP_ERROR_MSG.format(count=self.max_identical_rounds)
            )

        self.fingerprints.append(fingerprint)
        logger.debug(
            "LoopGuard: round=%d tool_calls=%d fingerprint=%s (ok)",
            self.rounds,
            num_tool_calls,
            fingerprint[:12],
        )

# Made with ❤️ by codx-junior