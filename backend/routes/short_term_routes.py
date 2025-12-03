# backend/routes/short_term_routes.py
from flask import Blueprint, jsonify, request, current_app
import requests
import math
from datetime import datetime, timedelta

short_term_bp = Blueprint("short_term_bp", __name__)

ML_SERVER_URL = "https://jacksonville-save-manchester-graduation.trycloudflare.com"

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
def short_term_forecast():
    data = request.get_json()
    city = data.get("city")
    hours = data.get("hours", 48)

    if not city:
        return jsonify({"error": "Missing city"}), 400

    # --- Try direct short-term model (if available)
    try:
        response = requests.post(
            f"{ML_SERVER_URL}/short_term",
            json={"city": city, "hours": hours},
            timeout=40
        )

        if response.status_code == 200:
            return jsonify(response.json())
    except Exception as e:
        print("Short-term request failed:", e)

    # --- FALLBACK: Use hybrid forecast but convert to short-term style
    try:
        # 1 month hybrid forecast (converted to 48 hours equivalent)
        fallback_payload = {"city": city, "horizon_months": 1}
        hybrid_resp = requests.post(
            f"{ML_SERVER_URL}/hybrid",
            json=fallback_payload,
            timeout=40
        )

        if hybrid_resp.status_code == 200:
            hybrid_data = hybrid_resp.json()
            daily = hybrid_data.get("forecast", [])

            short = []
            for i, d in enumerate(daily[:2]):  # Convert first 2 days → 48 hours
                short.append({"hour_index": i * 24, "predicted_aqi": d["predicted_aqi"]})

            return jsonify({
                "source": "fallback_hybrid",
                "city": city,
                "hours": hours,
                "forecast": short
            })
    except Exception as e:
        print("Hybrid fallback failed:", e)

    return jsonify({"error": "Short-term forecast unavailable"}), 500
