/**
 * Pure helpers shared by the DSH <-> codx-junior bridge.
 *
 * Nothing in this module touches Cordis, HTTP, or the filesystem. Keeping the
 * derivation rules here makes the interesting behaviour (message projection,
 * summary shaping, webhook signing) directly testable with `node --test`.
 */

import { createHmac, timingSafeEqual } from "node:crypto";

/** Fields accepted from the plugin row. Every value has a local default. */
export const DEFAULT_CONFIG = {
  codxApiUrl: "http://127.0.0.1:19980",
  codxPath: "",
  agentEnabled: true,
  token: "",
  tokenFile: "",
  instanceId: "",
  instanceName: "",
  heartbeatMs: 5000,
  pollWaitMs: 25000,
  sharedSecret: "",
  secretFile: "",
  workspaceDir: "",
  projectPath: "",
  board: "DSH",
  defaultColumn: "Todo",
  uiUrlTemplate: "http://127.0.0.1:3080/?session={sessionId}",
  bridgeEnabled: false,
  webhookEnabled: true,
  syncOnStart: true,
  debounceMs: 900,
  requestTimeoutMs: 15000,
  webhookRetries: 4,
  syncLimit: 250,
};

function positiveInt(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? Math.floor(number) : fallback;
}

function trimmed(value, fallback = "") {
  return typeof value === "string" ? value.trim() : fallback;
}

/**
 * Resolve a plugin row's config into the shape the bridge uses.
 *
 * Unknown fields are ignored. String values are trimmed; numeric values are
 * bounded to a positive integer. `workspaceDir` defaults to the process cwd so
 * a default `secretFile` can live next to the project's `.codx` directory.
 */
export function normalizeConfig(raw = {}) {
  const workspaceDir = trimmed(raw.workspaceDir) || process.cwd();
  return {
    ...DEFAULT_CONFIG,
    ...raw,
    codxApiUrl: trimmed(raw.codxApiUrl, DEFAULT_CONFIG.codxApiUrl).replace(/\/+$/, ""),
    codxPath: trimmed(raw.codxPath),
    agentEnabled: raw.agentEnabled !== false,
    token: trimmed(raw.token),
    tokenFile: trimmed(raw.tokenFile),
    instanceId: trimmed(raw.instanceId),
    instanceName: trimmed(raw.instanceName),
    heartbeatMs: positiveInt(raw.heartbeatMs, DEFAULT_CONFIG.heartbeatMs),
    pollWaitMs: positiveInt(raw.pollWaitMs, DEFAULT_CONFIG.pollWaitMs),
    sharedSecret: trimmed(raw.sharedSecret),
    secretFile: trimmed(raw.secretFile),
    workspaceDir,
    projectPath: trimmed(raw.projectPath),
    board: trimmed(raw.board, DEFAULT_CONFIG.board),
    defaultColumn: trimmed(raw.defaultColumn, DEFAULT_CONFIG.defaultColumn),
    uiUrlTemplate: trimmed(raw.uiUrlTemplate, DEFAULT_CONFIG.uiUrlTemplate),
    bridgeEnabled: raw.bridgeEnabled === true,
    webhookEnabled: raw.webhookEnabled !== false,
    syncOnStart: raw.syncOnStart !== false,
    debounceMs: positiveInt(raw.debounceMs, DEFAULT_CONFIG.debounceMs),
    requestTimeoutMs: positiveInt(raw.requestTimeoutMs, DEFAULT_CONFIG.requestTimeoutMs),
    webhookRetries: positiveInt(raw.webhookRetries, DEFAULT_CONFIG.webhookRetries),
    syncLimit: positiveInt(raw.syncLimit, DEFAULT_CONFIG.syncLimit),
  };
}

/** Join one or more content blocks into plain text. */
export function textFromContent(content) {
  if (typeof content === "string") return content;
  if (!Array.isArray(content)) return "";
  return content
    .filter((block) => block && block.type === "text" && typeof block.text === "string")
    .map((block) => block.text)
    .join("");
}

/** Join reasoning blocks into plain text. */
export function reasoningFromContent(content) {
  if (!Array.isArray(content)) return "";
  return content
    .filter((block) => block && block.type === "reasoning" && typeof block.text === "string")
    .map((block) => block.text)
    .join("");
}

/** Count tool calls in one assistant content array. */
export function toolCallNames(content) {
  if (!Array.isArray(content)) return [];
  return content
    .filter((block) => block && block.type === "tool-call" && typeof block.name === "string")
    .map((block) => block.name);
}

function messageFor(sessionId, event, message, role) {
  const content = textFromContent(message?.content);
  const reasoning = reasoningFromContent(message?.content);
  const usage = event?.data?.usage;
  const source = message?.source;
  return {
    id: `dsh-${sessionId}-${event.seq}`,
    role,
    content,
    think: reasoning || null,
    created_at: new Date(Number(event.time) || Date.now()).toISOString(),
    meta_data: {
      dsh: {
        session_id: sessionId,
        seq: event.seq,
        type: event.type,
      },
      ...(source?.provider ? { provider: source.provider } : {}),
      ...(source?.model ? { model: source.model } : {}),
      ...(usage ? { usage } : {}),
      ...(toolCallNames(message?.content).length
        ? { tool_calls: toolCallNames(message?.content) }
        : {}),
    },
  };
}

