import socketio

#Socket io (sio) create a Socket.IO server
sio = socketio.AsyncServer(cors_allowed_origins='*',async_mode='asgi')
