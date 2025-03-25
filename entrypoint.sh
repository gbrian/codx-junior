#!/bin/bash

if [ -f /user-entrypoint.sh ]; then
  . /user-entrypoint.sh
fi

echo "codx-junior entrypoint"
if [ ! -d "${HOME}/codx-junior" ]; then
  echo "Cloning codx-junior: $CODX_JUNIOR_BRANCH"
  git clone --depth 1 --branch $CODX_JUNIOR_BRANCH https://github.com/gbrian/codx-junior.git ${HOME}/codx-junior
fi

cd ${HOME}/codx-junior

if [ ! -f "${HOME}/codx-junior/installed" ]; then
  echo "Installing codx-junior at ${HOME}/codx-junior"
  bash codx-junior install
  touch ${HOME}/codx-junior/installed
fi

# Run supervisor
echo "Running supervisor"
mkdir -p $CODX_SUPERVISOR_LOG_FOLDER
sudo bash -c "USER=$USER HOME=$HOME bash ${HOME}/codx-junior/codx-junior supervisor"