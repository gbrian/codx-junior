#!/bin/bash

# Activate your python environment if any
source .venv/bin/activate

# Navigate to the directory where your FastAPI application is located
cd api

# Run the FastAPI application using uvicorn
uvicorn main:app --reload --debug