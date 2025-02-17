export PYTHONPATH=${CODX_JUNIOR_PATH}/api

cd ${CODX_JUNIOR_PATH}/api
if [ ! -d "$CODX_JUNIOR_API_VENV/bin" ]; then
  echo "Installing codx-junior at $CODX_JUNIOR_API_VENV"
  python3 -m venv $CODX_JUNIOR_API_VENV
  source ${CODX_JUNIOR_API_VENV}/bin/activate
  
  pip3 install wheel 
  
  pip3 install .  
fi