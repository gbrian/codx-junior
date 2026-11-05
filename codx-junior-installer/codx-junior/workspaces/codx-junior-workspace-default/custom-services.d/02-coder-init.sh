#!/usr/bin/with-contenv bash

echo "Checking dependencies for code-server..."

# 1. Run the one-time installation check
if [ ! -f /usr/bin/code-server ]; then
    echo "code-server not found, installing..."
 # Ensure the install script runs
  curl -fsSL https://code-server.dev/install.sh | sh
fi

# 2. Setup ports and directories
CODE_PORT=${CODE_SERVER_PORT:-9080}
export CODER_HTTP_ADDRESS=0.0.0.0:${CODE_PORT}

CODE_SERVER_DIR=/config/.local/share/code-server
mkdir -p "${CODE_SERVER_DIR}"

{
  cat <<EOF
bind-addr: 0.0.0.0:${CODE_PORT}
auth: none
password: 8e240165f98d107aade5dbdc
cert: false
EOF

  # Traefik forwards X-Forwarded-Port=80 for requests that reach it over the
  # `web` entrypoint (TLS is terminated upstream), while the browser's Origin
  # is https://<domain> (port 443). code-server's WebSocket origin check
  # compares that port and rejects the upgrade with 403, which the workbench
  # reports as "WebSocket close with status code 1006". Trusting the public
  # domain keeps the check meaningful without depending on proxy headers.
  if [ -n "${CODX_JUNIOR_DOMAIN:-}" ]; then
    cat <<EOF
trusted-origins:
  - "${CODX_JUNIOR_DOMAIN}"
EOF
  fi
} > "${CODE_SERVER_DIR}/config.yaml"

# 3. Ensure your user (1001) owns the config directory
chown -R $PUID:$PGID "${CODE_SERVER_DIR}"

echo "Starting code-server supervision loop..."

# 4. Hand execution over to s6-overlay as the specific user.
# s6 will now watch this process and automatically restart it if it crashes.
exec s6-setuidgid abc code-server --config "${CODE_SERVER_DIR}/config.yaml"
