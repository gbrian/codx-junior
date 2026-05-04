#!/bin/bash

sudo apt-get update && sudo apt-get install -y socat

cd ${CODX_JUNIOR_PATH}/browser
npm i && npm start