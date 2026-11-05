# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim

ARG DSH_VERSION=0.2.1-rc.5
ARG DSH_UID=1000
ARG DSH_GID=1000

LABEL org.opencontainers.image.title="dsh-service" \
      org.opencontainers.image.description="DeepSeek Harness web service behind Traefik" \
      org.opencontainers.image.version="${DSH_VERSION}"

ENV DEBIAN_FRONTEND=noninteractive \
    NODE_ENV=production \
    NPM_CONFIG_UPDATE_NOTIFIER=false \
    DSH_HOME=/home/dsh/.dsh \
    DSH_PORT=3080 \
    DSH_VERSION=${DSH_VERSION}

# git/ripgrep/ssh are used by the agent's tools; curl is useful for debugging
# and for the healthcheck override; tini is PID 1 so signals reach dsh.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      git \
      openssh-client \
      ripgrep \
      tini \
 && rm -rf /var/lib/apt/lists/*

RUN npm install --global --no-fund --no-audit "@deepseek-ai/dsh@${DSH_VERSION}" \
 && npm cache clean --force

# The official node image ships a `node` user at 1000:1000. Replace it so the
# container identity can be built to match the host owner of ./workspace.
RUN userdel --remove node 2>/dev/null || true \
 && groupdel node 2>/dev/null || true \
 && groupadd --gid "${DSH_GID}" dsh \
 && useradd --uid "${DSH_UID}" --gid dsh --create-home --shell /bin/bash dsh \
 && install -d -m 0700 -o dsh -g dsh /home/dsh/.dsh \
 && install -d -m 0755 -o dsh -g dsh /workspace

COPY --chmod=0755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY --chmod=0755 healthcheck.mjs /usr/local/bin/dsh-healthcheck.mjs

USER dsh
WORKDIR /workspace

# DSH's web listener is only reachable on the internal Docker network. Do not
# publish this port on the host; Traefik is the only intended client.
EXPOSE 3080

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/docker-entrypoint.sh"]
CMD []
