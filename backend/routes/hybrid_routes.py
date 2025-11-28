# backend/backend/routes/hybrid_routes.py
from flask import Blueprint, jsonify, request
from utils.hybrid_utils import generate_hybrid_forecast
from flask import current_app

hybrid_bp = Blueprint("hybrid_bp", __name__)

# POST route must be defined BEFORE GET route with path parameter to ensure correct matching
@hybrid_bp.route("/hybrid_forecast", methods=["POST"])
def hybrid_forecast_post():
    """
    POST /api/hybrid_forecast
    Body: { "city": "<city name>", "horizon_months": 3 }
    This wrapper accepts frontend-style POST and forwards to existing generator.
    """
    payload = request.get_json(silent=True) or {}
    city = payload.get("city") or ""
    if not city:
        return jsonify({"error": "Missing 'city' in body"}), 400
    try:
        horizon = int(payload.get("horizon_months", payload.get("horizon", 24)))
    except Exception:
        return jsonify({"error": "Invalid horizon_months; must be integer"}), 400

    # Reuse existing function logic by calling the internal generator
    try:
        result = generate_hybrid_forecast(city, horizon_months=horizon)
        if not result:
            return jsonify({"error": "No forecast generated"}), 500
        if "error" in result:
            return jsonify(result), 404

        return jsonify({
            "status": "success",
            "city": result.get("city", city),
            "forecast_horizon_months": result.get("forecast_horizon_months", horizon),
            "forecast_count": len(result.get("forecast", [])),
            "forecast": result.get("forecast", []),
            "message": "Hybrid forecast generated successfully (POST wrapper)"
        }), 200
    except FileNotFoundError as fnf:
        return jsonify({"error": str(fnf)}), 404
    except Exception as e:
        current_app.logger.exception("Hybrid forecast POST failed")
        return jsonify({"error": "Internal error generating hybrid forecast", "details": str(e)}), 500

@hybrid_bp.route("/hybrid_forecast/<path:city>", methods=["GET"])
def hybrid_forecast(city):
    """
    GET /api/hybrid_forecast/<city>?horizon=24
    city can include spaces (URL-encoded). horizon is months (int).
    """
    # get horizon from querystring (default 24)
    horizon = request.args.get("horizon", default=24)
    try:
        horizon = int(horizon)
    except Exception:
        return jsonify({"error": "Invalid horizon. Must be integer months."}), 400

    try:
        result = generate_hybrid_forecast(city, horizon_months=horizon)

        # If a function encountered a model-not-found, it returns {"error": "..."}
        if not result:
            return jsonify({"error": "No forecast generated"}), 500
        if "error" in result:
            # return 404 for model-not-found-like errors, 400 for invalid input if used
            return jsonify(result), 404

        # success
        return jsonify({
            "status": "success",
            "city": result.get("city", city),
            "forecast_horizon_months": result.get("forecast_horizon_months", horizon),
            "forecast_count": len(result.get("forecast", [])),
            "forecast": result.get("forecast", []),
            "message": "Hybrid forecast generated successfully"
        }), 200

    except FileNotFoundError as fnf:
        return jsonify({"error": str(fnf)}), 404
    except Exception as e:
        # log exception server-side if you use logging (not added here to keep snippet minimal)
        return jsonify({"error": "An internal error occurred while generating hybrid forecast", "details": str(e)}), 500