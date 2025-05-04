#!/bin/bash
# Function to log messages
log_info() {
  echo "[INFO] $1"
}

log_error() {
  echo "[ERROR] $1" >&2
}

# Stop script on error
set -e

# Load .env variables
source ${CODX_JUNIOR_PATH}/set_env.sh

bash scripts/logo.sh

echo "Starting installation..."

# Function to update and install packages
install_packages() {
    echo "Updating package list and installing packages..."
    sudo apt-get update
    sudo apt-get install -y \
        curl wget supervisor nano \
        locales python3.11 python3.11-venv firefox-esr \
        procps git tesseract-ocr
    sudo apt-get clean
    sudo rm -rf /var/lib/apt/lists/*
}

# Invoke the function to install packages
install_packages

# Configure Git
echo "Configuring Git..."
git config --global --add safe.directory '*'

# Create necessary directories
echo "Creating necessary directories..."
sudo mkdir -p "${CODX_SUPERVISOR_LOG_FOLDER}"

# Install codx APPS
echo "Installing codx APPS..."
curl -sL "https://raw.githubusercontent.com/gbrian/codx-cli/main/codx.sh" | bash -s


# Installers
function install_client() {
  echo "Install web client"
  bash ${CODX_JUNIOR_PATH}/scripts/install_client.sh

  echo "Install noVNC"
  bash ${CODX_JUNIOR_PATH}/scripts/install_noVNC.sh
}

function install_api() {
  echo "Install api"
  bash ${CODX_JUNIOR_PATH}/scripts/install_api.sh
}

function install_llmFactory () {
  echo "Install llm-factory"
  bash ${CODX_JUNIOR_PATH}/scripts/install_llmFactory.sh
}

function copy_app_conf() {
  if [ ! -d /etc/supervisord ]; then
    sudo mkdir /etc/supervisord
  fi
  
  app=$1
  log_info "Copying supervisor conf for: $app"
  conf_source="${HOME}/codx-junior/supervisor.${app}.conf"
  conf_dest="/etc/supervisord/supervisor.${app}.conf"

  if [ -f $conf_source ]; then
    sudo cp $conf_source $conf_dest
    log_info "Copied $conf_source to $conf_dest"
  else
    log_error "Configuration file $conf_source not found for app: $app"
  fi
}

function install_docker() {
  codx docker
  
  app=$1
  log_info "Copying supervisor conf for: $app"
  conf_source="${HOME}/codx-junior/supervisor.${app}.conf"
  conf_dest="/etc/supervisord/supervisor.${app}.conf"

}

echo "Load supervisor files"
# Check if CODX_JUNIOR_APPS is not empty
if [ -z "$CODX_JUNIOR_APPS" ]; then
  export CODX_JUNIOR_APPS="client api llm-factory"
fi

for app in $CODX_JUNIOR_APPS; do
  # Copy supervisor conf
  copy_app_conf $app

  # Execute custom instructions based on the app name
  case $app in
    client)
      install_client
      ;;
    api)
      install_api
      ;;
    llm-factory)
      install_llmFactory
      ;;
    docker)
      install_docker
      ;;
    *)
      echo "Unknown app: $app"
      ;;
  esac

done


# Create FileSync directory
echo "Creating FileSync directory..."
mkdir -p "${HOME}/FileSync"

echo "Installation complete!"