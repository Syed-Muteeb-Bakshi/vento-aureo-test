# backend/backend/app.py

import os
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import json, requests

# -----------------------------------------------------
# Blueprint imports (correct for your file structure)
# -----------------------------------------------------
from routes.forecast_routes import forecast_bp
from routes.iot_routes import iot_bp
from routes.ml_routes import ml_bp
from routes.live_aqi_routes import live_aqi_bp
from routes.trivia_routes import trivia_bp
from routes.hybrid_routes import hybrid_bp
from routes.prophet_routes import prophet_bp
from routes.short_term_routes import short_term_bp
from routes.city_aqi_routes import city_bp

# -----------------------------------------------------
# Basic App Setup
# -----------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))      # backend/backend
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "..", "frontend")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__, static_folder=FRONTEND_DIR, template_folder=TEMPLATES_DIR)
CORS(app)

# -----------------------------------------------------
# Register Blueprints
# -----------------------------------------------------
app.register_blueprint(forecast_bp, url_prefix="/api")
app.register_blueprint(iot_bp, url_prefix="/api")
app.register_blueprint(ml_bp, url_prefix="/api")
app.register_blueprint(live_aqi_bp, url_prefix="/api")
app.register_blueprint(hybrid_bp, url_prefix="/api")
app.register_blueprint(trivia_bp, url_prefix="/api")
app.register_blueprint(prophet_bp, url_prefix="/api")
app.register_blueprint(short_term_bp, url_prefix="/api")
app.register_blueprint(city_bp, url_prefix="/api")

# -----------------------------------------------------
# Serve dashboard.html
# -----------------------------------------------------
@app.route("/")
def serve_dashboard():
    static_dashboard = os.path.join(app.static_folder, "dashboard.html")
    template_dashboard = os.path.join(app.template_folder, "dashboard.html")

    if os.path.exists(static_dashboard):
        return send_from_directory(app.static_folder, "dashboard.html")

    if os.path.exists(template_dashboard):
        return send_from_directory(app.template_folder, "dashboard.html")

    return (
        "<h3 style='color:red;text-align:center;margin-top:40px;'>Dashboard file not found.</h3>"
        "<p style='text-align:center'>Put <code>dashboard.html</code> in frontend/ or backend/backend/templates/</p>",
        404,
    )


# -----------------------------------------------------
# GLOBAL AQI ENDPOINT
# -----------------------------------------------------
@app.route("/api/global_aqi")
def global_aqi():
    coords_file = os.path.join(BASE_DIR, "data", "city_coordinates.json")

    if not os.path.exists(coords_file):
        return jsonify({"error": "Coordinates file not ready"}), 500

    with open(coords_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    results = {}

    for city, info in list(data.items())[:300]:
        lat, lon = info["lat"], info["lon"]

        try:
            url = (
                f"https://air-quality-api.open-meteo.com/v1/air-quality?"
                f"latitude={lat}&longitude={lon}&hourly=us_aqi,pm10,pm2_5"
            )
            j = requests.get(url, timeout=5).json()

            results[city] = {
                "aqi": j["hourly"]["us_aqi"][-1],
                "pm25": j["hourly"]["pm2_5"][-1],
                "pm10": j["hourly"]["pm10"][-1],
                "lat": lat,
                "lon": lon
            }

        except:
            results[city] = {"aqi": None, "pm25": None, "pm10": None}

    return jsonify(results)


# -----------------------------------------------------
# Short-Term Forecast API
# -----------------------------------------------------

# -----------------------------------------------------
# RUN SERVER
# -----------------------------------------------------
if __name__ == "__main__":
    os.chdir(BASE_DIR)
    app.run(host="0.0.0.0", port=5000, debug=True)
