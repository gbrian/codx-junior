#!/bin/bash

# Install the required dependencies
echo "Installing dependencies..."
pip install .

# Run the llm-factory project
echo "Running llm-factory..."
python main.py # Adjust the script name as necessary
