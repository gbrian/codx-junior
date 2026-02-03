#!/bin/bash
echo "Starting codx-junior"

cd /home/codx-junior/codx-junior/codx-junior-installer/codx-junior
docker-compose up -d

echo "Run codx-junior default workspace"

cd workspaces/codx-junior-workspace-default
docker-compose -f docker-compose.workspace-default.yaml up -d
