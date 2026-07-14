# Static Site Workspace Docker Compose Template

## Overview

This file is a Jinja2 template used to generate a `docker-compose.yaml` configuration for static site workspaces. It dynamically renders service definitions based on workspace configuration, project paths, environment variables, and resource constraints.

---

## Service: `app`

The core service defined in this template is named `app`. Its configuration is driven entirely by the workspace object and associated projects.

### Image

```yaml
image: {{ workspace.env.get('IMAGE', 'node:22-slim') }}
```

The container image defaults to `node:22-slim` but can be overridden by setting the `IMAGE` key in the workspace environment variables.

### Container Name

```yaml
container_name: codx-ws-{{ workspace.slug }}-app
```

The container is named using the workspace slug to ensure uniqueness across multiple workspaces.

### Working Directory

```yaml
working_dir: {{ projects[0].container_path if projects else '/home/projects' }}
```

The working directory is set to the container path of the first project. If no projects are defined, it falls back to `/home/projects`.

### Command

```yaml
command: {{ workspace.env.get('COMMAND', 'sh -c "npm install && npm run dev -- --host"') }}
```

The startup command defaults to running `npm install` followed by `npm run dev -- --host`. This can be overridden via the `COMMAND` environment variable in the workspace configuration.

### Restart Policy

```yaml
restart: unless-stopped
```

The service is configured to restart automatically unless explicitly stopped.

### Shared Memory

```yaml
shm_size: '{{ workspace.resources.shm_size }}'
```

The shared memory size is sourced from `workspace.resources.shm_size`.

---

## Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '{{ workspace.resources.cpus }}'
      memory: {{ workspace.resources.memory }}
```

Resource limits are conditionally included only when `workspace.resources.cpus` or `workspace.resources.memory` are defined. Each limit is rendered independently — CPU limits require a non-empty `cpus` value and memory limits require a non-empty `memory` value.

---

## Volumes

```yaml
volumes:
{% for project in projects %}
  - {{ project.host_path }}:{{ project.container_path }}
{% endfor %}
```

Each project in the `projects` list contributes a volume mount, mapping the host path to the container path. This allows project files to be accessible inside the container.

---

## Environment Variables

```yaml
environment:
{% for key, value in workspace.env.items() %}
  - {{ key }}={{ value }}
{% endfor %}
```

All key-value pairs defined in `workspace.env` are passed as environment variables to the container. This includes any overrides such as `IMAGE` or `COMMAND`.

---

## Labels (Traefik Integration)

```yaml
labels:
{% for app in workspace.apps %}
{% for label in traefik_labels(workspace, app) %}
  - {{ label }}
{% endfor %}
{% endfor %}
```

Traefik routing labels are dynamically generated for each app associated with the workspace. The `traefik_labels` function is called with the workspace and each app to produce the appropriate label set.

---

## Networks

```yaml
networks:
  workspace:
    name: {{ workspace.network_name }}
```

The service is connected to a network named after `workspace.network_name`. This network is defined at the bottom of the template and ensures containers within the same workspace can communicate.

---

## Template Variables Reference

| Variable | Description |
|---|---|
| `workspace.slug` | Unique identifier used in naming the container |
| `workspace.env` | Dictionary of environment variables for the workspace |
| `workspace.resources.shm_size` | Shared memory size allocation |
| `workspace.resources.cpus` | Optional CPU limit |
| `workspace.resources.memory` | Optional memory limit |
| `workspace.apps` | List of apps for Traefik label generation |
| `workspace.network_name` | Name of the Docker network |
| `projects` | List of project objects with `host_path` and `container_path` |