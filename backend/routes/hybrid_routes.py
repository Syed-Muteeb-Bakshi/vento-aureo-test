# backend/backend/routes/hybrid_routes.py
from flask import Blueprint, jsonify, request
import requests

hybrid_bp = Blueprint("hybrid_bp", __name__)

ML_SERVER_URL = "https://extollingly-superfunctional-graciela.ngrok-free.dev"

# POST route must be defined BEFORE GET route with path parameter to ensure correct matching
@hybrid_bp.route("/hybrid_forecast", methods=["POST"])
def hybrid_forecast_post():
    """
    POST /api/hybrid_forecast
    Body: { "city": "<city name>", "horizon_months": 3 }
    Forwards request to external ML server.
    """
    try:
        data = request.get_json(force=True)
        city = data.get("city")
        horizon = data.get("horizon_months", 12)

        resp = requests.post(
            f"{ML_SERVER_URL}/hybrid",
            json={"city": city, "horizon_months": horizon},
            timeout=40
        )
        return resp.json(), resp.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@hybrid_bp.route("/hybrid_forecast/<path:city>", methods=["GET"])
def hybrid_forecast(city):
    """
    GET /api/hybrid_forecast/<city>?horizon=24
    city can include spaces (URL-encoded). horizon is months (int).
    Forwards request to external ML server.
    """
    # get horizon from querystring (default 24)
    horizon = request.args.get("horizon", default=24)
    try:
        horizon = int(horizon)
    except Exception:
        return jsonify({"error": "Invalid horizon. Must be integer months."}), 400

    try:
        resp = requests.post(
            f"{ML_SERVER_URL}/hybrid",
            json={"city": city, "horizon_months": horizon},
            timeout=40
        )
        return resp.json(), resp.status_code
    except Exception as e:
        return jsonify({"error": f"Failed to get hybrid forecast: {str(e)}"}), 500