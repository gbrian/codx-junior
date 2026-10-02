# Workspaces

Workspaces are dev containers managed by codx-junior. They run your projects with Docker Compose and publish their apps through Traefik, so the whole team works from the browser.

![Desktop](/images/NOV2025/codx-junior-desktop.png)

## Templates

| Template | What it creates |
| --- | --- |
| `dev-stack` | A `devbox` container running with Sysbox: systemd and its own Docker daemon, without `--privileged` or the host Docker socket. Good for full stack development. |
| `static-site` | An `app` container (default image `node:22-slim`) that runs `npm install && npm run dev`. The image and command can be changed with the `IMAGE` and `COMMAND` variables. |
| `custom` | Your own `docker-compose.yaml`. codx-junior can generate the files with AI from a description. |

## Settings

* **Projects** mounted into the workspace.
* **Users** allowed to use it (empty means everyone).
* **Apps**: name, icon, path, port and scheme. Each app is published under a path on your domain and protected by codx-junior's login.
* **Environment variables** and **resources** (CPUs, memory, shared memory).
* **Sysbox** on or off.

The workspace files (compose file, Dockerfile, env) can be edited from the UI. You can start, stop and restart workspaces, follow their status (`stopped`, `starting`, `running`, `error`) and read their logs.

## Default apps

The default workspace includes:

* **Coder**: VS Code in the browser, with extensions and Docker support.
* **Desktop**: a virtual desktop (noVNC or Kasm VNC) to test your app like a user.
* **LiteLLM**: the model manager UI.
* **Traefik**: the proxy dashboard.

Apps from all your workspaces appear in the home screen and in the workspaces menu, and open in tabs or windows on the [desktop](/features/development-tools).
