# backend/backend/routes/prophet_routes.py
from flask import Blueprint, jsonify, request
import requests

prophet_bp = Blueprint("prophet_bp", __name__)

ML_SERVER_URL = "https://extollingly-superfunctional-graciela.ngrok-free.dev"

# POST route defined first to ensure proper registration
@prophet_bp.route("/prophet_forecast", methods=["POST"])
def prophet_forecast_post():
    """
    POST /api/prophet_forecast
    Body: { "city": "<city>", "horizon_days": 7 }
    Forwards request to external ML server.
    """
    try:
        data = request.get_json(force=True)
        city = data.get("city")
        horizon = data.get("horizon_days", 7)

        resp = requests.post(
            f"{ML_SERVER_URL}/prophet",
            json={"city": city, "horizon_days": horizon},
            timeout=40
        )
        return resp.json(), resp.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@prophet_bp.route("/get_forecast/<path:city>", methods=["GET"])
def get_forecast(city):
    """
    GET /api/get_forecast/<city>?periods=12
    Forwards request to external ML server.
    """
    try:
        # Convert periods (months) to horizon_days (approximate: periods * 30)
        periods = int(request.args.get("periods", 12))
        horizon_days = periods * 30  # Approximate conversion

        resp = requests.post(
            f"{ML_SERVER_URL}/prophet",
            json={"city": city, "horizon_days": horizon_days},
            timeout=40
        )
        return resp.json(), resp.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to get prophet forecast: {str(e)}"}), 500