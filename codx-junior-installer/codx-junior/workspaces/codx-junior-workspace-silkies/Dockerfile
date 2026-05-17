FROM ghcr.io/selkies-project/selkies-gstreamer/gst-py-example:latest-ubuntu22.04

USER root

# 1. Install Python (Mandatory for the systemctl replacement)
RUN apt-get update && apt-get install -y \
    python3 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 2. Overwrite /usr/bin/systemctl with the replacement script
RUN wget https://githubusercontent.com -O /usr/bin/systemctl \
    && chmod +x /usr/bin/systemctl

# Now you can safely install tools that require systemctl
# RUN apt-get update && apt-get install -y some-service-tool

ENTRYPOINT ["/usr/bin/systemctl", "init"]