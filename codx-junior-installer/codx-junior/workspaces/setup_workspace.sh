#!/bin/bash

# Parse command-line arguments for workspace name and projects
while [[ $# -gt 0 ]]; do
  case $1 in
    --name)
      WORKSPACE_NAME="$2"
      shift # past argument
      shift # past value
      ;;
    --projects)
      PROJECT_LIST="$2"
      shift # past argument
      shift # past value
      ;;
    *)
      echo "Unknown option $1"
      exit 1
      ;;
  esac
done

# Directory containing projects
PROJECT_DIR="/home/codx-junior-projects"

# Function to generate volume mappings for Docker run command
generate_volume_args() {
  VOL_ARGS=""
  IFS=',' read -r -a PROJECT_ARRAY <<< "${PROJECT_LIST}"
  for PROJECT in "${PROJECT_ARRAY[@]}"; do
    VOL_ARGS="${VOL_ARGS} -v ${PROJECT_DIR}/${PROJECT}:${PROJECT_DIR}/${PROJECT}"
  done
  echo "${VOL_ARGS}"
}

# Run Docker container using the generated volume mappings
run_docker_container() {
  VOLUMES=$(generate_volume_args)
  docker run -d --name "${WORKSPACE_NAME}-workspace" \
    ${VOLUMES} \
    -e PUID=1001 -e PGID=1001 \
    -e CODE_SERVER_PORT=9080 \
    -l traefik.enable=true \
    -l traefik.http.routers.${WORKSPACE_NAME}-workspace-webtop-router.rule="PathPrefix('/${WORKSPACE_NAME}/preview')" \
    -l traefik.http.routers.${WORKSPACE_NAME}-workspace-webtop-router.service="${WORKSPACE_NAME}-workspace-webtop-service" \
    -l traefik.http.services.${WORKSPACE_NAME}-workspace-webtop-service.loadbalancer.server.port=3000 \
    -l traefik.http.middlewares.${WORKSPACE_NAME}-workspace-webtop-path.replacepathregex.regex="^/${WORKSPACE_NAME}/preview/(.*)" \
    -l traefik.http.middlewares.${WORKSPACE_NAME}-workspace-webtop-path.replacepathregex.replacement="/$$1" \
    -l traefik.http.routers.${WORKSPACE_NAME}-workspace-webtop-router.middlewares="${WORKSPACE_NAME}-workspace-webtop-path,codx-junior-auth" \
    codxjunior/codx-junior-default-workspace:latest
}

# Execute functions
run_docker_container

echo "Setup complete for workspace: ${WORKSPACE_NAME}"