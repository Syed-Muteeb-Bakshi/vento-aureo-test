# backend/backend/utils/hybrid_utils.py
import os
import re
import unicodedata
import numpy as np
import pandas as pd
import joblib
import requests

from model_loader import load_model  # load_model(filename, folder)
from tensorflow import keras as _keras  # used only if needed

# Universal model root passed via environment variable (MODEL_DIR=models)
MODEL_ROOT = os.environ.get("MODEL_DIR", "models")

PROPHET_DIR_LOCAL = os.path.join(MODEL_ROOT, "hybrid_models", "prophet_models")
LSTM_DIR_LOCAL = os.path.join(MODEL_ROOT, "hybrid_models", "lstm_models")
HYBRID_OUTPUT_DIR = os.path.join(MODEL_ROOT, "hybrid_models", "outputs")

SUPABASE_PUBLIC_URL = os.environ.get("SUPABASE_PUBLIC_URL")

def _normalize_name(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'[^0-9a-z]+', '', s.lower())
    return s

def _list_prophet_files():
    """Return a list of prophet joblib filenames (basename only). Try local first, then Supabase listing."""
    files = []
    # Local
    if os.path.isdir(PROPHET_DIR_LOCAL):
        try:
            files = [f for f in os.listdir(PROPHET_DIR_LOCAL) if f.endswith(".joblib")]
            if files:
                return files
        except Exception:
            pass

    # Supabase listing (best-effort)
    if SUPABASE_PUBLIC_URL:
        # many Supabase projects support 'list' with ?prefix=<folder>
        for prefix in ["hybrid_models/prophet_models", "prophet_models"]:
            try:
                url = f"{SUPABASE_PUBLIC_URL}?prefix={prefix}"
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        for obj in data:
                            name = obj.get("name") or obj.get("Key") or obj.get("key")
                            if name and name.endswith("_prophet.joblib"):
                                files.append(name.split("/")[-1])
                # continue to next prefix
            except Exception:
                continue
    return list(set(files))

def load_prophet_model_for_city(city: str):
    import difflib

    city_raw = city
    city = re.sub(r"[,._]+", " ", city.strip())
    city_tokens = city.split()
    drop_words = {"india","united","states","usa","england","uk","spain","france","germany","italy","china","japan","korea","russia","canada","australia","brazil","mexico","indonesia","turkey","argentina","south","africa","saudi","arabia","emirates","uae"}
    city_tokens = [t for t in city_tokens if t.lower() not in drop_words]
    city_core = " ".join(city_tokens[:3])
    city_norm = _normalize_name(city_core)

    all_files = _list_prophet_files()
    if not all_files:
        raise FileNotFoundError(f"No Prophet model files discovered (checked local and Supabase).")

    # candidate matching
    candidates = []
    for fname in all_files:
        name_only = os.path.splitext(fname)[0]
        norm = _normalize_name(name_only)
        if city_norm in norm or norm in city_norm:
            candidates.append(fname)
        else:
            if any(tok in norm for tok in city_norm.split()):
                candidates.append(fname)

    if candidates:
        candidates.sort(key=lambda f: abs(len(_normalize_name(os.path.splitext(f)[0])) - len(city_norm)))
        best_match = candidates[0]
        # Try loading from hybrid subfolder first then top-level
        for folder in ["hybrid_models/prophet_models", "prophet_models"]:
            try:
                model = load_model(best_match, folder)
                return model, best_match
            except Exception:
                continue
        # if none loaded:
        raise FileNotFoundError(f"Found match name '{best_match}' but failed to load the file from remote/local")

    # fallback: closest similarity
    norm_list = [_normalize_name(os.path.splitext(f)[0]) for f in all_files]
    closest = difflib.get_close_matches(city_norm, norm_list, n=1, cutoff=0.4)
    if closest:
        idx = norm_list.index(closest[0])
        best_match = all_files[idx]
        for folder in ["hybrid_models/prophet_models", "prophet_models"]:
            try:
                model = load_model(best_match, folder)
                return model, best_match
            except Exception:
                continue
        raise FileNotFoundError(f"Closest match '{best_match}' found but could not be loaded.")

    raise FileNotFoundError(f"No Prophet model found for '{city}' after checking {len(all_files)} files.")

def load_lstm_model_for_city(city: str):
    """Try to load an LSTM keras model and its scaler from folder hybrid_models/lstm_models"""
    city_norm = _normalize_name(city)
    # Try local listing first
    if os.path.isdir(LSTM_DIR_LOCAL):
        files = os.listdir(LSTM_DIR_LOCAL)
    else:
        # Could attempt Supabase listing but we will rely on loader to fetch directly if exact filename known
        files = []

    lstm_candidates = [f for f in files if f.endswith(".keras") and city_norm in _normalize_name(f)]
    scaler_candidates = [f for f in files if f.endswith("_scaler.joblib") and city_norm in _normalize_name(f)]

    if not lstm_candidates:
        # fallback: attempt to load a canonical name from Supabase using loader
        # Construct expected filename pattern -> try downloading by prefix (best-effort)
        # NOTE: If you have exact filenames in Supabase, load_model will fetch them when requested by caller.
        return None, None, None

    # Load first candidate found
    lstm_fname = lstm_candidates[0]
    try:
        lstm_model = load_model(lstm_fname, "hybrid_models/lstm_models")
    except Exception:
        return None, None, None

    scaler = None
    if scaler_candidates:
        scaler_fname = scaler_candidates[0]
        try:
            scaler = load_model(scaler_fname, "hybrid_models/lstm_models")
        except Exception:
            scaler = None

    return lstm_model, scaler, lstm_fname

def generate_hybrid_forecast(city: str, horizon_months: int = 24):
    from datetime import datetime

    # Step 1: load prophet
    try:
        prophet_model, prophet_fname = load_prophet_model_for_city(city)
    except FileNotFoundError as e:
        return {"error": str(e)}

    # Step 2: optional lstm
    try:
        lstm_model, scaler, lstm_fname = load_lstm_model_for_city(city)
    except Exception:
        lstm_model, scaler, lstm_fname = None, None, None

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

    # LSTM continuation
    preds = []
    last_seq = np.random.random((3, 1))
    for _ in range(horizon_months):
        next_pred = lstm_model.predict(last_seq.reshape(1, 3, 1), verbose=0)
        preds.append(next_pred[0][0])
        last_seq = np.append(last_seq[1:], next_pred).reshape(3, 1)

    try:
        forecast_lstm = scaler.inverse_transform(np.array(preds).reshape(-1, 1)).flatten()
    except Exception:
        # fallback: use raw preds
        forecast_lstm = np.array(preds).flatten()

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
