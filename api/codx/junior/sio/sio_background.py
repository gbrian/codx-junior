
import os
import time
import logging
import socketio

logger = logging.getLogger(__name__)

CODX_JUNIOR_API_BACKGROUND = os.environ.get("CODX_JUNIOR_API_BACKGROUND")

sio_client = None
if CODX_JUNIOR_API_BACKGROUND:
    sio_client = socketio.SimpleClient()
    url = f'http://0.0.0.0:{os.environ["CODX_JUNIOR_API_PORT"]}'
    while True:
        try:
            logger.info(f"***************** Background client SIOconnecting to {url}")
            sio_client.connect(url, socketio_path="/api/socket.io")
            server_response = sio_client.call("background-event", { "event": "hello", "data": {}})
            logger.info(f"***************** Background client SIO connected: {server_response}")
            break
        except Exception as ex:
            logger.error(f"***************** Background client SIO error: {ex}")
            time.sleep(5)
