# backend/backend/routes/iot_routes.py
from flask import Blueprint, jsonify, request, current_app
import os, json
from datetime import datetime
import pandas as pd

from db import get_db_cursor

iot_bp = Blueprint("iot_bp", __name__)

# Upload sensor (ingest + store)
@iot_bp.route("/upload_sensor", methods=["POST"])
def upload_sensor():
    payload = request.get_json()
    if not payload:
        return jsonify({"error": "No data provided"}), 400

    # Basic validation and normalization
    device_id = payload.get("device_id")
    city = payload.get("city")
    timestamp = payload.get("timestamp") or datetime.utcnow().isoformat()
    sensors = payload.get("sensors", {})
    meta = payload.get("meta", {})

    # Save raw payload in ingestion_logs
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO ingestion_logs (device_id, raw_payload, received_at, validated, validation_errors, stored_in_readings)
                VALUES (%s, %s, NOW(), %s, %s, %s)
                RETURNING id;
                """,
                (device_id, json.dumps(payload), True, None, False)
            )
            ingestion_id = cur.fetchone()["id"]
    except Exception as e:
        current_app.logger.exception("Failed to write ingestion log: %s", e)
        # continue, but notify client
        ingestion_id = None

    # Prepare fields for sensor_readings insert
    pm25 = sensors.get("pm25")
    pm10 = sensors.get("pm10")
    co2 = sensors.get("co2")
    temperature = sensors.get("temperature")
    humidity = sensors.get("humidity")
    voc = sensors.get("voc_ppm") or sensors.get("voc")
    latitude = sensors.get("latitude") or sensors.get("lat")
    longitude = sensors.get("longitude") or sensors.get("lon")

    # Insert into sensor_readings table
    try:
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                """
                INSERT INTO sensor_readings
                (device_id, device_type, city, timestamp, pm25, pm10, co2, temperature, humidity, voc_ppm,
                 latitude, longitude, measurements, meta, created_at)
                VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, NOW())
                RETURNING id;
                """,
                (
                    device_id,
                    payload.get("device_type", "portable"),
                    city,
                    timestamp,
                    pm25, pm10, co2, temperature, humidity, voc,
                    latitude, longitude,
                    json.dumps(sensors),
                    json.dumps(meta),
                )
            )
            reading_id = cur.fetchone()["id"]

        # Update ingestion_logs stored_in_readings flag if ingestion logged earlier
        if ingestion_id:
            with get_db_cursor(commit=True) as cur:
                cur.execute("UPDATE ingestion_logs SET stored_in_readings = TRUE WHERE id = %s", (ingestion_id,))

        return jsonify({"status": "ok", "reading_id": reading_id}), 201

    except Exception as e:
        current_app.logger.exception("Failed to insert sensor reading: %s", e)
        return jsonify({"error": "Database insert failed", "details": str(e)}), 500


# Visual/report endpoints and daily_report can remain unchanged (or be updated similarly to use DB)
