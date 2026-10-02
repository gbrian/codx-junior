#!/bin/bash
echo "Starting codx-junior"
BASE_PATH=/home/codx-junior/codx-junior/codx-junior-installer/codx-junior

cd $BASE_PATH
docker-compose up -d & # Create in background

echo "Run codx-junior default workspace"

cd ${BASE_PATH}/workspaces/codx-junior-workspace-default
docker-compose -f docker-compose.workspace-default.yaml up -d & # Create in background
