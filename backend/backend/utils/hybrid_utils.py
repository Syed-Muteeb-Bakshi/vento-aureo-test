# backend/backend/utils/hybrid_utils.py
import os
import re
import unicodedata
import numpy as np
import pandas as pd

from model_loader import load_model  # use the universal loader

# ============================================================
# FIXED PATHS
# ============================================================
MODEL_ROOT = os.environ.get("MODEL_DIR", "models")
PROPHET_DIR = os.path.join(MODEL_ROOT, "hybrid_models", "prophet_models")
LSTM_DIR = os.path.join(MODEL_ROOT, "hybrid_models", "lstm_models")
HYBRID_OUTPUT_DIR = os.path.join(MODEL_ROOT, "hybrid_models", "outputs")

def _normalize_name(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'[^0-9a-z]+', '', s.lower())
    return s

def load_prophet_model_for_city(city: str):
    import difflib

    city_raw = city
    city = re.sub(r"[,._]+", " ", city.strip())
    city_tokens = city.split()
    drop_words = {
        "india","united","states","usa","england","uk","spain","france","germany",
        "italy","china","japan","korea","russia","canada","australia","brazil",
        "mexico","indonesia","turkey","argentina","south","africa","saudi",
        "arabia","emirates","uae"
    }
    city_tokens = [t for t in city_tokens if t.lower() not in drop_words]
    city_core = " ".join(city_tokens[:3])
    city_norm = _normalize_name(city_core)

    if not os.path.isdir(PROPHET_DIR):
        # don't fail immediately — loader can still fetch from Supabase but we check file listing here
        file_list = []
    else:
        file_list = [f for f in os.listdir(PROPHET_DIR) if f.endswith(".joblib")]

    # If local list is empty, we still attempt to fetch using loader by trying common filename patterns.
    # Try direct filename
    candidates = []
    for fname in file_list:
        name_only = os.path.splitext(fname)[0]
        norm = _normalize_name(name_only)
        if city_norm in norm or norm in city_norm:
            candidates.append(fname)
        else:
            if any(tok in norm for tok in city_norm.split()):
                candidates.append(fname)

    if candidates:
        candidates.sort(key=lambda f: abs(len(_normalize_name(f)) - len(city_norm)))
        best = candidates[0]
        try:
            model, used = load_model(best, subfolder="hybrid_models/prophet_models"), best
            return model, best
        except Exception:
            pass

    # Try fuzzy matching based on expected filename
    target_filename = f"{city_core.replace(' ', '_')}_prophet.joblib"
    try:
        model = load_model(target_filename, subfolder="hybrid_models/prophet_models")
        return model, target_filename
    except Exception:
        pass

    # Try top-level prophet_models
    try:
        model = load_model(f"{city_core.replace(' ', '_')}_prophet.joblib", subfolder="prophet_models")
        return model, f"prophet_models/{city_core.replace(' ', '_')}_prophet.joblib"
    except Exception:
        pass

    # Fuzzy supabase/local fallback: try common small normalization list
    raise FileNotFoundError(f"No Prophet model found for '{city_raw}'")

def load_lstm_model_for_city(city: str):
    city_norm = _normalize_name(city)
    # Attempt to load exact
    # LSTM filenames are usually "City.keras" or similar
    # Try a few patterns:
    patterns = [
        f"{city.replace(' ', '_')}.keras",
        f"{city.replace(' ', '_')}.h5",
        f"{city.replace(' ', '_')}.hdf5"
    ]
    for p in patterns:
        try:
            model = load_model(p, subfolder="hybrid_models/lstm_models")
            # attempt to also load a scaler if present
            scaler_name = p.replace(".keras", "_scaler.joblib").replace(".h5", "_scaler.joblib")
            scaler = None
            try:
                scaler = load_model(scaler_name, subfolder="hybrid_models/lstm_models")
            except Exception:
                scaler = None
            return model, scaler, p
        except Exception:
            continue

    # Last attempt: list local LSTM dir entries and pick fuzzy match
    if os.path.isdir(LSTM_DIR):
        for f in os.listdir(LSTM_DIR):
            if f.endswith((".keras", ".h5")) and city_norm in _normalize_name(f):
                try:
                    model = load_model(f, subfolder="hybrid_models/lstm_models")
                    scaler = None
                    try:
                        sname = f + "_scaler.joblib"
                        scaler = load_model(sname, subfolder="hybrid_models/lstm_models")
                    except Exception:
                        scaler = None
                    return model, scaler, f
                except Exception:
                    continue

    return None, None, None

def generate_hybrid_forecast(city: str, horizon_months: int = 24):
    from datetime import datetime
    start_date = datetime.now()
    try:
        prophet_model, prophet_fname = load_prophet_model_for_city(city)
    except FileNotFoundError as e:
        return {"error": str(e)}

    lstm_model, scaler, lstm_fname = load_lstm_model_for_city(city)

    future_dates = pd.date_range(start=start_date, periods=horizon_months, freq="M")
    future = pd.DataFrame({"ds": future_dates})

    try:
        forecast_prophet = prophet_model.predict(future)
    except Exception as e:
        return {"error": f"Prophet forecast failed for {city}: {e}"}

    if forecast_prophet.empty or "yhat" not in forecast_prophet.columns:
        return {"error": f"Prophet model for {city} returned no predictions."}

    yhat_values = forecast_prophet["yhat"].values

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

    preds = []
    last_seq = np.random.random((3, 1))
    for _ in range(horizon_months):
        next_pred = lstm_model.predict(last_seq.reshape(1, 3, 1), verbose=0)
        preds.append(next_pred[0][0])
        last_seq = np.append(last_seq[1:], next_pred).reshape(3, 1)

    forecast_lstm = scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()
    hybrid_len = min(len(yhat_values), len(forecast_lstm))
    hybrid_forecast = 0.6 * yhat_values[-hybrid_len:] + 0.4 * forecast_lstm[-hybrid_len:]

    forecast = [
        {"date": str(future["ds"].iloc[i].date()), "predicted_aqi": float(hybrid_forecast[i])}
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
