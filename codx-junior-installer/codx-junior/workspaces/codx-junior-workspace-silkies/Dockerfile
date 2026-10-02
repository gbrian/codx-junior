FROM ghcr.io/selkies-project/selkies-gstreamer/gst-py-example:latest-ubuntu22.04

USER root

# Build-time arguments for user/group IDs
ARG USER_ID=1001
ARG GROUP_ID=1001

# 1. Install Python (Mandatory for the systemctl replacement)
RUN apt-get update && apt-get install -y \
    python3 \
    wget \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# 2. Create codx-junior group and user with specified IDs
RUN groupadd --gid ${GROUP_ID} codx-junior || true \
    && useradd --uid ${USER_ID} --gid ${GROUP_ID} --create-home --shell /bin/bash codx-junior \
    && echo "codx-junior ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers \
    && mkdir -p /home/codx-junior-projects/codx-junior \
    && chown -R ${USER_ID}:${GROUP_ID} /home/codx-junior-projects

# 3. Overwrite /usr/bin/systemctl with the replacement script
RUN wget https://githubusercontent.com -O /usr/bin/systemctl \
    && chmod +x /usr/bin/systemctl

# Now you can safely install tools that require systemctl
# RUN apt-get update && apt-get install -y some-service-tool

ENTRYPOINT ["/usr/bin/systemctl", "init"]