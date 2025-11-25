# backend/backend/app.py

import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from google.cloud.sql.connector import Connector, IPTypes
import pg8000.native
import model_paths  # sets MODEL_DIR, bucket paths

# ==========================
# Cloud SQL Connector Setup
# ==========================
PROJECT_ID = "just-smithy-479012-a1"
REGION = "us-east1"
INSTANCE = "vento-postgres"
INSTANCE_CONNECTION_NAME = f"{PROJECT_ID}:{REGION}:{INSTANCE}"

DB_USER = os.environ.get("DB_USER", "giorno_geovanna")
DB_PASS = os.environ.get("DB_PASS", "")
DB_NAME = os.environ.get("DB_NAME", "gold_experience")

connector = Connector(ip_type=IPTypes.PUBLIC)

def get_connection():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME
    )
    return conn


# ==========================
# Flask App Setup
# ==========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__, static_folder=FRONTEND_DIR, template_folder=TEMPLATES_DIR)
CORS(app)


# ==========================
# BLUEPRINTS
# ==========================
from routes.forecast_routes import forecast_bp
from routes.iot_routes import iot_bp
from routes.ml_routes import ml_bp
from routes.live_aqi_routes import live_aqi_bp
from routes.trivia_routes import trivia_bp
from routes.hybrid_routes import hybrid_bp
from routes.prophet_routes import prophet_bp
from routes.short_term_routes import short_term_bp
from routes.city_aqi_routes import city_bp
from routes.upload_routes import upload_bp

app.register_blueprint(forecast_bp, url_prefix="/api")
app.register_blueprint(iot_bp, url_prefix="/api")
app.register_blueprint(ml_bp, url_prefix="/api")
app.register_blueprint(live_aqi_bp, url_prefix="/api")
app.register_blueprint(hybrid_bp, url_prefix="/api")
app.register_blueprint(trivia_bp, url_prefix="/api")
app.register_blueprint(prophet_bp, url_prefix="/api")
app.register_blueprint(short_term_bp, url_prefix="/api")
app.register_blueprint(city_bp, url_prefix="/api")
app.register_blueprint(upload_bp, url_prefix="/api")


# ==========================
# HEALTH CHECK
# ==========================
@app.route("/health")
def health():
    return jsonify({"status": "ok"})


# ==========================
# DASHBOARD FALLBACK
# ==========================
@app.route("/")
def serve_dashboard():
    dashboard_path = os.path.join(app.static_folder, "dashboard.html")

    if os.path.exists(dashboard_path):
        return send_from_directory(app.static_folder, "dashboard.html")

    return "<h3>Frontend deployed on Vercel. Backend active.</h3>"


# ==========================
# GLOBAL AQI ENDPOINT (unchanged)
# ==========================
@app.route("/api/global_aqi")
def global_aqi():
    import json, requests

    coords_file = os.path.join(BASE_DIR, "data", "city_coordinates.json")
    if not os.path.exists(coords_file):
        return jsonify({"error": "city_coordinates.json missing"}), 500

    with open(coords_file) as f:
        data = json.load(f)

    results = {}
    for city, info in list(data.items())[:300]:
        try:
            url = (
                "https://air-quality-api.open-meteo.com/v1/air-quality?"
                f"latitude={info['lat']}&longitude={info['lon']}&hourly=us_aqi,pm10,pm2_5"
            )
            j = requests.get(url, timeout=5).json()
            results[city] = {
                "aqi": j["hourly"]["us_aqi"][-1],
                "pm25": j["hourly"]["pm2_5"][-1],
                "pm10": j["hourly"]["pm10"][-1],
            }
        except:
            results[city] = {"aqi": None, "pm25": None, "pm10": None}

    return jsonify(results)


@app.route("/api/db_test")
def db_test():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT NOW();")
        row = cur.fetchone()
        cur.close()
        conn.close()
        return {"db_status": "connected", "now": str(row[0])}
    except Exception as e:
        return {"db_status": "error", "message": str(e)}, 500

# ==========================
# LOCAL MODE
# ==========================
if __name__ == "__main__":
    app.run(debug=True, port=5000)
