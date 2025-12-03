# backend/routes/short_term_routes.py
from flask import Blueprint, jsonify, request, current_app
import requests
import math
from datetime import datetime, timedelta

short_term_bp = Blueprint("short_term_bp", __name__)

ML_SERVER_URL = "https://extollingly-superfunctional-graciela.ngrok-free.dev"

def downsample_monthly_to_days(monthly_forecast, horizon_days):
    """monthly_forecast: list of {date: 'YYYY-MM-DD', predicted_aqi: float}
       returns list of length horizon_days with daily estimates by repeating / linear interp.
    """
    if not monthly_forecast or horizon_days <= 0:
        return []
    # simple approach: repeat monthly value across that month's days proportionally
    # Build list of daily values by mapping each monthly value to approx 30 days each
    daily = []
    for mf in monthly_forecast:
        val = mf.get("predicted_aqi") if "predicted_aqi" in mf else (mf.get("hybrid_pred") or mf.get("prophet_pred") or 0)
        # clamp/convert
        try:
            v = float(val)
        except Exception:
            v = 0.0
        # assume 30 days per month for simplicity
        repeat_days = 30
        for _ in range(repeat_days):
            if len(daily) >= horizon_days:
                break
            daily.append(v)
        if len(daily) >= horizon_days:
            break
    # if still short, pad with last value
    while len(daily) < horizon_days:
        daily.append(daily[-1] if daily else 0.0)
    return daily[:horizon_days]

@short_term_bp.route("/short_term_forecast", methods=["POST"])
def short_term_forecast_post():
    """
    POST /api/short_term_forecast
    Body: { "device_id": "PORTABLE-01", "horizon_days": 7 }
    Forwards request to external ML server. If external server replies that no short-term model
    is available, fallback to hybrid monthly forecast and downsample to days.
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    device_id = data.get("device_id") or data.get("city") or ""
    horizon_days = int(data.get("horizon_days", data.get("hours", 7)))

    if not device_id:
        return jsonify({"error": "device_id (or city) required"}), 400

    # First try external short_term
    try:
        resp = requests.post(
            f"{ML_SERVER_URL}/short_term",
            json={"device_id": device_id, "horizon_days": horizon_days},
            timeout=60
        )
        j = resp.json()
        # If the external service returned a clear 'No short-term model available' message, fall back
        if resp.status_code != 200 and isinstance(j, dict) and "No short-term model" in str(j.get("detail") or j.get("error") or ""):
            raise RuntimeError("No short-term model on external ML server")
        if resp.status_code == 200 and ("forecast" in j or isinstance(j, dict)):
            return j, resp.status_code
    except Exception as e:
        current_app.logger.info("External short_term failed or missing: %s -- falling back to hybrid", str(e))

    # Fallback -> call hybrid (monthly) and downsample
    try:
        # call local backend hybrid endpoint (preferred) to avoid double-proxy; modify URL if needed
        # If your backend runs at same host, call internal route by requests to local server:
        hybrid_url = request.host_url.rstrip("/") + "/api/hybrid_forecast"
        # compute months needed (ceil)
        horizon_months = max(1, math.ceil(horizon_days / 30.0))
        resp2 = requests.post(hybrid_url, json={"city": device_id, "horizon_months": horizon_months}, timeout=60)
        j2 = resp2.json()
        if resp2.status_code != 200 or "forecast" not in j2:
            # as a last resort try the external ML hybrid endpoint
            resp3 = requests.post(f"{ML_SERVER_URL}/hybrid", json={"city": device_id, "horizon_months": horizon_months}, timeout=60)
            j2 = resp3.json() if resp3.status_code == 200 else {}
        monthly = j2.get("forecast", [])
        daily = downsample_monthly_to_days(monthly, horizon_days)
        # return structure expected by frontend
        out = {
            "device_id": device_id,
            "horizon_days": horizon_days,
            "source": "fallback_hybrid",
            "daily_forecast": [{"day_index": i+1, "predicted_aqi": float(daily[i])} for i in range(len(daily))]
        }
        return jsonify(out), 200
    except Exception as e:
        current_app.logger.exception("Short-term fallback failed")
        return jsonify({"error": f"Short-term fallback failed: {str(e)}"}), 500
