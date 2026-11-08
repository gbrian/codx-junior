"""
Tests for the SmolAgent tool execution timeout.

A tool that blocks must not freeze the turn: sync tools run in a daemon
thread, async tools are awaited with ``asyncio.wait_for``, and a timeout is
reported to the model as a normal tool error (never raised to the caller).
"""

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from engine.agent_runtime import AgentEventType, AgentRunContext

from codx.junior.ai.smol.smol_agent import SmolAgent


class _FakeSettings:
    project_id = "project-1"
    project_name = "Project 1"

    def __init__(self, timeout):
        self._timeout = timeout

    def get_llm_settings(self, llm_model=None):
        return SimpleNamespace(
            model="test-model",
            api_key="test-key",
            api_url="http://localhost/v1",
            provider="test",
            system="",
            temperature=0.0,
            input_k_tokens_cxjcoins=0.0,
            output_k_tokens_cxjcoins=0.0,
            max_tool_calls=5,
            max_iterations=10,
            tool_timeout_seconds=self._timeout,
        )


def _agent(timeout=0.2):
    with patch("codx.junior.ai.smol.smol_agent.OpenAI"):
        return SmolAgent(settings=_FakeSettings(timeout))


def _tool(name, func, is_async=False, timeout_seconds=None):
    settings = {"project_settings": False, "async": is_async}
    if timeout_seconds is not None:
        settings["timeout_seconds"] = timeout_seconds
    return {
        "tool_json": {"function": {"name": name}},
        "settings": settings,
        "tool_call": func,
    }


@pytest.mark.asyncio
async def test_sync_tool_is_aborted_after_timeout():
    agent = _agent(timeout=0.2)
    started = time.monotonic()

    def slow_tool(**kwargs):
        time.sleep(2)
        return "too late"

    agent.tools = [_tool("slow_tool", slow_tool)]
    context = AgentRunContext(project_id="project-1")
    events = []
    context.add_listener(events.append)

    with patch("codx.junior.ai.smol.smol_agent._get_analytics") as analytics:
        analytics.return_value = Mock()
        result = await agent._execute_tool(
            {"id": "call-1", "function": "slow_tool", "arguments": {}},
            run_context=context,
        )

    assert time.monotonic() - started < 1.5
    assert "timed out" in result
    tool_errors = [e for e in events if e.type == AgentEventType.TOOL_ERROR]
    assert tool_errors
    assert tool_errors[0].payload["timeout"] is True
    # The abandoned daemon thread must not keep the interpreter alive.
    assert any(
        thread.name == "smol-tool-slow_tool"
        for thread in __import__("threading").enumerate()
    )


@pytest.mark.asyncio
async def test_async_tool_is_aborted_after_timeout():
    agent = _agent(timeout=0.2)

    async def slow_async(**kwargs):
        await asyncio.sleep(2)
        return "too late"

    agent.tools = [_tool("slow_async", slow_async, is_async=True)]
    context = AgentRunContext(project_id="project-1")

    with patch("codx.junior.ai.smol.smol_agent._get_analytics") as analytics:
        analytics.return_value = Mock()
        result = await agent._execute_tool(
            {"id": "call-2", "function": "slow_async", "arguments": {}},
            run_context=context,
        )

    assert "timed out" in result


@pytest.mark.asyncio
async def test_fast_sync_tool_returns_normally():
    agent = _agent(timeout=5)

    def fast_tool(value=0, **kwargs):
        return f"value={value}"

    agent.tools = [_tool("fast_tool", fast_tool)]
    context = AgentRunContext(project_id="project-1")

    with patch("codx.junior.ai.smol.smol_agent._get_analytics") as analytics:
        analytics.return_value = Mock()
        result = await agent._execute_tool(
            {"id": "call-3", "function": "fast_tool", "arguments": {"value": 7}},
            run_context=context,
        )

    assert result == "value=7"


@pytest.mark.asyncio
async def test_per_tool_timeout_overrides_agent_default():
    agent = _agent(timeout=10)

    def slow_tool(**kwargs):
        time.sleep(1)
        return "done"

    agent.tools = [_tool("slow_tool", slow_tool, timeout_seconds=0.1)]
    context = AgentRunContext(project_id="project-1")

    with patch("codx.junior.ai.smol.smol_agent._get_analytics") as analytics:
        analytics.return_value = Mock()
        result = await agent._execute_tool(
            {"id": "call-4", "function": "slow_tool", "arguments": {}},
            run_context=context,
        )

    assert "timed out" in result
