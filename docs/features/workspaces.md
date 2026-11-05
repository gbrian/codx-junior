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

## Custom Traefik rules

Besides the Traefik labels generated for workspace apps, admins can define custom routes from **Settings → Global settings → Traefik** and **Settings → Project settings → Traefik**. Both screens use the same editor, but they write to different stores:

| Scope | Stored in | Travels with |
| --- | --- | --- |
| Global | `GlobalSettings.traefik_rules` | the codx-junior installation |
| Project | `.codx/project.json` (`CODXJuniorSettings.traefik_rules`) | the project, so it keeps its routes in another codx-junior instance |

The merged list shows three kinds of routes:

* **Workspace**: generated from the workspace apps. Container apps are still routed by their Docker labels; external-URL apps are published by the HTTP provider.
* **Global**: custom rules available to every project.
* **Project**: custom rules owned by one project.

A custom rule can target:

* a **workspace app** (it reuses the label-defined Traefik service, or the external URL service);
* a **running container** (`http://<container-name>:<port>`, with Traefik and the container sharing a Docker network);
* an **external URL**.

Each rule has a full Traefik rule expression (for example ``Host(`app.example.com`) && PathPrefix(`/app`)``), an optional strip-prefix middleware, the auth middleware, extra middlewares, entrypoints and a priority. Every enabled rule is published through `GET /api/traefik/config`, which Traefik polls every 10 seconds.

Project scope is organizational: Traefik is a single proxy, so every enabled global and project rule is published together. The project scope decides where the rule is stored and edited, not whether it is active.

The auth middleware lives in the Docker provider, so HTTP-provider routes reference `codx-junior-auth@docker`. Set `CODX_JUNIOR_TRAEFIK_AUTH_MIDDLEWARE` when the middleware has a different name (or set it to an empty value to disable it).

If a rule appears in the preview but not in Traefik's dashboard/API, check the Traefik container's HTTP provider endpoint. It must use the internal Docker service name:

```text
http://codx-junior-api:19980/api/traefik/config
```

Using the public `CODX_JUNIOR_DOMAIN` here usually fails because port `19980` is not exposed publicly. Recreate the Traefik container after changing the installer compose or `traefik/traefik.yaml`.

## Default apps

The default workspace includes:

* **Coder**: VS Code in the browser, with extensions and Docker support.
* **Desktop**: a virtual desktop (noVNC or Kasm VNC) to test your app like a user.
* **LiteLLM**: the model manager UI.
* **Traefik**: the proxy dashboard.

Apps from all your workspaces appear in the home screen and in the workspaces menu, and open in tabs or windows on the [desktop](/features/development-tools).
