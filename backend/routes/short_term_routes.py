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
    Body: { "city": "Mumbai", "hours": 48 } or { "device_id": "PORTABLE-01", "hours": 48 }
    Forwards request to external ML server. If external server replies that no short-term model
    is available, fallback to hybrid monthly forecast and convert to hourly predictions.
    """
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON body"}), 400

    city = data.get("city") or data.get("device_id") or ""
    hours = int(data.get("hours", data.get("horizon_days", 48)))
    
    if not city:
        return jsonify({"error": "city (or device_id) required"}), 400

    # First try external short_term endpoint
    try:
        resp = requests.post(
            f"{ML_SERVER_URL}/short_term",
            json={"city": city, "hours": hours},
            timeout=40
        )
        resp_data = resp.json()
        
        # Check if ML server explicitly says no short-term model available
        error_msg = str(resp_data.get("detail", "") or resp_data.get("error", "")).lower()
        if "no short-term model" in error_msg or "short_term error" in error_msg:
            raise RuntimeError("No short-term model available on ML server")
        
        # If successful response with forecast data
        if resp.status_code == 200:
            # Check if response has forecast data
            if "forecast" in resp_data or "hourly" in resp_data or isinstance(resp_data, list):
                return jsonify(resp_data), 200
    except RuntimeError:
        # Explicitly raised when no model available - proceed to fallback
        current_app.logger.info("Short-term model not available, using hybrid fallback")
        pass
    except Exception as e:
        current_app.logger.info(f"External short_term request failed: {e} -- falling back to hybrid")

    # FALLBACK: Use hybrid forecast and convert to hourly predictions
    try:
        # Get hybrid forecast for next 2 months (enough for 48 hours)
        horizon_months = max(1, math.ceil(hours / (24 * 30)))  # Convert hours to months (approx)
        
        hybrid_resp = requests.post(
            f"{ML_SERVER_URL}/hybrid",
            json={"city": city, "horizon_months": horizon_months},
            timeout=40
        )
        
        if hybrid_resp.status_code != 200:
            raise Exception(f"Hybrid forecast returned status {hybrid_resp.status_code}")
        
        hybrid_data = hybrid_resp.json()
        forecast_list = hybrid_data.get("forecast", [])
        
        if not forecast_list:
            raise Exception("Hybrid forecast returned empty data")
        
        # Convert daily/monthly forecast to hourly predictions
        # Take first few days and interpolate to hourly
        hourly_forecast = []
        days_needed = math.ceil(hours / 24)
        
        for i, day_data in enumerate(forecast_list[:days_needed]):
            # Get AQI value for this day
            aqi_value = day_data.get("predicted_aqi") or day_data.get("aqi") or 0
            try:
                aqi_value = float(aqi_value)
            except (ValueError, TypeError):
                aqi_value = 0.0
            
            # Create 24 hourly entries for this day (or remaining hours)
            hours_for_day = min(24, hours - len(hourly_forecast))
            for h in range(hours_for_day):
                hourly_forecast.append({
                    "hour_index": len(hourly_forecast),
                    "predicted_aqi": aqi_value
                })
            
            if len(hourly_forecast) >= hours:
                break
        
        # If we still need more hours, repeat last value
        while len(hourly_forecast) < hours:
            last_aqi = hourly_forecast[-1]["predicted_aqi"] if hourly_forecast else 0.0
            hourly_forecast.append({
                "hour_index": len(hourly_forecast),
                "predicted_aqi": last_aqi
            })
        
        # Return structure expected by frontend
        return jsonify({
            "city": city,
            "hours": hours,
            "source": "fallback_hybrid",
            "forecast": hourly_forecast[:hours]
        }), 200
        
    except Exception as e:
        current_app.logger.exception("Short-term fallback failed")
        return jsonify({"error": f"Short-term forecast unavailable: {str(e)}"}), 500
