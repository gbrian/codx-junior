"""Regression tests for the LoopGuard round accounting.

The agent loop used to increment ``LoopGuard.rounds`` once in ``check()`` and
again after processing the tools, so a configured ``max_iterations`` of N
behaved like N/2. A long investigation then stopped early with a "tool limit
reached" message even though half of the budget was never used.
"""

import pytest

from codx.junior.ai.smol.loop_guard import LoopGuard, ToolLoopError


def _tool_calls(round_index: int = 0, name: str = "project_read_file") -> dict:
    """One synthetic uncached tool round (unique per round)."""
    return {
        "call-1": {
            "id": "call-1",
            "function": name,
            "arguments": f'{{"file_path": "file_{round_index}.py"}}',
        }
    }


def test_checked_rounds_are_counted_once():
    guard = LoopGuard(max_iterations=4, max_tool_calls=5)

    for round_index in range(4):
        guard.check(_tool_calls(round_index))
        # The agent calls this after every round; for a checked round it must
        # NOT bump the counter a second time.
        guard.complete_round(checked=True)

    assert guard.rounds == 4


def test_fifth_checked_round_is_rejected():
    guard = LoopGuard(max_iterations=4, max_tool_calls=5)

    for round_index in range(4):
        guard.check(_tool_calls(round_index))
        guard.complete_round(checked=True)

    with pytest.raises(ToolLoopError):
        guard.check(_tool_calls(99))


def test_all_cached_rounds_still_count_towards_depth():
    """All-cached rounds skip check(); complete_round must count them."""
    guard = LoopGuard(max_iterations=3, max_tool_calls=5)

    guard.complete_round(checked=False)
    guard.complete_round(checked=False)
    guard.complete_round(checked=False)

    assert guard.rounds == 3
    with pytest.raises(ToolLoopError):
        guard.check(_tool_calls(99))
