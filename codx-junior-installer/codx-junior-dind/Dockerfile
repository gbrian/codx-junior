# Use the official Docker-in-Docker image as base (tracks the latest Docker release)
FROM docker:dind

# Install bash (used by the init scripts) and the packages Coolify needs.
# openrc/openssh let Coolify manage its "localhost" server over SSH from inside
# the DIND. The `service` shim maps SysV calls used by Coolify's installer onto
# OpenRC (Alpine has no systemctl/service).
RUN apk add --no-cache bash curl wget git jq openssl openssh openrc \
 && printf '#!/bin/sh\n# Minimal SysV "service" shim mapping to OpenRC (used by the Coolify installer).\nexec rc-service "$@"\n' > /usr/local/bin/service \
 && chmod +x /usr/local/bin/service

# Copy custom entrypoint wrapper
COPY ./codx-junior-installer/codx-junior-dind/entrypoint-wrapper.sh /usr/local/bin/entrypoint-wrapper.sh
RUN chmod +x /usr/local/bin/entrypoint-wrapper.sh

# Create the custom initialization directory similar to LS.io
RUN mkdir -p /custom-cont-init.d
COPY ./codx-junior-installer/codx-junior-dind/codx-junior-dind-init.sh /custom-cont-init.d/codx-junior-dind-init.sh
# Optional: install Coolify at boot so admins can deploy extra services (opt-in via COOLIFY_ENABLED=true)
COPY ./codx-junior-installer/codx-junior-dind/coolify-install.sh /custom-cont-init.d/coolify-install.sh

 # mmmm rethink this
 # COPY . /codx-junior

EXPOSE 80
EXPOSE 443

# Use the wrapper as the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint-wrapper.sh"]