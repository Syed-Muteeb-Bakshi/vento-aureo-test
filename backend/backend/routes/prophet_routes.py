# backend/backend/routes/prophet_routes.py
from flask import Blueprint, jsonify, request
import os, pandas as pd

from model_loader import load_model  # new loader

prophet_bp = Blueprint("prophet_bp", __name__)

MODEL_ROOT = os.environ.get("MODEL_DIR", "models")
# keep local folder for listing
LOCAL_PROPHET_DIR = os.path.join(MODEL_ROOT, "prophet_models")
LOCAL_HYBRID_PROPHET_DIR = os.path.join(MODEL_ROOT, "hybrid_models", "prophet_models")


@prophet_bp.route("/get_forecast/<city>", methods=["GET"])
def get_forecast(city):
    """Return Prophet forecast for the specified city."""
    safe_city = city.replace(" ", "_")
    filename = f"{safe_city}_prophet.joblib"

    # Prefer hybrid location first, then top-level prophet_models
    candidate_paths = [
        ("hybrid_models/prophet_models", filename),
        ("prophet_models", filename)
    ]

    model = None
    used_path = None
    for subfolder, fname in candidate_paths:
        try:
            model = load_model(fname, subfolder=subfolder)
            used_path = f"{subfolder}/{fname}"
            break
        except FileNotFoundError:
            model = None
            continue
        except Exception as e:
            return jsonify({"error": f"Failed to load model: {e}"}), 500

    if model is None:
        return jsonify({"error": f"Prophet model for {city} not found."}), 404

    try:
        # optional query param to control horizon/periods
        periods = int(request.args.get("periods", 12))
        # If it's a Prophet model object, use as such; otherwise if DataFrame passed, handle accordingly
        if hasattr(model, "make_future_dataframe"):
            future = model.make_future_dataframe(periods=periods, freq="M")
            forecast = model.predict(future)
            result = forecast[["ds", "yhat"]].tail(periods).to_dict(orient="records")
        elif isinstance(model, pd.DataFrame):
            # precomputed DataFrame
            result = model.tail(periods)[["ds", "yhat"]].to_dict(orient="records")
        else:
            return jsonify({"error": "Unsupported model object type."}), 500

        return jsonify({"city": city, "model_file": used_path, "forecast": result})
    except Exception as e:
        return jsonify({"error": f"Forecast generation failed: {e}"}), 500
