/**
 * DSH <-> codx-junior bridge.
 *
 * The Host plugin has two jobs:
 *
 * 1. Expose a small, token-protected HTTP bridge under
 *    `/api/codx-junior/*` so codx-junior can list DSH sessions, read their live
 *    message surface, create a DSH session (and prompt it), send follow-up
 *    prompts, rename, and cancel. No message content is stored by the bridge.
 * 2. Push task lifecycle notifications to codx-junior whenever a DSH session
 *    is created, changes, or is disposed, so its boards can mirror the task
 *    tree (including subagent sessions) without copying the conversation.
 *
 * The Session log remains the only source of truth. Everything the bridge
 * returns is derived from `sessionQuery`/`sessionController` at request time.
 */

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { dirname, isAbsolute, join } from "node:path";
import {
  constantTimeEqual,
  fallbackTitle,
  firstUserText,
  lastAssistantText,
  messagesFromEvents,
  normalizeConfig,
  presentedSecret,
  shortText,
  signBody,
  summarizeTask,
  taskWebUrl,
  webhookPayload,
} from "./lib/core.js";

export const name = "codx-junior-sync";

/** The routes need the Host web carrier; session services are optional. */
export const inject = ["webServer"];

const ROUTE_PREFIX = "/codx-junior";
const MAX_BODY_BYTES = 1024 * 1024;
const IMPORTANT_EVENTS = new Set([
  "user/message",
  "assistant/message",
  "session/title",
  "turn/end",
  "error",
]);

function service(ctx, key) {
  try {
    return ctx.get(key) ?? null;
  } catch {
    return null;
  }
}

function sendJson(res, status, payload) {
  res.statusCode = status;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.setHeader("cache-control", "no-store");
  res.end(JSON.stringify(payload));
}

function sendError(res, status, code, message) {
  sendJson(res, status, { ok: false, code, message });
}

async function readJson(req, limit = MAX_BODY_BYTES) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.byteLength;
    if (size > limit) {
      req.resume();
      const error = new Error("request body is too large");
      error.code = "payload-too-large";
      throw error;
    }
    chunks.push(chunk);
  }
  if (size === 0) return {};
  const text = Buffer.concat(chunks, size).toString("utf8");
  const parsed = JSON.parse(text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    const error = new Error("request body must be a JSON object");
    error.code = "bad-request";
    throw error;
  }
  return parsed;
}

function iso(ms) {
  return ms ? new Date(ms).toISOString() : null;
}

function ensureSecret(config, log) {
  if (config.sharedSecret) return config.sharedSecret;
  const fromEnv = String(process.env.DSH_CODX_JUNIOR_SECRET ?? "").trim();
  if (fromEnv) return fromEnv;
  const file = config.secretFile || join(config.workspaceDir, ".dsh-codx-junior", "secret");
  try {
    if (existsSync(file)) {
      const value = readFileSync(file, "utf8").trim();
      if (value) return value;
    }
    mkdirSync(dirname(file), { recursive: true });
    const value = randomBytes(32).toString("hex");
    writeFileSync(file, `${value}\n`, { mode: 0o600 });
    log.info(`codx-junior-sync: generated bridge secret at ${file}`);
    return value;
  } catch (error) {
    log.warn(`codx-junior-sync: cannot read or write ${file}: ${String(error)}`);
    return "";
  }
}

function taskFromLiveSession(ctx, session, extras = {}) {
  const id = String(session.id);
  let hasTitle = Boolean(extras.title);
  let title = extras.title;
  if (!title) {
    try {
      title = service(ctx, "sessionTitle")?.get(session)?.title;
      hasTitle = Boolean(title);
    } catch {
      title = undefined;
    }
  }
  let messages = [];
  if (!title) {
    try {
      messages = messagesFromEvents(id, session.snapshotEvents());
    } catch {
      messages = [];
    }
    title = fallbackTitle(id, messages);
  }
  const last = session.seq > 0 ? session.eventAt(session.seq - 1) : undefined;
  const running = service(ctx, "agents")?.get(id)?.status === "running";
  const task = summarizeTask({
    header: session.header,
    title,
    running,
    updatedAt: last?.time,
    webUrl: taskWebUrl(extras.uiUrlTemplate, id),
  });
  task.blank = messages.length === 0 && !hasTitle;
  if (messages.length) {
    task.description = shortText(firstUserText(messages), 4000);
    task.lastMessage = shortText(lastAssistantText(messages), 400);
  }
  return task;
}

