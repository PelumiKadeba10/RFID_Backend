from gevent import monkey
monkey.patch_all(thread=False)

from flask import Flask, request, jsonify, make_response
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from flask_cors import CORS
import os

# Load environment variables
load_dotenv()

# Flask App Initialization
app = Flask(__name__)
CORS(app)

# MongoDB Connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL environment variable")

client = MongoClient(DATABASE_URL)
db = client.get_database()

# Flask-SocketIO Setup
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

def get_db():
    """Returns the database instance."""
    return db

@app.route("/log", methods=["POST"])
def access_check():
    """
    Logs access attempts and emits real-time updates via SocketIO.
    """
    db = get_db()
    users_collection = db["Users"]
    logs_collection = db["Data"]

    data = request.json
    if not data or "matric" not in data:
        return jsonify({"error": "Missing matric"}), 400

    matric = data["matric"]
    timestamp = data.get("timestamp", datetime.utcnow().isoformat())
    # Status = data.get("Status")
    
    user = users_collection.find_one({"Matric": matric})

    log_entry = {
        "tag": user.get("tag") if user else None,
        "Name": user.get("Name") if user else "Unknown",
        "Matric": matric,
        # "Status": Status,
        "timestamp": timestamp
    }

    logs_collection.insert_one(log_entry)

    # Emit real-time updates
    socketio.emit("access_log", log_entry)

    return jsonify({"message": "Access granted" if user else "Access denied"}), 200 if user else 403


@app.route('/events', methods=['GET'])
def get_events():
    db = get_db()
    logs_collection = db["Data"]
    logs = logs_collection.find()  # Find all documents in the collection

    logs_list = [
        {
            'tag': log.get('tag'),  # Use 'log' instead of 'logs'
            'Name': log.get('Name'),
            'Matric': log.get('Matric'),
            'timestamp': log.get('timestamp')
        } for log in logs  # Iterate over each 'log' document
    ]
    
    # Return the events as JSON
    return jsonify(logs_list)


@socketio.on("connect")
def handle_connect():
    """Handles a new client connection."""
    print("Client connected!")
    emit("message", {"message": "Welcome to the RFID System!"})

@socketio.on("disconnect")
def handle_disconnect():
    """Handles client disconnection."""
    print("Client disconnected!")

if __name__ == "__main__":
   socketio = SocketIO(app, cors_allowed_origins="*", transports=['websocket', 'polling'])