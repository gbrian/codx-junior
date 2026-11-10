import test from "node:test";
import assert from "node:assert/strict";
import { Readable } from "node:stream";
import { createServer } from "node:http";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHmac } from "node:crypto";
import { apply } from "../index.js";

function fakeResponse() {
  return {
    statusCode: 0,
    headers: {},
    body: "",
    setHeader(key, value) {
      this.headers[String(key).toLowerCase()] = value;
    },
    end(chunk) {
      if (chunk !== undefined && chunk !== null) this.body += String(chunk);
    },
  };
}

function fakeRequest({ method = "GET", url = "/", headers = {}, body = null } = {}) {
  const req = Readable.from(body === null ? [] : [Buffer.from(body)]);
  req.method = method;
  req.url = url;
  req.headers = headers;
  return req;
}

function fakeContext({ controller, query, sessionTitle, agents } = {}) {
  const listeners = new Map();
  const routes = [];
  const disposers = [];
  const logger = { info() {}, warn() {}, error() {} };
  const ctx = {
    logger,
    disposers,
    routes,
    listeners,
    effect(fn) {
      const disposer = fn();
      if (typeof disposer === "function") disposers.push(disposer);
      return disposer;
    },
    on(name, listener) {
      const entry = listeners.get(name) ?? [];
      entry.push(listener);
      listeners.set(name, entry);
      return () => {
        listeners.set(name, (listeners.get(name) ?? []).filter((item) => item !== listener));
      };
    },
    emit(name, ...args) {
      for (const listener of listeners.get(name) ?? []) listener(...args);
    },
    get(name) {
      if (name === "sessionController") return controller;
      if (name === "sessionQuery") return query;
      if (name === "sessionTitle") return sessionTitle;
      if (name === "agents") return agents;
      return undefined;
    },
    webServer: {
      register(route) {
        routes.push(route);
        return () => {
          const index = routes.indexOf(route);
          if (index >= 0) routes.splice(index, 1);
        };
      },
    },
  };
  return ctx;
}

function fakeServices() {
  const promptCalls = [];
  const selectedModels = [];
  const controller = {
    async list() {
      return {
        items: [{
          sessionId: "session-live",
          updatedAt: 2_000,
          running: false,
          cwd: "/project",
          origin: "session",
          blank: false,
        }],
      };
    },
    async inspect(id) {
      return {
        meta: {
          version: 4,
          id,
          createdAt: 1_000,
          cwd: "/project",
          isSeeded: false,
          agentPreset: "default",
        },
        inheritedEventCount: 0,
        events: [
          { type: "user/message", seq: 1, time: 1_100, data: { role: "user", content: [{ type: "text", text: "Do the work" }] } },
          { type: "assistant/message", seq: 2, time: 1_200, data: { message: { role: "assistant", content: [{ type: "text", text: "Done" }] } } },
        ],
      };
    },
    async create() {
      return { sessionId: "session-new" };
    },
    async selectModel(request) {
      selectedModels.push(request);
      return { selected: request };
    },
    async rename() {
      return { title: "New task", seq: 2 };
    },
    async prompt(request) {
      promptCalls.push(request);
      return { accepted: true };
    },
    cancel() {},
  };
  const query = {
    async listSessions() {
      return [{ header: { id: "session-live", version: 4, createdAt: 1_000, isSeeded: false, cwd: "/project" } }];
    },
    async readTitleSnapshots(ids) {
      return ids.map((sessionId) => ({
        sessionId,
        status: "fulfilled",
        value: { title: { title: "Live task", eventSeq: 2 } },
      }));
    },
    async readTitle() {
      return { title: "Live task", eventSeq: 2 };
    },
  };
  const sessionTitle = {
    get() {
      return { title: "Live task" };
    },
  };
  return { controller, query, sessionTitle, promptCalls, selectedModels };
}

function routeOf(ctx) {
  return ctx.routes.find((route) => route.path === "/codx-junior");
}

async function callRoute(ctx, request) {
  const response = fakeResponse();
  await routeOf(ctx).handler(request, response);
  return response;
}

