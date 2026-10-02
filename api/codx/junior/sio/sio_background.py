import os
import time
import logging
import socketio
from typing import Optional

logger = logging.getLogger(__name__)

# Constants for environment variables
CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")
CODX_JUNIOR_API_URL = os.environ.get("CODX_JUNIOR_API_URL")

sio_client: Optional[socketio.SimpleClient] = None

def connect_to_server():
    """Connect to background server using socket.io."""
    global sio_client
    if sio_client and sio_client.connected:
        logger.info("Background client already connected.")
        return

    logger.info("Attempting to connect to the background server...")
    try:
        sio_client = socketio.Client()  # Ensure a Client instance is initialized 
        sio_client.connect(CODX_JUNIOR_API_URL, socketio_path="/api/socket.io")
        server_response = sio_client.call("background-event", {"event": "hello", "data": {}})
        logger.info("Connected to background server: %s", server_response)

    except socketio.exceptions.ConnectionError as connection_error:
        logger.error("Connection error while connecting to background server: %s", connection_error)
        sio_client = None  # Reset client on error
        time.sleep(5)  # Backoff strategy
        connect_to_server()  # Retry connection

if CODX_JUNIOR_API_BACKGROUND:
    connect_to_server()

# Made with ❤️ by codx-junior