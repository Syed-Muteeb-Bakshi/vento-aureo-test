# backend/backend/utils/hybrid_utils.py
import os
import re
import unicodedata
import numpy as np
import pandas as pd

from model_fetcher import load_joblib, load_keras
from model_paths import PATH_HYBRID_MODELS

# Build model root path (string)
MODEL_ROOT = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "..", "models"))
HYBRID_ROOT = PATH_HYBRID_MODELS  # local path
PROPHET_SUBFOLDER = "prophet_models"
LSTM_SUBFOLDER = "lstm_models"
HYBRID_OUTPUT_DIRNAME = "outputs"


def _normalize_name(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'[^0-9a-z]+', '', s.lower())
    return s


def _try_load_joblib_candidates(cands):
    for candidate in cands:
        try:
            return load_joblib(candidate), candidate
        except Exception:
            continue
    return None, None


def load_prophet_model_for_city(city: str):
    """
    Try to find the best prophet model for `city`.
    Search order:
      1) local hybrid_models/prophet_models/<file>
      2) local prophet_models/<file> (if present outside hybrid)
      3) remote (Supabase) same paths via load_joblib
    """
    city_raw = city
    city_norm = _normalize_name(re.sub(r"[,._]+", " ", city).strip())

    # list candidate filenames from local hybrid folder if available
    local_dir = os.path.join(HYBRID_ROOT, PROPHET_SUBFOLDER)
    all_files = []
    if os.path.isdir(local_dir):
        all_files = [f for f in os.listdir(local_dir) if f.endswith(".joblib")]

    # if none found locally, try the top-level prophet_models folder
    if not all_files:
        top_local = os.path.join(MODEL_ROOT, "prophet_models")
        if os.path.isdir(top_local):
            all_files = [f for f in os.listdir(top_local) if f.endswith(".joblib")]

    # Build fuzzy candidate list from available filenames or simply try to load by standard name
    try_name = f"{city_raw.replace(' ', '_')}_prophet.joblib"
    bucket_candidates = [
        f"hybrid_models/prophet_models/{try_name}",
        f"prophet_models/{try_name}"
    ]

    # 1) Try exact candidates via model_fetcher/local
    model, used = _try_load_joblib_candidates(bucket_candidates)
    if model is not None:
        return model, used

    # 2) If we have a local listing, fuzzy-match
    if all_files:
        # Normalize file basenames
        norm_list = [(_normalize_name(os.path.splitext(f)[0]), f) for f in all_files]
        # try substring matches first
        for norm, fname in norm_list:
            if city_norm in norm or norm in city_norm:
                # try loading via hybrid path or top-level
                subpath = f"hybrid_models/prophet_models/{fname}"
                try:
                    return load_joblib(subpath), subpath
                except Exception:
                    # fallback to top-level
                    subpath2 = f"prophet_models/{fname}"
                    try:
                        return load_joblib(subpath2), subpath2
                    except Exception:
                        continue

    # 3) As last effort try remote fuzzy by attempting to download a list? (not possible)
    # So return not found
    raise FileNotFoundError(f"No Prophet model found for '{city_raw}'.")


def load_lstm_model_for_city(city: str):
    """
    Try to load a keras .keras model and associated scaler from hybrid_models/lstm_models
    Return (lstm_model, scaler_obj, filename)
    """
    city_norm = _normalize_name(city)
    # local listing
    local_lstm_dir = os.path.join(HYBRID_ROOT, LSTM_SUBFOLDER)
    if os.path.isdir(local_lstm_dir):
        files = os.listdir(local_lstm_dir)
    else:
        files = []

    # find candidate keras and scaler names by normalization match
    keras_candidates = [f for f in files if f.endswith(".keras") and city_norm in _normalize_name(f)]
    scaler_candidates = [f for f in files if f.endswith(".joblib") and "_scaler" in f and city_norm in _normalize_name(f)]

    # try remote/local loading using candidate names
    if keras_candidates:
        keras_fname = keras_candidates[0]
        keras_subpath = f"hybrid_models/lstm_models/{keras_fname}"
        try:
            lstm_model = load_keras(keras_subpath)
        except Exception:
            lstm_model = None
        scaler = None
        if scaler_candidates:
            try:
                scaler = load_joblib(f"hybrid_models/lstm_models/{scaler_candidates[0]}")
            except Exception:
                scaler = None
        return lstm_model, scaler, keras_candidates[0]

    # fallback: try to load a standard-named keras file for the city
    standard_name = f"{city.replace(' ', '_')}_lstm.keras"
    try:
        lstm_model = load_keras(f"hybrid_models/lstm_models/{standard_name}")
        return lstm_model, None, standard_name
    except Exception:
        return None, None, None


def generate_hybrid_forecast(city: str, horizon_months: int = 24):
    from datetime import datetime
    # Step 1: Load prophet model
    try:
        prophet_model, prophet_fname = load_prophet_model_for_city(city)
    except FileNotFoundError as e:
        return {"error": str(e)}

    # Step 2: try LSTM
    lstm_model, scaler, lstm_fname = load_lstm_model_for_city(city)

    start_date = datetime.now()
    future_dates = pd.date_range(start=start_date, periods=horizon_months, freq="M")
    future = pd.DataFrame({"ds": future_dates})

    try:
        forecast_prophet = prophet_model.predict(future)
    except Exception as e:
        return {"error": f"Prophet forecast failed for {city}: {e}"}

    if forecast_prophet.empty or "yhat" not in forecast_prophet.columns:
        return {"error": f"Prophet model for {city} returned no predictions."}

    yhat_values = forecast_prophet["yhat"].values

    # if no lstm, return prophet-only
    if lstm_model is None or scaler is None:
        forecast = [
            {"date": str(row["ds"].date()), "predicted_aqi": float(row["yhat"])}
            for _, row in forecast_prophet.iterrows()
        ]
        return {
            "city": city,
            "model_used": "Prophet only",
            "forecast_horizon_months": horizon_months,
            "forecast": forecast,
        }

    # LSTM continuation simulation - ensure shapes are correct for model
    preds = []
    # create a seed; ideally you'd use last known sequence from training, here we use small random seed
    last_seq = np.random.random((3, 1))
    for _ in range(horizon_months):
        next_pred = lstm_model.predict(last_seq.reshape(1, 3, 1), verbose=0)
        preds.append(next_pred[0][0])
        last_seq = np.append(last_seq[1:], next_pred).reshape(3, 1)

    try:
        forecast_lstm = scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()
    except Exception:
        forecast_lstm = np.array(preds)

    hybrid_len = min(len(yhat_values), len(forecast_lstm))
    hybrid_forecast = 0.6 * yhat_values[-hybrid_len:] + 0.4 * forecast_lstm[-hybrid_len:]

    forecast = [
        {"date": str(forecast_prophet["ds"].iloc[i].date()), "predicted_aqi": float(hybrid_forecast[i])}
        for i in range(hybrid_len)
    ]

    return {
        "city": city,
        "model_used": "Prophet + LSTM Hybrid",
        "forecast_horizon_months": horizon_months,
        "prophet_model": prophet_fname,
        "lstm_model": lstm_fname,
        "forecast_count": len(forecast),
        "forecast": forecast,
    }
