import gevent
from gevent import monkey
monkey.patch_all()

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_cors import CORS
import os

load_dotenv()
app = Flask(__name__)
CORS(app)
app.config["MONGO_URI"] = os.getenv("DATABASE_URL")
socketio = SocketIO(app, cors_allowed_origins="*") #SocketIO for real time updates 

# MongoDB connection
try:
    client = MongoClient(app.config["MONGO_URI"]) 
    db = client.get_database()
    users_collection = db["Users"]
    logs_collection = db["Data"]
except Exception as e: 
    print("Error connecting to MongoDB: ", e)  
    raise ConnectionError("Failed to connect to the database.")


# Register a new user with an RFID tag.
@app.route("/Register", methods=["POST"])
def register_user():
    data = request.json
    if not data or "user_id" not in data or "rfid_tag" not in data:
        return jsonify({"Error": "Missing required fields"}), 400

    users_collection.insert_one(data)
    return jsonify({"message": "User registered successfully!"}), 201

# Verify RFID access and log the attempt.
@app.route("/log", methods=["POST"])
def access_check():
    data = request.json
    rfid_tag = data.get("rfid_tag")

    if not rfid_tag:
        return jsonify({"error": "Missing RFID tag"}), 400

    user = users_collection.find_one({"rfid_tag": rfid_tag})
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "rfid_tag": rfid_tag,
        "status": "access_granted" if user else "access_denied"
    }

    logs_collection.insert_one(log_entry)

    # Emit real-time updates to connected clients
    socketio.emit("access_log", log_entry)

    if user:
        return jsonify({"message": "Access granted"}), 200
    return jsonify({"message": "Access denied"}), 403

#Search functionality API
@app.route("/search", methods=["GET"])
def search():
    date_resp = request.args.get("date")
    if not date_resp:
        return jsonify({"error": "Date is required"}), 400

    date = datetime.strptime(date_resp, "%Y-%m-%d")
    logs = logs_collection.find({"date": date})
    logs_list = list(logs)
    
    if logs_list:
        return jsonify(logs_list), 200
    else:
        return jsonify({"Error message":"No events found for this day"}), 404
    
    

# Handle a new client connection.
@socketio.on("connect")
def handle_connect():
    print("Client connected!")
    emit("message", {"message": "Welcome to the RFID System!"})

#Handle client Disconnection
@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected!")

if __name__ == "__main__":
    # Remove socketio.run(app, debug=True)
    with app.app_context():
        app.run()