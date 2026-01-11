# Use the official Docker-in-Docker image as base
FROM docker:27-dind

# Install bash if your scripts need it
RUN apk add --no-cache bash

# Create the custom initialization directory similar to LS.io
RUN mkdir -p /custom-cont-init.d

# Copy your custom entrypoint wrapper
COPY codx-junior-dind/entrypoint-wrapper.sh /usr/local/bin/entrypoint-wrapper.sh
RUN chmod +x /usr/local/bin/entrypoint-wrapper.sh

WORKDIR /codx-junior-dind
COPY codx-junior/docker-compose.yaml /codx-junior-dind

EXPOSE 80
EXPOSE 443

# Use the wrapper as the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint-wrapper.sh"]
