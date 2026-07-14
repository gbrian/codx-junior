# Systemd + Docker inside, powered by Sysbox
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        systemd systemd-sysv curl ca-certificates git sudo \
    && curl -fsSL https://get.docker.com | sh \
    && curl -fsSL https://code-server.dev/install.sh | sh \
    && useradd -m -s /bin/bash -G docker,sudo dev \
    && echo "dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# code-server as a systemd service, bound to all interfaces for Traefik routing
RUN printf '[Unit]\nDescription=code-server\nAfter=network.target\n\n[Service]\nUser=dev\nEnvironment=HOME=/home/dev\nExecStart=/usr/bin/code-server --bind-addr 0.0.0.0:9080 --auth none\nRestart=always\n\n[Install]\nWantedBy=multi-user.target\n' \
        > /etc/systemd/system/code-server.service \
    && systemctl enable code-server docker

ENTRYPOINT ["/sbin/init"]