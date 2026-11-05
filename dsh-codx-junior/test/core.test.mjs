import test from "node:test";
import assert from "node:assert/strict";
import {
  chatStatusForTask,
  columnForStatus,
  constantTimeEqual,
  fallbackTitle,
  firstUserText,
  messagesFromEvents,
  normalizeConfig,
  shortText,
  signBody,
  summarizeTask,
  taskWebUrl,
} from "../lib/core.js";

test("projects user and assistant text out of a session log", () => {
  const events = [
    { type: "user/message", seq: 1, time: 1000, data: { role: "user", content: [{ type: "text", text: "Fix the login timeout" }] } },
    {
      type: "assistant/message",
      seq: 4,
      time: 2000,
      data: {
        usage: { inputTokens: 10, outputTokens: 3 },
        message: {
          role: "assistant",
          content: [
            { type: "reasoning", text: "Check the timeout constant." },
            { type: "text", text: "I will inspect the auth module." },
            { type: "tool-call", id: "call-1", name: "bash", arguments: "{}" },
          ],
          source: { provider: "deepseek", model: "deepseek-flash" },
        },
      },
    },
    { type: "tool/call", seq: 5, time: 2100, data: { name: "bash" } },
  ];
  const messages = messagesFromEvents("session-1", events);
  assert.equal(messages.length, 2);
  assert.equal(messages[0].role, "user");
  assert.equal(messages[0].content, "Fix the login timeout");
  assert.equal(messages[0].id, "dsh-session-1-1");
  assert.equal(messages[1].role, "assistant");
  assert.equal(messages[1].content, "I will inspect the auth module.");
  assert.equal(messages[1].think, "Check the timeout constant.");
  assert.deepEqual(messages[1].meta_data.tool_calls, ["bash"]);
  assert.equal(messages[1].meta_data.provider, "deepseek");
  assert.equal(messages[1].meta_data.usage.outputTokens, 3);
  assert.equal(firstUserText(messages), "Fix the login timeout");
});

test("ignores injected runtime context and empty messages", () => {
  const messages = messagesFromEvents("s", [
    { type: "user/message", seq: 1, time: 2, data: { role: "user", content: "Current runtime context", source: { kind: "runtime-context" } } },
    { type: "user/message", seq: 2, time: 3, data: { role: "user", content: "Real prompt", source: { kind: "user" } } },
  ]);
  assert.deepEqual(messages.map((message) => message.content), ["Real prompt"]);
});

test("ignores system events and empty messages", () => {
  const messages = messagesFromEvents("s", [
    { type: "system/message", seq: 0, time: 1, data: { message: { role: "system", content: "hidden" } } },
    { type: "user/message", seq: 1, time: 2, data: { role: "user", content: [] } },
    { type: "assistant/message", seq: 2, time: 3, data: { message: { role: "assistant", content: [{ type: "tool-call", name: "x" }] } } },
  ]);
  assert.deepEqual(messages, []);
});

test("summarizes a subagent session with its parent and depth", () => {
  const task = summarizeTask({
    summary: { sessionId: "child-1", parentSessionId: "parent-1", origin: "subagent", running: true, updatedAt: 50 },
    header: { id: "child-1", createdAt: 10, delegationDepth: 2, agentPreset: "researcher" },
    title: "Review the patch",
  });
  assert.equal(task.id, "child-1");
  assert.equal(task.title, "Review the patch");
  assert.equal(task.parentId, "parent-1");
  assert.equal(task.isSubagent, true);
  assert.equal(task.depth, 2);
  assert.equal(task.status, "running");
  assert.equal(task.agentPreset, "researcher");
});

test("falls back to the first prompt for a title", () => {
  const messages = [{ role: "user", content: "Implement the sync integration now" }];
  assert.equal(fallbackTitle("session-12345678", messages), "Implement the sync integration now");
  assert.equal(fallbackTitle("session-12345678", []), "DSH 12345678");
  assert.equal(shortText("a\n\nb", 10), "a b");
});

test("normalizes config and keeps string/number bounds", () => {
  const config = normalizeConfig({
    codxApiUrl: " http://localhost:19980/ ",
    debounceMs: "25",
    requestTimeoutMs: -1,
    webhookEnabled: false,
  });
  assert.equal(config.codxApiUrl, "http://localhost:19980");
  assert.equal(config.debounceMs, 25);
  assert.equal(config.requestTimeoutMs, 15000);
  assert.equal(config.webhookEnabled, false);
});

test("builds task links and signs webhook bodies", () => {
  assert.equal(
    taskWebUrl("http://dsh/?session={sessionId}", "session-a b"),
    "http://dsh/?session=session-a%20b",
  );
  const signature = signBody("secret", '{"a":1}');
  assert.equal(signature.length, 64);
  assert.equal(constantTimeEqual(signature, signBody("secret", '{"a":1}')), true);
  assert.equal(constantTimeEqual(signature, signBody("other", '{"a":1}')), false);
});

test("maps task state to board destination", () => {
  assert.equal(columnForStatus("running"), "Doing");
  assert.equal(columnForStatus("error"), "On hold");
  assert.equal(columnForStatus("idle", "Todo"), "Todo");
  assert.equal(chatStatusForTask({ status: "running" }, null), "doing");
  assert.equal(chatStatusForTask({ status: "idle" }, "doing"), "doing");
  assert.equal(chatStatusForTask({ status: "closed" }, "doing"), "done");
});
