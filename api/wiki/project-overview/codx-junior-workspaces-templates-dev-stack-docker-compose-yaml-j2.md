# Dev Stack Docker Compose Template

## Overview

This file is a Jinja2 template used to generate a `docker-compose.yaml` configuration for a development workspace environment. It defines the container infrastructure for a self-contained developer box (`devbox`) with its own Docker daemon, networking, and project volume mounts.

---

## Services

### `devbox`

The primary and only service defined in this template. It represents an isolated development container built from the local context.

**Key properties:**

- **Container name**: Dynamically generated using the workspace slug:
  ```
  codx-ws-{{ workspace.slug }}-devbox
  ```
- **Runtime**: Uses `sysbox-runc`, which enables systemd and an inner Docker daemon without requiring `--privileged` mode or access to the host `docker.sock`.
- **Restart policy**: `unless-stopped` — the container restarts automatically unless explicitly stopped.
- **Shared memory size**: Configurable via `workspace.resources.shm_size`.

---

## Volumes

### Mount Points

The `devbox` service mounts volumes from two sources:

1. **Project volumes** — dynamically generated from the `projects` list:
   ```yaml
   - {{ project.host_path }}:{{ project.container_path }}
   ```
   Each project defines its own host-to-container path mapping.

2. **Named volumes**:
   - `workspace-docker` → mounted at `/var/lib/docker` — persists the inner Docker daemon's data.
   - `workspace-home` → mounted at `/home/dev` — persists the developer's home directory.

### Top-level Volume Declarations

```yaml
volumes:
  workspace-docker:
  workspace-home:
```

Both are declared as named volumes without additional configuration.

---

## Environment Variables

Environment variables are injected into the `devbox` container from the workspace configuration:

```yaml
environment:
  - {{ key }}={{ value }}
```

All key-value pairs defined in `workspace.env` are passed through to the container.

---

## Labels (Traefik Integration)

Labels are dynamically generated for each application associated with the workspace using a `traefik_labels` helper function:

```yaml
labels:
  - {{ label }}
```

For each `app` in `workspace.apps`, the `traefik_labels(workspace, app)` function produces the relevant Traefik routing labels, enabling reverse proxy integration per application.

---

## Networking

The `devbox` service is connected to a single network named `workspace`:

```yaml
networks:
  workspace:
    name: {{ workspace.network_name }}
```

The actual network name is resolved from `workspace.network_name`, allowing each workspace to operate on its own isolated named network.

---

## Template Variables Reference

| Variable | Description |
|---|---|
| `workspace.slug` | Unique identifier used in the container name |
| `workspace.resources.shm_size` | Shared memory size for the container |
| `workspace.env` | Dictionary of environment variables |
| `workspace.apps` | List of applications for Traefik label generation |
| `workspace.network_name` | Name of the Docker network |
| `projects` | List of project objects with `host_path` and `container_path` |
| `traefik_labels(workspace, app)` | Helper function returning Traefik routing labels |