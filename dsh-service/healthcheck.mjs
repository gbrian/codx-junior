#!/usr/bin/env node
/**
 * Container healthcheck for the dsh web listener.
 *
 * DSH binds one concrete interface address, never a wildcard, so 127.0.0.1 is
 * not necessarily listening. Resolve the same first non-loopback address the
 * entrypoint uses, then probe `/`. An unauthenticated request is expected to
 * return 401; anything below 500 proves the listener and auth fence are up.
 */
import { networkInterfaces } from "node:os";

const port = process.env.DSH_PORT || "3080";
let host = process.env.DSH_HOST;

if (!host) {
  const addrs = Object.values(networkInterfaces()).flat().filter(Boolean);
  const pick =
    addrs.find((entry) => !entry.internal && entry.family === "IPv4") ??
    addrs.find((entry) => !entry.internal && entry.family === "IPv6");
  if (!pick) {
    console.error("dsh-healthcheck: no non-loopback address is available");
    process.exit(1);
  }
  host = pick.address;
}

const authority = host.includes(":") ? `[${host}]` : host;
const url = `http://${authority}:${port}/`;

try {
  const response = await fetch(url, {
    redirect: "manual",
    signal: AbortSignal.timeout(4000),
  });
  const healthy = [200, 303, 307, 308, 401, 403].includes(response.status);
  if (!healthy) {
    console.error(`dsh-healthcheck: GET ${url} returned ${response.status}`);
  }
  process.exit(healthy ? 0 : 1);
} catch (error) {
  console.error(`dsh-healthcheck: GET ${url} failed: ${error.message}`);
  process.exit(1);
}