async function taskFromStoredSession(ctx, sessionId, signal) {
  const controller = service(ctx, "sessionController");
  const query = service(ctx, "sessionQuery");
  if (!controller || !query) throw new Error("session services are unavailable");
  const inspection = await controller.inspect(sessionId, signal);
  if (!inspection) throw new Error(`session not found: ${sessionId}`);
  const messages = messagesFromEvents(sessionId, inspection.events);
  let title;
  try {
    title = (await query.readTitle(sessionId, signal))?.title;
  } catch {
    title = undefined;
  }
  const task = summarizeTask({
    header: inspection.meta,
    title: title || fallbackTitle(sessionId, messages),
    running: service(ctx, "agents")?.get(sessionId)?.status === "running",
    updatedAt: inspection.events.at(-1)?.time,
  });
  task.eventCount = inspection.events.length;
  task.blank = messages.length === 0;
  task.description = shortText(firstUserText(messages), 4000);
  task.lastMessage = shortText(lastAssistantText(messages), 400);
  return { task, messages, events: inspection.events };
}

async function listTasks(ctx, config, options = {}) {
  const controller = service(ctx, "sessionController");
  const query = service(ctx, "sessionQuery");
  if (!controller || !query) throw new Error("session services are unavailable");
  const signal = AbortSignal.timeout(config.requestTimeoutMs);
  const [value, records] = await Promise.all([
    controller.list({}, signal),
    query.listSessions(signal),
  ]);
  const headerById = new Map(records.map((record) => [String(record.header.id), record.header]));
  const summaries = value.items
    .filter((summary) => options.includeBlank || !summary.blank)
    .filter((summary) => !options.cwd || summary.cwd === options.cwd)
    .sort((left, right) => Number(right.updatedAt ?? 0) - Number(left.updatedAt ?? 0))
    .slice(0, options.limit ?? config.syncLimit);
  const ids = summaries.map((summary) => summary.sessionId);
  const titleById = new Map();
  if (ids.length) {
    try {
      const titles = await query.readTitleSnapshots(ids, signal);
      for (const entry of titles) {
        if (entry.status === "fulfilled" && entry.value.title) {
          titleById.set(String(entry.sessionId), entry.value.title.title);
        }
      }
    } catch {
      // A title read must not hide the task list; the fallback title below is enough.
    }
  }
  return summaries.map((summary) => {
    const id = String(summary.sessionId);
    const header = headerById.get(id) ?? {};
    const task = summarizeTask({
      summary,
      header,
      title: titleById.get(id) ?? `DSH ${id.slice(-8)}`,
      webUrl: taskWebUrl(config.uiUrlTemplate, id),
    });
    task.description = "";
    return task;
  });
}

