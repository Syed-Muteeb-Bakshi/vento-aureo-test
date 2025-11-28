# backend/backend/routes/forecast_routes.py
import os
import pandas as pd
from flask import Blueprint, jsonify, request
from model_loader import load_joblib
import model_paths

forecast_bp = Blueprint("forecast", __name__)
MODEL_PREFIX = "prophet_models"

@forecast_bp.route("/get_forecast/<path:city>", methods=["GET"])
def get_forecast(city):
    city_clean = city.strip().replace(" ", "_").replace(",", "_").lower()
    filename = f"{city_clean}_prophet.joblib"

    # Try direct load via loader (which will check local/GCS)
    try:
        model_obj = load_joblib(filename, MODEL_PREFIX)
    except Exception as e:
        return jsonify({
            "error": f"No forecast found for '{city}'.",
            "details": str(e)
        }), 404

    try:
        periods = int(request.args.get("periods", 12))
        if hasattr(model_obj, "make_future_dataframe"):
            future = model_obj.make_future_dataframe(periods=periods, freq='M')
            forecast_df = model_obj.predict(future)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
            if not request.args.get("start_date") and not request.args.get("end_date"):
                forecast_df = forecast_df.tail(periods)
        elif isinstance(model_obj, pd.DataFrame):
            forecast_df = model_obj
        else:
            forecast_df = pd.DataFrame()
        forecast_data = forecast_df.to_dict(orient="records")
        return jsonify({
            "city": city,
            "model_file": filename,
            "forecast": forecast_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@forecast_bp.route("/list_cities", methods=["GET"])
def list_cities():
    """
    Scan ALL model directories for available cities:
    - hybrid_models/prophet_models
    - prophet_models
    - uploaded_models (optional)
    Returns sorted list of clean city names.
    """
    # model_paths defines local model paths as constants
    try:
        model_dir = os.environ.get("MODEL_DIR", model_paths.LOCAL_MODEL_ROOT)
    except Exception:
        model_dir = os.environ.get("MODEL_DIR", "/var/models")

    candidates = [
        os.path.join(model_dir, "hybrid_models", "prophet_models"),
        os.path.join(model_dir, "prophet_models"),
        os.path.join(model_dir, "uploaded_models"),  # optional uploaded models
    ]

    cities = set()  # Use set to avoid duplicates
    for folder in candidates:
        try:
            if not os.path.exists(folder):
                continue
            for f in os.listdir(folder):
                if f.endswith(".joblib"):
                    # Extract city name from filename
                    # Handle both "_prophet.joblib" and just ".joblib" endings
                    clean = f.replace("_prophet.joblib", "").replace(".joblib", "")
                    clean = clean.replace("_", " ").strip()
                    if clean:
                        cities.add(clean.title())
        except Exception as e:
            # Log but continue scanning other directories
            continue
    
    # Also try to get cities from city_coordinates.json as fallback
    if not cities:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            coords_file = os.path.join(base_dir, "data", "city_coordinates.json")
            if os.path.exists(coords_file):
                import json
                with open(coords_file, "r", encoding="utf-8") as f:
                    coords_data = json.load(f)
                    cities.update(coords_data.keys())
        except Exception:
            pass
    
    return jsonify(sorted(list(cities)))
