#!/bin/bash
echo "codx-junior entrypoint"
env

# Install
if [ "$1" == "install" ]; then
  cd ${HOME}/codx-junior
  echo "Installing codx-junior at ${HOME}/codx-junior"
  bash codx-junior install

  exit
fi

# Run
if [ -f /user-entrypoint.sh ]; then
  . /user-entrypoint.sh
fi

# Run supervisor
echo "Entrypoint: running supervisor"
sudo -E bash -c "bash ${HOME}/codx-junior/codx-junior supervisor"