test("bridge lists tasks and rejects missing auth", async () => {
  const services = fakeServices();
  const ctx = fakeContext(services);
  apply(ctx, {
    bridgeEnabled: true,
    agentEnabled: false,
    sharedSecret: "test-secret",
    codxApiUrl: "http://127.0.0.1:1",
    projectPath: "/project",
    webhookEnabled: false,
    syncOnStart: false,
  });
  const unauthorized = await callRoute(ctx, fakeRequest({ url: "/codx-junior/tasks" }));
  assert.equal(unauthorized.statusCode, 401);

  const list = await callRoute(ctx, fakeRequest({
    url: "/codx-junior/tasks?cwd=%2Fproject",
    headers: { authorization: "Bearer test-secret" },
  }));
  assert.equal(list.statusCode, 200);
  const payload = JSON.parse(list.body);
  assert.equal(payload.tasks.length, 1);
  assert.equal(payload.tasks[0].id, "session-live");
  assert.equal(payload.tasks[0].title, "Live task");
  for (const dispose of ctx.disposers) dispose();
});

test("bridge gets live messages and creates/prompts a session", async () => {
  const services = fakeServices();
  const ctx = fakeContext(services);
  apply(ctx, {
    bridgeEnabled: true,
    agentEnabled: false,
    sharedSecret: "test-secret",
    codxApiUrl: "http://127.0.0.1:1",
    webhookEnabled: false,
    syncOnStart: false,
  });
  const detail = await callRoute(ctx, fakeRequest({
    url: "/codx-junior/tasks/session-live",
    headers: { authorization: "Bearer test-secret" },
  }));
  assert.equal(detail.statusCode, 200);
  const detailPayload = JSON.parse(detail.body);
  assert.equal(detailPayload.messages.length, 2);
  assert.equal(detailPayload.messages[0].content, "Do the work");
  assert.equal(detailPayload.messages[1].content, "Done");
  assert.equal(detailPayload.lastSeq, 2);

  const created = await callRoute(ctx, fakeRequest({
    method: "POST",
    url: "/codx-junior/tasks",
    headers: { authorization: "Bearer test-secret" },
    body: JSON.stringify({ title: "New task", prompt: "Please run" }),
  }));
  assert.equal(created.statusCode, 201, created.body);
  const createdPayload = JSON.parse(created.body);
  assert.equal(createdPayload.sessionId, "session-new");
  assert.equal(services.promptCalls.length, 1);
  assert.equal(services.promptCalls[0].sessionId, "session-new");
  assert.equal(services.promptCalls[0].content[0].text, "Please run");
  for (const dispose of ctx.disposers) dispose();
});

