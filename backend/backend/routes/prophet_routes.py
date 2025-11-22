# backend/backend/routes/prophet_routes.py
from flask import Blueprint, jsonify, request
import os, pandas as pd
from prophet import Prophet
from model_loader import load_model  # load_model(filename, folder)

prophet_bp = Blueprint("prophet_bp", __name__)

MODEL_ROOT = os.environ.get("MODEL_DIR", "models")
LOCAL_PROPHET_DIR = os.path.join(MODEL_ROOT, "prophet_models")  # for local listing only
HYBRID_PROPHET_SUBPATH = "hybrid_models/prophet_models"

@prophet_bp.route("/get_forecast/<path:city>", methods=["GET"])
def get_forecast(city):
    """Return Prophet forecast for the specified city."""
    safe_city = city.strip().replace(" ", "_")
    filename = f"{safe_city}_prophet.joblib"

    # Try multiple candidate folders (hybrid subfolder first, then top-level)
    candidates = [
        f"{HYBRID_PROPHET_SUBPATH}/{filename}",
        f"prophet_models/{filename}"
    ]

    model = None
    used_path = None
    for cand in candidates:
        # cand is like "hybrid_models/prophet_models/City_prophet.joblib" or "prophet_models/City_prophet.joblib"
        try:
            # load_model expects filename and folder; split cand
            folder, fname = cand.rsplit("/", 1)
            model = load_model(fname, folder)
            used_path = cand
            break
        except FileNotFoundError:
            model = None
            continue
        except Exception as e:
            return jsonify({"error": f"Failed loading model {cand}: {e}"}), 500

    if model is None:
        return jsonify({"error": f"Prophet model for {city} not found."}), 404

    try:
        # Allow optional query params
        periods = int(request.args.get("periods", 12))
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

        if start_date and end_date:
            future_dates = pd.date_range(start=start_date, end=end_date, freq='M')
            future = pd.DataFrame({"ds": future_dates})
        else:
            future = model.make_future_dataframe(periods=periods, freq='M')

        forecast = model.predict(future)
        # Return only ds + yhat (or more if you prefer)
        fields = ["ds", "yhat", "yhat_lower", "yhat_upper"]
        forecast_df = forecast[fields] if all(col in forecast.columns for col in fields) else forecast
        # Limit to last 'periods' rows for default case
        if not start_date and not end_date:
            forecast_df = forecast_df.tail(periods)

        result = forecast_df.to_dict(orient="records")
        return jsonify({"city": city, "model_used": used_path, "forecast": result})
    except Exception as e:
        return jsonify({"error": f"Forecast generation failed: {e}"}), 500
