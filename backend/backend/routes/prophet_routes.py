# backend/backend/routes/prophet_routes.py

from flask import Blueprint, jsonify, request
import os
import pandas as pd

# NEW — unified loader
from model_fetcher import load_joblib

prophet_bp = Blueprint("prophet_bp", __name__)

# LOCAL ROOT (kept for listing & fallback)
MODEL_ROOT = os.environ.get("MODEL_DIR", "models")
LOCAL_PROPHET_DIR = os.path.join(MODEL_ROOT, "prophet_models")


@prophet_bp.route("/get_forecast/<city>", methods=["GET"])
def get_forecast(city):
    """
    Loads prophet model from either:
    - hybrid_models/prophet_models/
    - prophet_models/
    using Supabase bucket or local fallback.
    """

    safe_city = city.replace(" ", "_")
    filename = f"{safe_city}_prophet.joblib"

    # These are possible model locations in Supabase storage
    bucket_paths = [
        f"hybrid_models/prophet_models/{filename}",
        f"prophet_models/{filename}",
    ]

    model = None
    model_file_used = None

    # Try both locations via Supabase loader
    for path in bucket_paths:
        try:
            model = load_joblib(path)
            model_file_used = path
            break
        except Exception:
            model = None

    # If still not found, try local folder fallback
    if model is None:
        local_path_1 = os.path.join(MODEL_ROOT, "hybrid_models", "prophet_models", filename)
        local_path_2 = os.path.join(MODEL_ROOT, "prophet_models", filename)

        if os.path.exists(local_path_1):
            model = load_joblib(f"hybrid_models/prophet_models/{filename}")
            model_file_used = local_path_1
        elif os.path.exists(local_path_2):
            model = load_joblib(f"prophet_models/{filename}")
            model_file_used = local_path_2

    # If still missing:
    if model is None:
        return jsonify({
            "error": f"Prophet model for '{city}' not found.",
            "tried": bucket_paths
        }), 404

    # Forecast logic
    try:
        periods = int(request.args.get("periods", 12))

        future = model.make_future_dataframe(periods=periods, freq="M")
        forecast = model.predict(future)

        result = forecast[["ds", "yhat"]].tail(periods).to_dict(orient="records")

        return jsonify({
            "city": city,
            "model_used": model_file_used,
            "forecast_periods": periods,
            "forecast": result
        })

    except Exception as e:
        return jsonify({"error": f"Forecast generation failed: {e}"}), 500
