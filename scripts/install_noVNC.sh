#!/bin/bash

# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH="$(cd "$(dirname "$0")/.." && pwd)"
echo "CODX_JUNIOR_PATH: $CODX_JUNIOR_PATH"

# Source the environment variables
source ${CODX_JUNIOR_PATH}/set_env.sh

# Update package lists
sudo apt update

# Install required packages
sudo apt install -y git wget python3 python3-pip novnc websockify

# Clone the noVNC repository if it does not exist
if [ -d "${CODX_JUNIOR_PATH}/noVNC" ]; then
  rm -rf ${CODX_JUNIOR_PATH}/noVNC
fi
git clone https://github.com/novnc/noVNC.git ${CODX_JUNIOR_PATH}/noVNC

# Install a VNC server, e.g., TightVNCserver
sudo apt install -y tigervnc-standalone-server

# Install a lightweight desktop environment, e.g., Xfce
sudo apt install -y xfce4 xfce4-goodies dbus-x11

# Install Browser
codx chrome

# Clean up
sudo apt autoremove -y

# Copy desktop files
cp -r ${CODX_JUNIOR_PATH}/scripts/Desktop ~/Desktop
sudo chmod +x ~/Desktop/*.desktop

[ ! -d $HOME/.vnc ] && mkdir $HOME/.vnc

vncpasswd -f > $HOME/.vnc/passwd <<EOF
12345678
12345678
EOF

chmod 600 $HOME/.vnc/passwd
chown -R codx-junior $HOME/.vnc
cp ${CODX_JUNIOR_PATH}/vnc/* ~/.vnc
chmod +x ~/.vnc/xstartup

echo "Installation of noVNC and its dependencies completed successfully."
