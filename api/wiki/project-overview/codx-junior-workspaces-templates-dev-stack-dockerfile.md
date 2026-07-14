# Dev Stack Dockerfile Overview

## Purpose

This Dockerfile builds a containerized development environment that runs **systemd as PID 1** alongside a full **Docker daemon** inside the container. It is designed to be used with **Sysbox**, a container runtime that enables running system-level workloads (like systemd and nested Docker) safely inside containers.

---

## Base Image

The image is built on top of **Ubuntu 24.04**:

```
FROM ubuntu:24.04
```

---

## Installed Components

The following components are installed during the build:

| Component | Purpose |
|---|---|
| `systemd`, `systemd-sysv` | Init system, runs as PID 1 inside the container |
| `curl`, `ca-certificates` | Utilities for downloading scripts and handling TLS |
| `git` | Version control tooling |
| `sudo` | Privilege escalation for the dev user |
| Docker (via get.docker.com) | Full Docker daemon running inside the container |
| code-server (via code-server.dev) | Browser-based VS Code IDE |

Installation is handled in a single `RUN` layer to minimize image size, followed by a cleanup of the apt cache:

```
&& apt-get clean && rm -rf /var/lib/apt/lists/*
```

---

## User Configuration

A non-root user named **`dev`** is created with the following properties:

- Default shell: `/bin/bash`
- Group memberships: `docker`, `sudo`
- Passwordless sudo access is granted via:

```
dev ALL=(ALL) NOPASSWD:ALL
```

This allows the `dev` user to perform administrative tasks without password prompts.

---

## code-server Service

`code-server` is configured as a **systemd service** so it starts automatically when the container boots.

Key service configuration details:

- **Runs as:** `dev` user
- **Bind address:** `0.0.0.0:9080` — bound to all interfaces to support routing via **Traefik**
- **Authentication:** None (`--auth none`)
- **Restart policy:** Always

The service unit file is written to `/etc/systemd/system/code-server.service` and enabled at boot.

---

## Enabled systemd Services

Both of the following services are enabled to start automatically via systemd:

- `code-server`
- `docker`

This is achieved with:

```
systemctl enable code-server docker
```

---

## Entrypoint

The container entrypoint is set to the systemd init process:

```
ENTRYPOINT ["/sbin/init"]
```

This means systemd manages all processes inside the container, including starting Docker and code-server on boot.

---

## Architecture Notes

- **Sysbox** is required as the container runtime to support running systemd and a nested Docker daemon safely.
- **Traefik** is referenced as the expected reverse proxy for routing traffic to code-server on port `9080`.
- The design enables a fully self-contained development environment with IDE access and Docker capabilities, all managed by systemd.