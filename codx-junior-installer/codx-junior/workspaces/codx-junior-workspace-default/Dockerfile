FROM kasmweb/firefox:1.18.0

USER root

# Install curl to fetch the code-server installer script
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Install code-server using their official automated script
RUN curl -sL "https://raw.githubusercontent.com/gbrian/codx-cli/main/codx.sh" | bash -s

RUN codx code-server

RUN codx docker

# Copy and permission the custom startup script
# COPY custom_startup.sh $STARTUP_DIR/custom_startup.sh
# RUN chmod +x $STARTUP_DIR/custom_startup.sh \
#    && chown 1000:1000 $STARTUP_DIR/custom_startup.sh

# Revert back to the unprivileged Kasm execution user
USER 1000
