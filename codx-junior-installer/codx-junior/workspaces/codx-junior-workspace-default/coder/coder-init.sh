#!/usr/bin/with-contenv bash

runcoder(){
  echo "Running coder for $USER"

  # Ensure the install script runs
  curl -fsSL https://code-server.dev/install.sh | sh

  CODE_PORT=${CODE_SERVER_PORT:-9080}
  export CODER_HTTP_ADDRESS=0.0.0.0:${CODE_PORT}

  # Ensure directory exists before sed
  mkdir -p ~/.config/code-server
  touch ~/.config/code-server/config.yaml

  sed -i "s/127.0.0.1:8080/0.0.0.0:${CODE_PORT}/" ~/.config/code-server/config.yaml 
  sed -i "s/auth: password/auth: none/" ~/.config/code-server/config.yaml 
  
  exec code-server
}

# Export the function so the subshell can see it
export -f runcoder

# Use sudo to run as specific UID and GID
# Note: \# is used for numeric IDs in sudo
sudo -u \#${PUID} -g \#${PGID} -E bash -c runcoder