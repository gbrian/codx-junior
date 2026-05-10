FROM kasmweb/ubuntu-noble-desktop:1.17.0
USER root

# Install Python 3 and other dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    curl \
    sudo \
    ssl-cert \
    && rm -rf /var/lib/apt/lists/*

# Download the replacement script and replace the original systemctl
RUN wget https://raw.githubusercontent.com/gdraheim/docker-systemctl-replacement/master/files/docker/systemctl3.py \
    -O /usr/local/bin/systemctl-shim \
    && chmod +x /usr/local/bin/systemctl-shim \
    && mv /usr/bin/systemctl /usr/bin/systemctl.original \
    && ln -s /usr/local/bin/systemctl-shim /usr/bin/systemctl

EXPOSE 9080
EXPOSE 6901

USER 1000