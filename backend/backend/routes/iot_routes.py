from flask import Blueprint, jsonify, request
import os
import json
import pandas as pd
from datetime import datetime, timedelta

# Blueprint for IoT-related routes
iot_bp = Blueprint("iot_bp", __name__)

# ===============================
# SETUP PATHS (Fix applied here)
# ===============================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # backend/
sensor_dir = os.path.join(BASE_DIR, "sensor_logs")
sensor_log_path = os.path.join(sensor_dir, "daily_readings.json")

# ===============================
# 1️⃣ Upload IoT Sensor Data
# ===============================
@iot_bp.route("/upload_sensor", methods=["POST"])
def upload_sensor():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data received"}), 400

    # Ensure folder exists
    os.makedirs(sensor_dir, exist_ok=True)

    # Initialize JSON file if missing
    if not os.path.exists(sensor_log_path):
        with open(sensor_log_path, "w") as f:
            json.dump([], f)

    # Append timestamp to data
    data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Read, append, and save
    with open(sensor_log_path, "r") as f:
        logs = json.load(f)
    logs.append(data)
    with open(sensor_log_path, "w") as f:
        json.dump(logs, f, indent=4)

    return jsonify({"message": "Sensor data uploaded successfully!"})

# ===============================
# 2️⃣ Generate Daily Exposure Report
# ===============================
@iot_bp.route("/daily_report", methods=["GET"])
def get_daily_report():
    if not os.path.exists(sensor_log_path):
        return jsonify({"error": "No sensor data available"}), 404

    with open(sensor_log_path, "r") as f:
        logs = json.load(f)

    if not logs:
        return jsonify({"message": "No readings available"}), 200

    # Convert logs to DataFrame
    df = pd.DataFrame(logs)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    cutoff = datetime.now() - timedelta(hours=24)
    df = df[df["timestamp"] >= cutoff]

    if df.empty:
        return jsonify({"message": "No readings in the last 24 hours"}), 200

    # Compute mean exposure for the last 24 hours
    report = {}
    for col in df.columns:
        if col not in ["timestamp", "city"]:
            report[col] = round(df[col].mean(), 2)

    return jsonify({
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "average_exposure": report,
        "entries_count": len(df)
    })

@iot_bp.route("/visual_report", methods=["GET"])
def visual_report():
    """Generate visualization-ready report grouped by city."""
    if not os.path.exists(sensor_log_path):
        return jsonify({"error": "No sensor data available"}), 404

    with open(sensor_log_path, "r") as f:
        logs = json.load(f)

    if not logs:
        return jsonify({"message": "No data found"}), 200

    df = pd.DataFrame(logs)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Group by city and compute average readings
    city_group = df.groupby("city").mean(numeric_only=True).reset_index()

    # Prepare data for visualization (bar/pie chart formats)
    pollutants = ["co2", "o3", "voc", "pm25", "temperature"]
    data = {
        "cities": city_group["city"].tolist(),
        "pollutants": {}
    }

    for p in pollutants:
        data["pollutants"][p] = city_group[p].round(2).tolist()

    return jsonify({
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": data,
        "entries_count": len(df)
    })
