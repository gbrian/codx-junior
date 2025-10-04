#!/bin/bash
# Bash installer that will build and run codx-junior instance

# Parse arguments
# -g, --user-gid use it to set env USER_GID
# -u, --user-uid use it to set env USER_UID
# -p, --port use it to set env CODX_JUNIOR_WEB_PORT

# Build the image
docker-compose up codx-junior-build

# Create bridge network: "codx-junior-network"
docker network create codx-junior-network

# Run instance
# User can pass environment variables:
docker-compose up -d

Create the installer