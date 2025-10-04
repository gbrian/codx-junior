#!/bin/bash

# Create a Python virtual environment in /tmp
python3 -m venv /tmp/myenv

# Activate the virtual environment
source /tmp/myenv/bin/activate

# Change directory to the script's parent folder
cd "$(dirname "$0")"

# Install the Python project
pip install -e .