test("bridge posts signed task webhooks to codx-junior", async () => {
  const received = [];
  const server = createServer((req, res) => {
    let body = "";
    req.on("data", (chunk) => { body += chunk; });
    req.on("end", () => {
      received.push({ url: req.url, headers: req.headers, body });
      res.statusCode = 200;
      res.setHeader("content-type", "application/json");
      res.end('{"ok":true}');
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  try {
    const services = fakeServices();
    const ctx = fakeContext(services);
    apply(ctx, {
      bridgeEnabled: true,
      agentEnabled: false,
      sharedSecret: "hook-secret",
      codxApiUrl: `http://127.0.0.1:${port}`,
      codxPath: "/project/.codx",
      webhookEnabled: true,
      syncOnStart: false,
      debounceMs: 5,
    });
    const session = {
      id: "session-live",
      seq: 3,
      header: { version: 4, id: "session-live", createdAt: 1_000, isSeeded: false, cwd: "/project" },
      snapshotEvents() {
        return [{ type: "user/message", seq: 1, time: 1_100, data: { role: "user", content: [{ type: "text", text: "Do it" }] } }];
      },
      eventAt(seq) {
        return seq === 2 ? { time: 1_200 } : undefined;
      },
    };
    for (const listener of ctx.listeners.get("session/created") ?? []) listener(session);
    const deadline = Date.now() + 2000;
    while (received.length === 0 && Date.now() < deadline) {
      await new Promise((resolve) => setTimeout(resolve, 10));
    }
    assert.equal(received.length, 1);
    const request = received[0];
    assert.match(request.url, /^\/api\/dsh\/events\?codx_path=%2Fproject%2F\.codx$/);
    assert.equal(request.headers.authorization, "Bearer hook-secret");
    const expected = "sha256=" + createHmac("sha256", "hook-secret").update(request.body).digest("hex");
    assert.equal(request.headers["x-dsh-signature"], expected);
    const payload = JSON.parse(request.body);
    assert.equal(payload.event, "session.created");
    assert.equal(payload.task.id, "session-live");
    assert.equal(payload.task.title, "Live task");
    for (const dispose of ctx.disposers) dispose();
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});

test("bridge suppresses blank session creation notifications", async () => {
  let calls = 0;
  const server = createServer((req, res) => {
    calls += 1;
    res.statusCode = 200;
    res.end("{}");
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  try {
    const ctx = fakeContext({
      ...fakeServices(),
      sessionTitle: { get() { return undefined; } },
    });
    apply(ctx, {
      bridgeEnabled: true,
      agentEnabled: false,
      sharedSecret: "hook-secret",
      codxApiUrl: `http://127.0.0.1:${port}`,
      webhookEnabled: true,
      syncOnStart: false,
      debounceMs: 5,
    });
    const blank = {
      id: "session-blank",
      seq: 0,
      header: { version: 4, id: "session-blank", createdAt: 1_000, isSeeded: false },
      snapshotEvents() { return []; },
      eventAt() { return undefined; },
    };
    for (const listener of ctx.listeners.get("session/created") ?? []) listener(blank);
    await new Promise((resolve) => setTimeout(resolve, 50));
    assert.equal(calls, 0);
    for (const dispose of ctx.disposers) dispose();
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
});


async function waitFor(predicate, timeoutMs = 4000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, 10));
  }
  throw new Error("timed out waiting for condition");
}

test("agent mode registers, heartbeats, executes a command and posts events", async () => {
  const workspace = mkdtempSync(join(tmpdir(), "dsh-agent-"));
  const received = [];
  let commandDelivered = false;
  const server = createServer((req, res) => {
    let body = "";
    req.on("data", (chunk) => { body += chunk; });
    req.on("end", () => {
      const url = new URL(req.url, "http://localhost");
      received.push({ path: url.pathname, search: url.search, headers: req.headers, body });
      const send = (status, payload) => {
        res.statusCode = status;
        res.setHeader("content-type", "application/json");
        res.end(payload === undefined ? "" : JSON.stringify(payload));
      };
      if (url.pathname === "/api/dsh/agent/register") {
        return send(200, {
          ok: true,
          instance: { id: "inst-test", name: "Test Host", status: "online" },
          conf: { board: "DSH" },
        });
      }
      if (url.pathname === "/api/dsh/agent/heartbeat") {
        return send(200, { ok: true });
      }
      if (url.pathname === "/api/dsh/agent/commands") {
        if (!commandDelivered) {
          commandDelivered = true;
          return send(200, {
            ok: true,
            commands: [{ id: "cmd-ping", type: "ping", payload: {} }],
          });
        }
        return send(204);
      }
      if (url.pathname.startsWith("/api/dsh/agent/commands/") && url.pathname.endsWith("/result")) {
        return send(200, { ok: true, accepted: true });
      }
      if (url.pathname === "/api/dsh/agent/events") {
        return send(200, { ok: true });
      }
      return send(404, { detail: "unknown" });
    });
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address();
  try {
    const services = fakeServices();
    const ctx = fakeContext(services);
    apply(ctx, {
      agentEnabled: true,
      bridgeEnabled: false,
      token: "agent-secret",
      instanceId: "inst-test",
      workspaceDir: workspace,
      codxPath: join(workspace, ".codx"),
      codxApiUrl: `http://127.0.0.1:${port}`,
      heartbeatMs: 1000,
      pollWaitMs: 500,
      debounceMs: 10,
      syncOnStart: false,
    });

    await waitFor(() => received.some((request) => request.path === "/api/dsh/agent/register"));
    await waitFor(() => received.some((request) => request.path.endsWith("/result")));
    const register = received.find((request) => request.path === "/api/dsh/agent/register");
    assert.equal(register.headers.authorization, "Bearer agent-secret");
    assert.match(register.search, /codx_path=/);
    assert.equal(JSON.parse(register.body).instance_id, "inst-test");
    const result = received.find((request) => request.path.endsWith("/result"));
    assert.equal(JSON.parse(result.body).ok, true);
    assert.equal(JSON.parse(result.body).instance_id, "inst-test");

    const session = {
      id: "session-agent",
      seq: 3,
      header: { version: 4, id: "session-agent", createdAt: 1_000, isSeeded: false },
      snapshotEvents() { return []; },
      eventAt() { return { time: 1_200 }; },
    };
    for (const listener of ctx.listeners.get("session/created") ?? []) listener(session);
    await waitFor(() => received.some((request) => request.path === "/api/dsh/agent/events"));
    const event = received.find((request) => request.path === "/api/dsh/agent/events");
    const eventPayload = JSON.parse(event.body);
    assert.equal(eventPayload.instance_id, "inst-test");
    assert.equal(eventPayload.task.id, "session-agent");
    for (const dispose of ctx.disposers) dispose();
  } finally {
    await new Promise((resolve) => server.close(resolve));
    rmSync(workspace, { recursive: true, force: true });
  }
});

test("create applies a codx-junior model selection", async () => {
  const workspace = mkdtempSync(join(process.cwd(), ".tmp-plugin-model-"));
  try {
    const services = fakeServices();
    const ctx = fakeContext(services);
    apply(ctx, {
      bridgeEnabled: true,
      agentEnabled: false,
      sharedSecret: "test-secret",
      codxApiUrl: "http://127.0.0.1:1",
      workspaceDir: workspace,
      workspaceRoot: workspace,
      webhookEnabled: false,
      syncOnStart: false,
    });
    const created = await callRoute(ctx, fakeRequest({
      method: "POST",
      url: "/codx-junior/tasks",
      headers: { authorization: "Bearer test-secret" },
      body: JSON.stringify({
        title: "Model task",
        prompt: "Run",
        cwd: workspace,
        model: {
          name: "codx-fast",
          provider: "deepseek-official",
          model: "deepseek-flash",
        },
      }),
    }));
    assert.equal(created.statusCode, 201, created.body);
    assert.deepEqual(services.selectedModels[0], {
      sessionId: "session-new",
      provider: "deepseek-official",
      model: "deepseek-flash",
    });
    const payload = JSON.parse(created.body);
    assert.equal(payload.modelSelection.applied, true);
    assert.equal(payload.task.model, "codx-fast");
    for (const dispose of ctx.disposers) dispose();
  } finally {
    rmSync(workspace, { recursive: true, force: true });
  }
});

test("create rejects a cwd outside the configured workspace", async () => {
  const workspace = mkdtempSync(join(process.cwd(), ".tmp-plugin-sandbox-"));
  try {
    const services = fakeServices();
    const ctx = fakeContext(services);
    apply(ctx, {
      bridgeEnabled: true,
      agentEnabled: false,
      sharedSecret: "test-secret",
      codxApiUrl: "http://127.0.0.1:1",
      workspaceDir: workspace,
      workspaceRoot: workspace,
      webhookEnabled: false,
      syncOnStart: false,
    });
    const denied = await callRoute(ctx, fakeRequest({
      method: "POST",
      url: "/codx-junior/tasks",
      headers: { authorization: "Bearer test-secret" },
      body: JSON.stringify({ title: "Escape", prompt: "Run", cwd: "/" }),
    }));
    assert.equal(denied.statusCode, 400, denied.body);
    assert.match(denied.body, /outside the configured workspace/);
    for (const dispose of ctx.disposers) dispose();
  } finally {
    rmSync(workspace, { recursive: true, force: true });
  }
});
