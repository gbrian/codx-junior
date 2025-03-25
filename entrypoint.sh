#!/bin/bash

if [ -f /user-entrypoint.sh ]; then
  . /user-entrypoint.sh
fi

echo "codx-junior entrypoint"
if [ ! -d "${HOME}/codx-junior" ]; then
  echo "Cloning codx-junior: $CODX_JUNIOR_BRANCH"
  git clone --depth 1 --branch $CODX_JUNIOR_BRANCH https://github.com/gbrian/codx-junior.git ${HOME}/codx-junior
  cd ${HOME}/codx-junior
  bash codx-junior install
fi

cd ${HOME}/codx-junior
# Run supervisor
echo "Running supervisor"
sudo bash ${HOME}/codx-junior/codx-junior supervisor