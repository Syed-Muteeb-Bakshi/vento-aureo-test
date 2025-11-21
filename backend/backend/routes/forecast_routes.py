# backend/backend/routes/forecast_routes.py

import os
import pandas as pd
from flask import Blueprint, jsonify, request

from model_fetcher import load_joblib

forecast_bp = Blueprint("forecast", __name__)

MODEL_ROOT = os.environ.get("MODEL_DIR", "models")
LOCAL_PROPHET_DIR = os.path.join(MODEL_ROOT, "prophet_models")
LOCAL_HYBRID_PROPHET_DIR = os.path.join(MODEL_ROOT, "hybrid_models", "prophet_models")


@forecast_bp.route("/get_forecast/<city>", methods=["GET"])
def get_forecast(city):
    """
    Try to load prophet joblib from:
      - prophet_models/<city>_prophet.joblib
      - hybrid_models/prophet_models/<city>_prophet.joblib
    Accepts ?periods=N (months)
    """
    city_clean = city.strip().replace(" ", "_").replace(",", "_").lower()
    filename = f"{city_clean}_prophet.joblib"
    bucket_variants = [
        f"prophet_models/{filename}",
        f"hybrid_models/prophet_models/{filename}"
    ]

    model_obj = None
    model_used = None

    # try remote/local via model_fetcher
    for variant in bucket_variants:
        try:
            model_obj = load_joblib(variant)
            model_used = variant
            break
        except Exception:
            model_obj = None

    # As final fallback attempt local file direct path (transparent)
    if model_obj is None:
        local1 = os.path.join(LOCAL_PROPHET_DIR, filename)
        local2 = os.path.join(LOCAL_HYBRID_PROPHET_DIR, filename)
        if os.path.exists(local1):
            model_obj = load_joblib(f"prophet_models/{filename}")
            model_used = local1
        elif os.path.exists(local2):
            model_obj = load_joblib(f"hybrid_models/prophet_models/{filename}")
            model_used = local2

    if model_obj is None:
        return jsonify({
            "error": f"No forecast model found for '{city}'",
            "tried": bucket_variants
        }), 404

    # Get periods param
    try:
        periods = int(request.args.get("periods", 12))
    except Exception:
        periods = 12

    try:
        # if saved object is Prophet model instance
        try:
            future = model_obj.make_future_dataframe(periods=periods, freq="M")
            forecast_df = model_obj.predict(future)[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
            if periods:
                forecast_df = forecast_df.tail(periods)
        except Exception:
            # maybe the saved object was already a DataFrame (precomputed)
            if isinstance(model_obj, pd.DataFrame):
                forecast_df = model_obj
            else:
                return jsonify({"error": "Loaded object is not a Prophet model or DataFrame."}), 500

        forecast_data = forecast_df.to_dict(orient="records")
        return jsonify({
            "city": city,
            "model_file": model_used,
            "forecast_periods": periods,
            "forecast": forecast_data
        })
    except Exception as e:
        return jsonify({"error": f"Forecast failed: {e}"}), 500


@forecast_bp.route("/list_cities", methods=["GET"])
def list_cities():
    # Try to list local files under MODEL_ROOT/prophet_models
    lst = []
    try:
        local_dir = os.path.join(MODEL_ROOT, "prophet_models")
        if os.path.isdir(local_dir):
            for f in os.listdir(local_dir):
                if f.endswith(".joblib"):
                    clean = f.replace("_prophet.joblib", "").replace("_", " ").title()
                    lst.append(clean)
    except Exception:
        pass
    return jsonify(sorted(lst))
