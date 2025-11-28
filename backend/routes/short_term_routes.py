# backend/backend/routes/short_term_routes.py

from flask import Blueprint, jsonify, request
from utils.short_term_utils import generate_short_term_forecast
from flask import current_app

short_term_bp = Blueprint("short_term_bp", __name__)

# POST route defined first to ensure proper registration
@short_term_bp.route("/short_term_forecast", methods=["POST"])
def short_term_forecast_post():
    """
    POST /api/short_term_forecast
    Body: { "city": "<city>", "base": 150.0 }
    """
    payload = request.get_json(silent=True) or {}
    city = payload.get("city") or ""
    if not city:
        return jsonify({"error": "Missing 'city' in body"}), 400
    try:
        base = float(payload.get("base", payload.get("base_aqi", 150.0)))
    except Exception:
        base = 150.0

    try:
        data = generate_short_term_forecast(city, base)
        return jsonify({"status": "success", "city": city, "forecast": data}), 200
    except Exception as e:
        current_app.logger.exception("Short-term forecast POST failed")
        return jsonify({"error": "Internal error generating short-term forecast", "details": str(e)}), 500

@short_term_bp.route("/short_term/<city>", methods=["GET"])
def short_term(city):
    base = request.args.get("base", None)
    try:
        base = float(base) if base else 150.0
    except:
        base = 150.0

    data = generate_short_term_forecast(city, base)
    return jsonify({
        "city": city,
        "base_aqi": base,
        "forecast": data
    })
