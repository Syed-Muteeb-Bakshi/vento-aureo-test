# ============================================================
# backend/backend/utils/hybrid_utils.py
# (Final fixed version — forecasts forward from now)
# ============================================================
import os
import re
import unicodedata
import joblib
import numpy as np
import pandas as pd

# Lazy import TensorFlow only when needed (saves memory on Render)
def _lazy_load_keras():
    from tensorflow.keras import models
    return models

# ============================================================
# FIXED PATHS (CLOUD SAFE, RENDER SAFE, LOCAL SAFE)
# ============================================================

# Universal model root passed via environment variable (MODEL_DIR=models)
MODEL_ROOT = os.environ.get("MODEL_DIR", "models")

# Subfolders under backend/backend/models/
PROPHET_DIR = os.path.join(MODEL_ROOT, "hybrid_models", "prophet_models")
LSTM_DIR = os.path.join(MODEL_ROOT, "hybrid_models", "lstm_models")

# If hybrid output folder exists:
HYBRID_OUTPUT_DIR = os.path.join(MODEL_ROOT, "hybrid_models", "outputs")

# ============================================================
# Normalization helper
# ============================================================
def _normalize_name(s: str) -> str:
    """Normalize names for fuzzy matching."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'[^0-9a-z]+', '', s.lower())
    return s


# ============================================================
# Prophet Loader (fuzzy matching)
# ============================================================
def load_prophet_model_for_city(city: str):
    """
    Load the Prophet model matching a given city name.
    Handles fuzzy matches, diacritics, punctuation, and extra country words.
    """

    import difflib

    # ---- Normalize city ----
    city_raw = city
    city = re.sub(r"[,._]+", " ", city.strip())
    city_tokens = city.split()
    # Remove very common country / region words
    drop_words = {
        "india","united","states","usa","england","uk","spain","france","germany",
        "italy","china","japan","korea","russia","canada","australia","brazil",
        "mexico","indonesia","turkey","argentina","south","africa","saudi",
        "arabia","emirates","uae"
    }
    city_tokens = [t for t in city_tokens if t.lower() not in drop_words]
    city_core = " ".join(city_tokens[:3])  # keep up to 3 words
    city_norm = _normalize_name(city_core)

    if not os.path.isdir(PROPHET_DIR):
        raise FileNotFoundError(f"Prophet directory not found: {PROPHET_DIR}")

    all_files = [f for f in os.listdir(PROPHET_DIR) if f.endswith(".joblib")]
    if not all_files:
        raise FileNotFoundError(f"No Prophet model files in {PROPHET_DIR}")

    # ---- Try direct / substring / token matches ----
    candidates = []
    for fname in all_files:
        name_only = os.path.splitext(fname)[0]
        norm = _normalize_name(name_only)
        if city_norm in norm or norm in city_norm:
            candidates.append(fname)
        else:
            # Token overlap check (e.g., 'losangeles' vs 'angeles')
            if any(tok in norm for tok in city_norm.split()):
                candidates.append(fname)

    if candidates:
        # Prefer closest string length difference
        candidates.sort(key=lambda f: abs(len(_normalize_name(f)) - len(city_norm)))
        best_match = candidates[0]
        model_path = os.path.join(PROPHET_DIR, best_match)
        print(f"[INFO] Prophet match → '{city_raw}' → '{best_match}'")
        return joblib.load(model_path), best_match

    # ---- Fallback: similarity ratio ----
    norm_list = [_normalize_name(os.path.splitext(f)[0]) for f in all_files]
    closest = difflib.get_close_matches(city_norm, norm_list, n=1, cutoff=0.4)
    if closest:
        idx = norm_list.index(closest[0])
        best_match = all_files[idx]
        model_path = os.path.join(PROPHET_DIR, best_match)
        print(f"[WARN] Fuzzy fallback → '{city_raw}' ≈ '{best_match}'")
        return joblib.load(model_path), best_match

    # ---- If nothing at all ----
    raise FileNotFoundError(
        f"No Prophet model found for '{city_raw}' in {PROPHET_DIR}. "
        f"({len(all_files)} models checked)"
    )

# ============================================================
# LSTM Loader (optional)
# ============================================================
def load_lstm_model_for_city(city: str):
    city_norm = _normalize_name(city)
    if not os.path.isdir(LSTM_DIR):
        return None, None, None

    all_files = os.listdir(LSTM_DIR)
    lstm_candidates = [f for f in all_files if f.endswith(".keras") and city_norm in _normalize_name(f)]
    scaler_candidates = [f for f in all_files if f.endswith("_scaler.joblib") and city_norm in _normalize_name(f)]

    if not lstm_candidates:
        return None, None, None

    lstm_path = os.path.join(LSTM_DIR, lstm_candidates[0])
    _models = _lazy_load_keras()
    lstm_model = _models.load_model(lstm_path)

    scaler = None
    if scaler_candidates:
        scaler_path = os.path.join(LSTM_DIR, scaler_candidates[0])
        if os.path.exists(scaler_path):
            scaler = joblib.load(scaler_path)

    return lstm_model, scaler, lstm_candidates[0]


# ============================================================
# Main Function: Generate Hybrid Forecast (updated)
# ============================================================
def generate_hybrid_forecast(city: str, horizon_months: int = 24):
    """
    Generate AQI forecasts using Prophet + LSTM hybrid model.
    Forecasts forward from the current date (not the training cutoff).
    """

    from datetime import datetime
    from dateutil.relativedelta import relativedelta

    # --- Step 1: Load Prophet model ---
    try:
        prophet_model, prophet_fname = load_prophet_model_for_city(city)
    except FileNotFoundError as e:
        return {"error": str(e)}

    # --- Step 2: Load LSTM model (optional) ---
    try:
        lstm_model, scaler, lstm_fname = load_lstm_model_for_city(city)
    except FileNotFoundError:
        lstm_model, scaler, lstm_fname = None, None, None

    # ✅ Forecast forward from *now* instead of training end
    start_date = datetime.now()
    future_dates = pd.date_range(start=start_date, periods=horizon_months, freq="M")
    future = pd.DataFrame({"ds": future_dates})

    # Prophet forecast
    try:
        forecast_prophet = prophet_model.predict(future)
    except Exception as e:
        return {"error": f"Prophet forecast failed for {city}: {e}"}

    if forecast_prophet.empty or "yhat" not in forecast_prophet.columns:
        return {"error": f"Prophet model for {city} returned no predictions."}

    yhat_values = forecast_prophet["yhat"].values

    # --- Step 3: Prophet-only fallback ---
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

    # --- Step 4: LSTM continuation ---
    preds = []
    last_seq = np.random.random((3, 1))
    for _ in range(horizon_months):
        next_pred = lstm_model.predict(last_seq.reshape(1, 3, 1), verbose=0)
        preds.append(next_pred[0][0])
        last_seq = np.append(last_seq[1:], next_pred).reshape(3, 1)

    forecast_lstm = scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()

    # --- Step 5: Combine Hybrid ---
    hybrid_len = min(len(yhat_values), len(forecast_lstm))
    hybrid_forecast = 0.6 * yhat_values[-hybrid_len:] + 0.4 * forecast_lstm[-hybrid_len:]

    # --- Step 6: Format JSON Output ---
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
