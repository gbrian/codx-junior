"""
Board-native orchestration for codx-junior.

The package exposes the durable multi-step run runtime that gives codx-junior
the execution model of DSH (plan → isolated workers → verify → finish) while
keeping every piece of work visible on the existing boards and sprints.

Public API (imported lazily):

* :class:`OrchestrationService` — create/plan/advance/control runs.
* :class:`RunStore` — durable run documents and single-flight locks.
* :class:`RunBoard` — board/sprint/card materialization.
* :class:`StepExecutor` — isolated worker turns.
* :class:`RunState` / :class:`RunConfig` / :class:`PlanStep` — data model.

Importing this package is free: the service (and with it the AI stack) is only
loaded when a symbol is used. This keeps the module safe to import from the
agent runtime, tools and tests.

Made with ❤️ by codx-junior
"""

from typing import Any

_LAZY_EXPORTS = {
    "OrchestrationService": ("codx.junior.orchestration.service", "OrchestrationService"),
    "RunStore": ("codx.junior.orchestration.store", "RunStore"),
    "RunLock": ("codx.junior.orchestration.store", "RunLock"),
    "RunBoard": ("codx.junior.orchestration.board", "RunBoard"),
    "StepExecutor": ("codx.junior.orchestration.executor", "StepExecutor"),
    "RunState": ("codx.junior.orchestration.models", "RunState"),
    "RunConfig": ("codx.junior.orchestration.models", "RunConfig"),
    "PlanStep": ("codx.junior.orchestration.models", "PlanStep"),
    "StepResult": ("codx.junior.orchestration.models", "StepResult"),
    "PlanError": ("codx.junior.orchestration.models", "PlanError"),
    "RunNotFound": ("codx.junior.orchestration.models", "RunNotFound"),
    "RunLocked": ("codx.junior.orchestration.models", "RunLocked"),
    "RunCorrupt": ("codx.junior.orchestration.models", "RunCorrupt"),
    "parse_step_result": ("codx.junior.orchestration.models", "parse_step_result"),
    "ready_steps": ("codx.junior.orchestration.models", "ready_steps"),
    "next_actions": ("codx.junior.orchestration.models", "next_actions"),
}

__all__ = list(_LAZY_EXPORTS)


def __getattr__(name: str) -> Any:
    """Resolve public names lazily (PEP 562)."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from importlib import import_module

    module_name, attribute = target
    return getattr(import_module(module_name), attribute)

# Made with ❤️ by codx-junior
