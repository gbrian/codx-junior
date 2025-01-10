#!/bin/bash

# Dynamically set CODX_JUNIOR_PATH to the parent directory of the script
export CODX_JUNIOR_PATH=$(dirname "$(dirname "$(realpath "$0")")")

export PYTHONPATH=${CODX_JUNIOR_PATH}/api

# VNC 
export DISPLAY=:10
export DISPLAY_SHARED=:20
export DISPLAY_WIDTH=1920
export DISPLAY_HEIGHT=1080
export VNC_NO_PASSWORD=1

# Set up environment variables
export API_VENV=/tmp/.venv_codx_junior_api_dev
export API_PORT=3984
export WEB_PORT=3983
export CODER_PORT=3909
export NOVNC_PORT=3986
export FILEBROWSER_PORT=3987
export BROWSER_PORT=3988
export STATIC_FOLDER=${CODX_JUNIOR_PATH}/client/dist

export CODX_SUPERVISOR_LOG_FOLDER=/var/log/codx-junior-dev-supervisor

# Ensure all background processes are terminated on script exit
trap "kill 0" EXIT

# Function to display help information
function show_help() {
    echo "Usage: app.cli [command]"
    echo
    echo "Commands:"
    echo "  help      Display this help message"
    echo "  install   Install the application"
    echo "  run       Run the application"
}

# Function to simulate installation process
function install_app() {
    echo "Starting the installation process..."
    
    bash ${CODX_JUNIOR_PATH}/scripts/install_api.sh

    echo "Application installed successfully."
}

# Function to simulate running the application
function run_app() {
    echo '
                      888                 d8b                   d8b                  
                      888                 Y8P                   Y8P                  
                      888                                                            
 .d8888b .d88b.   .d88888 888  888       8888 888  888 88888b.  888  .d88b.  888d888 
d88P"   d88""88b d88" 888 `Y8bd8P`       "888 888  888 888 "88b 888 d88""88b 888P"   
888     888  888 888  888   X88K  888888  888 888  888 888  888 888 888  888 888     
Y88b.   Y88..88P Y88b 888 .d8""8b.        888 Y88b 888 888  888 888 Y88..88P 888     
 "Y8888P "Y88P"   "Y88888 888  888        888  "Y88888 888  888 888  "Y88P"  888     
                                          888                                        
                                         d88P                                        
                                       888P'

    echo "Running the application..."
    /usr/bin/supervisord -c ${CODX_JUNIOR_PATH}/supervisor.conf
}

# Check the command line argument
case "$1" in
    help)
        show_help
        ;;
    install)
        install_app
        ;;
    run)
        run_app
        ;;
    *)
        echo "Invalid command. Use 'help' to see available commands."
        ;;
esac