function createWebhookQueue(ctx, config, log) {
  const secret = ensureSecret(config, log);
  const queue = new Map();
  let disposed = false;

  function post(payload) {
    if (!config.webhookEnabled) return Promise.resolve(false);
    if (!secret) {
      log.warn("codx-junior-sync: webhook skipped because no bridge secret is configured");
      return Promise.resolve(false);
    }
    if (!config.codxApiUrl) {
      log.warn("codx-junior-sync: webhook skipped because codxApiUrl is empty");
      return Promise.resolve(false);
    }
    const body = JSON.stringify(payload);
    const url = new URL(`${config.codxApiUrl}/api/dsh/events`);
    if (config.codxPath) url.searchParams.set("codx_path", config.codxPath);
    return fetch(url, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        accept: "application/json",
        authorization: `Bearer ${secret}`,
        "x-dsh-secret": secret,
        "x-dsh-signature": `sha256=${signBody(secret, body)}`,
        "x-dsh-source": "dsh",
      },
      body,
      signal: AbortSignal.timeout(config.requestTimeoutMs),
    }).then(async (response) => {
      if (response.ok) return true;
      const detail = await response.text().catch(() => "");
      throw new Error(`codx-junior returned ${response.status}: ${shortText(detail, 300)}`);
    });
  }

  function schedule(key, payload, delay = config.debounceMs) {
    if (disposed) return;
    const previous = queue.get(key);
    if (previous?.timer) clearTimeout(previous.timer);
    const attempts = previous?.attempts ?? 0;
    const timer = setTimeout(async () => {
      const current = queue.get(key);
      if (!current) return;
      try {
        await post(payload);
        queue.delete(key);
      } catch (error) {
        const nextAttempts = current.attempts + 1;
        if (nextAttempts > config.webhookRetries || disposed) {
          queue.delete(key);
          log.warn(`codx-junior-sync: webhook failed permanently for ${key}: ${String(error)}`);
          return;
        }
        queue.set(key, {
          payload,
          attempts: nextAttempts,
          timer: setTimeout(() => {
            const latest = queue.get(key);
            if (latest) schedule(key, latest.payload, 1500 * nextAttempts);
          }, 0),
        });
        log.warn(`codx-junior-sync: webhook retry ${nextAttempts}/${config.webhookRetries} for ${key}: ${String(error)}`);
      }
    }, delay);
    timer.unref?.();
    queue.set(key, { payload, attempts, timer });
  }

  function notify(kind, task, extra = {}) {
    if (!task?.id) return;
    schedule(`task:${task.id}`, webhookPayload(kind, task, extra));
  }

  function snapshot(tasks) {
    if (!config.webhookEnabled || !tasks.length) return;
    schedule(
      "snapshot",
      {
        version: 1,
        event: "sync.snapshot",
        sentAt: new Date().toISOString(),
        tasks,
      },
      Math.max(50, config.debounceMs),
    );
  }

  function close() {
    disposed = true;
    for (const entry of queue.values()) {
      if (entry.timer) clearTimeout(entry.timer);
    }
    queue.clear();
  }

  return { notify, snapshot, close, secret };
}

function buildTaskFromSession(ctx, session, config) {
  return taskFromLiveSession(ctx, session, { uiUrlTemplate: config.uiUrlTemplate });
}

