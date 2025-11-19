from flask import Blueprint, jsonify
import os, joblib, pandas as pd

prophet_bp = Blueprint("prophet_bp", __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
PROPHET_DIR = os.path.join(BASE_DIR, "models", "hybrid_models", "prophet_models")

@prophet_bp.route("/get_forecast/<city>", methods=["GET"])
def get_forecast(city):
    """Return Prophet forecast for the specified city."""
    safe_city = city.replace(" ", "_")
    model_path = os.path.join(PROPHET_DIR, f"{safe_city}_prophet.joblib")

    if not os.path.exists(model_path):
        return jsonify({"error": f"Prophet model for {city} not found."}), 404

    try:
        model = joblib.load(model_path)
        future = model.make_future_dataframe(periods=12, freq="M")
        forecast = model.predict(future)
        result = forecast[["ds", "yhat"]].tail(12).to_dict(orient="records")
        return jsonify({"city": city, "forecast": result})
    except Exception as e:
        return jsonify({"error": f"Forecast generation failed: {e}"}), 500
