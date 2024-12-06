cd ${CODX_JUNIOR_HOME}/browser
if [ ! -d "$BROWSER_VENV/bin" ]; then
  echo "Installing codx-junior at $BROWSER_VENV"
  python3 -m venv $BROWSER_VENV
  source ${BROWSER_VENV}/bin/activate
  
  pip3 install wheel
  pip3 install .  
fi