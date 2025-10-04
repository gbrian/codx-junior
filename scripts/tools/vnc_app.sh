#!/bin/bash

# Parse input arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -c|--command) command_to_run="$2"; shift ;;
        -n|--name) app_name="$2"; shift ;;
        -d|--display) virtual_display=":$2"; shift ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Check if required parameters are provided
if [ -z "$command_to_run" ] || [ -z "$app_name" ] || [ -z "$virtual_display" ]; then
    echo "Usage: $0 -c|--command <command> -n|--name <name> -d|--display <display_number>"
    exit 1
fi

# Step 1: Create a Virtual Display
export DISPLAY=$virtual_display
vncserver $DISPLAY -localhost yes -xstartup $command_to_run

echo "VNC streaming started for $app_name on display $virtual_display with window ID $window_id."
