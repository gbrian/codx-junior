#!/usr/bin/with-contenv bash

echo "Running coder*********"

curl -fsSL https://code-server.dev/install.sh | sh

CODE_PORT=${CODE_SERVER_PORT:-9080}

export CODER_HTTP_ADDRESS=0.0.0.0:${CODE_PORT}

sed -i "s/127.0.0.1:8080/0.0.0.0:${CODE_PORT}/" ~/.config/code-server/config.yaml 
sed -i "s/auth: password/auth: none/" ~/.config/code-server/config.yaml 

code-server