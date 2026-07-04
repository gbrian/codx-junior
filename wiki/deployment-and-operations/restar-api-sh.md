# API Restart Utility

## Overview
This script is used for the deployment and operations of the `codx-junior` project to facilitate the maintenance of the API service.

## Functionality
The script performs a forced termination of the API process to ensure a clean state during maintenance operations. It achieves this by identifying and killing any processes associated with `run_api.sh`.

## Usage
The script executes a `kill -9` command on all processes matching the pattern `run_api.sh` using the `pgrep` utility.

### References
* **Category:** Deployment and Operations
* **Keywords:** deployment, operations, scripts, maintenance