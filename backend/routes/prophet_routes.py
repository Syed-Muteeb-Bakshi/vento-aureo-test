# backend/backend/routes/prophet_routes.py
from flask import Blueprint, jsonify, request
import os, pandas as pd
from model_loader import load_joblib

prophet_bp = Blueprint("prophet_bp", __name__)

PROPHET_PREFIXS = [
    "hybrid_models/prophet_models",  # prefer hybrid folder
    "prophet_models"
]

@prophet_bp.route("/get_forecast/<path:city>", methods=["GET"])
def get_forecast(city):
    safe_city = city.strip().replace(" ", "_")
    filename = f"{safe_city}_prophet.joblib"
    model = None
    model_used_path = None
    for prefix in PROPHET_PREFIXS:
        try:
            model = load_joblib(filename, prefix)
            model_used_path = f"{prefix}/{filename}"
            break
        except Exception:
            model = None
    if model is None:
        return jsonify({"error": f"Prophet model for {city} not found."}), 404

    try:
        # default 12 months
        periods = int(request.args.get("periods", 12))
        if hasattr(model, "make_future_dataframe"):
            future = model.make_future_dataframe(periods=periods, freq="M")
            forecast = model.predict(future)
            result = forecast[["ds", "yhat"]].tail(periods).to_dict(orient="records")
        elif isinstance(model, pd.DataFrame):
            result = model.to_dict(orient="records")
        else:
            result = []
        return jsonify({"city": city, "model_file": model_used_path, "forecast": result})
    except Exception as e:
        return jsonify({"error": f"Forecast generation failed: {e}"}), 500
