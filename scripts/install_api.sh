cd ${CODX_JUNIOR_HOME}/api
if [ ! -d "$API_VENV/bin" ]; then
  echo "Installing codx-junior at $API_VENV"
  python3 -m venv $API_VENV
  source ${API_VENV}/bin/activate
  
  pip3 install wheel 
  
  pip3 install .  
fi