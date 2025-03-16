#!/bin/bash

# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"

# Source the environment variables
source ${CODX_JUNIOR_PATH}/.env

# Function to clean up background processes on exit
cleanup() {
    if [[ ! -z "$VNC_PID" ]]; then
        echo "Killing VNC server with PID: $VNC_PID"
        kill $(pgrep -x "Xtigervnc")
    fi
}
trap cleanup EXIT INT

# Check if vncserver is already running, if not, start it
if ! pgrep -x "Xtightvnc" > /dev/null; then
    vncserver -SecurityTypes None ${CODX_JUNIOR_DISPLAY} &
fi

# Change directory to noVNC
cd ${CODX_JUNIOR_PATH}/noVNC

# Check if Firefox is already running, if not, start it
if ! pgrep -x "firefox" > /dev/null; then
    DISPLAY=${CODX_JUNIOR_DISPLAY} firefox &
fi

echo "Launch noVNC using websockify to bridge the VNC server to the web VNC client"
./utils/novnc_proxy --listen 0.0.0.0:${CODX_JUNIOR_NOVNC_PORT} --vnc 0.0.0.0:5955