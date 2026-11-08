"""
Integration tests: the conversation history sent to the model must carry the
tool memory of the previous turns.
"""
from types import SimpleNamespace

from langchain.messages import HumanMessage

from codx.junior.chat.chat_prompt_builder import (
    CONVERSATION_GUARDRAIL_SYSTEM_PROMPT,
    CONVERSATION_HISTORY_HEADER,
    ChatPromptBuilder,
)


class FakeToolEvent:
    def __init__(self, tool, request=None, status="done", response=""):
        self.tool = tool
        self.request = request or {}
        self.status = status
        self.response = response
        self.output = ""
        self.error = ""


class FakeMessage:
    def __init__(
        self,
        role="user",
        content="",
        tool_events=None,
        hide=False,
        improvement=False,
        is_answer=False,
        files=None,
        attachments=None,
    ):
        self.role = role
        self.content = content
        self.tool_events = tool_events or []
        self.hide = hide
        self.improvement = improvement
        self.is_answer = is_answer
        self.files = files or []
        self.attachments = attachments or []


def fake_chat(messages, parent_id=None, ignore_parent_knowledge=False):
    return SimpleNamespace(
        messages=messages,
        parent_id=parent_id,
        ignore_parent_knowledge=ignore_parent_knowledge,
        owner_project_id="project-1",
        doc_id="chat-1",
        name="Test chat",
    )


def builder():
    return ChatPromptBuilder(
        get_chat_manager=lambda project_id=None: None,
        get_chat_analysis_parents=lambda chat: "",
    )


def test_history_contains_tool_memory_of_prior_turn():
    prior_assistant = FakeMessage(
        role="assistant",
        content="Done.",
        tool_events=[
            FakeToolEvent(
                "project_read_file",
                {"file_path": "src/app.py"},
                response="print('hello')",
            )
        ],
    )
    current_user = FakeMessage(role="user", content="What does app.py do?")
    chat = fake_chat([FakeMessage(role="user", content="Read app.py"), prior_assistant, current_user])

    messages = builder().build_message_history(chat=chat)

    assert len(messages) == 1
    assert isinstance(messages[0], HumanMessage)
    content = messages[0].content
    assert CONVERSATION_HISTORY_HEADER.strip().splitlines()[0] in content
    assert "<conversation_history>" in content
    assert "<session_memory>" in content
    assert "src/app.py" in content
    assert "print('hello')" in content
    # The live user request is NOT part of the history block.
    assert "What does app.py do?" not in content


def test_history_is_returned_when_only_tool_memory_exists():
    """Even with no assistant text, prior tool results are sent to the model."""
    chat = fake_chat(
        [
            FakeMessage(
                role="assistant",
                content="",
                tool_events=[
                    FakeToolEvent("project_grep", {"pattern": "TODO"}, response="src/x.py:1: TODO")
                ],
            ),
            FakeMessage(role="user", content="continue"),
        ]
    )

    messages = builder().build_message_history(chat=chat)

    assert len(messages) == 1
    assert "<session_memory>" in messages[0].content
    assert "TODO" in messages[0].content


def test_no_history_and_no_tool_memory_returns_empty():
    chat = fake_chat([FakeMessage(role="user", content="hi")])

    assert builder().build_message_history(chat=chat) == []


def test_prebuilt_tool_memory_section_is_reused():
    """The engine passes the section it already logged/counted."""
    chat = fake_chat([FakeMessage(role="user", content="go")])

    messages = builder().build_message_history(
        chat=chat,
        tool_memory_section="<session_memory>prebuilt</session_memory>",
    )

    assert len(messages) == 1
    assert "prebuilt" in messages[0].content


def test_system_guardrail_tells_the_model_to_reuse_tool_memory():
    assert "<session_memory>" in CONVERSATION_GUARDRAIL_SYSTEM_PROMPT
    assert "same arguments" in CONVERSATION_GUARDRAIL_SYSTEM_PROMPT
