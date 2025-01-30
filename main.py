import gevent
from gevent import monkey
monkey.patch_all()

from flask import Flask, request, jsonify, g
from flask import make_response
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from datetime import datetime
from dotenv import load_dotenv
from flask_cors import CORS
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)
app.config["MONGO_URI"] = os.getenv("DATABASE_URL")
socketio = SocketIO(app, cors_allowed_origins="*")  # SocketIO for real-time updates

# MongoDB connection inside a function (fixes fork issue)
def get_db():
    if "db" not in g:
        with app.app_context():  # ✅ Ensures the app context is available
            client = MongoClient(os.getenv("DATABASE_URL"))
            g.db = client.get_database()
    return g.db

# Register a new user with an RFID tag.
@app.route("/Register", methods=["POST"])
def register_user():
    db = get_db()  # ✅ Call inside the route
    users_collection = db["Users"]

    data = request.json
    if not data or "uid" not in data:
        return jsonify({"Error": "Missing required fields"}), 400

    users_collection.insert_one(data)
    return jsonify({"message": "User registered successfully!"}), 201

# Verify RFID access and log the attempt.
@app.route("/log", methods=["POST"])
def access_check():
    db = get_db()  # ✅ Call inside the route
    users_collection = db["Users"]
    logs_collection = db["Data"]

    data = request.json
    rfid_tag = data.get("uid")

    if not rfid_tag:
        return jsonify({"error": "Missing RFID tag"}), 400

    user = users_collection.find_one({"rfid_tag": rfid_tag})

    log_entry = {
        "rfid_tag": rfid_tag,
        "Name": user.get("Name") if user else "Unknown",
        "Matric": user.get("Matric") if user else "Unknown",
        "Status": "Accepted" if user else "Denied",
        "timestamp": user.get("timestamp")  # Use current UTC time if missing
    }

    logs_collection.insert_one(log_entry)

    # Emit real-time updates to connected clients
    socketio.emit("access_log", log_entry)

    return jsonify({"message": "Access granted" if user else "Access denied"}), 200 if user else 403

# Search functionality API
@app.route("/search", methods=["GET"])
def search():
    db = get_db()  # ✅ Call inside the route
    logs_collection = db["Data"]

    date_resp = request.args.get("date")
    
    if not date_resp:
        return make_response(jsonify({"error": "Date is required"}), 400)

    date_resp = datetime.strptime(date_resp, "%Y-%m-%d")
    start = datetime.combine(date_resp, datetime.min.time())
    end = datetime.combine(date_resp, datetime.max.time())

    logs = logs_collection.find({"timestamp": {"$gte": start, "$lt": end}})
    logs_list = list(logs)

    if logs_list:
        return make_response(jsonify(logs_list), 200)
    
    return make_response(jsonify({"Error message": "No events found for this day"}), 404)

# Handle a new client connection.
@socketio.on("connect")
def handle_connect():
    print("Client connected!")
    emit("message", {"message": "Welcome to the RFID System!"})

# Handle client disconnection
@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected!")

if __name__ == "__main__":
    with app.app_context():  #  Ensures Flask context before running
        socketio.run(app, debug=True, host="0.0.0.0", port=5000)