export function apply(ctx, rawConfig = {}) {
  const log = ctx.logger ?? console;
  // The Host process cwd is not necessarily the workspace. Prefer the
  // composed working-directory default so the secret file and codx_path land
  // next to the project the user is actually working on.
  let resolvedConfig = rawConfig;
  if (!resolvedConfig.workspaceDir) {
    // The Host cwd is often the profile directory. Prefer a registered
    // workspace that actually owns a codx-junior `.codx` folder.
    let detected;
    try {
      const workspaces = service(ctx, "workspaceRegistry")?.list?.() ?? [];
      const owners = workspaces
        .filter((workspace) => workspace?.path && existsSync(join(workspace.path, ".codx")))
        .sort((left, right) => left.path.length - right.path.length);
      detected = owners[0]?.path ?? workspaces[0]?.path;
    } catch {
      detected = undefined;
    }
    detected ||= service(ctx, "workingDirectory")?.defaultDirectory;
    if (detected) resolvedConfig = { ...resolvedConfig, workspaceDir: detected };
  }
  const config = normalizeConfig(resolvedConfig);
  if (!config.codxPath) config.codxPath = join(config.workspaceDir, ".codx");
  const queue = createWebhookQueue(ctx, config, log);

  // The bridge routes and webhooks share one secret. Requests without it are
  // rejected before any session data is read.
  const authorized = (req) =>
    Boolean(queue.secret) && constantTimeEqual(presentedSecret(req.headers), queue.secret);

  // -------------------------------------------------------------------------
  // Webhooks: the Session log drives codx-junior's mirror tasks.
  // -------------------------------------------------------------------------

  const notifySession = (kind, session, delay) => {
    try {
      const task = buildTaskFromSession(ctx, session, config);
      // A brand-new blank Session has no task yet. It becomes visible after
      // its first prompt (or when codx-junior creates it explicitly).
      if (kind === "session.created" && task.blank) return;
      queue.notify(kind, task);
    } catch (error) {
      log.warn(`codx-junior-sync: cannot build ${kind} payload: ${String(error)}`);
    }
  };

  ctx.effect(() =>
    ctx.on("session/created", (session) => {
      notifySession("session.created", session, 50);
    }),
  );

  ctx.effect(() =>
    ctx.on("session/event", (session, event) => {
      if (!IMPORTANT_EVENTS.has(event?.type)) return;
      notifySession("session.updated", session, config.debounceMs);
    }),
  );

  ctx.effect(() =>
    ctx.on("agent/status", ({ agent }) => {
      const session = agent?.session;
      if (!session) return;
      notifySession("session.updated", session, config.debounceMs);
    }),
  );

  ctx.effect(() =>
    ctx.on("session/disposed", (session) => {
      notifySession("session.disposed", session, 50);
    }),
  );

  if (config.syncOnStart) {
    const timer = setTimeout(async () => {
      try {
        const tasks = await listTasks(ctx, config, { limit: config.syncLimit });
        queue.snapshot(tasks);
      } catch (error) {
        log.warn(`codx-junior-sync: initial snapshot failed: ${String(error)}`);
      }
    }, 1500);
    timer.unref?.();
    ctx.effect(() => () => clearTimeout(timer));
  }

  ctx.effect(() => () => queue.close());

  // -------------------------------------------------------------------------
  // HTTP bridge.
  // -------------------------------------------------------------------------

  async function handleHealth(req, res) {
    const controller = service(ctx, "sessionController");
    const query = service(ctx, "sessionQuery");
    sendJson(res, 200, {
      ok: true,
      name,
      version: 1,
      codxApiUrl: config.codxApiUrl,
      codxPath: config.codxPath,
      board: config.board,
      webhookEnabled: config.webhookEnabled,
      sessionServices: { controller: Boolean(controller), query: Boolean(query) },
    });
  }

  async function handleList(req, res, url) {
    const cwd = url.searchParams.get("cwd") || config.projectPath || undefined;
    const includeBlank = url.searchParams.get("includeBlank") === "1";
    const limit = Number(url.searchParams.get("limit") ?? config.syncLimit);
    const tasks = await listTasks(ctx, config, {
      cwd,
      includeBlank,
      limit: Number.isFinite(limit) ? Math.max(1, Math.min(1000, limit)) : config.syncLimit,
    });
    sendJson(res, 200, { ok: true, tasks });
  }

  async function handleGet(req, res, sessionId) {
    const { task, messages } = await taskFromStoredSession(ctx, sessionId, AbortSignal.timeout(config.requestTimeoutMs));
    task.webUrl = taskWebUrl(config.uiUrlTemplate, sessionId);
    sendJson(res, 200, { ok: true, task, messages, lastSeq: messages.at(-1)?.meta_data?.dsh?.seq ?? null });
  }

  async function handleCreate(req, res) {
    const controller = service(ctx, "sessionController");
    if (!controller) return sendError(res, 503, "unavailable", "sessionController is unavailable");
    const body = await readJson(req);
    const prompt = String(body.prompt ?? body.text ?? "").trim();
    const title = shortText(body.title ?? body.name ?? "", 200) || shortText(prompt, 80) || "DSH task";
    const cwd = String(body.cwd ?? config.projectPath ?? "").trim();
    if (cwd && !isAbsolute(cwd)) return sendError(res, 400, "bad-request", "cwd must be absolute");
    const agentPreset = body.agentPreset ? String(body.agentPreset) : undefined;
    const created = await controller.create({
      cwd: cwd || undefined,
      agentPreset,
    });
    const sessionId = String(created.sessionId);
    try {
      await controller.rename({ sessionId, title });
    } catch (error) {
      log.warn(`codx-junior-sync: created ${sessionId} but could not rename it: ${String(error)}`);
    }
    let promptAccepted = false;
    if (prompt) {
      await controller.prompt({
        sessionId,
        requestId: `codx-${randomBytes(12).toString("hex")}`,
        mode: "queue",
        content: [{ type: "text", text: prompt }],
        clientTimeZone: "UTC",
      });
      promptAccepted = true;
    }
    const { task } = await taskFromStoredSession(ctx, sessionId, AbortSignal.timeout(config.requestTimeoutMs));
    task.webUrl = taskWebUrl(config.uiUrlTemplate, sessionId);
    // An explicit codx-junior creation is a task even before its first prompt.
    task.blank = false;
    if (body.codxTaskId) task.codxTaskId = String(body.codxTaskId);
    if (body.parentSessionId) task.requestedParentSessionId = String(body.parentSessionId);
    sendJson(res, 201, { ok: true, sessionId, promptAccepted, task });
  }

  async function handlePrompt(req, res, sessionId) {
    const controller = service(ctx, "sessionController");
    if (!controller) return sendError(res, 503, "unavailable", "sessionController is unavailable");
    const body = await readJson(req);
    const text = String(body.text ?? body.prompt ?? "").trim();
    if (!text) return sendError(res, 400, "bad-request", "text or prompt is required");
    await controller.prompt({
      sessionId,
      requestId: `codx-${randomBytes(12).toString("hex")}`,
      mode: body.mode === "steer" ? "steer" : "queue",
      content: [{ type: "text", text }],
      clientTimeZone: String(body.clientTimeZone ?? "UTC"),
    });
    sendJson(res, 202, { ok: true, accepted: true, sessionId });
  }

  async function handleCancel(req, res, sessionId) {
    const controller = service(ctx, "sessionController");
    if (!controller) return sendError(res, 503, "unavailable", "sessionController is unavailable");
    controller.cancel({ sessionId });
    sendJson(res, 202, { ok: true, cancelled: true, sessionId });
  }

  async function handleRename(req, res, sessionId) {
    const controller = service(ctx, "sessionController");
    if (!controller) return sendError(res, 503, "unavailable", "sessionController is unavailable");
    const body = await readJson(req);
    const title = shortText(body.title ?? body.name ?? "", 200);
    if (!title) return sendError(res, 400, "bad-request", "title is required");
    const value = await controller.rename({ sessionId, title });
    sendJson(res, 200, { ok: true, title: value.title, seq: value.seq });
  }

  async function route(req, res) {
    const url = new URL(String(req.url), "http://localhost");
    const path = url.pathname;
    if (!path.startsWith(ROUTE_PREFIX)) return sendError(res, 404, "not-found", "unknown route");
    if (!authorized(req)) {
      return sendError(res, 401, "unauthorized", "missing or invalid DSH bridge secret");
    }
    if (req.method === "GET" && (path === `${ROUTE_PREFIX}/health` || path === `${ROUTE_PREFIX}/`)) {
      return handleHealth(req, res);
    }
    if (req.method === "GET" && path === `${ROUTE_PREFIX}/tasks`) {
      return handleList(req, res, url);
    }
    if (req.method === "POST" && path === `${ROUTE_PREFIX}/tasks`) {
      return handleCreate(req, res);
    }
    const match = path.match(/^\/codx-junior\/tasks\/([^/]+)(?:\/(prompt|cancel|title))?$/);
    if (match) {
      const sessionId = decodeURIComponent(match[1]);
      const action = match[2];
      if (!action && req.method === "GET") return handleGet(req, res, sessionId);
      if (action === "prompt" && req.method === "POST") return handlePrompt(req, res, sessionId);
      if (action === "cancel" && req.method === "POST") return handleCancel(req, res, sessionId);
      if (action === "title" && req.method === "POST") return handleRename(req, res, sessionId);
    }
    return sendError(res, 404, "not-found", "unknown route");
  }

  ctx.effect(() =>
    ctx.webServer.register({
      kind: "prefix",
      path: ROUTE_PREFIX,
      handler: async (req, res) => {
        try {
          await route(req, res);
        } catch (error) {
          const status = error?.code === "payload-too-large" ? 413
            : error?.code === "bad-request" ? 400
            : /not found/i.test(String(error?.message)) ? 404
            : 500;
          log.warn(`codx-junior-sync: ${req.method} ${req.url} failed: ${String(error)}`);
          sendError(res, status, status === 500 ? "internal" : "bad-request", String(error?.message ?? error));
        }
      },
    }),
  );

  log.info(
    `codx-junior-sync: bridge at ${ROUTE_PREFIX}, codx-junior ${config.codxApiUrl}${config.codxPath ? ` (${config.codxPath})` : ""}`,
  );
}
