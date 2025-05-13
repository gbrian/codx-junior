#!/bin/bash

if [ -f /user-entrypoint.sh ]; then
  . /user-entrypoint.sh
fi

echo "codx-junior entrypoint"

if [ "$1" == "install" ]; then

  if [ ! -d "${HOME}/codx-junior" ]; then
    echo "Cloning codx-junior"
    git clone --depth 1 https://github.com/gbrian/codx-junior.git ${HOME}/codx-junior
  fi

  cd ${HOME}/codx-junior

  echo "Installing codx-junior at ${HOME}/codx-junior"
  bash codx-junior install

else

    # Run supervisor
    echo "Installation done, running supervisor"
    sudo -E bash -c "bash ${HOME}/codx-junior/codx-junior supervisor"

fi