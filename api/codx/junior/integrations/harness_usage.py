"""
Usage accounting for harness tasks.

Harnesses execute outside codx-junior's SmolAgent loop, so their token/cost
counters would otherwise be invisible to analytics. Every task update that
carries a usage/cost change is appended to ``<project>/.codx/harness/usage.jsonl``
and mirrored on ``Chat.harness_usage`` / ``Chat.harness_cost``.

The JSONL file is intentionally simple: it is append-only, one record per
observed change, and contains no conversation content.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def usage_log_path(project_root: Optional[str]) -> Optional[str]:
    """Return the harness usage log path for a project, creating nothing yet."""
    if not project_root:
        return None
    return os.path.join(project_root, ".codx", "harness", "usage.jsonl")


def _as_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def log_usage(
    *,
    project_root: Optional[str],
    project_name: Optional[str],
    chat: Any,
    task: Any,
    instance_id: Optional[str],
    source: str = "event",
) -> Optional[Dict[str, Any]]:
    """
    Append one usage record when the task reports counters.

    Returns the record that was written, or ``None`` when there is nothing to
    measure. Failures never break task mirroring: the caller treats accounting
    as best effort.
    """
    usage = _as_dict(getattr(task, "usage", None))
    cost = _as_float(getattr(task, "cost", None))
    if not usage and cost is None:
        return None

    record = {
        "at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "project": project_name,
        "harness": getattr(chat, "harness", None) or "dsh",
        "task_id": getattr(chat, "id", None),
        "session_id": getattr(task, "id", None),
        "instance_id": instance_id or getattr(chat, "harness_instance_id", None),
        "status": getattr(task, "status", None),
        "model": getattr(task, "model", None) or getattr(chat, "harness_model", None),
        "usage": usage,
        "cost": cost,
        "external_updated_at": getattr(task, "updated_at", None),
    }

    path = usage_log_path(project_root)
    if not path:
        return record
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except OSError as ex:
        logger.warning("harness usage: cannot append %s: %s", path, ex)
        return record
    logger.info(
        "harness usage: task=%s session=%s model=%s usage=%s cost=%s",
        record["task_id"],
        record["session_id"],
        record["model"],
        record["usage"],
        record["cost"],
    )
    return record


def aggregate_usage(chats: Any) -> Dict[str, Any]:
    """Aggregate the usage/cost currently mirrored on a project's tasks."""
    total_cost = 0.0
    total_input = 0
    total_output = 0
    measured = 0
    for chat in chats:
        usage = _as_dict(getattr(chat, "harness_usage", None))
        cost = _as_float(getattr(chat, "harness_cost", None))
        if usage or cost is not None:
            measured += 1
        if cost:
            total_cost += cost
        for key in ("input_tokens", "inputTokens"):
            if usage.get(key):
                total_input += int(usage.get(key) or 0)
                break
        for key in ("output_tokens", "outputTokens"):
            if usage.get(key):
                total_output += int(usage.get(key) or 0)
                break
    return {
        "measured_tasks": measured,
        "cost": round(total_cost, 6) if total_cost else 0.0,
        "input_tokens": total_input,
        "output_tokens": total_output,
    }
