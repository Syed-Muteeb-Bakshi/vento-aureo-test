import os
import json
import joblib
import pandas as pd
from flask import Blueprint, jsonify, request
from difflib import get_close_matches
from prophet import Prophet

forecast_bp = Blueprint("forecast", __name__)

# Proper path to models
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "..", "models", "prophet_models")

@forecast_bp.route("/get_forecast/<city>", methods=["GET"])
def get_forecast(city):
    city_clean = city.strip().replace(" ", "_").replace(",", "_").lower()
    model_name = f"{city_clean}_prophet.joblib"

    if not os.path.exists(MODEL_DIR):
        return jsonify({"error": f"Model directory not found: {MODEL_DIR}"}), 500

    all_models = [f for f in os.listdir(MODEL_DIR) if f.endswith(".joblib")]

    # Try to find exact match (case-insensitive)
    matched_model = next((m for m in all_models if m.lower() == model_name), None)
    if not matched_model:
        # Try partial match
        matched_model = next((m for m in all_models if city_clean in m.lower()), None)

    if not matched_model:
        return jsonify({
            "error": f"No forecast found for '{city}'",
            "suggestions": all_models[:5]
        }), 404

    model_path = os.path.join(MODEL_DIR, matched_model)

    try:
        model_obj = joblib.load(model_path)

        # --- NEW: Read optional query params ---
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        periods = int(request.args.get("periods", 12))  # default 12 months

        # --- Handle Prophet model ---
        if isinstance(model_obj, Prophet):
            if start_date and end_date:
                # Use custom date range if provided
                future_dates = pd.date_range(start=start_date, end=end_date, freq='M')
                future = pd.DataFrame({"ds": future_dates})
            else:
                # Default forecast period
                future = model_obj.make_future_dataframe(periods=periods, freq='M')

            forecast_df = model_obj.predict(future)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
            if not start_date and not end_date:
                forecast_df = forecast_df.tail(periods)

        # --- Handle precomputed forecast DataFrame ---
        elif isinstance(model_obj, pd.DataFrame):
            forecast_df = model_obj

        else:
            forecast_df = pd.DataFrame()

        forecast_data = forecast_df.to_dict(orient="records")

        # Return with metadata
        return jsonify({
            "city": city,
            "model_file": matched_model,
            "forecast": forecast_data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@forecast_bp.route("/list_cities", methods=["GET"])
def list_cities():
    if not os.path.exists(MODEL_DIR):
        return jsonify([])

    cities = []
    for f in os.listdir(MODEL_DIR):
        if f.endswith(".joblib"):
            clean = f.replace("_prophet.joblib", "").replace("_", " ").title()
            cities.append(clean)
    return jsonify(sorted(cities))
