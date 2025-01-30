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
socketio = SocketIO(app, cors_allowed_origins="*")

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

    user = users_collection.find_one({"Matric": matric})
    
    log_entry = {
        "tag": user.get("tag") if user else None,
        "Name": user.get("Name") if user else "Unknown",
        "Matric": matric,
        "Status": "Granted" if user else "Denied",
        "timestamp": timestamp
    }

    logs_collection.insert_one(log_entry)

    # Emit real-time updates
    socketio.emit("access_log", log_entry)

    return jsonify({"message": "Access granted" if user else "Access denied"}), 200 if user else 403

@app.route("/search", methods=["GET"])
def search():
    """
    Searches access logs based on the provided date.
    """
    db = get_db()
    logs_collection = db["Data"]

    date_str = request.args.get("date")
    if not date_str:
        return make_response(jsonify({"error": "Date is required"}), 400)

    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        start = datetime.combine(date_obj, datetime.min.time())
        end = datetime.combine(date_obj, datetime.max.time())

        logs = list(logs_collection.find({"timestamp": {"$gte": start.isoformat(), "$lt": end.isoformat()}}))

        if logs:
            for log in logs:
                log["_id"] = str(log["_id"])  # Convert ObjectId to string for JSON serialization
            return make_response(jsonify(logs), 200)
        
        return make_response(jsonify({"message": "No logs found for this day"}), 404)

    except Exception as e:
        return make_response(jsonify({"error": str(e)}), 500)

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
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
