# backend/backend/routes/short_term_routes.py

from flask import Blueprint, jsonify, request
import requests

short_term_bp = Blueprint("short_term_bp", __name__)

API_BASE = "https://summaries-game-hypothesis-chapel.trycloudflare.com"

# POST route defined first to ensure proper registration
@short_term_bp.route("/short_term_forecast", methods=["POST"])
def short_term_forecast_post():
    """
    POST /api/short_term_forecast
    Body: { "device_id": "PORTABLE-01", "horizon_days": 7 }
    Forwards request to external ML server.
    """
    try:
        data = request.get_json(force=True)
        device_id = data.get("device_id")
        horizon = data.get("horizon_days", 7)

        resp = requests.post(
            f"{API_BASE}/short_term",
            json={"device_id": device_id, "horizon_days": horizon},
            timeout=60
        )
        return resp.json(), resp.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@short_term_bp.route("/short_term/<city>", methods=["GET"])
def short_term(city):
    """
    GET /api/short_term/<city>?base=150.0
    Legacy endpoint - converts to device_id format for external ML server.
    """
    try:
        # For GET requests, use city as device_id (legacy compatibility)
        horizon_days = 7  # Default horizon
        
        resp = requests.post(
            f"{API_BASE}/short_term",
            json={"device_id": city, "horizon_days": horizon_days},
            timeout=60
        )
        return resp.json(), resp.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to get short-term forecast: {str(e)}"}), 500
