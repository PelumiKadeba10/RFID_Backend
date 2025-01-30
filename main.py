from flask import Flask, request, jsonify
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

def get_db():
    """Returns the database instance."""
    return db

@app.route("/log", methods=["POST"])
def access_check():
    """
    Logs access attempts.
    """
    db = get_db()
    users_collection = db["Users"]
    logs_collection = db["Data"]

    data = request.json
    if not data or "matric" not in data:
        return jsonify({"error": "Missing matric"}), 400

    matric = data["matric"]
    timestamp = data.get("timestamp", datetime.utcnow().isoformat())
    Status = data.get("status")

    user = users_collection.find_one({"Matric": matric})

    log_entry = {
        "tag": user.get("tag") if user else None,
        "Name": user.get("Name") if user else "Unknown",
        "Matric": matric,
        "Status": Status,
        "timestamp": timestamp
    }

    logs_collection.insert_one(log_entry)

    return jsonify({"message": "Access granted" if user else "Access denied"}), 200 if user else 403


@app.route('/gt_logs', methods=['GET'])
def get_events():
    db = get_db()
    logs_collection = db["Data"]
    logs = logs_collection.find()  # Find all documents in the collection

    logs_list = [
        {
            'tag': log.get('tag'),
            'Name': log.get('Name'),
            'Matric': log.get('Matric'),
            'timestamp': log.get('timestamp')
        } for log in logs  # Iterate over each 'log' document
    ]
    
    return jsonify(logs_list)

if __name__ == "__main__":
    app.run(debug=True)  # Run the app in debug mode
