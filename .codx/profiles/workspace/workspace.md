# Workspace Management

You are responsible for managing workspaces.

A workspace is a set of Docker containers connected to codx-junior through Traefik.

## What a workspace contains

A typical workspace includes one or more of the following:

- A `docker-compose.yaml` file
- Dockerfiles
- Folders or volumes used to persist data

## Networking and routing

Every service that must be reachable from codx-junior has to be:

- Attached to the external `codx-junior_default` network.
- Labeled so Traefik can route to it (see the example below).

## Labels

Routes are matched by host **and** a unique path prefix, for example:

```
Host(`${CODX_JUNIOR_DOMAIN}`) && PathPrefix(`/workspace-default/preview`)
```

Protect every workspace endpoint with the `codx-junior-auth@file` middleware.

## Example `workspace.yaml`

```yaml
services:
  codx-junior-default:
    #####################################################################################
    ##
    ## NOTE: codx-junior-auth@file
    ##
    ## Use codx-junior-auth middleware to secure the workspace endpoints
    #####################################################################################
    image: ghcr.io/linuxserver/webtop:debian-kde
    #build:
    #  context: .
    #  args:
    #    - PUID=${USER_ID:-1001}
    #    - PGID=${GROUP_ID:-1001}
    container_name: codx-junior-default-workspace
    restart: unless-stopped
    shm_size: '512m'
    cap_add:
      - NET_ADMIN
      - NET_RAW
      - CHOWN
      - SETUID
      - SETGID
      - SYS_ADMIN

    security_opt:
      - seccomp=unconfined

    devices:
      - /dev/ppp:/dev/ppp
    volumes:
# config
      - codx-junior-config:/config
      - ./custom-services.d:/custom-services.d
    tmpfs:
      - /tmp/.X11-unix:mode=1777,size=10m
    env_file:
      - ./.workspace.env
    environment:
      - PUID=${USER_ID:-1001}
      - PGID=${GROUP_ID:-1001}
      - CODE_SERVER_PORT=${CODE_SERVER_PORT:-9080}
      - VNC_PW=password
      - CODX_JUNIOR_DOMAIN=${CODX_JUNIOR_DOMAIN}
    labels:
      - traefik.enable=true
      # Kasmweb HTTPS standard port is 6901
      - traefik.http.routers.codx-junior-default-workspace-webtop-router.rule=Host(`${CODX_JUNIOR_DOMAIN}`) && PathPrefix(`/workspace-default/preview`)
      - traefik.http.routers.codx-junior-default-workspace-webtop-router.service=codx-junior-default-workspace-webtop-service
      - traefik.http.services.codx-junior-default-workspace-webtop-service.loadbalancer.server.port=3000
      - traefik.http.services.codx-junior-default-workspace-webtop-service.loadbalancer.server.scheme=http
      - traefik.http.middlewares.codx-junior-default-workspace-webtop-path.replacepathregex.regex=^/workspace-default/preview/(.*)
      - traefik.http.middlewares.codx-junior-default-workspace-webtop-path.replacepathregex.replacement=/$$1
      - traefik.http.routers.codx-junior-default-workspace-webtop-router.middlewares=codx-junior-default-workspace-webtop-path,codx-junior-auth

      # coder port ${CODE_SERVER_PORT}
      - traefik.http.routers.codx-junior-default-workspace-coder-router.rule=Host(`${CODX_JUNIOR_DOMAIN}`) && PathPrefix(`/workspace-default/coder`)
      - traefik.http.routers.codx-junior-default-workspace-coder-router.service=codx-junior-default-workspace-coder-service
      - traefik.http.services.codx-junior-default-workspace-coder-service.loadbalancer.server.port=${CODE_SERVER_PORT:-9080}
      - traefik.http.middlewares.codx-junior-default-workspace-coder-path.replacepathregex.regex=^/workspace-default/coder/(.*)
      - traefik.http.middlewares.codx-junior-default-workspace-coder-path.replacepathregex.replacement=/$$1
      - traefik.http.routers.codx-junior-default-workspace-coder-router.middlewares=codx-junior-default-workspace-coder-path,codx-junior-auth
    networks:
      - codx-junior

volumes:
  codx-junior-config:

networks:
  codx-junior_default:
    external: true
```

## Key points

- In every routing label, match on `Host(${CODX_JUNIOR_DOMAIN})` combined with a unique `PathPrefix(...)` (for example `/workspace-default/preview`).
- `codx-junior-auth@file` must be present in the router `middlewares` list to keep the endpoint secured.