/**
 * Project the durable session log into the small message surface codx-junior
 * renders. Only user and assistant text becomes a message; tool traffic is
 * counted in `meta_data` so the board view stays readable.
 *
 * This is a live projection. It is never persisted by codx-junior.
 */
export function messagesFromEvents(sessionId, events = []) {
  const messages = [];
  for (const event of events) {
    if (!event || typeof event !== "object") continue;
    if (event.type === "user/message") {
      const message = event.data?.message ?? event.data;
      // DSH stores injected runtime/time context as user/message events with a
      // non-user `source.kind`. Those snapshots are model context, not a task
      // prompt, so they must not appear on the codx-junior card.
      const sourceKind = message?.source?.kind;
      if (message && message.role !== "system" && (!sourceKind || sourceKind === "user")) {
        const projected = messageFor(sessionId, event, { ...message, role: "user" }, "user");
        if (projected.content || projected.think) messages.push(projected);
      }
      continue;
    }
    if (event.type === "assistant/message") {
      const message = event.data?.message;
      if (message) {
        const projected = messageFor(sessionId, event, message, "assistant");
        if (projected.content || projected.think) messages.push(projected);
      }
    }
  }
  return messages;
}

/** First non-empty user text, used for fallback titles and descriptions. */
export function firstUserText(messages = []) {
  const message = messages.find((entry) => entry.role === "user" && entry.content);
  return message ? message.content : "";
}

/** Last assistant text, used by codx-junior list previews. */
export function lastAssistantText(messages = []) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    if (messages[index].role === "assistant" && messages[index].content) {
      return messages[index].content;
    }
  }
  return "";
}

/** Compact single-line text for task names/descriptions. */
export function shortText(value, limit = 120) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (text.length <= limit) return text;
  return `${text.slice(0, Math.max(0, limit - 1))}…`;
}

/** Stable fallback title when the session log has no title event yet. */
export function fallbackTitle(sessionId, messages = []) {
  const prompt = shortText(firstUserText(messages), 80);
  if (prompt) return prompt;
  return `DSH ${String(sessionId).slice(-8)}`;
}

/**
 * Shape one task summary for codx-junior.
 *
 * @param {{summary?: object, header?: object, title?: string, running?: boolean}} input
 */
export function summarizeTask(input = {}) {
  const summary = input.summary ?? {};
  const header = input.header ?? {};
  const id = String(summary.sessionId ?? summary.id ?? header.id ?? "");
  const createdAt = Number(header.createdAt ?? summary.createdAt ?? 0) || null;
  const updatedAt = Number(summary.updatedAt ?? input.updatedAt ?? createdAt ?? 0) || null;
  const running = Boolean(input.running ?? summary.running);
  const origin = summary.origin ?? header.origin ?? "session";
  return {
    id,
    title: shortText(input.title, 200) || `DSH ${id.slice(-8)}`,
    parentId: summary.parentSessionId ?? header.parentSession ?? null,
    origin,
    isSubagent: origin === "subagent",
    depth: Number(header.delegationDepth ?? 0) || 0,
    cwd: summary.cwd ?? header.cwd ?? null,
    agentPreset: header.agentPreset ?? null,
    createdAt,
    updatedAt,
    running,
    blank: Boolean(summary.blank),
    status: running ? "running" : "idle",
    webUrl: String(input.webUrl ?? ""),
  };
}

/** Build a task URL from the configured template. */
export function taskWebUrl(template, sessionId) {
  return String(template || "")
    .replaceAll("{sessionId}", encodeURIComponent(String(sessionId)))
    .replaceAll("{session}", encodeURIComponent(String(sessionId)));
}

/** The JSON body signed for codx-junior webhooks. */
export function webhookPayload(kind, task, extra = {}) {
  return {
    version: 1,
    event: kind,
    sentAt: new Date().toISOString(),
    task,
    ...extra,
  };
}

/** Hex HMAC-SHA256 for a UTF-8 request body. */
export function signBody(secret, body) {
  return createHmac("sha256", secret).update(body, "utf8").digest("hex");
}

/** Constant-time comparison that never throws on different lengths. */
export function constantTimeEqual(left, right) {
  const a = Buffer.from(String(left ?? ""), "utf8");
  const b = Buffer.from(String(right ?? ""), "utf8");
  if (a.length !== b.length) return false;
  return timingSafeEqual(a, b);
}

/** Accept `Bearer <secret>` or the dedicated bridge header. */
export function presentedSecret(headers = {}) {
  const authorization = headers.authorization ?? headers.Authorization ?? "";
  if (typeof authorization === "string" && authorization.startsWith("Bearer ")) {
    return authorization.slice(7).trim();
  }
  return headers["x-dsh-secret"] ?? headers["X-DSH-Secret"] ?? "";
}

/** Map a DSH task status to a codx-junior kanban column. */
export function columnForStatus(status, fallback = "Todo") {
  if (status === "running") return "Doing";
  if (status === "error") return "On hold";
  if (status === "closed") return "Done";
  return fallback;
}

/** Map a DSH task status to a codx-junior task status. */
export function chatStatusForTask(task, previous = null) {
  if (task?.status === "running") return "doing";
  if (task?.status === "error") return "onhold";
  if (task?.status === "closed") return "done";
  return previous || "todo";
}
