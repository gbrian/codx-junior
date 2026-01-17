#!/bin/bash
echo "Starting codx-junior"

IMAGES_FOLDER=/codx-junior/codx-junior-installer/codx-junior-dind/images
if [ -d "${IMAGES_FOLDER}" ];then
  echo "Load docker images"
  cd ${IMAGES_FOLDER}
  # Iterate over all .tar files in the current directory
  for tarfile in *.tar; do
    # Check if the file exists to avoid errors if no .tar files are found
    if [[ -f "$tarfile" ]]; then
      echo "Loading image from $tarfile..."
      docker load -i "$tarfile"
    else
      echo "No .tar files found in $(pwd)."
      break
    fi
  done
fi

echo "Run codx-junior"

cd /codx-junior/codx-junior-installer/codx-junior
docker-compose up -d

echo "Run codx-junior default workspace"

cd workspaces/codx-junior-workspace-default
docker-compose -f docker-compose.workspace-default.yaml up -d
