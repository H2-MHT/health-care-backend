import socketio
import eventlet

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Use the logger with Socket.IO
sio = socketio.Server(cors_allowed_origins="*", logger=True, engineio_logger=True)
app = socketio.WSGIApp(sio)


# Store registered users
users = {}


@sio.event
def connect(sid, environ):
    print(f"User connected with session ID: {sid}")
    logging.info(f"User connected with session ID: {sid}")


@sio.event
def register(sid, data):
    """
    Register a user with their user ID (no email).
    """
    user_id = data.get("user_id")  # Only use user_id
    if user_id:
        users[user_id] = sid
        logging.info(f"User registered: {user_id} with session ID: {sid}")
    else:
        logging.info(f"Registration failed: No user_id provided for session {sid}")

@sio.event
def initiateCall(sid, data):
    """
    Handle call initiation and emit 'incomingCall' event to the target user.
    """
    logging.info(f"initiateCall connected with session ID: {sid}")
    logging.info(users, "Registered users")
    logging.info("Initiating call...")
    target_id = data.get("targetId")
    signal_data = data.get("signalData")
    sender_id = data.get("senderId")
    sender_name = data.get("senderName")
    target_sid = users.get(target_id)
    logging.info("Sending call to target user...")
    if not target_sid:
        logging.info("Target ID is undefined or invalid")
        return

    try:
        sio.emit("incomingCall", {
            "signal": signal_data,
            "from": sender_id,
            "name": sender_name,
        }, to=target_sid)
        logging.info(f"Call initiated and 'incomingCall' event emitted to {target_sid}")
    except Exception as e:
        logging.info(f"Error initiating call: {e}")

@sio.event
def changeMediaStatus(sid, data):
    """
    Broadcast media status changes to all connected clients.
    """
    media_type = data.get("mediaType")
    is_active = data.get("isActive")
    sio.emit("mediaStatusChanged", {
        "mediaType": media_type,
        "isActive": is_active,
    }, skip_sid=sid)

@sio.event
def sendMessage(sid, data):
    """
    Send a message to a specific user.
    """
    target_id = data.get("targetId")
    message = data.get("message")
    sender_name = data.get("senderName")

    target_sid = users.get(target_id)
    if target_sid:
        sio.emit("receiveMessage", {
            "message": message,
            "senderName": sender_name,
        }, to=target_sid)
    else:
        logging.info(f"Target user {target_id} is not connected")

@sio.event
def answerCall(sid, data):
    """
    Broadcast call answer and media status to all connected clients.
    """
    media_type = data.get("mediaType")
    media_status = data.get("mediaStatus")
    target_sid = data.get("to")

    sio.emit("mediaStatusChanged", {
        "mediaType": media_type,
        "isActive": media_status,
    }, skip_sid=sid)

    if target_sid:
        sio.emit("callAnswered", data, to=target_sid)

@sio.event
def terminateCall(sid, data):
    """
    Emit call termination event to the target user.
    """
    target_id = data.get("targetId")
    target_sid = users.get(target_id)
    if target_sid:
        sio.emit("callTerminated", {}, to=target_sid)

@sio.event
def disconnect(sid):
    """
    Handle user disconnection.
    """
    # Remove user from users dictionary
    user_id = next((key for key, value in users.items() if value == sid), None)
    if user_id:
        del users[user_id]
    logging.info(f"User disconnected with session ID: {sid}")

# Run the server
if __name__ == "__main__":
    ip_address = "0.0.0.0"
    port = 8080
    eventlet.wsgi.server(eventlet.listen((ip_address, port)), app)
